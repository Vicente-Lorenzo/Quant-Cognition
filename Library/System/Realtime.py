from __future__ import annotations

import os
import struct
import contextlib

from datetime import datetime, timedelta
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
from Library.Portfolio.Order import OrderAPI, OrderType
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionAPI, ActionID, InitActionAPI, ExecutionActionAPI
from Library.Protocol.Binary import BinaryAPI
from Library.Protocol.Update import UpdateID, CompleteUpdateAPI, InitUpdateAPI, BarUpdateAPI
from Library.System.System import SystemAPI, SystemType
from Library.Protocol.Transport import TransportAPI
from Library.Universe.Contract import CommissionMode, SwapMode
from Library.Universe.Security import SecurityAPI
from Library.Utility.DateTime import Weekday, timestamp_to_datetime
from Library.Utility.Statistic import Timer, timer

if TYPE_CHECKING:
    from Library.Parameter import Parameter
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Timeframe import TimeframeAPI

_MARKET_CLOSURE_ = timedelta(days=4)

class RealtimeAPI(SystemAPI):

    _DIRECTION_ = {0: Direction.Buy, 1: Direction.Sell}
    _ORDER_TYPE_ = {0: OrderType.Limit, 1: OrderType.Stop, 2: OrderType.StopLimit}  # cTrader PendingOrderType: Limit=0, Stop=1, StopLimit=2

    _binary_init_ = BinaryAPI('i')
    _binary_denied_ = BinaryAPI('B', 's')
    _binary_exception_ = BinaryAPI('s')

    _binary_account_ = BinaryAPI('s', 's', 'B', 's', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'B')
    _binary_security_ = BinaryAPI('s', 's', 'i', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'B', 'd', 'd', 'B', 'i')
    
    _binary_tick_ = BinaryAPI('q', 'd', 'd', 'd', 'd', 'd', 'd', 'd')

    _binary_order_ = BinaryAPI('i', 'B', 'B', 'd', 'd', 'D', 'D', 'q', 's')
    _binary_position_ = BinaryAPI('i', 'B', 'B', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'D', 'D', 's')
    _binary_trade_ = BinaryAPI('i', 'i', 'B', 'B', 'q', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 's')

    _bar_payload_ = 1 + 8 + 5 * _binary_tick_._size_ + 8

    def __init__(self,
                 system: SystemType,
                 strategy: Type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 parameters: Parameter,
                 iid: str,
                 database: Union[str, None],
                 market: tuple[int, float],
                 portfolio: tuple[int, float],
                 report: bool = True,
                 export: bool = True) -> None:
        if database is None:
            market = (0, 0.0)
            portfolio = (0, 0.0)
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, parameters=parameters, market=market, portfolio=portfolio, report=report, export=export)

        self._system_: SystemType = system
        self._iid_: str = iid
        self._database_: Union[str, None] = database

        self._db_: Union[DatabaseAPI, None] = None
        self._stack_: Union[contextlib.ExitStack, None] = None
        self._transport_: Union[TransportAPI, None] = None
        self._last_update_data_: bytes = b""
        self._exc_info_: tuple = (None, None, None)

        self._sync_buffer_: list[BarAPI] = []
        self._warmup_window_: Union[int, None] = None
        self._warmup_database_: int = 0
        self._warmup_db_timestamps_: list[datetime] = []
        self._warmup_ready_: bool = False
        self._initial_account_: Union[AccountAPI, None] = None
        self._start_timestamp_: Union[datetime, None] = None
        self._stop_timestamp_: Union[datetime, None] = None

        self._metrics_: dict = {"Ticks": 0, "Bars": 0, "Accounts": 0, "Orders": 0, "Positions": 0, "Trades": 0, "Actions": 0}
        self._warmup_timer_: Timer = Timer()
        self._execution_timer_: Timer = Timer()
        self._shutdown_timer_: Timer = Timer()

    def _connect_(self) -> None:
        stack = contextlib.ExitStack()
        stack.__enter__()
        self._stack_ = stack
        try:
            self._transport_ = TransportAPI(iid=self._iid_, create=False)
            self._stack_.callback(lambda: self._transport_.close() if self._transport_ else None)
            self._log_.debug(lambda: f"Connect Operation: Bound Shared Memory (iid {self._iid_})")
            self.strategy = self._strategy_(money_management=self._parameters_.MoneyManagement, risk_management=self._parameters_.RiskManagement, signal_management=self._parameters_.SignalManagement)
            self.market = MarketAPI()
            self.indicator = IndicatorAPI(technical=self._parameters_.TechnicalManagement, fundamental=self._parameters_.FundamentalManagement, sentimental=self._parameters_.SentimentalManagement)
            self.portfolio = PortfolioAPI(Parameter=self._parameters_.PortfolioManagement)
            self._db_ = None if self._database_ is None else self._stack_.enter_context(PostgresAPI(database=self._database_))
        except Exception:
            self._stack_.__exit__(None, None, None)
            raise
        if self._portfolio_.Active:
            self._session_ = SessionAPI(IID=self._iid_, Type=self._system_, Strategy=self._strategy_.__name__, Security=self._security_, StartTimestamp=datetime.now(), db=self._db_)
            self._session_.save()
        self._warmup_timer_.start()
        super()._connect_()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._exc_info_ = (exc_type, exc_value, exc_traceback)
        return super().__exit__(exc_type, exc_value, exc_traceback)

    def _disconnect_(self) -> None:
        if self._execution_timer_._start_ is not None and self._execution_timer_._stop_ is None:
            self._execution_timer_.stop()
        self._shutdown_timer_.start()
        if self._portfolio_.Active and self._session_ is not None:
            self._session_.StopTimestamp = datetime.now()
            if not self._portfolio_.Empty: self._portfolio_.flush()
            if self.account is not None and self.account.UID is not None:
                self._session_.FinalAccount = self.account
            self._session_.save()
        super()._disconnect_()
        if self._stack_: self._stack_.__exit__(*self._exc_info_)
        self._shutdown_timer_.stop()
        self._log_metrics_()
        self._log_.debug(lambda: f"Disconnect Operation: Closed (iid {self._iid_})")

    def _log_metrics_(self) -> None:
        m = self._metrics_
        warmup = self._warmup_timer_.result() if self._warmup_timer_._stop_ else "N/A"
        execution = self._execution_timer_.result() if self._execution_timer_._stop_ else "N/A"
        shutdown = self._shutdown_timer_.result() if self._shutdown_timer_._stop_ else "N/A"
        exec_delta = self._execution_timer_.delta() if self._execution_timer_._stop_ else 0.0
        bars_per_sec = (m["Bars"] / exec_delta) if exec_delta > 0 else 0.0
        ticks_per_sec = (m["Ticks"] / exec_delta) if exec_delta > 0 else 0.0
        self._log_.info(lambda: f"Phase Warmup: {warmup}")
        self._log_.info(lambda: f"Phase Execution: {execution} · {ticks_per_sec:.1f} Ticks/s · {bars_per_sec:.1f} Bars/s")
        self._log_.info(lambda: f"Phase Shutdown: {shutdown}")
        self._log_.info(lambda: "Summary: " + " · ".join(f"{k} {v}" for k, v in m.items()))

    def send_action(self, action: ActionAPI) -> None:
        self._transport_.send(action.serialize())
        self._metrics_["Actions"] += 1

    def _receive_(self) -> bytes:
        return self._transport_.receive()

    def receive_update_id(self) -> UpdateID:
        self._last_update_data_ = self._receive_()
        return UpdateID(self._last_update_data_[0])

    def _receive_update_init_(self, offset: int = 1) -> InitUpdateAPI:
        pid = self._binary_init_.unpack(self._last_update_data_, offset)[0]
        return InitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, ProcessID=pid)

    def receive_update_account(self, offset: int = 1) -> AccountAPI:
        number, environment, account_type, asset, balance, equity, credit, leverage, margin_used, margin_free, margin_level, margin_stop, margin_mode = self._binary_account_.unpack(self._last_update_data_, 1)
        self._metrics_["Accounts"] += 1
        return AccountAPI(
            Timestamp=datetime.now(),
            Number=number,
            Provider=self._security_.Provider if self._security_ else None,
            Environment=environment,
            AccountType=AccountType(account_type),
            Asset=asset,
            Balance=balance, Equity=equity, Credit=credit,
            Leverage=leverage, MarginUsed=margin_used, MarginFree=margin_free,
            MarginLevel=margin_level, MarginStopLevel=margin_stop,
            MarginMode=MarginMode(margin_mode),
            db=self._db_
        )

    def receive_update_security(self, offset: int = 1) -> SecurityAPI:
        (base_asset, quote_asset, digits, tick_size, pip_size, lot_size,
         volume_min, volume_max, volume_step, commission, commission_type,
         swap_long, swap_short, swap_calculation_type, swap_3_days_rollover
        ) = self._binary_security_.unpack(self._last_update_data_, 1)
        day_of_week = {0: Weekday.Sunday, 1: Weekday.Monday, 2: Weekday.Tuesday, 3: Weekday.Wednesday, 4: Weekday.Thursday, 5: Weekday.Friday, 6: Weekday.Saturday}
        if self._security_:
            if self._security_.Ticker:
                self._security_.Ticker.BaseAsset = base_asset
                self._security_.Ticker.QuoteAsset = quote_asset
            if self._security_.Contract:
                self._security_.Contract.Digits = digits
                self._security_.Contract.PointSize = tick_size
                self._security_.Contract.PipSize = pip_size
                self._security_.Contract.LotSize = lot_size
                self._security_.Contract.VolumeMin = volume_min
                self._security_.Contract.VolumeMax = volume_max
                self._security_.Contract.VolumeStep = volume_step
                self._security_.Contract.Commission = commission
                self._security_.Contract.CommissionMode = CommissionMode(commission_type)
                self._security_.Contract.SwapLong = swap_long
                self._security_.Contract.SwapShort = swap_short
                self._security_.Contract.SwapMode = SwapMode(swap_calculation_type)
                self._security_.Contract.SwapExtraDay = day_of_week.get(swap_3_days_rollover, Weekday.Wednesday)
        return self._security_

    def receive_update_order(self, offset: int = _bar_payload_) -> OrderAPI:
        uid, order_type_id, direction_id, volume, target_price, stop_loss, take_profit, expiration_ts, label = self._binary_order_.unpack(self._last_update_data_, offset)
        self._metrics_["Orders"] += 1
        order_type = self._ORDER_TYPE_[order_type_id]
        has_limit = order_type in (OrderType.Limit, OrderType.StopLimit)
        has_stop = order_type in (OrderType.Stop, OrderType.StopLimit)
        return OrderAPI(
            UID=uid,
            Session=self._session_,
            Account=self.account,
            Security=self._security_,
            Direction=self._DIRECTION_[direction_id],
            OrderType=order_type,
            Volume=volume,
            LimitPrice=target_price if has_limit else None,
            StopPrice=target_price if has_stop else None,
            StopLossPrice=stop_loss, TakeProfitPrice=take_profit,
            ExpirationTimestamp=timestamp_to_datetime(expiration_ts, milliseconds=True) if expiration_ts != 0 else None,
            Label=label,
            db=self._db_
        )

    def receive_update_position(self, offset: int = _bar_payload_) -> PositionAPI:
        uid, pos_type_id, direction_id, entry_ts, entry_price, volume, quantity, gross_pnl, commission_pnl, swap_pnl, net_pnl, used_margin, stop_loss, take_profit, label = self._binary_position_.unpack(self._last_update_data_, offset)
        self._metrics_["Positions"] += 1
        pos_type = PositionType(pos_type_id)
        return PositionAPI(
            UID=uid,
            Session=self._session_,
            Account=self.account,
            Security=self._security_,
            Type=pos_type,
            Direction=self._DIRECTION_[direction_id],
            EntryTimestamp=timestamp_to_datetime(entry_ts, milliseconds=True),
            EntryPrice=entry_price, Volume=volume, Quantity=quantity,
            GrossPnL=gross_pnl, CommissionPnL=commission_pnl, SwapPnL=swap_pnl, NetPnL=net_pnl,
            UsedMargin=used_margin, StopLossPrice=stop_loss, TakeProfitPrice=take_profit,
            Label=label, Comment=pos_type.name,
            db=self._db_
        )

    def receive_update_position_trade(self, offset: int = _bar_payload_) -> tuple[PositionAPI, TradeAPI]:
        pos = self.receive_update_position(offset)
        trade_offset = offset + 94 + 2 + (len(pos.Label.encode('utf-8')) if pos.Label else 0)
        trade = self.receive_update_trade(trade_offset)
        return pos, trade

    def receive_update_trade(self, offset: int = 1) -> TradeAPI:
        uid, position_id, pos_type_id, direction_id, entry_ts, exit_ts, entry_price, exit_price, volume, quantity, gross_pnl, commission_pnl, swap_pnl, net_pnl, label = self._binary_trade_.unpack(self._last_update_data_, offset)
        self._metrics_["Trades"] += 1
        pos_type = PositionType(pos_type_id)
        return TradeAPI(
            UID=uid, Position=position_id,
            Session=self._session_,
            Account=self.account,
            Security=self._security_,
            Type=pos_type,
            Direction=self._DIRECTION_[direction_id],
            EntryTimestamp=timestamp_to_datetime(entry_ts, milliseconds=True),
            ExitTimestamp=timestamp_to_datetime(exit_ts, milliseconds=True),
            EntryPrice=entry_price, ExitPrice=exit_price,
            Volume=volume, Quantity=quantity,
            GrossPnL=gross_pnl, CommissionPnL=commission_pnl, SwapPnL=swap_pnl, NetPnL=net_pnl,
            Label=label, Comment=pos_type.name,
            db=self._db_
        )

    def receive_update_tick(self, offset: int = 1) -> TickAPI:
        ts, ask, bid, ask_base, bid_base, ask_quote, bid_quote, volume = self._binary_tick_.unpack(self._last_update_data_, 1)
        self._metrics_["Ticks"] += 1
        return TickAPI(
            Security=self._security_,
            Timestamp=timestamp_to_datetime(ts, milliseconds=True),
            Ask=ask, Bid=bid,
            AskBaseConversion=ask_base, BidBaseConversion=bid_base,
            AskQuoteConversion=ask_quote, BidQuoteConversion=bid_quote,
            Volume=volume, db=self._db_
        )

    def _deserialize_tick_(self, data: bytes, offset: int) -> TickAPI:
        ts, ask, bid, ask_base, bid_base, ask_quote, bid_quote, volume = self._binary_tick_.unpack(data, offset)
        return TickAPI(
            Security=self._security_,
            Timestamp=timestamp_to_datetime(ts, milliseconds=True),
            Ask=ask, Bid=bid,
            AskBaseConversion=ask_base, BidBaseConversion=bid_base,
            AskQuoteConversion=ask_quote, BidQuoteConversion=bid_quote,
            Volume=volume, db=self._db_
        )

    def receive_update_bar(self, offset: int = 1) -> BarAPI:
        data = self._last_update_data_
        bar_ts = struct.unpack_from('<q', data, 1)[0]
        tick_size = self._binary_tick_._size_
        off = 9
        gap = self._deserialize_tick_(data, off); off += tick_size
        opn = self._deserialize_tick_(data, off); off += tick_size
        high = self._deserialize_tick_(data, off); off += tick_size
        low = self._deserialize_tick_(data, off); off += tick_size
        close = self._deserialize_tick_(data, off); off += tick_size
        volume = struct.unpack_from('<d', data, off)[0]
        self._metrics_["Ticks"] += 5
        self._metrics_["Bars"] += 1
        return BarAPI(
            Security=self._security_, Timeframe=self._timeframe_,
            Timestamp=timestamp_to_datetime(bar_ts, milliseconds=True),
            GapTick=gap, OpenTick=opn, HighTick=high, LowTick=low, CloseTick=close,
            Volume=volume, db=self._db_
        )

    def receive_update_denied(self, offset: int = 1) -> tuple[ActionID, str]:
        action_id, reason = self._binary_denied_.unpack(self._last_update_data_, 1)
        return ActionID(action_id), reason or ""

    def receive_update_exception(self, offset: int = 1) -> str:
        (reason,) = self._binary_exception_.unpack(self._last_update_data_, 1)
        return reason or ""

    def _indicator_window_(self) -> int:
        windows = [getattr(self.indicator.Technical, "Window", 0) or 0,
                   getattr(self.indicator.Fundamental, "Window", 0) or 0,
                   getattr(self.indicator.Sentimental, "Window", 0) or 0]
        return max(windows)

    def _warmup_horizon_(self) -> timedelta:
        step = self._timeframe_.Seconds or 0.0
        return timedelta(seconds=step) + _MARKET_CLOSURE_

    def _warmup_database_clean_(self) -> bool:
        database = self._warmup_db_timestamps_
        if self._warmup_window_ is None or not self._sync_buffer_: return False
        if len(database) < self._warmup_window_:
            self._log_.debug(lambda: f"Phase Warmup: Database Insufficient · {len(database)} of {self._warmup_window_} Bars")
            return False
        horizon = self._warmup_horizon_()
        sequence = [*database, self._sync_buffer_[0].Timestamp.DateTime]
        for earlier, later in zip(sequence, sequence[1:]):
            if not earlier < later <= earlier + horizon:
                self._log_.debug(lambda: f"Phase Warmup: Database Discontinuous · After {earlier} Got {later} · Beyond {horizon}")
                return False
        return True

    def system_management(self) -> MachineAPI:
        system_engine = MachineAPI(Name="System Management", Events=len(UpdateID))

        initialization = system_engine.state(name="Initialization")
        execution = system_engine.state(name="Execution")
        termination = system_engine.state(name="Termination", end=True)

        def init(update: InitUpdateAPI):
            self._transport_.watchdog(update.ProcessID)
            self._log_.debug(lambda: f"Handshake Operation: Exchanged PIDs (peer {update.ProcessID} · self {os.getpid()})")
            return [InitActionAPI(ProcessID=os.getpid())]

        def warmup(update: BarUpdateAPI):
            if self._warmup_window_ is None:
                self._warmup_window_ = self._indicator_window_()
                if self._warmup_window_ > 0 and self._db_ is not None and self._security_ is not None and self._security_.UID is not None:
                    frame = MarketAPI.pull_bars(self._db_, self._security_.UID, self._timeframe_.UID, stop=update.Bar.Timestamp.DateTime, limit=self._warmup_window_)
                    self._warmup_db_timestamps_ = frame[str(BarAPI.ID.Timestamp)].to_list() if frame.height else []
                self._log_.debug(lambda: f"Phase Warmup: Started · Window {self._warmup_window_} · Database {len(self._warmup_db_timestamps_)} Bars")
            self._market_.add(update.Bar.GapTick)
            self._market_.add(update.Bar.OpenTick)
            self._market_.add(update.Bar.HighTick)
            self._market_.add(update.Bar.LowTick)
            self._market_.add(update.Bar.CloseTick)
            self._market_.add(update.Bar)
            self._sync_buffer_.append(update.Bar)
            if len(self._sync_buffer_) == 1:
                self._warmup_database_ = self._warmup_window_ if self._warmup_database_clean_() else 0
                if self._warmup_db_timestamps_ and not self._warmup_database_:
                    self._log_.debug(lambda: f"Phase Warmup: Database Evicted · {len(self._warmup_db_timestamps_)} Bars Discontinuous")
            if not self._warmup_ready_ and self._warmup_database_ + len(self._sync_buffer_) >= self._warmup_window_:
                self._warmup_ready_ = True
                return [ExecutionActionAPI()]

        def execute(update: CompleteUpdateAPI):
            updates = len(self._sync_buffer_)
            first = self._sync_buffer_[0].Timestamp.DateTime if self._sync_buffer_ else None
            last = self._sync_buffer_[-1].Timestamp.DateTime if self._sync_buffer_ else None
            if self._warmup_timer_._start_ is not None:
                self._warmup_timer_.stop()
                self._log_.info(lambda: f"Phase Warmup: Completed · {self._warmup_timer_.result()} · {self._metrics_['Ticks']} Ticks · {self._metrics_['Bars']} Bars")
            self._log_.debug(lambda: f"Phase Warmup: Window {self._warmup_window_} · Database {self._warmup_database_} Bars · Updates {updates} Bars")
            self._log_.debug(lambda: f"Phase Warmup: First Bar {first}")
            self._log_.debug(lambda: f"Phase Warmup: Last Bar {last}")
            self._execution_timer_.start()
            self._initial_account_ = update.Portfolio.Account
            if self._sync_buffer_:
                stream = pl.DataFrame([b.dict(flatten=True) for b in self._sync_buffer_], strict=False)
                combined = stream
                if self._warmup_database_ and self._db_ is not None and self._security_ is not None and self._security_.UID is not None:
                    database = MarketAPI.pull_bars(self._db_, self._security_.UID, self._timeframe_.UID, stop=self._sync_buffer_[0].Timestamp.DateTime, limit=self._warmup_window_)
                    if database.height: combined = pl.concat([database, stream], how="diagonal_relaxed").select(stream.columns)
                update.Market.init_data(combined)
            self._sync_buffer_.clear()

        def update(update: BarUpdateAPI):
            if self._start_timestamp_ is None: self._start_timestamp_ = update.Bar.Timestamp.DateTime
            self._stop_timestamp_ = update.Bar.Timestamp.DateTime
            update.Market.update_data(update.Bar)

        def report(update: CompleteUpdateAPI):
            if self._execution_timer_._start_ is not None and self._execution_timer_._stop_ is None:
                self._execution_timer_.stop()
                self._log_.info(lambda: f"Phase Execution: Completed · {self._execution_timer_.result()}")
            self._log_.debug(lambda: f"Phase Execution: First Bar {self._start_timestamp_}")
            self._log_.debug(lambda: f"Phase Execution: Last Bar {self._stop_timestamp_}")
            if self._portfolio_.Active and self.portfolio and self.portfolio.Security: self.portfolio.Security.save()
            account = self._initial_account_ if self._initial_account_ is not None else update.Portfolio.Account
            start = (self._start_timestamp_ if self._start_timestamp_ is not None else datetime.now()).date()
            stop = (self._stop_timestamp_ if self._stop_timestamp_ is not None else datetime.now()).date()
            self._report_(update.Portfolio, account, start, stop)

        initialization.on(event=UpdateID.Init, to=initialization, action=init, reason="Handshake Initialized")
        initialization.on(event=UpdateID.BarClosed, to=initialization, action=warmup, reason=None)
        initialization.on(event=UpdateID.Execution, to=execution, action=execute, reason="Market Initialized")
        initialization.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

        execution.on(event=UpdateID.BarClosed, to=execution, action=update, reason=None)
        execution.on(event=UpdateID.Shutdown, to=termination, action=report, reason="Safely Terminated")

        return system_engine

    @timer
    def run(self) -> None:
        self.deploy()