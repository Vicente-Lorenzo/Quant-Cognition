from __future__ import annotations

import contextlib
import hashlib
import math
import threading

from pathlib import Path
from collections import deque
from dataclasses import dataclass
from itertools import count
from datetime import date, datetime, timedelta
from typing import Any, Type, Union, Iterator, TYPE_CHECKING

from Library.Database.Database import DatabaseAPI
from Library.Database.Dataframe import np, pl
from Library.Database.Postgres.Postgres import PostgresAPI
from Library.Engine import MachineAPI
from Library.Indicator.Indicator import IndicatorAPI
from Library.Market.Bar import BarAPI
from Library.Market.Market import MarketAPI
from Library.Market.Price import Direction, PriceAPI
from Library.Market.Tick import TickAPI
from Library.Portfolio.Account import AccountAPI, AccountType, Environment, MarginMode
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import (
    ActionAPI,
    ActionID,
    ModifyBuyPositionStopLossActionAPI,
    ModifyBuyPositionTakeProfitActionAPI,
    ModifyBuyPositionVolumeActionAPI,
    ModifySellPositionStopLossActionAPI,
    ModifySellPositionTakeProfitActionAPI,
    ModifySellPositionVolumeActionAPI,
    OpenBuyPositionActionAPI,
    OpenSellPositionActionAPI
)
from Library.Protocol.Update import UpdateID, BarUpdateAPI, CompleteUpdateAPI, InitUpdateAPI
from Library.Universe.Contract import CommissionMode, CommissionType, SpreadType, SwapMode, SwapType
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import MICROSECOND, Weekday, datetime_to_epoch, epoch_to_datetime, is_summer_time, parse_datetime
from Library.Utility.IO import mkdir, read_json, write_json
from Library.Utility.Math import equals, truncate
from Library.Utility.Statistic import Timer, timer
from Library.Utility.Typing import MISSING, Missing
from Library.System.System import SystemAPI

if TYPE_CHECKING:
    from Library.Parameter import Parameter
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Security import SecurityAPI

@dataclass(frozen=True, slots=True)
class DatasetAPI:
    WarmupBars: Union[pl.DataFrame, None]
    ExecutionBars: list[BarAPI]
    TickTimestamps: np.ndarray
    TickAsks: np.ndarray
    TickBids: np.ndarray
    TickConversions: Union[tuple[np.ndarray, ...], None]
    IntraLevels: list[str]
    IntraBars: dict[str, pl.DataFrame]
    IndicatorResults: Union[dict, None] = None

