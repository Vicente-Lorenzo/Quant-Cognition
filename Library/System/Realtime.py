from __future__ import annotations

import os
import sys
import zmq
import json
import ctypes
import tempfile
import threading
import contextlib

from datetime import datetime
from typing import Type, Union, TYPE_CHECKING

from Library.Database.Database import DatabaseAPI
from Library.Database.Dataframe import pl
from Library.Database.Postgres.Postgres import PostgresAPI
from Library.Engine import MachineAPI
from Library.Indicator.Indicator import IndicatorAPI
from Library.Market.Bar import BarAPI
from Library.Market.Market import MarketAPI
from Library.Market.Price import Direction
from Library.Market.Tick import TickAPI
from Library.Portfolio.Account import AccountAPI, AccountType, MarginMode
from Library.Portfolio.Order import OrderAPI, OrderStatus, OrderType, TimeInForce
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionAPI, ActionID
from Library.Protocol.Update import UpdateID, BarUpdateAPI, CompleteUpdateAPI
from Library.System.System import SystemAPI, SystemType
from Library.Universe.Security import SecurityAPI
from Library.Utility.DateTime import timestamp_to_datetime
from Library.Utility.Statistic import Timer, timer

if TYPE_CHECKING:
    from Library.Parameter import Parameter
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Timeframe import TimeframeAPI

