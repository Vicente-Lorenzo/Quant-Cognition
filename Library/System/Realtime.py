from __future__ import annotations

import os
import contextlib

from pathlib import Path
from datetime import datetime, timedelta
from typing import Union, TYPE_CHECKING

from Library.Database.Database import DatabaseAPI
from Library.Database.Dataframe import pl
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Engine import MachineAPI
from Library.Market.Bar import BarAPI
from Library.Market.Market import MarketAPI
from Library.Market.Point import PointAPI
from Library.Market.Price import Direction
from Library.Market.Tick import TickAPI
from Library.Portfolio.Account import AccountAPI, AccountType, MarginMode
from Library.Portfolio.Order import OrderAPI, OrderType
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionAPI, ActionID, Stream, InitActionAPI, ExecutionActionAPI, SubscribeActionAPI, UnsubscribeActionAPI
from Library.Protocol.Binary import BinaryAPI
from Library.Protocol.Transport import TransportAPI, PeerExit
from Library.Protocol.Update import UpdateID, CompleteUpdateAPI, InitUpdateAPI, BarUpdateAPI
from Library.System.System import SystemAPI, SystemType
from Library.Universe.Contract import ContractAPI, CommissionMode, SwapMode, TradingMode
from Library.Universe.Security import SecurityAPI
from Library.Utility.Datetime import timestamp_to_datetime, utc_now, Weekday
from Library.Utility.Profiler import timer

if TYPE_CHECKING:
    from Library.Utility.Parameter import Parameter
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Timeframe import TimeframeAPI

