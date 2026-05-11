import queue
from typing import Union, Type, Callable
from datetime import datetime
from dataclasses import dataclass

from Library.Database import DatabaseAPI
from Library.Database.Dataframe import pl
from Library.Parameters import Parameters
from Library.Utils import timer

from Library.Utility import *
from Library.Engine import MachineAPI
from Library.Market import MarketAPI, TickAPI, BarAPI
from Library.Portfolio import PortfolioAPI, AccountAPI, PositionAPI, TradeAPI, AccountType, Environment, MarginMode
from Library.Universe import ContractAPI, ContractType, SecurityAPI
from Library.System import SystemAPI

@dataclass(slots=True)
class _TickSnapshot:
    Timestamp: datetime
    Ask: float
    Bid: float
    AskBaseConversion: float
    BidBaseConversion: float
    AskQuoteConversion: float
    BidQuoteConversion: float

@dataclass(slots=True)
class _LastPositionData:
    Volume: float
    StopLoss: Union[float, None]
    TakeProfit: Union[float, None]

class TradingSystemAPI(SystemAPI):

    SENTINEL = -1.0

    def __init__(self,
                 api,
                 broker: str,
                 group: str,
                 symbol: str,
                 timeframe: str,
                 strategy: Type[StrategyAPI],
                 parameters: Parameters) -> None:

        super().__init__(
            broker=broker,
            group=group,
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            parameters=parameters
        )

        self.api = api
        self.queue: queue.Queue = queue.Queue()

        self._sync_buffer: list[BarAPI] = []
        self._initial_account: Union[AccountAPI, None] = None
        self._start_timestamp: Union[datetime, None] = None
        self._stop_timestamp: Union[datetime, None] = None

        self._ask_base_conversion: Callable[[], float] = lambda: 1.0
        self._bid_base_conversion: Callable[[], float] = lambda: 1.0
        self._ask_quote_conversion: Callable[[], float] = lambda: 1.0
        self._bid_quote_conversion: Callable[[], float] = lambda: 1.0

        self._bar_timestamp: Union[datetime, None] = None
        self._gap_tick: Union[_TickSnapshot, None] = None
        self._open_tick: Union[_TickSnapshot, None] = None
        self._high_tick: Union[_TickSnapshot, None] = None
        self._low_tick: Union[_TickSnapshot, None] = None
        self._close_tick: Union[_TickSnapshot, None] = None

        self._positions_cache: dict[int, _LastPositionData] = {}

        self._ask_above_target: Union[float, None] = None
        self._ask_below_target: Union[float, None] = None
        self._bid_above_target: Union[float, None] = None
        self._bid_below_target: Union[float, None] = None

        self._bar_db: Union[DatabaseAPI, None] = None

    def __enter__(self):
        self.strategy = self._strategy_(
            money_management=self.parameters.MoneyManagement,
            risk_management=self.parameters.RiskManagement,
            signal_management=self.parameters.SignalManagement
        )
        self.market = MarketAPI(parameters=None)
        from Library.Indicator import IndicatorAPI
        self.indicator = IndicatorAPI(parameters=self.parameters.AnalystManagement)
        self.portfolio = PortfolioAPI(parameters=self.parameters.ManagerManagement)

        self._bar_db = DatabaseAPI(
            broker=self._broker,
            group=self._group,
            symbol=self._symbol,
            timeframe=self._timeframe
        )
        self._bar_db.__enter__()

        self._setup_conversions()
        self._init_running_bar()
        self._attach_handlers()

        return super().__enter__()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._detach_handlers()
        if self._bar_db:
            self._bar_db.__exit__(None, None, None)
        return super().__exit__(exc_type, exc_value, exc_traceback)

    def _setup_conversions(self) -> None:
        base = self.api.Symbol.BaseAsset
        quote = self.api.Symbol.QuoteAsset
        account = self.api.Account.Asset
        self._ask_base_conversion, self._bid_base_conversion = self._find_conversions(base, account)
        self._ask_quote_conversion, self._bid_quote_conversion = self._find_conversions(quote, account)

    def _find_conversions(self, from_asset, to_asset) -> tuple[Callable[[], float], Callable[[], float]]:
        if from_asset == to_asset:
            return (lambda: 1.0, lambda: 1.0)
        for symbol_name in self.api.Symbols:
            try:
                if not self.api.Symbols.Exists(symbol_name):
                    continue
                s = self.api.Symbols.GetSymbol(symbol_name)
                if s.BaseAsset is None or s.QuoteAsset is None:
                    continue
                if s.BaseAsset == from_asset and s.QuoteAsset == to_asset:
                    return (lambda sym=s: sym.Ask, lambda sym=s: sym.Bid)
                if s.QuoteAsset == from_asset and s.BaseAsset == to_asset:
                    return (lambda sym=s: 1.0 / sym.Bid, lambda sym=s: 1.0 / sym.Ask)
            except Exception as e:
                self._log.warning(lambda m=str(e): m)
        raise RuntimeError(f"No conversion symbol found for {from_asset} -> {to_asset}")

    def _tick_snapshot(self) -> _TickSnapshot:
        return _TickSnapshot(
            Timestamp=self.api.Server.Time,
            Ask=self.api.Symbol.Ask,
            Bid=self.api.Symbol.Bid,
            AskBaseConversion=self._ask_base_conversion(),
            BidBaseConversion=self._bid_base_conversion(),
            AskQuoteConversion=self._ask_quote_conversion(),
            BidQuoteConversion=self._bid_quote_conversion()
        )

    def _init_running_bar(self) -> None:
        tick = self._tick_snapshot()
        self._bar_timestamp = self.api.Bars.LastBar.OpenTime
        self._gap_tick = tick
        self._open_tick = tick
        self._high_tick = tick
        self._low_tick = tick
        self._close_tick = tick

    def _reset_running_bar(self, timestamp: datetime) -> None:
        tick = self._tick_snapshot()
        self._bar_timestamp = timestamp
        self._gap_tick = self._close_tick
        self._open_tick = tick
        self._high_tick = tick
        self._low_tick = tick
        self._close_tick = tick

    def _update_running_bar(self, tick: _TickSnapshot) -> None:
        if tick.Ask > self._high_tick.Ask or tick.Bid > self._high_tick.Bid:
            self._high_tick = tick
        if tick.Ask < self._low_tick.Ask or tick.Bid < self._low_tick.Bid:
            self._low_tick = tick
        self._close_tick = tick

    def _snapshot_bar(self, tick_volume: float) -> BarAPI:
        return BarAPI(
            Timestamp=self._bar_timestamp,
            Security=self.portfolio._security_,
            Timeframe=self._timeframe,
            Volume=tick_volume,
            # Ticks will be mapped to proper fields in BarAPI if needed
            db=self._bar_db
        )

    def _convert_account(self, acc) -> AccountAPI:
        return AccountAPI(
            UID=acc.Number,
            Environment=Environment.Demo if acc.IsDemo else Environment.Live,
            AccountType=AccountType.Hedged if acc.AccountType == 0 else AccountType.Netted,
            MarginMode=MarginMode.Max, # Placeholder
            Asset=acc.Asset.Name,
            Balance=acc.Balance,
            Equity=acc.Equity,
            Credit=acc.Credit,
            Leverage=acc.PreciseLeverage,
            MarginUsed=acc.Margin,
            MarginFree=acc.FreeMargin,
            MarginLevel=acc.MarginLevel,
            MarginStopLevel=acc.StopOutLevel,
            db=self._bar_db
        )

    def _convert_position(self, pos) -> PositionAPI:
        return PositionAPI(
            UID=pos.Id,
            Security=self.portfolio._security_,
            Direction=Direction.Buy if int(pos.Direction) == 0 else Direction.Sell,
            Volume=pos.VolumeInUnits,
            Quantity=pos.Quantity,
            EntryTimestamp=pos.EntryTime,
            EntryPrice=pos.EntryPrice,
            StopLossPrice=pos.StopLoss,
            TakeProfitPrice=pos.TakeProfit,
            ExitPrice=pos.CurrentPrice,
            NetPnL=pos.NetProfit,
            UsedMargin=pos.Margin,
            db=self._bar_db
        )

    def _convert_trade(self, trd) -> TradeAPI:
        return TradeAPI(
            UID=trd.ClosingDealId,
            Position=trd.PositionId,
            Security=self.portfolio._security_,
            Direction=Direction.Buy if int(trd.Direction) == 0 else Direction.Sell,
            Volume=trd.VolumeInUnits,
            Quantity=trd.Quantity,
            EntryTimestamp=trd.EntryTime,
            ExitTimestamp=trd.ClosingTime,
            EntryPrice=trd.EntryPrice,
            ExitPrice=trd.ClosingPrice,
            NetPnL=trd.NetProfit,
            db=self._bar_db
        )

    def _is_own_position(self, pos) -> bool:
        return pos.Label == self.api.InstanceId

    def _find_trade(self, position_id: int):
        last = None
        for trd in self.api.History:
            if trd.PositionId == position_id:
                last = trd
        return last

    def _attach_handlers(self) -> None:
        self.api.Positions.Opened += self._on_position_opened
        self.api.Positions.Modified += self._on_position_modified
        self.api.Positions.Closed += self._on_position_closed

    def _detach_handlers(self) -> None:
        try:
            self.api.Positions.Opened -= self._on_position_opened
            self.api.Positions.Modified -= self._on_position_modified
            self.api.Positions.Closed -= self._on_position_closed
        except Exception:
            pass

    def receive_update_id(self) -> UpdateID:
        return self.queue.get()

    def receive_update_account(self) -> AccountAPI:
        return self.queue.get()

    def receive_update_symbol(self) -> SecurityAPI:
        return self.queue.get()

    def receive_update_position(self) -> PositionAPI:
        return self.queue.get()

    def receive_update_trade(self) -> TradeAPI:
        return self.queue.get()

    def receive_update_bar(self) -> BarAPI:
        return self.queue.get()

    def receive_update_target(self) -> TickAPI:
        return self.queue.get()

    def send_action_complete(self, action: CompleteAction) -> None:
        pass

    def send_action_open(self, action: Union[OpenBuyAction, OpenSellAction]) -> None:
        trade_type = 0 if isinstance(action, OpenBuyAction) else 1
        sl = action.StopLoss if action.StopLoss is not None else None
        tp = action.TakeProfit if action.TakeProfit is not None else None
        result = self.api.ExecuteMarketOrder(
            trade_type,
            self.api.Symbol.Name,
            action.Volume,
            self.api.InstanceId,
            sl,
            tp,
            action.PositionType.name
        )
        if result is not None and not result.IsSuccessful:
            self._log.error(lambda: f"Open order failed: {result.Error}")
            self.api.Stop()

    def send_action_modify_volume(self, action: Union[ModifyBuyVolumeAction, ModifySellVolumeAction]) -> None:
        pos = next((p for p in self.api.Positions if p.Id == action.PositionID), None)
        if pos is None:
            self._log.warning(lambda: f"ModifyVolume: position {action.PositionID} not found")
            return
        result = pos.ModifyVolume(action.Volume)
        if result is not None and not result.IsSuccessful:
            self._log.error(lambda: f"ModifyVolume failed: {result.Error}")
            self.api.Stop()

    def send_action_modify_stop_loss(self, action: Union[ModifyBuyStopLossAction, ModifySellStopLossAction]) -> None:
        pos = next((p for p in self.api.Positions if p.Id == action.PositionID), None)
        if pos is None:
            self._log.warning(lambda: f"ModifyStopLoss: position {action.PositionID} not found")
            return
        result = pos.ModifyStopLossPrice(action.StopLoss)
        if result is not None and not result.IsSuccessful:
            self._log.error(lambda: f"ModifyStopLoss failed: {result.Error}")
            self.api.Stop()

    def send_action_modify_take_profit(self, action: Union[ModifyBuyTakeProfitAction, ModifySellTakeProfitAction]) -> None:
        pos = next((p for p in self.api.Positions if p.Id == action.PositionID), None)
        if pos is None:
            self._log.warning(lambda: f"ModifyTakeProfit: position {action.PositionID} not found")
            return
        result = pos.ModifyTakeProfitPrice(action.TakeProfit)
        if result is not None and not result.IsSuccessful:
            self._log.error(lambda: f"ModifyTakeProfit failed: {result.Error}")
            self.api.Stop()

    def send_action_close(self, action: Union[CloseBuyAction, CloseSellAction]) -> None:
        pos = next((p for p in self.api.Positions if p.Id == action.PositionID), None)
        if pos is None:
            self._log.warning(lambda: f"Close: position {action.PositionID} not found")
            return
        result = self.api.ClosePosition(pos)
        if result is not None and not result.IsSuccessful:
            self._log.error(lambda: f"Close failed: {result.Error}")
            self.api.Stop()

    def send_action_ask_above_target(self, action: AskAboveTargetAction) -> None:
        self._ask_above_target = action.Ask

    def send_action_ask_below_target(self, action: AskBelowTargetAction) -> None:
        self._ask_below_target = action.Ask

    def send_action_bid_above_target(self, action: BidAboveTargetAction) -> None:
        self._bid_above_target = action.Bid

    def send_action_bid_below_target(self, action: BidBelowTargetAction) -> None:
        self._bid_below_target = action.Bid

    def system_management(self) -> MachineAPI:
        system_engine = MachineAPI("System Management")
        initialization = system_engine.create_state(name="Initialization", end=False)
        execution = system_engine.create_state(name="Execution", end=False)
        termination = system_engine.create_state(name="Termination", end=True)

        def sync_market(update: BarUpdate):
            self._sync_buffer.append(update.Bar)

        def init_market(update: CompleteUpdate):
            self._initial_account = update.Portfolio._account_
            self._start_timestamp = self._sync_buffer[-1].Timestamp.DateTime if self._sync_buffer else None
            df = pl.from_dicts([b.dict() for b in self._sync_buffer]) if self._sync_buffer else pl.DataFrame()
            update.Market.init_data(df)
            update.Indicator.init_data(update.Market)

        def update_market(update: BarUpdate):
            self._stop_timestamp = update.Bar.Timestamp.DateTime
            update.Market.update_data(update.Bar)
            update.Indicator.update_data(update.Market)

        def update_database(update: CompleteUpdate):
            self._bar_db.push_market_data(update.Market.dataframe())
            from Library.Portfolio.Statistics import StatisticsAPI
            self.individual_trades, self.aggregated_trades, self.statistics = StatisticsAPI.data(
                update.Portfolio.TradesDataframe, self._initial_account, self._start_timestamp, self._stop_timestamp
            )

        initialization.on_bar_closed(to=initialization, action=sync_market, reason=None)
        initialization.on_complete(to=execution, action=init_market, reason="Market Initialized")
        initialization.on_shutdown(to=termination, action=None, reason="Abruptly Terminated")

        execution.on_bar_closed(to=execution, action=update_market, reason=None)
        execution.on_shutdown(to=termination, action=update_database, reason="Safely Terminated")

        return system_engine

    def on_tick(self) -> None:
        try:
            tick = self._tick_snapshot()
            self._update_running_bar(tick)

            fired = False
            if self._ask_above_target is not None and tick.Ask >= self._ask_above_target:
                self._enqueue_target(UpdateID.AskAboveTarget, tick)
                fired = True
            if self._ask_below_target is not None and tick.Ask <= self._ask_below_target:
                self._enqueue_target(UpdateID.AskBelowTarget, tick)
                fired = True
            if self._bid_above_target is not None and tick.Bid >= self._bid_above_target:
                self._enqueue_target(UpdateID.BidAboveTarget, tick)
                fired = True
            if self._bid_below_target is not None and tick.Bid <= self._bid_below_target:
                self._enqueue_target(UpdateID.BidBelowTarget, tick)
                fired = True

            if not fired:
                return
        except Exception as e:
            self._log.exception(lambda m=str(e): f"on_tick: {m}")
            self.api.Stop()

    def _enqueue_target(self, update_id: UpdateID, tick: _TickSnapshot) -> None:
        self.queue.put(update_id)
        self.queue.put(TickAPI(
            Timestamp=tick.Timestamp,
            Ask=tick.Ask,
            Bid=tick.Bid,
            AskBaseConversion=tick.AskBaseConversion,
            BidBaseConversion=tick.BidBaseConversion,
            AskQuoteConversion=tick.AskQuoteConversion,
            BidQuoteConversion=tick.BidQuoteConversion,
            Security=self.portfolio._security_
        ))
        self.queue.put(UpdateID.Complete)

    def on_bar_closed(self) -> None:
        try:
            last = self.api.Bars.LastBar
            bar = self._snapshot_bar(tick_volume=last.TickVolume)
            self.queue.put(UpdateID.BarClosed)
            self.queue.put(bar)
            self.queue.put(UpdateID.Complete)
            self._reset_running_bar(timestamp=last.OpenTime)
        except Exception as e:
            self._log.exception(lambda m=str(e): f"on_bar_closed: {m}")
            self.api.Stop()

    def _on_position_opened(self, args) -> None:
        try:
            pos = args.Position
            if not self._is_own_position(pos):
                return
            self._positions_cache[pos.Id] = _LastPositionData(
                Volume=pos.VolumeInUnits,
                StopLoss=pos.StopLoss,
                TakeProfit=pos.TakeProfit
            )
            update_id = UpdateID.OpenedBuy if int(pos.Direction) == 0 else UpdateID.OpenedSell
            self.queue.put(update_id)
            self.queue.put(self._snapshot_bar(tick_volume=0.0))
            self.queue.put(self._convert_account(self.api.Account))
            self.queue.put(self._convert_position(pos))
            self.queue.put(UpdateID.Complete)
        except Exception as e:
            self._log.exception(lambda m=str(e): f"on_position_opened: {m}")
            self.api.Stop()

    def _on_position_modified(self, args) -> None:
        try:
            pos = args.Position
            if not self._is_own_position(pos):
                return
            last = self._positions_cache.get(pos.Id)
            if last is None:
                return

            buy = int(pos.Direction) == 0
            if abs(pos.VolumeInUnits - last.Volume) > 1e-12:
                trade = self._find_trade(pos.Id)
                update_id = UpdateID.ModifiedBuyVolume if buy else UpdateID.ModifiedSellVolume
                self.queue.put(update_id)
                self.queue.put(self._snapshot_bar(tick_volume=0.0))
                self.queue.put(self._convert_account(self.api.Account))
                self.queue.put(self._convert_position(pos))
                self.queue.put(self._convert_trade(trade) if trade is not None else None)
                self.queue.put(UpdateID.Complete)
                last.Volume = pos.VolumeInUnits
                return

            if self._changed(last.StopLoss, pos.StopLoss):
                update_id = UpdateID.ModifiedBuyStopLoss if buy else UpdateID.ModifiedSellStopLoss
                self.queue.put(update_id)
                self.queue.put(self._snapshot_bar(tick_volume=0.0))
                self.queue.put(self._convert_account(self.api.Account))
                self.queue.put(self._convert_position(pos))
                self.queue.put(UpdateID.Complete)
                last.StopLoss = pos.StopLoss
                return

            if self._changed(last.TakeProfit, pos.TakeProfit):
                update_id = UpdateID.ModifiedBuyTakeProfit if buy else UpdateID.ModifiedSellTakeProfit
                self.queue.put(update_id)
                self.queue.put(self._snapshot_bar(tick_volume=0.0))
                self.queue.put(self._convert_account(self.api.Account))
                self.queue.put(self._convert_position(pos))
                self.queue.put(UpdateID.Complete)
                last.TakeProfit = pos.TakeProfit
        except Exception as e:
            self._log.exception(lambda m=str(e): f"on_position_modified: {m}")
            self.api.Stop()

    def _on_position_closed(self, args) -> None:
        try:
            pos = args.Position
            if not self._is_own_position(pos):
                return
            trade = self._find_trade(pos.Id)
            buy = int(pos.Direction) == 0
            update_id = UpdateID.ClosedBuy if buy else UpdateID.ClosedSell
            self.queue.put(update_id)
            self.queue.put(self._snapshot_bar(tick_volume=0.0))
            self.queue.put(self._convert_account(self.api.Account))
            self.queue.put(self._convert_trade(trade) if trade is not None else None)
            self.queue.put(UpdateID.Complete)
            self._positions_cache.pop(pos.Id, None)
        except Exception as e:
            self._log.exception(lambda m=str(e): f"on_position_closed: {m}")
            self.api.Stop()

    @staticmethod
    def _changed(old: Union[float, None], new: Union[float, None]) -> bool:
        if old is None and new is None:
            return False
        if old is None or new is None:
            return True
        return abs(float(old) - float(new)) > 1e-12

    def on_shutdown(self) -> None:
        self.queue.put(UpdateID.Shutdown)

    @timer
    def run(self) -> None:
        self.queue.put(UpdateID.Account)
        self.queue.put(self._convert_account(self.api.Account))
        self.queue.put(UpdateID.Symbol)
        # Use SecurityAPI for symbol update
        self.queue.put(self.portfolio._security_)
        self.queue.put(UpdateID.Complete)
        self.deploy(strategy=self.strategy, market=self.market, indicator=self.indicator, portfolio=self.portfolio)