class BacktestingAPI(SystemAPI):

    _EPSILON_: float = 1e-9
    _CACHE_DIR_: Path = Path.home() / ".cache" / "cAlgo" / "preload"
    _CONVERSION_COLUMNS_: tuple = (TickAPI.ID.AskBaseConversion, TickAPI.ID.BidBaseConversion, TickAPI.ID.AskQuoteConversion, TickAPI.ID.BidQuoteConversion)

    _PRELOAD_CACHE_: dict = {}
    _PRELOAD_LOCK_ = threading.Lock()
    _DISK_CACHE_: bool = True

    _db_: DatabaseAPI
    _feed_: Iterator
    _resolution_: TimeframeAPI
    _dataset_: DatasetAPI
    _uid_queue_: deque
    _arg_queue_: deque
    _bar_: BarAPI
    _tick_: TickAPI

    def __init__(self,
                 strategy: Type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 resolution: Union[str, TimeframeAPI, Missing, None],
                 parameters: Parameter,
                 start: Union[str, date, datetime],
                 stop: Union[str, date, datetime],
                 account: tuple[str, float, float],
                 spread: tuple[SpreadType, Union[float, Missing, None]],
                 commission: tuple[CommissionType, Union[float, Missing, None]],
                 swap: tuple[SwapType, Union[float, Missing, None], Union[float, Missing, None]],
                 report: bool = True,
                 export: bool = True,
                 dataset: Union[DatasetAPI, None] = None) -> None:
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, parameters=parameters, universe=(0, 0.0, 0, 0), market=(0, 0.0, 0, 0), portfolio=(0, 0.0, 0, 0), report=report, export=export)
        self._injected_: Union[DatasetAPI, None] = dataset

        self._start_: datetime = parse_datetime(start, end_of_day=False)
        self._stop_: datetime = parse_datetime(stop, end_of_day=True)

        self._account_asset_, self._account_balance_, self._account_leverage_ = account
        self._spread_type_, spread_value, *spread_seed = spread
        self._commission_type_, commission_value = commission
        self._swap_type_, swap_long, swap_short = swap
        if self._spread_type_ == SpreadType.Auto: self._spread_type_ = SpreadType.Accurate
        if self._commission_type_ == CommissionType.Auto: self._commission_type_ = CommissionType.Accurate
        if self._swap_type_ == SwapType.Auto: self._swap_type_ = SwapType.Accurate
        self._spread_value_: Union[float, None] = spread_value if spread_value is not MISSING else None
        self._commission_value_: Union[float, None] = commission_value if commission_value is not MISSING else None
        self._swap_long_: Union[float, None] = swap_long if swap_long is not MISSING else None
        self._swap_short_: Union[float, None] = swap_short if swap_short is not MISSING else None

        self._resolution_arg_: Union[str, TimeframeAPI, Missing, None] = resolution
        self._auto_: bool = False
        self._skipped_bars_: int = 0
        self._descended_bars_: int = 0
        self._arm_version_: int = 0
        self._rng_: np.random.Generator = np.random.default_rng(spread_seed[0] if spread_seed and isinstance(spread_seed[0], int) else None)

        self._stack_: Union[contextlib.ExitStack, None] = None
        self._contract_: Any = None
        self._base_asset_: Union[str, None] = None
        self._quote_asset_: Union[str, None] = None
        self._needs_conversion_: bool = False
        self._digits_: int = 5

        self._window_: int = 0

        self._pids_: count = count(start=-1, step=-1)
        self._tids_: count = count(start=-1, step=-1)
        self._positions_: dict[int, PositionAPI] = {}
        self._ask_above_: Union[float, None] = None
        self._ask_below_: Union[float, None] = None
        self._bid_above_: Union[float, None] = None
        self._bid_below_: Union[float, None] = None

        self._preload_seconds_: float = 0.0

    def _connect_(self) -> None:
        stack = contextlib.ExitStack()
        stack.__enter__()
        self._stack_ = stack
        try:
            self._db_ = stack.enter_context(PostgresAPI(database="Quant"))
            self.strategy = self._strategy_(money_management=self._parameters_.MoneyManagement, risk_management=self._parameters_.RiskManagement, signal_management=self._parameters_.SignalManagement)
            self.market = MarketAPI()
            self.indicator = IndicatorAPI(technical=self._parameters_.TechnicalManagement, fundamental=self._parameters_.FundamentalManagement, sentimental=self._parameters_.SentimentalManagement)
            self.portfolio = PortfolioAPI(Parameter=self._parameters_.PortfolioManagement)
            self._contract_ = self._security_.Contract
            self._digits_ = int(self._contract_.Digits) if getattr(self._contract_, "Digits", None) else 5
            ticker = self._security_.Ticker
            self._base_asset_ = ticker.BaseAsset if ticker else None
            self._quote_asset_ = ticker.QuoteAsset if ticker else None
            self._needs_conversion_ = self._account_asset_ not in (self._base_asset_, self._quote_asset_)
            self._window_ = self._indicator_window_()
            if isinstance(self._resolution_arg_, TimeframeAPI):
                self._resolution_ = self._resolution_arg_
            elif isinstance(self._resolution_arg_, str) and self._resolution_arg_:
                self._resolution_ = TimeframeAPI(UID=self._resolution_arg_, db=self._db_)
            else:
                self._auto_ = True
                self._resolution_ = TimeframeAPI(UID="T1", db=self._db_)
            if self._resolution_ > self._timeframe_:
                raise ValueError(f"Resolution {self._resolution_.UID}: Failed · Due to source coarser than execution timeframe {self._timeframe_.UID}")
            self.account = self._build_account_()
            self._preload_()
        except Exception:
            stack.__exit__(None, None, None)
            raise
        self._uid_queue_ = deque()
        self._arg_queue_ = deque()
        self._feed_ = self._generate_()
        super()._connect_()

    def _disconnect_(self) -> None:
        super()._disconnect_()
        if self._stack_: self._stack_.__exit__(None, None, None)

    def _indicator_window_(self) -> int:
        windows = [getattr(self.indicator.Technical, "Window", 0) or 0,
                   getattr(self.indicator.Fundamental, "Window", 0) or 0,
                   getattr(self.indicator.Sentimental, "Window", 0) or 0]
        return max(windows)

    def _build_account_(self) -> AccountAPI:
        return AccountAPI(
            Timestamp=self._start_,
            Provider=self._security_.Provider if self._security_ else None,
            Environment=Environment.Demo,
            AccountType=AccountType.Hedged,
            Asset=self._account_asset_,
            Balance=self._account_balance_,
            Equity=self._account_balance_,
            Credit=0.0,
            Leverage=self._account_leverage_,
            MarginUsed=0.0,
            MarginFree=self._account_balance_,
            MarginLevel=None,
            MarginStopLevel=50.0,
            MarginMode=MarginMode.Max,
            Number=0
        )

    def _row_to_bar_(self, row: dict) -> BarAPI:
        def tick(prefix: str) -> TickAPI:
            return TickAPI(
                Security=self._security_,
                Timestamp=row.get(f"{prefix}.Timestamp"),
                Ask=row.get(f"{prefix}.Ask"),
                Bid=row.get(f"{prefix}.Bid"),
                Mid=row.get(f"{prefix}.Mid"),
                AskBaseConversion=row.get(f"{prefix}.AskBaseConversion"),
                BidBaseConversion=row.get(f"{prefix}.BidBaseConversion"),
                AskQuoteConversion=row.get(f"{prefix}.AskQuoteConversion"),
                BidQuoteConversion=row.get(f"{prefix}.BidQuoteConversion"),
                Volume=row.get(f"{prefix}.Volume")
            )
        return BarAPI(
            Security=self._security_,
            Timeframe=self._timeframe_,
            Timestamp=row.get("Timestamp"),
            GapTick=tick("GapTick"),
            OpenTick=tick("OpenTick"),
            HighTick=tick("HighTick"),
            LowTick=tick("LowTick"),
            CloseTick=tick("CloseTick"),
            Volume=row.get("Volume")
        )

    @staticmethod
    def _clean_(df: pl.DataFrame) -> pl.DataFrame:
        if df.is_empty(): return df
        timestamp, open_timestamp = str(BarAPI.ID.Timestamp), str(BarAPI.OID.OpenTick.Timestamp)
        if timestamp in df.columns and open_timestamp in df.columns:
            df = df.filter(pl.col(timestamp) != pl.col(open_timestamp))
        return df.unique(subset=open_timestamp, keep="first", maintain_order=True) if open_timestamp in df.columns else df

    def _load_bars_(self) -> tuple[Union[pl.DataFrame, None], list[BarAPI]]:
        warmup_df = self._clean_(MarketAPI.pull_bars(self._db_, self._security_.UID, self._timeframe_.UID, stop=self._start_, limit=self._window_))
        execution_df = self._clean_(MarketAPI.pull_bars(self._db_, self._security_.UID, self._timeframe_.UID, start=self._start_, stop=self._stop_))
        warmup_bars = [self._row_to_bar_(row) for row in warmup_df.to_dicts()] if warmup_df.height else []
        execution_bars = [self._row_to_bar_(row) for row in execution_df.to_dicts()] if execution_df.height else []
        if execution_bars:
            warmup_bars.append(execution_bars.pop(0))
        warmup_frame = pl.DataFrame([bar.dict(flatten=True) for bar in warmup_bars], strict=False) if warmup_bars else pl.DataFrame()
        return warmup_frame, execution_bars

    def _candidate_rungs_(self) -> list[TimeframeAPI]:
        rungs = [TimeframeAPI(UID=uid, db=self._db_) for uid in ("H1", "M1")]
        rungs = [rung for rung in rungs if rung < self._timeframe_]
        rungs.sort(reverse=True)
        return rungs

    def _load_frames_(self, bars: list[BarAPI]) -> tuple:
        start = bars[0].OpenTick.Timestamp.DateTime
        stop = bars[-1].CloseTick.Timestamp.DateTime
        bar_level = not self._auto_ and not self._resolution_.IsTick and self._resolution_.Seconds == self._timeframe_.Seconds
        if bar_level and not self._needs_conversion_:
            tick_ts, tick_ask, tick_bid, tick_conversions = np.empty(0, dtype="int64"), np.empty(0, dtype="float64"), np.empty(0, dtype="float64"), None
        else:
            columns = [str(TickAPI.ID.Timestamp), str(TickAPI.ID.Ask), str(TickAPI.ID.Bid)]
            if self._needs_conversion_:
                columns += [str(column) for column in self._CONVERSION_COLUMNS_]
            tick_frame = MarketAPI.pull_ticks(self._db_, self._security_.UID, start, stop, columns=columns)
            if tick_frame.height:
                tick_ts = tick_frame["Timestamp"].dt.epoch("us").to_numpy()
                tick_ask = tick_frame["Ask"].to_numpy()
                tick_bid = tick_frame["Bid"].to_numpy()
            else:
                tick_ts, tick_ask, tick_bid = np.empty(0, dtype="int64"), np.empty(0, dtype="float64"), np.empty(0, dtype="float64")
            if self._needs_conversion_ and tick_frame.height:
                tick_conversions = tuple(tick_frame[str(column)].to_numpy().astype("float64") for column in self._CONVERSION_COLUMNS_)
            else:
                tick_conversions = None
        intra_levels, intra_bars = [], {}
        if self._auto_:
            for rung in self._candidate_rungs_():
                frame = self._clean_(MarketAPI.pull_bars(self._db_, self._security_.UID, rung.UID, start=start, stop=stop))
                if not frame.is_empty():
                    intra_bars[rung.UID] = frame
                    intra_levels.append(rung.UID)
        elif not self._resolution_.IsTick and self._resolution_.Seconds != self._timeframe_.Seconds:
            frame = self._clean_(MarketAPI.pull_bars(self._db_, self._security_.UID, self._resolution_.UID, start=start, stop=stop))
            if not frame.is_empty():
                intra_bars[self._resolution_.UID] = frame
                intra_levels.append(self._resolution_.UID)
        return tick_ts, tick_ask, tick_bid, tick_conversions, intra_levels, intra_bars

    def _cache_signature_(self) -> str:
        key = (self._security_.UID, self._start_.isoformat(), self._stop_.isoformat(), self._timeframe_.UID, self._auto_, None if self._auto_ else self._resolution_.UID)
        return hashlib.md5(repr(key).encode()).hexdigest()

    def _data_token_(self, bars: list[BarAPI]) -> int:
        return MarketAPI.last_tick_uid(self._db_, self._security_.UID, bars[0].OpenTick.Timestamp.DateTime, bars[-1].CloseTick.Timestamp.DateTime)

    def _read_cache_(self, folder: Path, token: int) -> Union[tuple, None]:
        info = read_json(folder / "meta.json")
        if info.get("token") != token or "levels" not in info: return None
        ticks = pl.read_parquet(folder / "ticks.parquet")
        levels = info["levels"]
        intra_bars = {uid: pl.read_parquet(folder / f"intra_{uid}.parquet") for uid in levels}
        names = [str(column) for column in self._CONVERSION_COLUMNS_]
        tick_conversions = tuple(ticks[name].to_numpy() for name in names) if all(name in ticks.columns for name in names) else None
        return ticks["ts"].to_numpy(), ticks["ask"].to_numpy(), ticks["bid"].to_numpy(), tick_conversions, levels, intra_bars

    def _write_cache_(self, folder: Path, frames: tuple, token: int) -> None:
        tick_ts, tick_ask, tick_bid, tick_conversions, intra_levels, intra_bars = frames
        mkdir(folder)
        columns = {"ts": tick_ts, "ask": tick_ask, "bid": tick_bid}
        if tick_conversions is not None:
            for name, array in zip((str(column) for column in self._CONVERSION_COLUMNS_), tick_conversions): columns[name] = array
        pl.DataFrame(columns).write_parquet(folder / "ticks.parquet")
        for uid, frame in intra_bars.items(): frame.write_parquet(folder / f"intra_{uid}.parquet")
        write_json(folder / "meta.json", {"token": token, "levels": intra_levels})

    def _acquire_frames_(self, bars: list[BarAPI]) -> tuple:
        if not self._DISK_CACHE_: return self._load_frames_(bars)
        folder, token = self._CACHE_DIR_ / self._cache_signature_(), self._data_token_(bars)
        cached = self._read_cache_(folder, token)
        if cached is not None and not (self._needs_conversion_ and cached[3] is None): return cached
        frames = self._load_frames_(bars)
        self._write_cache_(folder, frames, token)
        return frames

    def extract(self) -> DatasetAPI:
        return self._dataset_

    def inject(self, dataset: DatasetAPI) -> None:
        self._injected_ = dataset

    def _build_dataset_(self) -> DatasetAPI:
        warmup, bars = self._load_bars_()
        if not bars:
            return DatasetAPI(WarmupBars=warmup, ExecutionBars=[], TickTimestamps=np.empty(0, dtype="int64"), TickAsks=np.empty(0, dtype="float64"), TickBids=np.empty(0, dtype="float64"), TickConversions=None, IntraLevels=[], IntraBars={})
        tick_ts, tick_ask, tick_bid, tick_conversions, intra_levels, intra_bars = self._acquire_frames_(bars)
        return DatasetAPI(WarmupBars=warmup, ExecutionBars=bars, TickTimestamps=tick_ts, TickAsks=tick_ask, TickBids=tick_bid, TickConversions=tick_conversions, IntraLevels=intra_levels, IntraBars=intra_bars)

    def _preload_(self) -> None:
        watch = Timer(); watch.start()
        if self._injected_ is not None:
            self._dataset_ = self._injected_
            outcome = "Injected"
        else:
            key = (self._security_.UID, self._start_, self._stop_, self._timeframe_.UID, self._auto_, None if self._auto_ else self._resolution_.UID)
            with self._PRELOAD_LOCK_:
                reused = key in self._PRELOAD_CACHE_
                if not reused:
                    self._PRELOAD_CACHE_.clear()
                    self._PRELOAD_CACHE_[key] = self._build_dataset_()
                self._dataset_ = self._PRELOAD_CACHE_[key]
            outcome = "Reused" if reused else "Completed"
        watch.stop()
        self._preload_seconds_ = watch.delta()
        ticks = self._dataset_.TickTimestamps.size
        intra = " · ".join(f"{uid}:{self._dataset_.IntraBars[uid].height}" for uid in self._dataset_.IntraLevels) or "Tick"
        self._log_.info(lambda: f"Phase Preload: {outcome} · {watch.result()} · {ticks} Ticks · Intra {intra}")

    @staticmethod
    def _symbol_rate_(tick: TickAPI) -> float:
        return (tick.Ask.Price + tick.Bid.Price) / 2.0

    def _base_conversion_(self, rate: float) -> float:
        return rate if self._account_asset_ == self._quote_asset_ else 1.0

    def _quote_conversion_(self, rate: float) -> float:
        if self._account_asset_ == self._base_asset_: return 1.0 / rate
        return 1.0

    @staticmethod
    def _stored_(price: Union[PriceAPI, None]) -> Union[float, None]:
        return price.Price if price else None

    def _conversions_(self, tick: TickAPI) -> tuple[float, float]:
        base = self._stored_(tick.BidBaseConversion)
        quote = self._stored_(tick.BidQuoteConversion)
        if base is None: base = tick.Bid.Price if self._account_asset_ == self._quote_asset_ else 1.0
        if quote is None: quote = 1.0 / tick.Ask.Price if self._account_asset_ == self._base_asset_ else 1.0
        return base, quote

    def _spread_value_amount_(self, raw_ask: float, raw_bid: float) -> float:
        match self._spread_type_:
            case SpreadType.Points: return (self._spread_value_ or 0.0) * self._contract_.PointSize
            case SpreadType.Percentage: return (self._spread_value_ or 0.0) / 100.0 * raw_bid
            case SpreadType.Random: return self._rng_.uniform(0.0, self._spread_value_ or 0.0) * self._contract_.PointSize
            case _: return raw_ask - raw_bid

    def _round_(self, price: float) -> float:
        return round(price, self._digits_)

    def _effective_ask_bid_(self, raw_ask: float, raw_bid: float) -> tuple[float, float]:
        if self._spread_type_ in (SpreadType.Accurate, SpreadType.Approximate): return self._round_(raw_ask), self._round_(raw_bid)
        return self._round_(raw_bid + self._spread_value_amount_(raw_ask, raw_bid)), self._round_(raw_bid)

    def _ask_bid_(self, tick: TickAPI) -> tuple[float, float]:
        return self._effective_ask_bid_(tick.Ask.Price, tick.Bid.Price)

    def _commission_(self, volume: float, rate: float, base_conversion: Union[float, Missing] = MISSING, quote_conversion: Union[float, Missing] = MISSING) -> float:
        base_conversion = base_conversion if base_conversion is not MISSING else self._base_conversion_(rate)
        quote_conversion = quote_conversion if quote_conversion is not MISSING else self._quote_conversion_(rate)
        match self._commission_type_:
            case CommissionType.Points:
                return volume * (-(self._commission_value_ or 0.0) * self._contract_.PointSize) * quote_conversion
            case CommissionType.Percentage:
                return -(self._commission_value_ or 0.0) / 100.0 * volume * rate * quote_conversion
            case CommissionType.Amount:
                return -(self._commission_value_ or 0.0)
            case CommissionType.Accurate:
                commission = self._contract_.Commission or 0.0
                match self._contract_.CommissionMode:
                    case CommissionMode.BaseAssetPerMillionVolume:
                        return volume * (-commission / 1_000_000) * base_conversion
                    case CommissionMode.BaseAssetPerOneLot:
                        return self._quantity_(volume) * -commission * base_conversion
                    case CommissionMode.PercentageOfVolume:
                        return -commission / 100.0 * volume * rate * quote_conversion
                    case CommissionMode.QuoteAssetPerOneLot:
                        return self._quantity_(volume) * -commission * quote_conversion
        return 0.0

    def _overnights_(self, entry: datetime, exit: datetime) -> int:
        if exit <= entry: return 0
        period = timedelta(hours=self._contract_.SwapPeriod)
        def rollover(at: datetime, at_isdst: bool) -> tuple[datetime, bool]:
            to = at + period
            to_isdst = is_summer_time(to)
            if at_isdst and not to_isdst: return to.replace(hour=self._contract_.SwapWinterTime), to_isdst
            if not at_isdst and to_isdst: return to.replace(hour=self._contract_.SwapSummerTime), to_isdst
            return to, to_isdst
        rollover_isdst = is_summer_time(entry)
        rollover_at = datetime(year=entry.year, month=entry.month, day=entry.day, hour=self._contract_.SwapSummerTime if rollover_isdst else self._contract_.SwapWinterTime)
        while rollover_at < entry: rollover_at, rollover_isdst = rollover(rollover_at, rollover_isdst)
        overnights = 0
        while rollover_at < exit:
            match rollover_at.weekday():
                case day if day == self._contract_.SwapExtraDay.value: overnights += 3
                case day if day in (Weekday.Saturday.value, Weekday.Sunday.value): overnights += 0
                case _: overnights += 1
            rollover_at, rollover_isdst = rollover(rollover_at, rollover_isdst)
        return overnights

    def _swap_(self, direction: Direction, volume: float, rate: float, entry: datetime, exit: datetime, quote_conversion: Union[float, Missing] = MISSING) -> float:
        overnights = self._overnights_(entry, exit)
        if not overnights: return 0.0
        quote_conversion = quote_conversion if quote_conversion is not MISSING else self._quote_conversion_(rate)
        long = direction == Direction.Buy
        match self._swap_type_:
            case SwapType.Points:
                points = (self._swap_long_ if long else self._swap_short_) or 0.0
                return volume * points * self._contract_.PointSize * overnights * quote_conversion
            case SwapType.Percentage:
                percent = (self._swap_long_ if long else self._swap_short_) or 0.0
                return volume * rate * (percent / 100.0) * (overnights / 365.0) * quote_conversion
            case SwapType.Amount:
                return (self._swap_long_ if long else self._swap_short_) or 0.0
            case SwapType.Accurate:
                match self._contract_.SwapMode:
                    case SwapMode.Pips:
                        pips = (self._contract_.SwapLong if long else self._contract_.SwapShort) or 0.0
                        return volume * pips * self._contract_.PipSize * overnights * quote_conversion
                    case SwapMode.Percentage:
                        percent = (self._contract_.SwapLong if long else self._contract_.SwapShort) or 0.0
                        return volume * rate * (percent / 100.0) * (overnights / 365.0) * quote_conversion
        return 0.0

    def _next_pid_(self) -> int:
        next(self._tids_)
        return next(self._pids_)

    def _quantity_(self, volume: float) -> float:
        return volume / self._contract_.LotSize if self._contract_.LotSize else 0.0

    def _build_position_(self, direction: Direction, position_type: PositionType, volume: float, tick: TickAPI, sl_price: Union[float, None], tp_price: Union[float, None]) -> PositionAPI:
        ask, bid = self._ask_bid_(tick)
        entry_price = ask if direction == Direction.Buy else bid
        rate = self._symbol_rate_(tick)
        base_conversion, quote_conversion = self._conversions_(tick)
        gross = (bid - ask) * volume * quote_conversion
        commission = truncate(self._commission_(volume, rate, base_conversion, quote_conversion))
        return PositionAPI(
            UID=self._next_pid_(),
            Account=self.account,
            Security=self._security_,
            Type=position_type,
            Direction=direction,
            EntryTimestamp=tick.Timestamp.DateTime,
            EntryPrice=entry_price,
            Volume=volume,
            Quantity=self._quantity_(volume),
            GrossPnL=gross,
            CommissionPnL=commission,
            SwapPnL=0.0,
            NetPnL=gross + commission,
            UsedMargin=0.0,
            StopLossPrice=sl_price,
            TakeProfitPrice=tp_price,
            Label=self.__class__.__name__,
            Comment=position_type.name
        )

    def _build_trade_(self, position: PositionAPI, volume: float, tick: TickAPI, exit_price: float) -> TradeAPI:
        direction = position.Direction
        rate = self._symbol_rate_(tick)
        base_conversion, quote_conversion = self._conversions_(tick)
        entry = position.EntryPrice.Price
        delta = (exit_price - entry) if direction == Direction.Buy else (entry - exit_price)
        gross = delta * volume * quote_conversion
        ratio = volume / position.Volume if position.Volume else 1.0
        commission = (position.CommissionPnL.PnL if position.CommissionPnL else 0.0) * ratio + truncate(self._commission_(volume, rate, base_conversion, quote_conversion))
        swap = self._swap_(direction, volume, rate, position.EntryTimestamp.DateTime, tick.Timestamp.DateTime, quote_conversion)
        return TradeAPI(
            UID=next(self._tids_),
            Position=position.UID,
            Account=self.account,
            Security=self._security_,
            Type=position.Type,
            Direction=direction,
            EntryTimestamp=position.EntryTimestamp.DateTime,
            ExitTimestamp=tick.Timestamp.DateTime,
            EntryPrice=entry,
            ExitPrice=exit_price,
            Volume=volume,
            Quantity=self._quantity_(volume),
            GrossPnL=gross,
            CommissionPnL=commission,
            SwapPnL=swap,
            NetPnL=gross + commission + swap,
            Label=self.__class__.__name__,
            Comment=position.Type.name
        )

    def _exit_price_(self, position: PositionAPI, tick: TickAPI) -> float:
        ask, bid = self._ask_bid_(tick)
        return bid if position.Direction == Direction.Buy else ask

    def _enqueue_(self, update_id: UpdateID, *args: Any) -> None:
        self._uid_queue_.append(update_id)
        for arg in args: self._arg_queue_.append(arg)
        self._uid_queue_.append(UpdateID.Complete)

    def _emit_open_(self, action: Union[OpenBuyPositionActionAPI, OpenSellPositionActionAPI], direction: Direction) -> None:
        volume = action.Volume
        if volume > self._contract_.VolumeMax or volume < self._contract_.VolumeMin or not equals(volume % self._contract_.VolumeStep, 0.0, abs_=self._EPSILON_):
            self._log_.error(lambda: f"Action Open: Failed · Due to invalid Volume ({volume})"); return
        ask, bid = self._ask_bid_(self._tick_)
        entry = ask if direction == Direction.Buy else bid
        sl_distance = action.StopLoss * self._contract_.PipSize if action.StopLoss else None
        tp_distance = action.TakeProfit * self._contract_.PipSize if action.TakeProfit else None
        if direction == Direction.Buy:
            sl_price = None if sl_distance is None else self._round_(entry - sl_distance)
            tp_price = None if tp_distance is None else self._round_(entry + tp_distance)
        else:
            sl_price = None if sl_distance is None else self._round_(entry + sl_distance)
            tp_price = None if tp_distance is None else self._round_(entry - tp_distance)
        position = self._build_position_(direction, action.PositionType, volume, self._tick_, sl_price, tp_price)
        self._positions_[position.UID] = position
        self._arm_version_ += 1
        update_id = UpdateID.OpenedBuyPosition if direction == Direction.Buy else UpdateID.OpenedSellPosition
        self._enqueue_(update_id, self._bar_, position)

    def _emit_close_(self, position: PositionAPI, tick: TickAPI, update_id: UpdateID) -> None:
        trade = self._build_trade_(position, position.Volume, tick, self._exit_price_(position, tick))
        del self._positions_[position.UID]
        self._arm_version_ += 1
        self._enqueue_(update_id, position, trade, self._bar_)

    def _emit_modify_volume_(self, action: Union[ModifyBuyPositionVolumeActionAPI, ModifySellPositionVolumeActionAPI], direction: Direction) -> None:
        position = self._positions_.get(action.PositionID)
        if position is None: self._log_.error(lambda: "Action Modify Volume: Failed · Due to Position not found"); return
        if equals(action.Volume, 0.0, abs_=self._EPSILON_):
            self._emit_close_(position, self._tick_, UpdateID.ClosedBuyPosition if direction == Direction.Buy else UpdateID.ClosedSellPosition); return
        closing = position.Volume - action.Volume
        if closing <= 0.0: self._log_.error(lambda: f"Action Modify Volume: Failed · Due to invalid Volume ({action.Volume})"); return
        initial_commission = position.CommissionPnL.PnL if position.CommissionPnL else 0.0
        trade = self._build_trade_(position, closing, self._tick_, self._exit_price_(position, self._tick_))
        position.Volume = action.Volume
        position.Quantity = self._quantity_(action.Volume)
        position.CommissionPnL = initial_commission * (action.Volume / (action.Volume + closing))
        update_id = UpdateID.ModifiedBuyPositionVolume if direction == Direction.Buy else UpdateID.ModifiedSellPositionVolume
        self._enqueue_(update_id, position, trade, self._bar_)

    def _emit_modify_stop_loss_(self, action: Union[ModifyBuyPositionStopLossActionAPI, ModifySellPositionStopLossActionAPI], direction: Direction) -> None:
        position = self._positions_.get(action.PositionID)
        if position is None: self._log_.error(lambda: "Action Modify Stop-Loss: Failed · Due to Position not found"); return
        position.StopLossPrice = self._round_(action.StopLoss) if action.StopLoss is not None else None
        self._arm_version_ += 1
        update_id = UpdateID.ModifiedBuyPositionStopLoss if direction == Direction.Buy else UpdateID.ModifiedSellPositionStopLoss
        self._enqueue_(update_id, self._bar_, position)

    def _emit_modify_take_profit_(self, action: Union[ModifyBuyPositionTakeProfitActionAPI, ModifySellPositionTakeProfitActionAPI], direction: Direction) -> None:
        position = self._positions_.get(action.PositionID)
        if position is None: self._log_.error(lambda: "Action Modify Take-Profit: Failed · Due to Position not found"); return
        position.TakeProfitPrice = self._round_(action.TakeProfit) if action.TakeProfit is not None else None
        self._arm_version_ += 1
        update_id = UpdateID.ModifiedBuyPositionTakeProfit if direction == Direction.Buy else UpdateID.ModifiedSellPositionTakeProfit
        self._enqueue_(update_id, self._bar_, position)

    def send_action(self, action: ActionAPI) -> None:
        match action.ActionID:
            case ActionID.Complete | ActionID.Init: pass
            case ActionID.Execution: self._enqueue_(UpdateID.Execution)
            case ActionID.OpenBuyPosition: self._emit_open_(action, Direction.Buy)
            case ActionID.OpenSellPosition: self._emit_open_(action, Direction.Sell)
            case ActionID.CloseBuyPosition:
                position = self._positions_.get(action.PositionID)
                if position is None: self._log_.error(lambda: "Action Close: Failed · Due to Position not found"); return
                self._emit_close_(position, self._tick_, UpdateID.ClosedBuyPosition)
            case ActionID.CloseSellPosition:
                position = self._positions_.get(action.PositionID)
                if position is None: self._log_.error(lambda: "Action Close: Failed · Due to Position not found"); return
                self._emit_close_(position, self._tick_, UpdateID.ClosedSellPosition)
            case ActionID.ModifyBuyPositionVolume: self._emit_modify_volume_(action, Direction.Buy)
            case ActionID.ModifySellPositionVolume: self._emit_modify_volume_(action, Direction.Sell)
            case ActionID.ModifyBuyPositionStopLoss: self._emit_modify_stop_loss_(action, Direction.Buy)
            case ActionID.ModifySellPositionStopLoss: self._emit_modify_stop_loss_(action, Direction.Sell)
            case ActionID.ModifyBuyPositionTakeProfit: self._emit_modify_take_profit_(action, Direction.Buy)
            case ActionID.ModifySellPositionTakeProfit: self._emit_modify_take_profit_(action, Direction.Sell)
            case ActionID.AskAboveTarget: self._ask_above_ = action.Ask; self._arm_version_ += 1
            case ActionID.AskBelowTarget: self._ask_below_ = action.Ask; self._arm_version_ += 1
            case ActionID.BidAboveTarget: self._bid_above_ = action.Bid; self._arm_version_ += 1
            case ActionID.BidBelowTarget: self._bid_below_ = action.Bid; self._arm_version_ += 1

    @staticmethod
    def _intrabar_(bar: BarAPI) -> list[TickAPI]:
        high, low = bar.HighTick, bar.LowTick
        extremes = [high, low] if high.Timestamp.DateTime <= low.Timestamp.DateTime else [low, high]
        return [bar.OpenTick, *extremes, bar.CloseTick]

    @staticmethod
    def _stop_level_(position: PositionAPI, ask: float, bid: float) -> tuple[Union[float, None], Union[UpdateID, None]]:
        sl = position.StopLossPrice.Price if position.StopLossPrice else None
        tp = position.TakeProfitPrice.Price if position.TakeProfitPrice else None
        if position.Direction == Direction.Buy:
            if sl is not None and bid <= sl: return sl, UpdateID.StopLossBuyPosition
            if tp is not None and bid >= tp: return tp, UpdateID.TakeProfitBuyPosition
        else:
            if sl is not None and ask >= sl: return sl, UpdateID.StopLossSellPosition
            if tp is not None and ask <= tp: return tp, UpdateID.TakeProfitSellPosition
        return None, None

    def _fill_stop_(self, position: PositionAPI, timestamp: Union[int, datetime], level: float, raw_ask: float, raw_bid: float, ask: float, bid: float, spread: float, update_id: UpdateID) -> None:
        if update_id in (UpdateID.StopLossBuyPosition, UpdateID.StopLossSellPosition):
            fill_ask, fill_bid = ask, bid
        elif position.Direction == Direction.Buy:
            fill_ask, fill_bid = level + spread, level
        else:
            fill_ask, fill_bid = level, level - spread
        fill = self._synth_tick_(timestamp, fill_ask, fill_bid, raw_ask, raw_bid)
        self._tick_ = fill
        self._emit_close_(position, fill, update_id)

    def _datetime_(self, timestamp: Union[int, datetime]) -> datetime:
        return epoch_to_datetime(timestamp, unit=MICROSECOND) if isinstance(timestamp, int) else timestamp

    def _conversion_at_(self, timestamp: Union[int, datetime]) -> tuple:
        arrays, ts = self._dataset_.TickConversions, self._dataset_.TickTimestamps
        if arrays is None or ts.size == 0: return None, None, None, None
        us = timestamp if isinstance(timestamp, int) else datetime_to_epoch(timestamp, unit=MICROSECOND)
        index = int(np.searchsorted(ts, us, side="right")) - 1
        if index < 0: return None, None, None, None
        return tuple(None if math.isnan(array[index]) else float(array[index]) for array in arrays)

    def _tick_conversions_(self, timestamp: Union[int, datetime], raw_ask: float, raw_bid: float) -> tuple:
        if self._needs_conversion_: return self._conversion_at_(timestamp)
        if self._account_asset_ == self._quote_asset_: return raw_ask, raw_bid, 1.0, 1.0
        if self._account_asset_ == self._base_asset_: return 1.0, 1.0, 1.0 / raw_bid, 1.0 / raw_ask
        return 1.0, 1.0, 1.0, 1.0

    def _synth_tick_(self, timestamp: Union[int, datetime], ask: float, bid: float, raw_ask: float, raw_bid: float) -> TickAPI:
        ask_base, bid_base, ask_quote, bid_quote = self._tick_conversions_(timestamp, raw_ask, raw_bid)
        return TickAPI(Security=self._security_, Timestamp=self._datetime_(timestamp), Ask=ask, Bid=bid, AskBaseConversion=ask_base, BidBaseConversion=bid_base, AskQuoteConversion=ask_quote, BidQuoteConversion=bid_quote, Volume=1.0)

    def _walk_(self, timestamp: Union[int, datetime], raw_ask: float, raw_bid: float) -> Iterator:
        ask, bid = self._effective_ask_bid_(raw_ask, raw_bid)
        spread = (raw_ask - raw_bid) if self._spread_type_ in (SpreadType.Accurate, SpreadType.Approximate) else self._spread_value_amount_(raw_ask, raw_bid)
        for position in list(self._positions_.values()):
            if position.UID not in self._positions_: continue
            level, update_id = self._stop_level_(position, ask, bid)
            if level is not None:
                self._fill_stop_(position, timestamp, level, raw_ask, raw_bid, ask, bid, spread, update_id)
                yield
        if self._ask_above_ is not None and ask >= self._ask_above_:
            self._tick_ = self._synth_tick_(timestamp, ask, bid, raw_ask, raw_bid)
            self._enqueue_(UpdateID.AskAboveTarget, self._tick_); yield
        if self._ask_below_ is not None and ask <= self._ask_below_:
            self._tick_ = self._synth_tick_(timestamp, ask, bid, raw_ask, raw_bid)
            self._enqueue_(UpdateID.AskBelowTarget, self._tick_); yield
        if self._bid_above_ is not None and bid >= self._bid_above_:
            self._tick_ = self._synth_tick_(timestamp, ask, bid, raw_ask, raw_bid)
            self._enqueue_(UpdateID.BidAboveTarget, self._tick_); yield
        if self._bid_below_ is not None and bid <= self._bid_below_:
            self._tick_ = self._synth_tick_(timestamp, ask, bid, raw_ask, raw_bid)
            self._enqueue_(UpdateID.BidBelowTarget, self._tick_); yield

    def _bounds_(self, open_ts: datetime, close_ts: datetime) -> tuple[int, int]:
        ts = self._dataset_.TickTimestamps
        if ts.size == 0: return 0, 0
        return (int(np.searchsorted(ts, datetime_to_epoch(open_ts, unit=MICROSECOND), side="left")),
                int(np.searchsorted(ts, datetime_to_epoch(close_ts, unit=MICROSECOND), side="right")))

    def _slice_ticks_(self, open_ts: datetime, close_ts: datetime) -> tuple[list, list, list]:
        start, stop = self._bounds_(open_ts, close_ts)
        if stop <= start: return [], [], []
        dataset = self._dataset_
        return dataset.TickTimestamps[start:stop].tolist(), dataset.TickAsks[start:stop].tolist(), dataset.TickBids[start:stop].tolist()

    def _period_ticks_(self, bar: BarAPI) -> tuple[list, list, list]:
        return self._slice_ticks_(bar.OpenTick.Timestamp.DateTime, bar.CloseTick.Timestamp.DateTime)

    def _effective_bounds_(self, raw_ask: np.ndarray, raw_bid: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        match self._spread_type_:
            case SpreadType.Points:
                ask = raw_bid + (self._spread_value_ or 0.0) * self._contract_.PointSize
                return raw_bid, ask, ask
            case SpreadType.Percentage:
                ask = raw_bid + (self._spread_value_ or 0.0) / 100.0 * raw_bid
                return raw_bid, ask, ask
            case SpreadType.Random:
                return raw_bid, raw_bid, raw_bid + (self._spread_value_ or 0.0) * self._contract_.PointSize
            case _:
                return raw_bid, raw_ask, raw_ask

    def _candidate_mask_(self, bid: np.ndarray, ask_low: np.ndarray, ask_high: np.ndarray) -> np.ndarray:
        pad = 10.0 ** -self._digits_
        mask = np.zeros(bid.shape, dtype=bool)
        if self._ask_above_ is not None: mask |= ask_high >= self._ask_above_ - pad
        if self._ask_below_ is not None: mask |= ask_low <= self._ask_below_ + pad
        if self._bid_above_ is not None: mask |= bid >= self._bid_above_ - pad
        if self._bid_below_ is not None: mask |= bid <= self._bid_below_ + pad
        for position in self._positions_.values():
            sl = position.StopLossPrice.Price if position.StopLossPrice else None
            tp = position.TakeProfitPrice.Price if position.TakeProfitPrice else None
            if position.Direction == Direction.Buy:
                if sl is not None: mask |= bid <= sl + pad
                if tp is not None: mask |= bid >= tp - pad
            else:
                if sl is not None: mask |= ask_high >= sl - pad
                if tp is not None: mask |= ask_low <= tp + pad
        return mask

    def _ticks_(self, open_ts: datetime, close_ts: datetime) -> Iterator[tuple[int, float, float]]:
        start, stop = self._bounds_(open_ts, close_ts)
        if stop <= start: return
        dataset = self._dataset_
        times, asks, bids = dataset.TickTimestamps[start:stop], dataset.TickAsks[start:stop], dataset.TickBids[start:stop]
        bid, ask_low, ask_high = self._effective_bounds_(asks, bids)
        size, cursor, version, candidates, pointer = stop - start, 0, None, None, 0
        while cursor < size:
            if version != self._arm_version_:
                version = self._arm_version_
                candidates = np.flatnonzero(self._candidate_mask_(bid, ask_low, ask_high))
                pointer = int(np.searchsorted(candidates, cursor, side="left"))
            if pointer >= candidates.size: return
            index = int(candidates[pointer]); pointer += 1
            yield int(times[index]), float(asks[index]), float(bids[index])
            cursor = index + 1

    def _tick_stream_(self, bar: BarAPI) -> Iterator[tuple[int, float, float]]:
        yield from self._ticks_(bar.OpenTick.Timestamp.DateTime, bar.CloseTick.Timestamp.DateTime)

    def _tick_bars_(self, bar: BarAPI, n: int) -> Iterator[tuple[Union[int, datetime], float, float]]:
        timestamps, asks, bids = self._period_ticks_(bar)
        for start in range(0, len(timestamps), n):
            ts, ak, bd = timestamps[start:start + n], asks[start:start + n], bids[start:start + n]
            if not bd: continue
            last = len(bd) - 1
            high, low = max(range(len(bd)), key=lambda i: bd[i]), min(range(len(bd)), key=lambda i: bd[i])
            order, seen = [], set()
            for i in (0, min(high, low), max(high, low), last):
                if i not in seen: seen.add(i); order.append(i)
            for i in order: yield ts[i], ak[i], bd[i]

    def _finer_bars_(self, bar: BarAPI) -> Iterator[tuple[datetime, float, float]]:
        frame = self._dataset_.IntraBars.get(self._resolution_.UID)
        if frame is None or frame.is_empty(): return
        opens = frame["OpenTick.Timestamp"]
        start = opens.search_sorted(bar.OpenTick.Timestamp.DateTime, side="left")
        stop = opens.search_sorted(bar.CloseTick.Timestamp.DateTime, side="right")
        for row in frame.slice(start, max(stop - start, 0)).iter_rows(named=True):
            yield row["OpenTick.Timestamp"], row["OpenTick.Ask"], row["OpenTick.Bid"]
            if row["HighTick.Timestamp"] <= row["LowTick.Timestamp"]:
                yield row["HighTick.Timestamp"], row["HighTick.Ask"], row["HighTick.Bid"]
                yield row["LowTick.Timestamp"], row["LowTick.Ask"], row["LowTick.Bid"]
            else:
                yield row["LowTick.Timestamp"], row["LowTick.Ask"], row["LowTick.Bid"]
                yield row["HighTick.Timestamp"], row["HighTick.Ask"], row["HighTick.Bid"]
            yield row["CloseTick.Timestamp"], row["CloseTick.Ask"], row["CloseTick.Bid"]

    def _spread_ceiling_(self, bids: tuple, asks: tuple) -> float:
        raw = max(ask - bid for ask, bid in zip(asks, bids))
        match self._spread_type_:
            case SpreadType.Points | SpreadType.Random: return max(raw, (self._spread_value_ or 0.0) * self._contract_.PointSize)
            case SpreadType.Percentage: return max(raw, (self._spread_value_ or 0.0) / 100.0 * max(bids))
            case _: return raw

    def _should_descend_(self, bids: tuple, asks: tuple) -> bool:
        pad = self._spread_ceiling_(bids, asks)
        low_bid, high_bid = min(bids) - pad, max(bids) + pad
        low_ask, high_ask = min(asks) - pad, max(asks) + pad
        if self._ask_above_ is not None and self._ask_above_ <= high_ask: return True
        if self._ask_below_ is not None and self._ask_below_ >= low_ask: return True
        if self._bid_above_ is not None and self._bid_above_ <= high_bid: return True
        if self._bid_below_ is not None and self._bid_below_ >= low_bid: return True
        for position in self._positions_.values():
            sl = position.StopLossPrice.Price if position.StopLossPrice else None
            tp = position.TakeProfitPrice.Price if position.TakeProfitPrice else None
            if position.Direction == Direction.Buy:
                if sl is not None and sl >= low_bid: return True
                if tp is not None and tp <= high_bid: return True
            else:
                if sl is not None and sl <= high_ask: return True
                if tp is not None and tp >= low_ask: return True
        return False

    def _sub_rows_(self, resolution: str, open_ts: datetime, close_ts: datetime) -> Iterator[dict]:
        frame = self._dataset_.IntraBars.get(resolution)
        if frame is None or frame.is_empty(): return
        opens = frame["OpenTick.Timestamp"]
        start = opens.search_sorted(open_ts, side="left")
        stop = opens.search_sorted(close_ts, side="right")
        yield from frame.slice(start, max(stop - start, 0)).iter_rows(named=True)

    def _descend_(self, open_ts: datetime, close_ts: datetime, ladder: list) -> Iterator[tuple[int, float, float]]:
        if not ladder:
            yield from self._ticks_(open_ts, close_ts)
            return
        head, rest = ladder[0], ladder[1:]
        for row in self._sub_rows_(head, open_ts, close_ts):
            bids = (row["OpenTick.Bid"], row["HighTick.Bid"], row["LowTick.Bid"], row["CloseTick.Bid"])
            asks = (row["OpenTick.Ask"], row["HighTick.Ask"], row["LowTick.Ask"], row["CloseTick.Ask"])
            if self._should_descend_(bids, asks):
                yield from self._descend_(row["OpenTick.Timestamp"], row["CloseTick.Timestamp"], rest)

    def _intrabar_source_(self, bar: BarAPI) -> Iterator[tuple[Union[int, datetime], float, float]]:
        if self._auto_:
            bids = (bar.OpenTick.Bid.Price, bar.HighTick.Bid.Price, bar.LowTick.Bid.Price, bar.CloseTick.Bid.Price)
            asks = (bar.OpenTick.Ask.Price, bar.HighTick.Ask.Price, bar.LowTick.Ask.Price, bar.CloseTick.Ask.Price)
            if self._should_descend_(bids, asks):
                self._descended_bars_ += 1
                yield from self._descend_(bar.OpenTick.Timestamp.DateTime, bar.CloseTick.Timestamp.DateTime, self._dataset_.IntraLevels)
            else:
                self._skipped_bars_ += 1
            return
        resolution = self._resolution_
        if not resolution.IsTick and resolution.Seconds == self._timeframe_.Seconds:
            for t in self._intrabar_(bar): yield t.Timestamp.DateTime, t.Ask.Price, t.Bid.Price
        elif resolution.IsTick and (resolution.Value or 1) == 1:
            yield from self._tick_stream_(bar)
        elif resolution.IsTick:
            yield from self._tick_bars_(bar, resolution.Value or 1)
        else:
            yield from self._finer_bars_(bar)

    def _generate_(self) -> Iterator:
        self._enqueue_(UpdateID.Account, self.account)
        yield
        self._enqueue_(UpdateID.Security, self.security)
        yield
        self._enqueue_(UpdateID.Execution)
        yield
        bars = self._dataset_.ExecutionBars
        total = len(bars)
        for index, bar in enumerate(bars):
            self._bar_ = bar
            self._tick_ = bars[index + 1].OpenTick if index + 1 < total else bar.CloseTick
            self._enqueue_(UpdateID.BarClosed, bar)
            yield
            if index + 1 >= total: continue
            nbar = bars[index + 1]
            self._bar_ = nbar
            for timestamp, raw_ask, raw_bid in self._intrabar_source_(nbar):
                for _ in self._walk_(timestamp, raw_ask, raw_bid): yield

    def receive_update_id(self) -> UpdateID:
        if not self._uid_queue_:
            try: next(self._feed_)
            except StopIteration: return UpdateID.Shutdown
        return self._uid_queue_.popleft() if self._uid_queue_ else UpdateID.Shutdown

    def _receive_update_init_(self, offset: int = 1) -> InitUpdateAPI:
        return InitUpdateAPI(Account=self.account, Security=self.security, Market=self.market, Technical=self.technical, Fundamental=self.fundamental, Sentimental=self.sentimental, Portfolio=self.portfolio, ProcessID=0)

    def receive_update_account(self, offset: int = 1) -> AccountAPI:
        return self._arg_queue_.popleft()

    def receive_update_security(self, offset: int = 1) -> SecurityAPI:
        return self._arg_queue_.popleft()

    def receive_update_tick(self, offset: int = 1) -> TickAPI:
        return self._arg_queue_.popleft()

    def receive_update_bar(self, offset: int = 1) -> BarAPI:
        return self._arg_queue_.popleft()

    def receive_update_order(self, offset: int = 1) -> Any:
        return self._arg_queue_.popleft()

    def receive_update_position(self, offset: int = 1) -> PositionAPI:
        return self._arg_queue_.popleft()

    def receive_update_trade(self, offset: int = 1) -> TradeAPI:
        return self._arg_queue_.popleft()

    def receive_update_position_trade(self, offset: int = 1) -> tuple[PositionAPI, TradeAPI]:
        return self._arg_queue_.popleft(), self._arg_queue_.popleft()

    def receive_update_denied(self, offset: int = 1) -> tuple[ActionID, str]:
        return ActionID.Complete, ""

    def receive_update_exception(self, offset: int = 1) -> str:
        return ""

    def system_management(self) -> MachineAPI:
        system_engine = MachineAPI(Name="System Management", Events=len(UpdateID))

        initialization = system_engine.state(name="Initialization")
        execution = system_engine.state(name="Execution")
        termination = system_engine.state(name="Termination", end=True)

        def execute(update: CompleteUpdateAPI):
            warmup = self._dataset_.WarmupBars
            self._log_.debug(lambda: f"Phase Warmup: Completed · {warmup.height if warmup is not None else 0} Bars")
            if warmup is not None and warmup.height:
                update.Market.init_data(warmup)
            self._transition_(self._initialization_timer_, "Initialization", self._execution_timer_)

        def advance(update: BarUpdateAPI):
            if self.strategy.Transform.Market and self._dataset_.IndicatorResults is None: update.Market.update_data(update.Bar)

        def report(update: CompleteUpdateAPI):
            self._transition_(self._execution_timer_, "Execution", self._finalization_timer_)
            if self._auto_:
                self._log_.info(lambda: f"Phase Resolution: Completed · Auto · {self._skipped_bars_} Skipped · {self._descended_bars_} Descended")
            self._report_(update.Portfolio, self.account, self._start_.date(), self._stop_.date())

        initialization.on(event=UpdateID.Execution, to=execution, action=execute, reason="Market Initialized")
        initialization.on(event=UpdateID.Shutdown, to=termination, action=None, reason="Abruptly Terminated")

        execution.on(event=UpdateID.BarClosed, to=execution, action=advance, reason=None)
        execution.on(event=UpdateID.Shutdown, to=termination, action=report, reason="Safely Terminated")

        return system_engine

    @timer
    def run(self) -> None:
        self.deploy()

__all__ = ["DatasetAPI", "BacktestingAPI"]