class RealtimeAPI(SystemAPI):

    _MARKET_CLOSURE_ = timedelta(days=4)
    _CONNECTOR_ = "Connector"

    _DIRECTION_ = {0: Direction.Buy, 1: Direction.Sell}
    _ORDER_TYPE_ = {0: OrderType.Limit, 1: OrderType.Stop, 2: OrderType.StopLimit}
    _WEEKDAY_ = {0: Weekday.Sunday, 1: Weekday.Monday, 2: Weekday.Tuesday, 3: Weekday.Wednesday, 4: Weekday.Thursday, 5: Weekday.Friday, 6: Weekday.Saturday}
    _TRADING_MODE_ = {0: TradingMode.Enabled, 1: TradingMode.CloseOnlyMode, 2: TradingMode.DisabledWithPendingsExecution, 3: TradingMode.DisabledWithoutPendingsExecution}

    _binary_init_ = BinaryAPI('i')
    _binary_denied_ = BinaryAPI('B', 's')
    _binary_exception_ = BinaryAPI('s')

    _binary_account_ = BinaryAPI('s', 's', 'B', 's', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'B')
    _binary_security_ = BinaryAPI('q', 's', 's', 's', 'i', 'd', 'd', 'q', 'd', 'd', 'd', 'B', 'd', 'B', 'd', 'd', 'i', 'B')

    _binary_tick_ = BinaryAPI('q', 'd', 'd', 'd', 'd', 'd', 'd', 'd')

    _binary_order_ = BinaryAPI('i', 'B', 'B', 'd', 'd', 'D', 'D', 'q', 's')
    _binary_position_ = BinaryAPI('i', 'B', 'B', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'D', 'D', 's')
    _binary_trade_ = BinaryAPI('i', 'i', 'B', 'B', 'q', 'q', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 'd', 's')

    _bar_payload_ = 1 + 8 + 9 * _binary_tick_._size_ + 8

    def __init__(self,
                 system: SystemType,
                 strategy: type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 parameters: Parameter,
                 iid: str,
                 database: str = "Quant",
                 risk_free: float = 0.0,
                 benchmark: Union[str, list, None] = None,
                 report: bool = True,
                 export: bool = True,
                 plot: bool = False,
                 run: Union[str, Path, None] = None,
                 description: Union[str, None] = None) -> None:
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, parameters=parameters, risk_free=risk_free, benchmark=benchmark, report=report, export=export, plot=plot, run=run, description=description)

        self._system_: SystemType = system
        self._iid_: str = iid
        self._database_: str = database

        self._db_: Union[DatabaseAPI, None] = None
        self._stack_: Union[contextlib.ExitStack, None] = None
        self._transport_: Union[TransportAPI, None] = None
        self._last_update_data_: bytes = b""
        self._exc_info_: tuple = (None, None, None)

        self._sync_buffer_: list[BarAPI] = []
        self._warmup_window_: Union[int, None] = None
        self._warmup_frame_: Union[pl.DataFrame, None] = None
        self._warmup_database_: int = 0
        self._warmup_db_timestamps_: list[datetime] = []
        self._warmup_ready_: bool = False
        self._initial_account_: Union[AccountAPI, None] = None
        self._start_timestamp_: Union[datetime, None] = None
        self._stop_timestamp_: Union[datetime, None] = None

        self._metrics_: dict = {"Ticks": 0, "Bars": 0, "Accounts": 0, "Orders": 0, "Positions": 0, "Trades": 0, "Actions": 0}

    def _connect_(self) -> None:
        stack = contextlib.ExitStack()
        stack.__enter__()
        self._stack_ = stack
        try:
            self._transport_ = TransportAPI(iid=self._iid_, create=False)
            self._stack_.callback(lambda: self._transport_.close() if self._transport_ else None)
            self._log_.debug(lambda: f"Connect Operation: Bound Shared Memory (iid {self._iid_})")
            self._assemble_()
            self._db_ = self._stack_.enter_context(PostgresDatabaseAPI(database=self._database_))
        except Exception:
            self._stack_.__exit__(None, None, None)
            raise
        super()._connect_()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._exc_info_ = (exc_type, exc_value, exc_traceback)
        return super().__exit__(exc_type, exc_value, exc_traceback)

    def _disconnect_(self) -> None:
        super()._disconnect_()
        if self._stack_: self._stack_.__exit__(*self._exc_info_)
        self._log_.debug(lambda: f"Disconnect Operation: Closed (iid {self._iid_})")

    def _summary_(self) -> None:
        m = self._metrics_
        exec_delta = self._execution_timer_.delta() if self._execution_timer_._stop_ else 0.0
        bars_per_sec = (m["Bars"] / exec_delta) if exec_delta > 0 else 0.0
        ticks_per_sec = (m["Ticks"] / exec_delta) if exec_delta > 0 else 0.0
        self._log_.info(lambda: f"Phase Execution: {ticks_per_sec:.1f} Ticks/s · {bars_per_sec:.1f} Bars/s")
        self._log_.info(lambda: "Summary: " + " · ".join(f"{k} {v}" for k, v in m.items()))

    def label(self) -> str:
        return self._run_.name if self._run_ is not None else self._iid_

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
            Timestamp=utc_now(),
            Number=number,
            Provider=self._security_.Provider if self._security_ else None,
            Environment=environment,
            AccountType=AccountType(account_type),
            Asset=asset,
            Balance=balance,
            Equity=equity,
            Credit=credit,
            Leverage=leverage,
            MarginUsed=margin_used,
            MarginFree=margin_free,
            MarginLevel=margin_level,
            MarginStopLevel=margin_stop,
            MarginMode=MarginMode(margin_mode),
            db=self._db_
        )

    def receive_update_security(self, offset: int = 1) -> SecurityAPI:
        (symbol, base_asset, quote_asset, description, digits, point_size, pip_size, lot_size, volume_min, volume_max, volume_step,
         commission_mode, commission, swap_mode, swap_long, swap_short, swap_extra_day, trading_mode
        ) = self._binary_security_.unpack(self._last_update_data_, offset)
        security = self._security_
        if security:
            security.Symbol = symbol
            if security.Ticker:
                security.Ticker.BaseAsset = base_asset
                security.Ticker.QuoteAsset = quote_asset
                security.Ticker.Description = description
            contract = security.Contract if security.Contract is not None else ContractAPI(Security=security.UID)
            contract.Digits = digits
            contract.PointSize = point_size
            contract.PipSize = pip_size
            contract.LotSize = lot_size
            contract.VolumeMin = volume_min
            contract.VolumeMax = volume_max
            contract.VolumeStep = volume_step
            contract.CommissionMode = CommissionMode(commission_mode)
            contract.Commission = commission
            contract.SwapMode = SwapMode(swap_mode)
            contract.SwapLong = swap_long
            contract.SwapShort = swap_short
            contract.SwapExtraDay = self._WEEKDAY_.get(swap_extra_day)
            contract.TradingMode = self._TRADING_MODE_[trading_mode]
            contract.UpdatedAt = utc_now()
            contract.UpdatedBy = self._CONNECTOR_
            security.Contract = contract
            self._record_contract_()
        return security

    def receive_update_order(self, offset: int = _bar_payload_) -> OrderAPI:
        uid, order_type_id, direction_id, volume, target_price, stop_loss, take_profit, expiration_ts, label = self._binary_order_.unpack(self._last_update_data_, offset)
        self._metrics_["Orders"] += 1
        order_type = self._ORDER_TYPE_[order_type_id]
        has_limit = order_type in (OrderType.Limit, OrderType.StopLimit)
        has_stop = order_type in (OrderType.Stop, OrderType.StopLimit)
        return OrderAPI(
            UID=uid,
            Account=self.account,
            Security=self._security_,
            Direction=self._DIRECTION_[direction_id],
            OrderType=order_type,
            Volume=volume,
            LimitPrice=target_price if has_limit else None,
            StopPrice=target_price if has_stop else None,
            StopLossPrice=stop_loss,
            TakeProfitPrice=take_profit,
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
            Account=self.account,
            Security=self._security_,
            Type=pos_type,
            Direction=self._DIRECTION_[direction_id],
            EntryTimestamp=timestamp_to_datetime(entry_ts, milliseconds=True),
            EntryPrice=entry_price,
            Volume=volume,
            Quantity=quantity,
            GrossPnL=gross_pnl,
            CommissionPnL=commission_pnl,
            SwapPnL=swap_pnl,
            NetPnL=net_pnl,
            UsedMargin=used_margin,
            StopLossPrice=stop_loss,
            TakeProfitPrice=take_profit,
            Label=label,
            Comment=pos_type.name,
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
            UID=uid,
            Position=position_id,
            Account=self.account,
            Security=self._security_,
            Type=pos_type,
            Direction=self._DIRECTION_[direction_id],
            EntryTimestamp=timestamp_to_datetime(entry_ts, milliseconds=True),
            ExitTimestamp=timestamp_to_datetime(exit_ts, milliseconds=True),
            EntryPrice=entry_price,
            ExitPrice=exit_price,
            Volume=volume,
            Quantity=quantity,
            GrossPnL=gross_pnl,
            CommissionPnL=commission_pnl,
            SwapPnL=swap_pnl,
            NetPnL=net_pnl,
            Label=label,
            Comment=pos_type.name,
            db=self._db_
        )

    def receive_update_tick(self, offset: int = 1) -> TickAPI:
        self._metrics_["Ticks"] += 1
        return self._deserialize_tick_(self._last_update_data_, 1)

    def _deserialize_tick_(self, data: bytes, offset: int) -> TickAPI:
        ts, ask, bid, ask_base, bid_base, ask_quote, bid_quote, volume = self._binary_tick_.unpack(data, offset)
        timestamp = timestamp_to_datetime(ts, milliseconds=True)
        return TickAPI(
            Security=self._security_,
            Timestamp=timestamp,
            Ask=ask,
            Bid=bid,
            AskBaseConversion=ask_base,
            BidBaseConversion=bid_base,
            AskQuoteConversion=ask_quote,
            BidQuoteConversion=bid_quote,
            Volume=volume
        )

    def receive_update_bar(self, offset: int = 1) -> BarAPI:
        data = self._last_update_data_
        bar_ts = BinaryAPI.INT64.unpack_from(data, 1)[0]
        tick_size = self._binary_tick_._size_
        off = 9
        gap = self._deserialize_tick_(data, off); off += tick_size
        opn = self._deserialize_tick_(data, off); off += tick_size
        high_ask = self._deserialize_tick_(data, off); off += tick_size
        high_bid = self._deserialize_tick_(data, off); off += tick_size
        high_mid = self._deserialize_tick_(data, off); off += tick_size
        low_ask = self._deserialize_tick_(data, off); off += tick_size
        low_bid = self._deserialize_tick_(data, off); off += tick_size
        low_mid = self._deserialize_tick_(data, off); off += tick_size
        close = self._deserialize_tick_(data, off); off += tick_size
        volume = BinaryAPI.FLOAT64.unpack_from(data, off)[0]
        self._metrics_["Ticks"] += 9
        self._metrics_["Bars"] += 1
        return BarAPI(
            Security=self._security_,
            Timeframe=self._timeframe_,
            Timestamp=timestamp_to_datetime(bar_ts, milliseconds=True),
            GapPoint=PointAPI(AskTick=gap, MidTick=gap, BidTick=gap),
            OpenPoint=PointAPI(AskTick=opn, MidTick=opn, BidTick=opn),
            HighPoint=PointAPI(AskTick=high_ask, MidTick=high_mid, BidTick=high_bid),
            LowPoint=PointAPI(AskTick=low_ask, MidTick=low_mid, BidTick=low_bid),
            ClosePoint=PointAPI(AskTick=close, MidTick=close, BidTick=close),
            Volume=volume
        )

    def receive_update_denied(self, offset: int = 1) -> tuple[ActionID, str]:
        action_id, reason = self._binary_denied_.unpack(self._last_update_data_, 1)
        return ActionID(action_id), reason or ""

    def receive_update_exception(self, offset: int = 1) -> str:
        (reason,) = self._binary_exception_.unpack(self._last_update_data_, 1)
        return reason or ""

    def _warmup_horizon_(self) -> timedelta:
        step = self._timeframe_.Seconds or 0.0
        return timedelta(seconds=step) + self._MARKET_CLOSURE_

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
            subscribed = int(self.strategy.Subscription)
            unsubscribed = int(Stream.All) & ~subscribed
            actions = [InitActionAPI(ProcessID=os.getpid(), Label=self.label())]
            if subscribed: actions.append(SubscribeActionAPI(Streams=subscribed))
            if unsubscribed: actions.append(UnsubscribeActionAPI(Streams=unsubscribed))
            return actions

        def warmup(update: BarUpdateAPI):
            if self._warmup_window_ is None:
                self._warmup_window_ = self._indicator_window_()
                if self._warmup_window_ > 0 and self._db_ is not None and self._security_ is not None and self._security_.UID is not None:
                    self._warmup_frame_ = MarketAPI.pull_bars(self._db_, self._security_.UID, self._timeframe_.UID, stop=update.Bar.Timestamp.DateTime, limit=self._warmup_window_)
                    self._warmup_db_timestamps_ = self._warmup_frame_[str(BarAPI.ID.Timestamp)].to_list() if self._warmup_frame_.height else []
                self._log_.debug(lambda: f"Phase Warmup: Started · Window {self._warmup_window_} · Database {len(self._warmup_db_timestamps_)} Bars")
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
            self._log_.info(lambda: f"Phase Warmup: Completed · {self._metrics_['Ticks']} Ticks · {self._metrics_['Bars']} Bars")
            self._log_.debug(lambda: f"Phase Warmup: Window {self._warmup_window_} · Database {self._warmup_database_} Bars · Updates {updates} Bars")
            self._log_.debug(lambda: f"Phase Warmup: First Bar {first}")
            self._log_.debug(lambda: f"Phase Warmup: Last Bar {last}")
            self._initial_account_ = update.Portfolio.Account
            if self._sync_buffer_:
                stream = pl.DataFrame([b.dict(flatten=True) for b in self._sync_buffer_], strict=False)
                combined = stream
                if self._warmup_database_ and self._warmup_frame_ is not None and self._warmup_frame_.height:
                    combined = pl.concat([self._warmup_frame_, stream], how="diagonal_relaxed").select(stream.columns)
                update.Market.init_data(combined)
            self._sync_buffer_.clear()
            self._transition_(self._initialization_timer_, "Initialization", self._execution_timer_)

        def update(update: BarUpdateAPI):
            if self._start_timestamp_ is None: self._start_timestamp_ = update.Bar.Timestamp.DateTime
            self._stop_timestamp_ = update.Bar.Timestamp.DateTime
            update.Market.update_data(update.Bar)

        def report(update: CompleteUpdateAPI):
            self._transition_(self._execution_timer_, "Execution", self._finalization_timer_)
            self._log_.debug(lambda: f"Phase Execution: First Bar {self._start_timestamp_}")
            self._log_.debug(lambda: f"Phase Execution: Last Bar {self._stop_timestamp_}")
            account = self._initial_account_ if self._initial_account_ is not None else update.Portfolio.Account
            start = (self._start_timestamp_ if self._start_timestamp_ is not None else utc_now()).date()
            stop = (self._stop_timestamp_ if self._stop_timestamp_ is not None else utc_now()).date()
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
        try:
            self.deploy()
        except PeerExit:
            self._log_.info(lambda: "Shutdown Operation: Peer Stopped · Draining and Terminating")