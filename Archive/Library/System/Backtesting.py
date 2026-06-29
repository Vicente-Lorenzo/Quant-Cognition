import copy

from time import localtime
from datetime import date, datetime, timedelta
from itertools import count
from queue import Queue
from typing import Union, Type, Iterator, Callable

from Library.Database.Dataframe import pl
from Library.Classes import *
from Library.Database import DatabaseAPI
from Library.Parameters import ParametersAPI, Parameters
from Library.Utils import timer, equals, datetime_to_string, string_to_datetime

from Library.Utility import *
from Library.Market import MarketAPI
from Library.Portfolio import PortfolioAPI
from Library.Engine import MachineAPI
from Library.Strategy import StrategyAPI
from Library.System import SystemAPI

class BacktestingSystemAPI(SystemAPI):

    watchlist = ParametersAPI().Watchlist
    TICK = watchlist.Timeframes[0]
    SYMBOLS = [symbol for group in watchlist.Symbols.values() for symbol in group]

    account: Union[tuple[AssetType, float, float], None] = None
    account_data: Union[Account, None] = None

    tick_db: Union[DatabaseAPI, None] = None
    tick_df: Union[pl.DataFrame, None] = None

    bar_db: Union[DatabaseAPI, None] = None
    bar_df: Union[pl.DataFrame, None] = None

    symbol_data: Union[Symbol, None] = None

    base_conversion_db: Union[DatabaseAPI, None] = None
    base_conversion_df: Union[pl.DataFrame, None] = None
    base_conversion_rate: Callable[[datetime, float], float] | None = None

    quote_conversion_db: Union[DatabaseAPI, None] = None
    quote_conversion_df: Union[pl.DataFrame, None] = None
    quote_conversion_rate: Callable[[datetime, float], float] | None = None

    spread: Union[tuple[SpreadType, float], None] = None
    spread_fee: Callable[[datetime, float], float] | None = None

    commission: Union[tuple[CommissionType, float], None] = None
    commission_fee: Callable[[datetime, float, float], float] | None = None

    swap: Union[tuple[SwapType, float, float], None] = None
    swap_buy_fee: Callable[[datetime, datetime, datetime, float, float], float] | None = None
    swap_sell_fee: Callable[[datetime, datetime, datetime, float, float], float] | None = None

    window: Union[int, None] = None
    offset: Union[int, None] = None

    def __init__(self,
                 broker: str,
                 group: str,
                 symbol: str,
                 timeframe: str,
                 strategy: Type[StrategyAPI],
                 parameters: Parameters,
                 start: Union[str, date],
                 stop: Union[str, date],
                 account: tuple[AssetType, float, float],
                 spread: tuple[SpreadType, float],
                 commission: tuple[CommissionType, float],
                 swap: tuple[SwapType, float, float]) -> None:

        super().__init__(
            broker=broker,
            group=group,
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            parameters=parameters
        )

        def parse_date(x: Union[str, date]) -> tuple[Union[str, date], str | date]:
            if isinstance(x, str):
                return x, string_to_datetime(x, "%d-%m-%Y").date()
            else:
                return datetime_to_string(x, "%d-%m-%Y"), x

        self._start_str, self._start_date = parse_date(start)
        self._stop_str, self._stop_date = parse_date(stop)

        self.account = account
        self._account_asset, self._account_balance, self._account_leverage = account
        self._account_data: Union[Account, None] = None

        self.spread = spread
        self._spread_type, self._spread_value = spread
        self.commission = commission
        self._commission_type, self._commission_value = commission
        self.swap = swap
        self._swap_type, self._swap_buy, self._swap_sell  = swap

        self._tick_df_iterator: Union[Iterator, None] = None
        self._tick_data_next: Union[Bar, None] = None
        self._tick_open_next: Union[Tick, None] = None

        self._bar_df_iterator: Union[Iterator, None] = None
        self._bar_data_at: Union[Bar, None] = None
        self._bar_data_at_last: Union[Bar, None] = None
        self._bar_data_next: Union[Bar, None] = None

        self._offset: Union[int, None] = None

        self._update_id_queue: Union[Queue[UpdateID], None] = None
        self._update_args_queue: Union[Queue[Account, Symbol, Position, Trade, Bar, Tick], None] = None

        self._pids: count = count(start=1)
        self._tids: count = count(start=1)
        self._positions: dict[int, Position] = {}
        self._ask_above_target: Union[float, None] = None
        self._ask_below_target: Union[float, None] = None
        self._bid_above_target: Union[float, None] = None
        self._bid_below_target: Union[float, None] = None

    def __enter__(self):
        self.strategy = self._strategy_(money_management=self.parameters.MoneyManagement, risk_management=self.parameters.RiskManagement, signal_management=self.parameters.SignalManagement)

        self.market = MarketAPI(parameters=None) # Or remove entirely if not needed
        from Library.Indicator import IndicatorAPI
        self.indicator = IndicatorAPI(parameters=self.parameters.AnalystManagement)

        self.portfolio = PortfolioAPI(parameters=self.parameters.ManagerManagement)

        if self.window is None:
            self.window = self.indicator._window_

        if self.account_data is None:
            self.account_data: Account = Account(
                AccountType=AccountType.Hedged,
                AssetType=self._account_asset,
                Balance=self._account_balance,
                Equity=self._account_balance,
                Credit=0.0,
                Leverage=self._account_leverage,
                MarginUsed=0.0,
                MarginFree=self._account_balance,
                MarginLevel=None,
                MarginStopLevel=50.0,
                MarginMode=MarginMode.Max
            )
        self._account_data: Account = copy.deepcopy(self.account_data)

        if self.tick_df is None:
            self.tick_db = DatabaseAPI(broker=self._broker, group=self._group, symbol=self._symbol, timeframe=self.TICK)
            self.tick_db.__enter__()
            self.tick_df = self.tick_db.pull_market_data(start=self._start_str, stop=self._stop_str, window=None)
        self._tick_df_iterator = self.tick_df.iter_rows()
        tick_data_next_row = next(self._tick_df_iterator)
        self._tick_data_next = Bar(*tick_data_next_row)
        self._tick_open_next = None

        if self.bar_df is None:
            self.bar_db = DatabaseAPI(broker=self._broker, group=self._group, symbol=self._symbol, timeframe=self._timeframe)
            self.bar_db.__enter__()
            self.bar_df = self.bar_db.pull_market_data(start=self._start_str, stop=self._stop_str, window=self.window)
            self.offset = self.bar_df.height - self.window + 1
        self._offset = self.offset
        self._bar_df_iterator = self.bar_df.filter((pl.col(str(Bar.Timestamp)) >= self._start_date) & (pl.col(str(Bar.Timestamp)) <= self._stop_date)).iter_rows()
        start_bar_data_row = self.bar_df.row(self.window)
        start_bar_data_index = Bar(*start_bar_data_row)
        bar_data_at_row = next(self._bar_df_iterator)
        self._bar_data_at = Bar(*bar_data_at_row)
        bar_data_next_row = next(self._bar_df_iterator)
        self._bar_data_next = Bar(*bar_data_next_row)
        while self._bar_data_at.Timestamp.Timestamp < start_bar_data_index.Timestamp.Timestamp:
            self._bar_data_at = self._bar_data_next
            bar_data_next_row = next(self._bar_df_iterator)
            self._bar_data_next = Bar(*bar_data_next_row)
        self._bar_data_at_last = Bar(
            Timestamp=self._bar_data_at.Timestamp,
            GapPrice=self._bar_data_at.GapPrice,
            OpenPrice=self._bar_data_at.OpenPrice,
            HighPrice=self._bar_data_at.OpenPrice,
            LowPrice=self._bar_data_at.OpenPrice,
            ClosePrice=self._bar_data_at.OpenPrice,
            TickVolume=0.0
        )

        if self.symbol_data is None:
            self.symbol_data: Symbol = self.bar_db.pull_symbol_data()

        if self.base_conversion_df is None or self.base_conversion_rate is None or self.quote_conversion_df is None or self.quote_conversion_rate is None:
            symbol_rate = lambda timestamp: self.tick_df.filter(pl.col(str(Bar.Timestamp)) <= timestamp.Timestamp).tail(1).select(str(Bar.OpenPrice)).item()
            base_rate = lambda timestamp: self.base_conversion_df.filter(pl.col(str(Bar.Timestamp)) <= timestamp.Timestamp).tail(1).select(str(Bar.OpenPrice)).item()
            quote_rate = lambda timestamp: self.quote_conversion_df.filter(pl.col(str(Bar.Timestamp)) <= timestamp.Timestamp).tail(1).select(str(Bar.OpenPrice)).item()

            self.base_conversion_db = self.tick_db
            self.base_conversion_df = self.tick_df
            self.base_conversion_rate = lambda timestamp, spread: 1.0

            self.quote_conversion_db = self.tick_db
            self.quote_conversion_df = self.tick_df
            self.quote_conversion_rate = lambda timestamp, spread: 1.0

            if self.account_data.AssetType == self.symbol_data.BaseAssetType:
                self.quote_conversion_rate = lambda timestamp, spread: 1.0 / (symbol_rate(timestamp) + spread)
            elif self.account_data.AssetType == self.symbol_data.QuoteAssetType:
                self.base_conversion_rate = lambda timestamp, spread: symbol_rate(timestamp)
            else:
                if (symbol := f"{self.account_data.AssetType.name}{self.symbol_data.BaseAssetType.name}") in self.SYMBOLS:
                    self.base_conversion_db = DatabaseAPI(broker=self._broker, group=self._group, symbol=symbol, timeframe=self.TICK)
                    self.base_conversion_db.__enter__()
                    self.base_conversion_df = self.base_conversion_db.pull_market_data(start=self._start_str, stop=self._stop_str, window=None)
                    self.base_conversion_rate = lambda timestamp, spread: 1.0 / (base_rate(timestamp) + spread)
                elif (symbol := f"{self.symbol_data.BaseAssetType.name}{self.account_data.AssetType.name}") in self.SYMBOLS:
                    self.base_conversion_db = DatabaseAPI(broker=self._broker, group=self._group, symbol=symbol, timeframe=self.TICK)
                    self.base_conversion_db.__enter__()
                    self.base_conversion_df = self.base_conversion_db.pull_market_data(start=self._start_str, stop=self._stop_str, window=None)
                    self.base_conversion_rate = lambda timestamp, spread: base_rate(timestamp)
                else:
                    self._log.error(lambda: f"Base Asset to Account Asset convertion formula not found")

                if (symbol := f"{self.account_data.AssetType.name}{self.symbol_data.QuoteAssetType.name}") in self.SYMBOLS:
                    self.quote_conversion_db = DatabaseAPI(broker=self._broker, group=self._group, symbol=symbol, timeframe=self.TICK)
                    self.quote_conversion_db.__enter__()
                    self.quote_conversion_df = self.quote_conversion_db.pull_market_data(start=self._start_str, stop=self._stop_str, window=None)
                    self.quote_conversion_rate = lambda timestamp, spread: 1.0 / (quote_rate(timestamp) + spread)
                elif (symbol := f"{self.symbol_data.QuoteAssetType.name}{self.account_data.AssetType.name}") in self.SYMBOLS:
                    self.quote_conversion_db = DatabaseAPI(broker=self._broker, group=self._group, symbol=symbol, timeframe=self.TICK)
                    self.quote_conversion_db.__enter__()
                    self.quote_conversion_df = self.quote_conversion_db.pull_market_data(start=self._start_str, stop=self._stop_str, window=None)
                    self.quote_conversion_rate = lambda timestamp, spread: quote_rate(timestamp)
                else:
                    self._log.error(lambda: f"Quote Asset to Account Asset convertion formula not found")

        if self.spread_fee is None:

            def build_spread_fee_points(points: float):
                return lambda timestamp, price: points * self.symbol_data.PointSize

            def build_spread_fee_pips(pips: float):
                return lambda timestamp, price: pips * self.symbol_data.PipSize

            def build_spread_fee_percent(percent: float):
                return lambda timestamp, price: (percent / 100.0) * price

            match self._spread_type:
                case SpreadType.Points:
                    self.spread_fee = build_spread_fee_points(points=self._spread_value)
                case SpreadType.Pips:
                    self.spread_fee = build_spread_fee_pips(pips=self._spread_value)
                case SpreadType.Percentage:
                    self.spread_fee = build_spread_fee_percent(percent=self._spread_value)
                case SpreadType.Accurate:
                    raise NotImplementedError

        if self.commission_fee is None:

            def build_commission_fee_points(points: float):
                def fn(timestamp, volume, spread):
                    total_quote = volume * (-points * self.symbol_data.PointSize)
                    return total_quote * self.quote_conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            def build_commission_fee_pips(pips: float):
                def fn(timestamp, volume, spread):
                    total_quote = volume * (-pips * self.symbol_data.PipSize)
                    return total_quote * self.quote_conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            def build_commission_fee_percent(percent: float):
                def fn(timestamp, volume, spread):
                    notional_quote = volume * symbol_rate(timestamp)
                    total_quote = (-percent / 100.0) * notional_quote
                    return total_quote * self.quote_conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            def build_commission_fee_amount(amount: float):
                return lambda timestamp, volume, spread: -amount

            def build_commission_fee_ratio(ratio: float, size: float, conversion_rate: Callable):
                def fn(timestamp, volume, spread):
                    total = volume * (-ratio / size)
                    return total * conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            match self._commission_type:
                case CommissionType.Points:
                    self.commission_fee = build_commission_fee_points(points=self._commission_value)
                case CommissionType.Pips:
                    self.commission_fee = build_commission_fee_pips(pips=self._commission_value)
                case CommissionType.Percentage:
                    self.commission_fee = build_commission_fee_percent(percent=self._commission_value)
                case CommissionType.Amount:
                    self.commission_fee = build_commission_fee_amount(amount=self._commission_value)
                case CommissionType.Accurate:
                    match self.symbol_data.CommissionMode:
                        case CommissionMode.BaseAssetPerMillionVolume:
                            self.commission_fee = build_commission_fee_ratio(ratio=self.symbol_data.Commission, size=1_000_000, conversion_rate=self.base_conversion_rate)
                        case CommissionMode.BaseAssetPerOneLot:
                            self.commission_fee = build_commission_fee_ratio(ratio=self.symbol_data.Commission, size=self.symbol_data.LotSize, conversion_rate=self.base_conversion_rate)
                        case CommissionMode.PercentageOfVolume:
                            self.commission_fee = build_commission_fee_percent(percent=self.symbol_data.Commission)
                        case CommissionMode.QuoteAssetPerOneLot:
                            self.commission_fee = build_commission_fee_ratio(ratio=self.symbol_data.Commission, size=self.symbol_data.LotSize, conversion_rate=self.quote_conversion_rate)

        if self.swap_buy_fee is None or self.swap_sell_fee is None:

            def calculate_overnights(entry_timestamp, exit_timestamp) -> int:

                entry_timestamp = entry_timestamp.Timestamp
                exit_timestamp = exit_timestamp.Timestamp

                def isdst(timestamp):
                    return bool(localtime(timestamp.timestamp()).tm_isdst)

                def rollover(at_timestamp: datetime, at_isdst, period=timedelta(hours=self.symbol_data.SwapPeriod)):
                    to_timestamp = at_timestamp + period
                    to_isdst = isdst(to_timestamp)
                    if at_isdst and not to_isdst:
                        to_timestamp = to_timestamp.replace(hour=self.symbol_data.SwapWinterTime)
                        return to_timestamp, to_isdst
                    if not at_isdst and to_isdst:
                        to_timestamp = to_timestamp.replace(hour=self.symbol_data.SwapSummerTime)
                        return to_timestamp, to_isdst
                    return to_timestamp, to_isdst

                if exit_timestamp <= entry_timestamp:
                    return 0

                rollover_isdst = isdst(entry_timestamp)
                rollover_timestamp = datetime(
                    year=entry_timestamp.year,
                    month=entry_timestamp.month,
                    day=entry_timestamp.day,
                    hour=self.symbol_data.SwapSummerTime if rollover_isdst else self.symbol_data.SwapWinterTime,
                )

                while rollover_timestamp < entry_timestamp:
                    rollover_timestamp, rollover_isdst = rollover(rollover_timestamp, rollover_isdst)

                overnights = 0
                while rollover_timestamp < exit_timestamp:
                    mul = 0
                    match rollover_timestamp.weekday():
                        case self.symbol_data.SwapExtraDay.value:
                            mul = 3
                        case Day.Saturday.value | Day.Sunday.value:
                            mul = 0
                        case _:
                            mul = 1
                    overnights += mul
                    rollover_timestamp, rollover_isdst = rollover(rollover_timestamp, rollover_isdst)
                return overnights

            def build_swap_fee_points(points: float):
                def fn(timestamp, entry_timestamp, exit_timestamp, volume, spread):
                    overnights = calculate_overnights(entry_timestamp, exit_timestamp)
                    total_quote = volume * points * self.symbol_data.PointSize * overnights
                    return total_quote * self.quote_conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            def build_swap_fee_pips(pips: float):
                def fn(timestamp, entry_timestamp, exit_timestamp, volume, spread):
                    overnights = calculate_overnights(entry_timestamp, exit_timestamp)
                    total_quote = volume * pips * self.symbol_data.PipSize * overnights
                    return total_quote * self.quote_conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            def build_swap_fee_percent(percent: float, day_count: int = 365):
                def fn(timestamp, entry_timestamp, exit_timestamp, volume, spread):
                    overnights = calculate_overnights(entry_timestamp, exit_timestamp)
                    notional_quote = volume * symbol_rate(timestamp)
                    total_quote = notional_quote * (percent / 100.0) * (overnights / day_count)
                    return total_quote * self.quote_conversion_rate(timestamp=timestamp, spread=spread)
                return fn

            def build_swap_fee_amount(amount: float):
                return lambda timestamp, entry_timestamp, exit_timestamp, volume, spread: amount

            match self._swap_type:
                case SwapType.Points:
                    self.swap_buy_fee = build_swap_fee_points(points=self._swap_buy)
                    self.swap_sell_fee = build_swap_fee_points(points=self._swap_sell)
                case SwapType.Pips:
                    self.swap_buy_fee = build_swap_fee_pips(pips=self._swap_buy)
                    self.swap_sell_fee = build_swap_fee_pips(pips=self._swap_sell)
                case SwapType.Percentage:
                    self.swap_buy_fee = build_swap_fee_percent(percent=self._swap_buy)
                    self.swap_sell_fee = build_swap_fee_percent(percent=self._swap_sell)
                case SwapType.Amount:
                    self.swap_buy_fee = build_swap_fee_amount(amount=self._swap_buy)
                    self.swap_sell_fee = build_swap_fee_amount(amount=self._swap_sell)
                case SwapType.Accurate:
                    match self.symbol_data.SwapMode:
                        case SwapMode.Pips:
                            self.swap_buy_fee = build_swap_fee_pips(pips=self.symbol_data.SwapLong)
                            self.swap_sell_fee = build_swap_fee_pips(pips=self.symbol_data.SwapShort)
                        case SwapMode.Percentage:
                            self.swap_buy_fee = build_swap_fee_percent(percent=self.symbol_data.SwapLong)
                            self.swap_sell_fee = build_swap_fee_percent(percent=self.symbol_data.SwapShort)

        self._update_id_queue = Queue()
        self._update_args_queue = Queue()

        return super().__enter__()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.tick_db:
            self.tick_db.__exit__(None, None, None)
        if self.bar_db:
            self.bar_db.__exit__(None, None, None)
        if self.base_conversion_db:
            self.base_conversion_db.__exit__(None, None, None)
        if self.quote_conversion_db:
            self.quote_conversion_db.__exit__(None, None, None)
        return super().__exit__(exc_type, exc_value, exc_traceback)

    def _calculate_ask_bid(self, timestamp: Timestamp, price: Price) -> tuple[float, float]:
        return price.Price + self.spread_fee(timestamp=timestamp, price=price), price.Price

    def _update_position(self, pid: int, position: Position) -> None:
        self._positions[pid] = position

    def _delete_position(self, pid: int) -> None:
        del self._positions[pid]

    def _find_position(self, pid: int) -> Union[Position, None]:
        return self._positions[pid] if pid in self._positions else None

    def _next_pid(self):
        next(self._tids)
        return next(self._pids)

    def _next_tid(self):
        return next(self._tids)

    def _calculate_statistics(self, entry_timestamp: datetime, exit_timestamp: datetime, trade_type: Direction, volume: float, price_delta: float, tick: Tick) -> tuple[float, float, float, float, float, float, float]:
        quantity = volume / self.symbol_data.LotSize
        points = price_delta / self.symbol_data.PointSize
        pips = price_delta / self.symbol_data.PipSize
        spread = tick.Spread.Price
        gross_pnl = price_delta * volume * self.quote_conversion_rate(timestamp=tick.Timestamp, spread=spread)
        commission_pnl = self.commission_fee(timestamp=tick.Timestamp, volume=volume, spread=spread)
        swap_pnl = 0.0
        match trade_type:
            case Direction.Buy:
                swap_pnl = self.swap_buy_fee(
                    timestamp=tick.Timestamp,
                    entry_timestamp=entry_timestamp,
                    exit_timestamp=exit_timestamp,
                    volume=volume,
                    spread=spread
                )
            case Direction.Sell:
                swap_pnl = self.swap_sell_fee(
                    timestamp=tick.Timestamp,
                    entry_timestamp=entry_timestamp,
                    exit_timestamp=exit_timestamp,
                    volume=volume,
                    spread=spread
                )
        used_margin = 0.0
        return quantity, points, pips, gross_pnl, commission_pnl, swap_pnl, used_margin

    def _open_position(self, position_type: PositionType, trade_type: Direction, volume: float, entry_price: float, sl_price: Union[float, None], tp_price: Union[float, None], price_delta: float, tick: Tick) -> Position:
        pid = self._next_pid()
        entry_timestamp = tick.Timestamp
        quantity, points, pips, gross_pnl, commission_pnl, swap_pnl, used_margin = self._calculate_statistics(
            entry_timestamp=entry_timestamp,
            exit_timestamp=entry_timestamp,
            trade_type=trade_type,
            volume=volume,
            price_delta=price_delta,
            tick=tick
        )
        net_pnl = gross_pnl + commission_pnl + swap_pnl
        return Position(
            PositionID=pid,
            PositionType=position_type,
            Direction=trade_type,
            EntryTimestamp=entry_timestamp,
            EntryPrice=entry_price,
            Volume=volume,
            Quantity=quantity,
            Points=points,
            Pips=pips,
            GrossPnL=gross_pnl,
            CommissionPnL=commission_pnl,
            SwapPnL=swap_pnl,
            NetPnL=net_pnl,
            UsedMargin=used_margin,
            StopLoss=sl_price,
            TakeProfit=tp_price
        )

    def _open_buy_position(self, position_type: PositionType, volume: float, sl_price_delta: Union[float, None], tp_price_delta: Union[float, None], tick: Tick) -> Position:
        entry_price = tick.Ask.Price
        sl_price = None if sl_price_delta is None else entry_price - sl_price_delta
        tp_price = None if tp_price_delta is None else entry_price + tp_price_delta
        price_delta = tick.Bid.Price - entry_price
        return self._open_position(position_type, Direction.Buy, volume, entry_price, sl_price, tp_price, price_delta, tick)

    def _open_sell_position(self, position_type: PositionType, volume: float, sl_price_delta: Union[float, None], tp_price_delta: Union[float, None], tick: Tick) -> Position:
        entry_price = tick.Bid.Price
        sl_price = None if sl_price_delta is None else entry_price + sl_price_delta
        tp_price = None if tp_price_delta is None else entry_price - tp_price_delta
        price_delta = entry_price - tick.Ask.Price
        return self._open_position(position_type, Direction.Sell, volume, entry_price, sl_price, tp_price, price_delta, tick)

    def _close_position(self, position: Position, exit_price: float, price_delta: float, tick: Tick) -> Trade:
        tid = self._next_tid()
        trade_type = position.Direction
        entry_timestamp = position.EntryTimestamp
        exit_timestamp = tick.Timestamp
        quantity, points, pips, gross_pnl, commission_pnl, swap_pnl, used_margin = self._calculate_statistics(
            entry_timestamp=entry_timestamp,
            exit_timestamp=exit_timestamp,
            trade_type=trade_type,
            volume=position.Volume,
            price_delta=price_delta,
            tick=tick
        )
        commission_pnl += position.CommissionPnL
        swap_pnl += position.SwapPnL
        net_pnl = gross_pnl + commission_pnl + swap_pnl
        return Trade(
            PositionID=position.PositionID,
            TradeID=tid,
            Type=position.Type,
            Direction=trade_type,
            EntryTimestamp=entry_timestamp,
            ExitTimestamp=exit_timestamp,
            EntryPrice=position.EntryPrice,
            ExitPrice=exit_price,
            Volume=position.Volume,
            Quantity=quantity,
            Points=points,
            Pips=pips,
            GrossPnL=gross_pnl,
            CommissionPnL=commission_pnl,
            SwapPnL=swap_pnl,
            NetPnL=net_pnl
        )

    def _close_buy_position(self, position: Position, tick: Tick) -> Trade:
        exit_price = tick.Bid.Price
        price_delta = exit_price - position.EntryPrice.Price
        return self._close_position(position, exit_price, price_delta, tick)

    def _close_sell_position(self, position: Position, tick: Tick) -> Trade:
        exit_price = tick.Ask.Price
        price_delta = position.EntryPrice.Price - exit_price
        return self._close_position(position, exit_price, price_delta, tick)

    def send_action_complete(self, action: CompleteAction) -> None:
        pass

    def send_action_open(self, action: Union[OpenBuyAction, OpenSellAction]) -> None:
        if action.Volume > self.symbol_data.VolumeInUnitsMax:
            return self._log.error(lambda: f"Action Open: Invalid Volume above the maximum units ({action.Volume})")
        if action.Volume < self.symbol_data.VolumeInUnitsMin:
            return self._log.error(lambda: f"Action Open: Invalid Volume below the minimum units ({action.Volume})")
        if not equals(action.Volume % self.symbol_data.VolumeInUnitsStep, 0.0):
            return self._log.error(lambda: f"Action Open: Invalid Volume not normalised to minimum step ({action.Volume})")
        if action.StopLoss:
            action.StopLoss = action.StopLoss * self.symbol_data.PipSize
            if action.StopLoss < self.symbol_data.PointSize:
                self._log.error(lambda: f"Action Open: Invalid Stop Loss below the minimum tick ({action.StopLoss})")
                action.StopLoss = None
        if action.TakeProfit:
            action.TakeProfit = action.TakeProfit * self.symbol_data.PipSize
            if action.TakeProfit < self.symbol_data.PointSize:
                self._log.error(lambda: f"Action Open: Invalid Take Profit below the minimum tick ({action.TakeProfit})")
                action.TakeProfit = None

        update_id: Union[UpdateID, None] = None
        position: Union[Position, None] = None
        match action.ActionID:
            case ActionID.OpenBuy:
                update_id = UpdateID.OpenedBuy
                position = self._open_buy_position(action.PositionType, action.Volume, action.StopLoss, action.TakeProfit, self._tick_open_next)
            case ActionID.OpenSell:
                update_id = UpdateID.OpenedSell
                position = self._open_sell_position(action.PositionType, action.Volume, action.StopLoss, action.TakeProfit, self._tick_open_next)

        self._update_position(position.PositionID, position)
        self._update_id_queue.put(update_id)
        self._update_args_queue.put(self._bar_data_at_last)
        self._update_args_queue.put(self._account_data)
        self._update_args_queue.put(position)
        return self._update_id_queue.put(UpdateID.Complete)

    def send_action_modify_volume(self, action: Union[ModifyBuyVolumeAction, ModifySellVolumeAction]) -> None:
        position: Position = self._find_position(action.PositionID)
        if not position:
            return self._log.error(lambda: "Action Modify Volume: Position not found")
        if equals(action.Volume, position.Volume):
            return self._log.error(lambda: f"Action Modify Volume: Invalid new Volume equal to old Volume ({action.Volume})")
        if action.Volume > self.symbol_data.VolumeInUnitsMax:
            return self._log.error(lambda: f"Action Modify Volume: Invalid Volume above the maximum units ({action.Volume})")
        if action.Volume < self.symbol_data.VolumeInUnitsMin:
            return self._log.error(lambda: f"Action Modify Volume: Invalid Volume below the minimum units ({action.Volume})")
        if not equals(action.Volume % self.symbol_data.VolumeInUnitsStep, 0.0):
            return self._log.error(lambda: f"Action Modify Volume: Invalid Volume not normalised to minimum step ({action.Volume})")

        update_id: Union[UpdateID, None] = None
        trade: Union[Trade, None] = None

        initial_volume: float = position.Volume
        initial_commission: float = position.CommissionPnL

        position.Volume = initial_volume - action.Volume
        closing_volume_ratio = position.Volume / initial_volume
        remaining_volume_ratio = action.Volume / initial_volume
        position.CommissionPnL = initial_commission * closing_volume_ratio

        match action.ActionID:
            case ActionID.ModifyBuyVolume:
                if equals(action.Volume, 0.0):
                    self._log.warning(lambda: f"Action Modify Volume: Closing Buy position as Volume is zero")
                    return self.send_action_close(CloseBuyAction(action.PositionID))
                update_id = UpdateID.ModifiedBuyVolume
                trade = self._close_buy_position(position, self._tick_open_next)
            case ActionID.ModifySellVolume:
                if equals(action.Volume, 0.0):
                    self._log.warning(lambda: f"Action Modify Volume: Closing Sell position as Volume is zero")
                    return self.send_action_close(CloseSellAction(action.PositionID))
                update_id = UpdateID.ModifiedSellVolume
                trade = self._close_sell_position(position, self._tick_open_next)

        position.Volume = action.Volume
        position.CommissionPnL = initial_commission * remaining_volume_ratio

        self._account_data.Balance += trade.NetPnL
        self._account_data.Equity += trade.NetPnL
        self._update_position(position.PositionID, position)
        self._update_id_queue.put(update_id)
        self._update_args_queue.put(self._bar_data_at_last)
        self._update_args_queue.put(self._account_data)
        self._update_args_queue.put(position)
        self._update_args_queue.put(trade)
        return self._update_id_queue.put(UpdateID.Complete)

    def send_action_modify_stop_loss(self, action: Union[ModifyBuyStopLossAction, ModifySellStopLossAction]) -> None:
        position: Position = self._find_position(action.PositionID)
        if not position:
            return self._log.error(lambda: "Action Modify Stop Loss: Position not found")
        if equals(action.StopLoss, position.StopLoss.Price):
            return self._log.error(lambda: f"Action Modify Stop Loss: Invalid new Stop Loss equal to old Stop Loss ({action.StopLoss})")

        update_id: Union[UpdateID, None] = None
        match action.ActionID:
            case ActionID.ModifyBuyStopLoss:
                if action.StopLoss > self._tick_open_next.Bid.Price:
                    return self._log.error(lambda: f"Action Modify Stop Loss: Invalid Buy Stop Loss above to the Bid Price ({action.StopLoss})")
                update_id = UpdateID.ModifiedBuyStopLoss
            case ActionID.ModifySellStopLoss:
                if action.StopLoss < self._tick_open_next.Ask.Price:
                    return self._log.error(lambda: f"Action Modify Stop Loss: Invalid Sell Stop Loss below the Ask Price ({action.StopLoss})")
                update_id = UpdateID.ModifiedSellStopLoss

        position.StopLoss = action.StopLoss
        self._update_position(position.PositionID, position)
        self._update_id_queue.put(update_id)
        self._update_args_queue.put(self._bar_data_at_last)
        self._update_args_queue.put(self._account_data)
        self._update_args_queue.put(position)
        return self._update_id_queue.put(UpdateID.Complete)

    def send_action_modify_take_profit(self, action: Union[ModifyBuyTakeProfitAction, ModifySellTakeProfitAction]) -> None:
        position: Position = self._find_position(action.PositionID)
        if not position:
            return self._log.error(lambda: "Action Modify Take Profit: Position not found")
        if equals(action.TakeProfit, position.TakeProfit.Price):
            return self._log.error(lambda: f"Action Modify Take Profit: Invalid new Take Profit equal to old Take Profit ({action.TakeProfit})")

        update_id: Union[UpdateID, None] = None
        match action.ActionID:
            case ActionID.ModifyBuyTakeProfit:
                if action.TakeProfit < self._tick_open_next.Bid.Price:
                    return self._log.error(lambda: f"Action Modify Take Profit: Invalid Buy Take Profit below the Bid Price ({action.TakeProfit})")
                update_id = UpdateID.ModifiedBuyTakeProfit
            case ActionID.ModifySellTakeProfit:
                if action.TakeProfit > self._tick_open_next.Ask.Price:
                    return self._log.error(lambda: f"Action Modify Take Profit: Invalid Sell Take Profit above the Entry Price ({action.TakeProfit})")
                update_id = UpdateID.ModifiedSellTakeProfit

        position.TakeProfit = action.TakeProfit
        self._update_position(position.PositionID, position)
        self._update_id_queue.put(update_id)
        self._update_args_queue.put(self._bar_data_at_last)
        self._update_args_queue.put(self._account_data)
        self._update_args_queue.put(position)
        return self._update_id_queue.put(UpdateID.Complete)

    def send_action_close(self, action: Union[CloseBuyAction, CloseSellAction], tick: Tick = None) -> None:
        position: Position = self._find_position(action.PositionID)
        if not position:
            return self._log.error(lambda: "Action Close: Position not found")

        update_id: Union[UpdateID, None] = None
        trade: Union[Trade, None] = None
        match action.ActionID:
            case ActionID.CloseBuy:
                update_id = UpdateID.ClosedBuy
                trade = self._close_buy_position(position, self._tick_open_next if not tick else tick)
            case ActionID.CloseSell:
                update_id = UpdateID.ClosedSell
                trade = self._close_sell_position(position, self._tick_open_next if not tick else tick)

        self._account_data.Balance += trade.NetPnL
        self._account_data.Equity += trade.NetPnL
        self._delete_position(position.PositionID)
        self._update_id_queue.put(update_id)
        self._update_args_queue.put(self._bar_data_at_last)
        self._update_args_queue.put(self._account_data)
        self._update_args_queue.put(trade)
        return self._update_id_queue.put(UpdateID.Complete)

    def send_action_ask_above_target(self, action: AskAboveTargetAction) -> None:
        self._ask_above_target = action.Ask

    def send_action_ask_below_target(self, action: AskBelowTargetAction) -> None:
        self._ask_below_target = action.Ask

    def send_action_bid_above_target(self, action: BidAboveTargetAction) -> None:
        self._bid_above_target = action.Bid

    def send_action_bid_below_target(self, action: BidBelowTargetAction) -> None:
        self._bid_below_target = action.Bid

    def receive_update_id(self) -> UpdateID:

        while self._bar_data_next or self._tick_data_next or not self._update_id_queue.empty():

            if not self._update_id_queue.empty():
                return self._update_id_queue.get()

            if self._bar_data_next and (not self._tick_data_next or self._tick_data_next.Timestamp.Timestamp >= self._bar_data_next.Timestamp.Timestamp):

                self._update_id_queue.put(UpdateID.BarClosed)
                self._update_args_queue.put(self._bar_data_at)
                self._update_id_queue.put(UpdateID.Complete)

                self._bar_data_at_last = Bar(
                    Timestamp=self._bar_data_next.Timestamp,
                    GapPrice=self._bar_data_at.ClosePrice,
                    OpenPrice=self._bar_data_next.OpenPrice,
                    HighPrice=self._bar_data_next.OpenPrice,
                    LowPrice=self._bar_data_next.OpenPrice,
                    ClosePrice=self._bar_data_next.OpenPrice,
                    TickVolume=0.0,
                )
                self._bar_data_at = self._bar_data_next
                try:
                    bar_data_next_row = next(self._bar_df_iterator)
                    self._bar_data_next = Bar(*bar_data_next_row)
                except StopIteration:
                    self._bar_data_next = None
                continue

            if self._tick_data_next:

                high_ask_at, high_bid_at = self._calculate_ask_bid(timestamp=self._tick_data_next.Timestamp, price=self._tick_data_next.HighPrice)
                low_ask_at, low_bid_at = self._calculate_ask_bid(timestamp=self._tick_data_next.Timestamp, price=self._tick_data_next.LowPrice)

                self._bar_data_at_last.HighPrice = max(self._bar_data_at_last.HighPrice.Price, self._tick_data_next.HighPrice.Price)
                self._bar_data_at_last.LowPrice = min(self._bar_data_at_last.LowPrice.Price, self._tick_data_next.LowPrice.Price)
                self._bar_data_at_last.ClosePrice = self._tick_data_next.ClosePrice
                self._bar_data_at_last.TickVolume += self._tick_data_next.TickVolume

                try:
                    tick_data_next_row = next(self._tick_df_iterator)
                    self._tick_data_next = Bar(*tick_data_next_row)
                    self._tick_open_next = Tick(self._tick_data_next.Timestamp, *self._calculate_ask_bid(timestamp=self._tick_data_next.Timestamp, price=self._tick_data_next.OpenPrice))
                except StopIteration:
                    self._tick_data_next = None

                for position_id, position in list(self._positions.items()):
                    match position.Direction:
                        case Direction.Buy:
                            if position.StopLoss.Price is not None:
                                if low_bid_at <= position.StopLoss.Price:
                                    self.send_action_close(CloseBuyAction(position_id), Tick(self._tick_open_next.Timestamp, low_ask_at, low_bid_at))
                                    continue
                                if self._tick_open_next.Bid.Price <= position.StopLoss.Price:
                                    self.send_action_close(CloseBuyAction(position_id))
                                    continue
                            if position.TakeProfit.Price is not None:
                                if high_bid_at >= position.TakeProfit.Price:
                                    self.send_action_close(CloseBuyAction(position_id), Tick(self._tick_open_next.Timestamp, high_ask_at, high_bid_at))
                                    continue
                                if self._tick_open_next.Bid.Price >= position.TakeProfit.Price:
                                    self.send_action_close(CloseBuyAction(position_id))
                                    continue
                        case Direction.Sell:
                            if position.StopLoss.Price is not None:
                                if high_ask_at >= position.StopLoss.Price:
                                    self.send_action_close(CloseSellAction(position_id), Tick(self._tick_open_next.Timestamp, high_ask_at, high_bid_at))
                                    continue
                                if self._tick_open_next.Ask.Price >= position.StopLoss.Price:
                                    self.send_action_close(CloseSellAction(position_id))
                                    continue
                            if position.TakeProfit.Price is not None:
                                if low_ask_at <= position.TakeProfit.Price:
                                    self.send_action_close(CloseSellAction(position_id), Tick(self._tick_open_next.Timestamp, low_ask_at, low_bid_at))
                                    continue
                                if self._tick_open_next.Ask.Price <= position.TakeProfit.Price:
                                    self.send_action_close(CloseSellAction(position_id))
                                    continue

                if self._ask_above_target is not None and self._tick_open_next.Ask.Price >= self._ask_above_target:
                    self._update_id_queue.put(UpdateID.AskAboveTarget)
                    self._update_args_queue.put(self._tick_open_next)
                    self._update_id_queue.put(UpdateID.Complete)

                if self._ask_below_target is not None and self._tick_open_next.Ask.Price <= self._ask_below_target:
                    self._update_id_queue.put(UpdateID.AskBelowTarget)
                    self._update_args_queue.put(self._tick_open_next)
                    self._update_id_queue.put(UpdateID.Complete)

                if self._bid_above_target is not None and self._tick_open_next.Bid.Price >= self._bid_above_target:
                    self._update_id_queue.put(UpdateID.BidAboveTarget)
                    self._update_args_queue.put(self._tick_open_next)
                    self._update_id_queue.put(UpdateID.Complete)

                if self._bid_below_target is not None and self._tick_open_next.Bid.Price <= self._bid_below_target:
                    self._update_id_queue.put(UpdateID.BidBelowTarget)
                    self._update_args_queue.put(self._tick_open_next)
                    self._update_id_queue.put(UpdateID.Complete)

        return UpdateID.Shutdown

    def receive_update_account(self) -> Account:
        return self._update_args_queue.get()

    def receive_update_symbol(self) -> Symbol:
        return self._update_args_queue.get()

    def receive_update_position(self) -> Position:
        return self._update_args_queue.get()

    def receive_update_trade(self) -> Trade:
        return self._update_args_queue.get()

    def receive_update_bar(self) -> Bar:
        return self._update_args_queue.get()

    def receive_update_target(self) -> Tick:
        return self._update_args_queue.get()

    def system_management(self) -> MachineAPI:

        system_engine = MachineAPI("System Management")

        initialisation = system_engine.create_state(name="Initialisation", end=False)
        execution = system_engine.create_state(name="Execution", end=False)
        termination = system_engine.create_state(name="Termination", end=True)

        def init_market(update: CompleteUpdate):
            update.Market.init_data(self.bar_df)
            update.Indicator.init_data(update.Market)
            update.Market.update_offset(self.offset)
            update.Indicator.update_offset(self.offset)

        def update_market(update: BarUpdate):
            self._offset -= 1
            update.Market.update_offset(self._offset)
            update.Indicator.update_offset(self._offset)

        def update_results(update: CompleteUpdate):
            from Library.Portfolio.Statistics import StatisticsAPI
            self.individual_trades, self.aggregated_trades, self.statistics = StatisticsAPI.data(update.Portfolio.TradesDataframe, self.account_data, self._start_date, self._stop_date)
            self._log.warning(lambda: str(self.individual_trades))
            self._log.warning(lambda: str(self.aggregated_trades))
            self._log.warning(lambda: str(self.statistics))

        initialisation.on_complete(to=execution, action=init_market, reason="Market Initialized")
        initialisation.on_shutdown(to=termination, action=None, reason="Abruptly Terminated")

        execution.on_bar_closed(to=execution, action=update_market, reason=None)
        execution.on_shutdown(to=termination, action=update_results, reason="Safely Terminated")

        return system_engine

    @timer
    def run(self) -> None:
        self._update_id_queue.put(UpdateID.Account)
        self._update_args_queue.put(self.account_data)

        self._update_id_queue.put(UpdateID.Symbol)
        self._update_args_queue.put(self.symbol_data)

        self._update_id_queue.put(UpdateID.Complete)

        self.deploy(strategy=self.strategy, market=self.market, indicator=self.indicator, portfolio=self.portfolio)