class RealtimeAPI(SystemAPI):

    def __init__(self,
                 system: SystemType,
                 strategy: Type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 parameters: Parameter,
                 pid: int,
                 iid: str,
                 database: Union[str, None],
                 market: tuple[int, float],
                 portfolio: tuple[int, float],
                 host: str = "localhost",
                 port: int = 5555) -> None:
        if database is None:
            market = (0, 0.0)
            portfolio = (0, 0.0)
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, parameters=parameters, market=market, portfolio=portfolio)

        self._system_: SystemType = system
        self._pid_: int = pid
        self._iid_: str = iid
        self._database_: Union[str, None] = database
        self._host_: str = host
        self._port_: int = port
        self._pid_file_: str = os.path.join(tempfile.gettempdir(), f"cAlgo_{iid}.pid")

        self._context_ = None
        self._socket_ = None
        self._db_: Union[DatabaseAPI, None] = None
        self._stack_: Union[contextlib.ExitStack, None] = None

        self._sync_buffer_: list[BarAPI] = []
        self._initial_account_: Union[AccountAPI, None] = None
        self._start_timestamp_: Union[datetime, None] = None
        self._stop_timestamp_: Union[datetime, None] = None
        self._last_update_msg_: dict = {}

        self._metrics_: dict = {"Ticks": 0, "Bars": 0, "Accounts": 0, "Orders": 0, "Positions": 0, "Trades": 0, "Actions": 0}
        self._warmup_timer_: Timer = Timer()
        self._execution_timer_: Timer = Timer()
        self._shutdown_timer_: Timer = Timer()

    def __enter__(self):
        with open(self._pid_file_, "w") as f: f.write(str(os.getpid()))
        stack = contextlib.ExitStack()
        stack.__enter__()
        self._stack_ = stack
        self._stack_.callback(lambda: os.path.exists(self._pid_file_) and os.remove(self._pid_file_))
        try:
            self.strategy = self._strategy_(money_management=self._parameters_.MoneyManagement, risk_management=self._parameters_.RiskManagement, signal_management=self._parameters_.SignalManagement)
            self.market = MarketAPI()
            self.indicator = IndicatorAPI(technical=self._parameters_.TechnicalManagement, fundamental=self._parameters_.FundamentalManagement, sentimental=self._parameters_.SentimentalManagement)
            self.portfolio = PortfolioAPI(Parameter=self._parameters_.PortfolioManagement)
            self._db_ = None if self._database_ is None else self._stack_.enter_context(PostgresAPI(database=self._database_))
            self._context_ = self._stack_.enter_context(zmq.Context())
            self._socket_ = self._stack_.enter_context(self._context_.socket(zmq.PAIR))
            self._socket_.setsockopt(zmq.LINGER, 0)
            self._socket_.bind(f"tcp://{self._host_}:{self._port_}")
            self._start_peer_watchdog_()
            self._log_.info(lambda: f"Connect Operation: Bound to {self._host_}:{self._port_} (pid={os.getpid()}, ctrader_pid={self._pid_})")
        except Exception as e:
            self._log_.error(lambda: f"Connect Operation: Failed ({e})")
            self._stack_.__exit__(None, None, None)
            raise
        if self._portfolio_.Active:
            self._session_ = SessionAPI(IID=self._iid_, Type=self._system_, Strategy=self._strategy_.__name__, Security=self._security_, StartTimestamp=datetime.now(), db=self._db_)
            self._session_.save()
        self._warmup_timer_.start()
        return super().__enter__()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self._execution_timer_._start_ is not None and self._execution_timer_._stop_ is None:
            self._execution_timer_.stop()
        self._shutdown_timer_.start()
        if self._portfolio_.Active and self._session_ is not None:
            self._session_.StopTimestamp = datetime.now()
            if not self._portfolio_.Empty: self._portfolio_.flush()
            if self.account is not None and self.account.UID is not None:
                self._session_.FinalAccount = self.account
            self._session_.save()
        result = super().__exit__(exc_type, exc_value, exc_traceback)
        if self._stack_: self._stack_.__exit__(exc_type, exc_value, exc_traceback)
        self._shutdown_timer_.stop()
        self._log_metrics_()
        self._log_.info(lambda: f"Disconnect Operation: Closed {self._host_}:{self._port_}")
        return result

    def _log_metrics_(self) -> None:
        m = self._metrics_
        warmup = self._warmup_timer_.result() if self._warmup_timer_._stop_ else "N/A"
        execution = self._execution_timer_.result() if self._execution_timer_._stop_ else "N/A"
        shutdown = self._shutdown_timer_.result() if self._shutdown_timer_._stop_ else "N/A"
        exec_delta = self._execution_timer_.delta() if self._execution_timer_._stop_ else 0.0
        bars_per_sec = (m["Bars"] / exec_delta) if exec_delta > 0 else 0.0
        ticks_per_sec = (m["Ticks"] / exec_delta) if exec_delta > 0 else 0.0
        self._log_.info(lambda: f"Phase Warmup: {warmup}")
        self._log_.info(lambda: f"Phase Execution: {execution} ({ticks_per_sec:.1f} Ticks/s, {bars_per_sec:.1f} Bars/s)")
        self._log_.info(lambda: f"Phase Shutdown: {shutdown}")
        self._log_.info(lambda: f"Summary: " + ", ".join(f"{k}={v}" for k, v in m.items()))

    def _start_peer_watchdog_(self) -> None:
        if self._pid_ is None or sys.platform != "win32": return
        SYNCHRONIZE = 0x00100000
        INFINITE = 0xFFFFFFFF
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(SYNCHRONIZE, False, self._pid_)
        if not handle:
            self._log_.warning(lambda: f"Cannot open cTrader process (pid={self._pid_}); peer-death detection disabled")
            return
        def _watch_():
            kernel32.WaitForSingleObject(handle, INFINITE)
            kernel32.CloseHandle(handle)
            self._log_.error(lambda: f"cTrader process (pid={self._pid_}) exited, terminating ZMQ context")
            try:
                if self._context_ is not None: self._context_.term()
            except Exception: pass
        t = threading.Thread(target=_watch_, name="cTraderWatchdog", daemon=True)
        t.start()

    def send_action(self, action: ActionAPI) -> None:
        try:
            self._socket_.send_string(action.serialize())
            self._metrics_["Actions"] += 1
        except zmq.ContextTerminated:
            raise SystemExit("cTrader peer died during send")

    def _receive_(self) -> dict:
        try:
            msg = self._socket_.recv_string()
        except zmq.ContextTerminated:
            raise SystemExit("cTrader peer died during receive")
        return json.loads(msg)

    def receive_update_id(self) -> UpdateID:
        self._last_update_msg_ = self._receive_()
        return UpdateID(self._last_update_msg_.get("UpdateID", 0))

    def receive_update_account(self) -> AccountAPI:
        content = self._last_update_msg_
        self._metrics_["Accounts"] += 1
        return AccountAPI(
            Timestamp=datetime.now(),
            Number=content.get("AccountNumber"),
            Provider=self._security_.Provider if self._security_ else None,
            AccountType=AccountType(content.get("AccountType")),
            Asset=content.get("AssetType"),
            Balance=content.get("Balance"),
            Equity=content.get("Equity"),
            Credit=content.get("Credit"),
            Leverage=content.get("Leverage"),
            MarginUsed=content.get("MarginUsed"),
            MarginFree=content.get("MarginFree"),
            MarginLevel=content.get("MarginLevel"),
            MarginStopLevel=content.get("MarginStopLevel"),
            MarginMode=MarginMode(content.get("MarginMode")),
            db=self._db_
        )

    def receive_update_security(self) -> SecurityAPI:
        return self._security_

    def receive_update_order(self) -> OrderAPI:
        content = self._last_update_msg_
        self._metrics_["Orders"] += 1
        return OrderAPI(
            UID=content.get("OrderID"),
            Position=content.get("PositionID"),
            OrderType=OrderType(content.get("OrderType")) if content.get("OrderType") is not None else None,
            Direction=Direction(content.get("TradeType")),
            OrderStatus=OrderStatus(content.get("OrderStatus")) if content.get("OrderStatus") is not None else None,
            TimeInForce=TimeInForce(content.get("TimeInForce")) if content.get("TimeInForce") is not None else None,
            Volume=content.get("Volume"),
            StopPrice=content.get("StopPrice"),
            LimitPrice=content.get("LimitPrice"),
            StopLossPrice=content.get("StopLoss"),
            TakeProfitPrice=content.get("TakeProfit"),
            db=self._db_
        )

    def receive_update_position(self) -> PositionAPI:
        content = self._last_update_msg_
        self._metrics_["Positions"] += 1
        timestamp = timestamp_to_datetime(content.get("EntryTimestamp"), milliseconds=True)
        return PositionAPI(
            UID=content.get("PositionID"),
            Type=PositionType[content.get("PositionType")] if content.get("PositionType") in PositionType.__members__ else PositionType.Normal,
            Direction=Direction(content.get("TradeType")),
            EntryTimestamp=timestamp,
            EntryPrice=content.get("EntryPrice"),
            Volume=content.get("Volume"),
            Quantity=content.get("Quantity"),
            GrossPnL=content.get("GrossPnL"),
            CommissionPnL=content.get("CommissionPnL"),
            SwapPnL=content.get("SwapPnL"),
            NetPnL=content.get("NetPnL"),
            UsedMargin=content.get("UsedMargin"),
            StopLossPrice=content.get("StopLoss"),
            TakeProfitPrice=content.get("TakeProfit"),
            db=self._db_
        )

    def receive_update_trade(self) -> TradeAPI:
        content = self._last_update_msg_
        self._metrics_["Trades"] += 1
        entry_timestamp = timestamp_to_datetime(content.get("EntryTimestamp"), milliseconds=True)
        exit_timestamp = timestamp_to_datetime(content.get("ExitTimestamp"), milliseconds=True)
        return TradeAPI(
            Position=content.get("PositionID"),
            UID=content.get("TradeID"),
            Type=PositionType[content.get("PositionType")] if content.get("PositionType") in PositionType.__members__ else PositionType.Normal,
            Direction=Direction(content.get("TradeType")),
            EntryTimestamp=entry_timestamp,
            ExitTimestamp=exit_timestamp,
            EntryPrice=content.get("EntryPrice"),
            ExitPrice=content.get("ExitPrice"),
            Volume=content.get("Volume"),
            Quantity=content.get("Quantity"),
            GrossPnL=content.get("GrossPnL"),
            CommissionPnL=content.get("CommissionPnL"),
            SwapPnL=content.get("SwapPnL"),
            NetPnL=content.get("NetPnL"),
            db=self._db_
        )

    def receive_update_bar(self) -> BarAPI:
        content = self._last_update_msg_
        self._metrics_["Ticks"] += 5
        self._metrics_["Bars"] += 1
        timestamp = timestamp_to_datetime(content.get("Timestamp"), milliseconds=True)
        gap_tick = TickAPI(Security=self._security_, Timestamp=timestamp_to_datetime(content.get("GapTimestamp"), milliseconds=True), Ask=content.get("GapAsk"), Bid=content.get("GapBid"), AskBaseConversion=content.get("GapAskBaseConversion"), BidBaseConversion=content.get("GapBidBaseConversion"), AskQuoteConversion=content.get("GapAskQuoteConversion"), BidQuoteConversion=content.get("GapBidQuoteConversion"), Volume=content.get("GapVolume"), db=self._db_)
        open_tick = TickAPI(Security=self._security_, Timestamp=timestamp_to_datetime(content.get("OpenTimestamp"), milliseconds=True), Ask=content.get("OpenAsk"), Bid=content.get("OpenBid"), AskBaseConversion=content.get("OpenAskBaseConversion"), BidBaseConversion=content.get("OpenBidBaseConversion"), AskQuoteConversion=content.get("OpenAskQuoteConversion"), BidQuoteConversion=content.get("OpenBidQuoteConversion"), Volume=content.get("OpenVolume"), db=self._db_)
        high_tick = TickAPI(Security=self._security_, Timestamp=timestamp_to_datetime(content.get("HighTimestamp"), milliseconds=True), Ask=content.get("HighAsk"), Bid=content.get("HighBid"), AskBaseConversion=content.get("HighAskBaseConversion"), BidBaseConversion=content.get("HighBidBaseConversion"), AskQuoteConversion=content.get("HighAskQuoteConversion"), BidQuoteConversion=content.get("HighBidQuoteConversion"), Volume=content.get("HighVolume"), db=self._db_)
        low_tick = TickAPI(Security=self._security_, Timestamp=timestamp_to_datetime(content.get("LowTimestamp"), milliseconds=True), Ask=content.get("LowAsk"), Bid=content.get("LowBid"), AskBaseConversion=content.get("LowAskBaseConversion"), BidBaseConversion=content.get("LowBidBaseConversion"), AskQuoteConversion=content.get("LowAskQuoteConversion"), BidQuoteConversion=content.get("LowBidQuoteConversion"), Volume=content.get("LowVolume"), db=self._db_)
        close_tick = TickAPI(Security=self._security_, Timestamp=timestamp_to_datetime(content.get("CloseTimestamp"), milliseconds=True), Ask=content.get("CloseAsk"), Bid=content.get("CloseBid"), AskBaseConversion=content.get("CloseAskBaseConversion"), BidBaseConversion=content.get("CloseBidBaseConversion"), AskQuoteConversion=content.get("CloseAskQuoteConversion"), BidQuoteConversion=content.get("CloseBidQuoteConversion"), Volume=content.get("CloseVolume"), db=self._db_)
        return BarAPI(
            Security=self._security_,
            Timeframe=self._timeframe_,
            Timestamp=timestamp,
            GapTick=gap_tick,
            OpenTick=open_tick,
            HighTick=high_tick,
            LowTick=low_tick,
            CloseTick=close_tick,
            Volume=content.get("Volume"),
            db=self._db_
        )

    def receive_update_target(self) -> TickAPI:
        content = self._last_update_msg_
        self._metrics_["Ticks"] += 1
        timestamp = timestamp_to_datetime(content.get("Timestamp"), milliseconds=True)
        return TickAPI(
            Security=self._security_,
            Timestamp=timestamp,
            Ask=content.get("Ask"),
            Bid=content.get("Bid"),
            AskBaseConversion=content.get("AskBaseConversion"),
            BidBaseConversion=content.get("BidBaseConversion"),
            AskQuoteConversion=content.get("AskQuoteConversion"),
            BidQuoteConversion=content.get("BidQuoteConversion"),
            Volume=content.get("Volume"),
            db=self._db_
        )

    def receive_update_denied(self) -> tuple[ActionID, str]:
        content = self._last_update_msg_
        return ActionID(content.get("ActionID")), content.get("Reason", "")

    def receive_update_exception(self) -> str:
        content = self._last_update_msg_
        return content.get("Reason", "")

    def system_management(self) -> MachineAPI:
        system_engine = MachineAPI(Name="System Management", Events=len(UpdateID))

        initialisation = system_engine.state(name="Initialisation")
        execution = system_engine.state(name="Execution")
        termination = system_engine.state(name="Termination", end=True)

        def sync_market(update: BarUpdateAPI):
            self._market_.add(update.Bar.GapTick)
            self._market_.add(update.Bar.OpenTick)
            self._market_.add(update.Bar.HighTick)
            self._market_.add(update.Bar.LowTick)
            self._market_.add(update.Bar.CloseTick)
            self._market_.add(update.Bar)
            self._sync_buffer_.append(update.Bar)

        def init_market(update: CompleteUpdateAPI):
            if self._warmup_timer_._start_ is not None:
                self._warmup_timer_.stop()
                self._log_.info(lambda: f"Phase Warmup: completed ({self._warmup_timer_.result()}, {self._metrics_['Ticks']} Ticks, {self._metrics_['Bars']} Bars)")
            self._execution_timer_.start()
            self._initial_account_ = update.Portfolio.Account
            if not self._sync_buffer_: return
            self._start_timestamp_ = self._sync_buffer_[-1].Timestamp.DateTime
            df = pl.DataFrame([b.dict() for b in self._sync_buffer_])
            update.Market.init_data(df)
            self._sync_buffer_.clear()

        def update_market(update: BarUpdateAPI):
            self._stop_timestamp_ = update.Bar.Timestamp.DateTime
            update.Market.update_data(update.Bar)

        def report_statistics(update: CompleteUpdateAPI):
            from Library.Portfolio.Statistic import generate_net_report
            if self._execution_timer_._start_ is not None and self._execution_timer_._stop_ is None:
                self._execution_timer_.stop()
                self._log_.info(lambda: f"Phase Execution: completed ({self._execution_timer_.result()})")
            if self.portfolio and self.portfolio.Security: self.portfolio.Security.save()
            if self._initial_account_ and self._start_timestamp_ and self._stop_timestamp_:
                self.statistics = generate_net_report(update.Portfolio.Positions, update.Portfolio.Trades, self._initial_account_, self._start_timestamp_.date(), self._stop_timestamp_.date())
                self._log_.warning(lambda: str(self.statistics))

        initialisation.on(event=UpdateID.BarClosed, to=initialisation, action=sync_market, reason=None)
        initialisation.on(event=UpdateID.Complete, to=execution, action=init_market, reason="Market Initialized")
        initialisation.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

        execution.on(event=UpdateID.BarClosed, to=execution, action=update_market, reason=None)
        execution.on(event=UpdateID.Shutdown, to=termination, action=report_statistics, reason="Safely Terminated")

        return system_engine

    @timer
    def run(self) -> None:
        self.deploy()