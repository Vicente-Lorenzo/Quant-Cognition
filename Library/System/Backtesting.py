from __future__ import annotations

import math
import threading
import contextlib

from pathlib import Path
from itertools import count
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Union, Iterator, TYPE_CHECKING

from Library.Database.Database import DatabaseAPI
from Library.Database.Dataframe import np, pl
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Engine import MachineAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Model.Split import SplitAPI
from Library.Statistic.Composition import analysis, searchspace
from Library.Statistic.Label import (
    NET_TOTAL_AGGREGATED,
    STATISTICS_METRICS_LABEL
)
from Library.Market.Bar import BarAPI
from Library.Market.Point import PointAPI
from Library.Market.Price import Direction, PriceAPI
from Library.Market.Tape import ShareAPI, TapeAPI
from Library.Market.Tick import TickAPI
from Library.Portfolio.Account import AccountAPI, AccountType, Environment, MarginMode
from Library.Portfolio.Position import PositionAPI, PositionMode, PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Protocol.Action import ActionAPI, ActionID, OpenBuyPositionActionAPI, OpenSellPositionActionAPI
from Library.Protocol.Update import UpdateID, BarUpdateAPI, CompleteUpdateAPI, InitUpdateAPI
from Library.Universe.Contract import CommissionMode, CommissionType, SpreadType, SwapType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime, parse_datetime
from Library.Utility.Math import EPSILON, equals, quantize
from Library.Utility.Memory import memory_to_string
from Library.Utility.Progress import ProgressAPI
from Library.Utility.Profiler import Timer, timer
from Library.Utility.Typing import MISSING, Missing
from Library.System.Selection import ElectionMode, FitnessType, SelectionMode
from Library.System.System import SystemAPI

if TYPE_CHECKING:
    from Library.Utility.Parameter import Parameter
    from Library.Strategy.Strategy import StrategyAPI

@dataclass(frozen=True, slots=True)
class DatasetAPI:

    WarmupBars: Union[pl.DataFrame, None]
    ExecutionBars: list[BarAPI]
    Ticks: TapeAPI
    Conversions: tuple
    Points: Union[TapeAPI, None] = None
    ExecutionRows: Union[pl.DataFrame, None] = None
    IndicatorResults: Union[dict, None] = None

class BacktestingAPI(SystemAPI):

    _PRELOAD_CACHE_: dict = {}
    _PRELOAD_LOCK_ = threading.Lock()
    _TAPE_CACHE_: dict = {}
    _TAPE_LOCK_ = threading.Lock()

    _db_: DatabaseAPI
    _feed_: Iterator
    _resolution_: TimeframeAPI
    _dataset_: DatasetAPI
    _advance_index_: int
    _uid_queue_: deque
    _arg_queue_: deque
    _bar_: BarAPI
    _walked_: BarAPI
    _tick_: TickAPI

    def __init__(self,
                 strategy: type[StrategyAPI],
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
                 risk_free: float = 0.0,
                 benchmark: Union[str, list, None] = None,
                 report: bool = True,
                 export: bool = True,
                 plot: bool = False,
                 run: Union[str, Path, None] = None,
                 description: Union[str, None] = None,
                 dataset: Union[DatasetAPI, None] = None,
                 readers: int = 32,
                 shelf: Union[dict, Missing] = MISSING,
                 history: Union[dict, Missing] = MISSING,
                 spans: Union[dict, Missing] = MISSING) -> None:
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, parameters=parameters, risk_free=risk_free, benchmark=benchmark, report=report, export=export, plot=plot, run=run, description=description)
        self._injected_: Union[DatasetAPI, None] = dataset
        self._readers_: int = max(1, readers)
        self._shelf_: dict = shelf if shelf is not MISSING else {}
        self._history_: dict = history if history is not MISSING else {}
        self._spans_: dict = spans if spans is not MISSING else {}
        self._shared_: Union[ShareAPI, None] = None
        self._folded_: list = []
        self._journal_: list = []

        self._start_: datetime = parse_datetime(start, end_of_day=False)
        self._stop_: datetime = parse_datetime(stop, end_of_day=True)

        self._account_asset_, self._account_balance_, self._account_leverage_, *bridge = account
        self._bridge_: Union[str, Missing] = bridge[0] if bridge and bridge[0] else MISSING
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
        self._descended_: int = 0
        self._skipped_: int = 0
        self._arm_version_: int = 0
        self._rng_: np.random.Generator = np.random.default_rng(spread_seed[0] if spread_seed and isinstance(spread_seed[0], int) else None)

        self._stack_: Union[contextlib.ExitStack, None] = None
        self._contract_: Any = None
        self._base_asset_: Union[str, None] = None
        self._quote_asset_: Union[str, None] = None
        self._needs_conversion_: bool = False
        self._digits_: int = 5

        self._window_: int = 0
        self._rolls_: tuple = (np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64))
        self._roll_index_: int = 0
        self._roll_rates_: np.ndarray = np.empty(0)
        self._mark_: int = 0
        self._segmented_: bool = False
        self._walking_: bool = False

        self._pids_: count = count(start=-1, step=-1)
        self._tids_: count = count(start=-1, step=-1)
        self._positions_: dict[int, PositionAPI] = {}
        self._ask_above_: Union[float, None] = None
        self._ask_below_: Union[float, None] = None
        self._bid_above_: Union[float, None] = None
        self._bid_below_: Union[float, None] = None

        self._preload_seconds_: float = 0.0

    def _connect_(self) -> None:
        if self._spawns_(): self._shelve_()
        if self._stack_ is None:
            self._stack_ = contextlib.ExitStack()
            self._stack_.__enter__()
            self._db_ = self._stack_.enter_context(PostgresDatabaseAPI(database="Quant"))
        try:
            self._assemble_()
            self._netting_ = self._position_mode_() == PositionMode.Netting
            self._contract_ = self._security_.Contract
            self._record_contract_()
            self._digits_ = int(self._contract_.Digits) if getattr(self._contract_, "Digits", None) else 5
            ticker = self._security_.Ticker
            self._base_asset_ = ticker.BaseAsset if ticker else None
            self._quote_asset_ = ticker.QuoteAsset if ticker else None
            self._needs_conversion_ = self._account_asset_ not in (self._base_asset_, self._quote_asset_)
            self._window_ = self._indicator_window_()
            self._rolls_ = self._schedule_()
            if isinstance(self._resolution_arg_, TimeframeAPI): self._resolution_ = self._resolution_arg_
            else:
                uid = self._resolution_arg_ if isinstance(self._resolution_arg_, str) and self._resolution_arg_ else "Auto"
                self._auto_ = uid == "Auto"
                self._resolution_ = TimeframeAPI(UID="T1" if self._auto_ else uid, db=self._db_)
            if self._resolution_ > self._timeframe_:
                raise ValueError(f"Resolution {self._resolution_.UID}: Failed · Due to source coarser than execution timeframe {self._timeframe_.UID}")
            self.account = self._build_account_()
            self._preload_()
        except Exception:
            self._hangup_()
            raise
        self._advance_index_ = 0
        self._descended_, self._skipped_ = 0, 0
        self._positions_ = {}
        self._lots_ = {}
        self._pids_, self._tids_ = count(start=-1, step=-1), count(start=-1, step=-1)
        self._ask_above_ = None
        self._ask_below_ = None
        self._bid_above_ = None
        self._bid_below_ = None
        self._arm_version_ += 1
        self._roll_index_, self._mark_, self._segmented_, self._walking_ = 0, 0, False, False
        self._roll_rates_ = TapeAPI.rates(self._rolls_[0], self._dataset_.Conversions[1])[1] if self._dataset_.Conversions else np.ones(self._rolls_[0].size)
        self._uid_queue_ = deque()
        self._arg_queue_ = deque()
        self._feed_ = self._generate_()
        super()._connect_()

    def _hangup_(self) -> None:
        if self._stack_ is not None: self._stack_.__exit__(None, None, None)
        self._stack_ = None

    def _disconnect_(self) -> None:
        super()._disconnect_()
        self._hangup_()

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
        return BarAPI.row(row, self._security_, self._timeframe_)

    def _source_(self, asset: str, tape: TapeAPI) -> Union[tuple[TapeAPI, bool], None]:
        return TapeAPI.source(self._db_, self._security_, asset, self._account_asset_, tape, workers=self._readers_, shelf=self._shelf_, bridge=self._bridge_)

    def _charges_base_(self) -> bool:
        return self._commission_type_ == CommissionType.Accurate and self._contract_.CommissionMode in (CommissionMode.BaseAssetPerMillionVolume, CommissionMode.BaseAssetPerOneLot)

    def _minimum_asset_(self, contract: Any) -> Union[str, None]:
        if self._commission_type_ != CommissionType.Accurate or contract is None or not contract.MinCommission: return None
        ticker = self._security_.Ticker
        return None if contract.MinCommissionAsset in (self._account_asset_, ticker.BaseAsset, ticker.QuoteAsset) else contract.MinCommissionAsset

    def _base_source_(self, tape: TapeAPI) -> Union[tuple[TapeAPI, bool], None]:
        try: return self._source_(self._base_asset_, tape)
        except ValueError:
            if self._charges_base_(): raise
            self._log_.debug(lambda: f"Conversion {self._base_asset_} to {self._account_asset_}: Unavailable · Notional sizing refused")
            return TapeAPI.empty(tape.Security), False

    def _share_(self, start: datetime, stop: datetime) -> ShareAPI:
        first, last = TapeAPI.reach(start, stop, self._timeframe_)
        ticker = self._security_.Ticker
        with PostgresDatabaseAPI(database="Quant") as db:
            securities = {self._security_.UID: first}
            for asset in (ticker.BaseAsset, ticker.QuoteAsset, self._minimum_asset_(self._security_.Contract)):
                if asset is None: continue
                try: legs = TapeAPI.legs(db, self._security_, asset, self._account_asset_, self._bridge_)
                except ValueError: continue
                for leg in legs:
                    if leg[0] not in securities: securities[leg[0]] = first - timedelta(days=7)
            share = ShareAPI([TapeAPI.read(db, security, begin, last, workers=self._readers_, shared=True) for security, begin in securities.items()])
        self._log_.debug(lambda: f"Shared Tapes: Published · {len(securities)} Tapes · {memory_to_string(share.size())}")
        return share

    def _spawns_(self) -> bool:
        return False

    def _shelve_(self) -> ShareAPI:
        if self._shared_ is None:
            self._shared_ = self._share_(self._range_start_, self._range_stop_)
            self._shelf_ = {**self._shelf_, **self._shared_.tapes()}
        return self._shared_

    def _shared_bars_(self, share: ShareAPI, scopes: list) -> dict:
        shelf, spans = share.tapes().get(self._security_.UID, MISSING), {}
        with PostgresDatabaseAPI(database="Quant") as db:
            for start, stop in dict.fromkeys(scopes): spans[(start, stop)] = TapeAPI.span(db, self._security_.UID, self._timeframe_, start, stop, workers=self._readers_, shelf=shelf)[1]
        self._log_.debug(lambda: f"Shared Bars: Published · {len(spans)} Scopes · {sum(frame.height for frame in spans.values())} Bars")
        return spans

    def _histories_(self, share: ShareAPI, starts: list, window: int) -> dict:
        if window <= 0: return {}
        shelf, histories = share.tapes().get(self._security_.UID, MISSING), {}
        with PostgresDatabaseAPI(database="Quant") as db:
            for start in dict.fromkeys(starts):
                prior_tape, prior = TapeAPI.before(db, self._security_.UID, self._timeframe_, start, window, workers=self._readers_, shelf=shelf)
                histories[start] = (prior_tape.materialize(prior, self._timeframe_), window)
        self._log_.debug(lambda: f"Shared Warmup: Published · {len(histories)} Starts · {window} Bars")
        return histories

    def _finer_(self) -> bool:
        return self._resolution_ < self._timeframe_ and not (self._resolution_.IsTick and (self._resolution_.Value or 1) == 1)

    def _walks_ticks_(self) -> bool:
        return self._auto_ or (self._resolution_.IsTick and (self._resolution_.Value or 1) == 1)

    @staticmethod
    def _reduce_(source: Union[tuple, None], stamps: np.ndarray) -> Union[tuple, None]:
        if source is None: return None
        asks, bids = TapeAPI.rates(stamps, source)
        return TapeAPI(Security=source[0].Security, Stamps=stamps, Asks=asks, Bids=bids, Volumes=np.zeros(stamps.size)), False

    def _load_tape_(self) -> tuple:
        tape, bars = TapeAPI.span(self._db_, self._security_.UID, self._timeframe_, self._start_, self._stop_, workers=self._readers_, shelf=self._shelf_.get(self._security_.UID, MISSING), bars=self._spans_.get((self._start_, self._stop_), MISSING))
        minimum = self._minimum_asset_(self._contract_)
        conversions = (self._base_source_(tape), self._source_(self._quote_asset_, tape), self._source_(minimum, tape) if minimum else None) if tape.Stamps.size else (None, None, None)
        start = datetime_to_epoch(self._start_)
        early = tape.materialize(bars.filter(pl.col("Timestamp") < start), self._timeframe_)
        executed = bars.filter(pl.col("Timestamp") >= start)
        rows = tape.materialize(executed, self._timeframe_, *conversions[:2]) if executed.height else None
        if executed.height < 2: return early, (None, None), rows, [], TapeAPI.empty(tape.Security), None, [None]
        window = tape.slice(int(executed["Open"][1]), int(executed["Close"][-1]))
        points = self._points_(window, window.bars(self._resolution_, workers=self._readers_)) if self._finer_() else None
        walked = [self._row_to_bar_(row) for row in rows.slice(1).to_dicts()]
        if self._walks_ticks_(): return early, conversions, rows, walked, window, points, [None]
        visited = executed.slice(1)
        stamps = points.Stamps if points is not None else tape.Stamps[np.concatenate((visited["Open"].to_numpy(), visited["HighAsk"].to_numpy(), visited["HighBid"].to_numpy(), visited["LowAsk"].to_numpy(), visited["LowBid"].to_numpy(), visited["Close"].to_numpy()))]
        stamps = np.unique(np.concatenate((stamps, self._rolls_[0])))
        return early, tuple(self._reduce_(source, stamps) for source in conversions), rows, walked, TapeAPI.empty(tape.Security), points, [None]

    def _load_warmup_(self, early: pl.DataFrame, rows: Union[pl.DataFrame, None], history: list) -> pl.DataFrame:
        count = max(self._window_ - early.height, 0)
        if history[0] is None: history[0] = self._history_.get(self._start_)
        if history[0] is None or history[0][1] < count:
            reach = max(count, 2 * history[0][1] if history[0] is not None else 0)
            prior_tape, prior = TapeAPI.before(self._db_, self._security_.UID, self._timeframe_, self._start_, reach, workers=self._readers_, shelf=self._shelf_.get(self._security_.UID, MISSING))
            history[0] = (prior_tape.materialize(prior, self._timeframe_), reach)
        warmup = pl.concat([history[0][0].tail(count), early]).tail(self._window_)
        return warmup if rows is None else pl.concat([warmup, rows.head(1)], how="vertical_relaxed")

    def _scope_(self) -> tuple:
        return self._security_.UID, self._start_, self._stop_, self._timeframe_.UID, self._resolution_.UID, self._account_asset_, self._bridge_ or None

    def extract(self) -> DatasetAPI:
        return self._dataset_

    def inject(self, dataset: DatasetAPI) -> None:
        self._injected_ = dataset

    @staticmethod
    def _memoize_(cache: dict, lock: threading.Lock, key: tuple, build) -> tuple[Any, bool]:
        with lock:
            reused = key in cache
            if not reused:
                cache.clear()
                cache[key] = build()
            return cache[key], reused

    def _tape_(self) -> tuple:
        return self._memoize_(self._TAPE_CACHE_, self._TAPE_LOCK_, self._scope_(), self._load_tape_)[0]

    def _build_dataset_(self) -> DatasetAPI:
        early, conversions, rows, executed, window, points, history = self._tape_()
        warmup = self._load_warmup_(early, rows, history)
        if not executed: return DatasetAPI(WarmupBars=warmup, ExecutionBars=[], Ticks=window, Conversions=conversions)
        return DatasetAPI(WarmupBars=warmup, ExecutionBars=executed, Ticks=window, Conversions=conversions, Points=points, ExecutionRows=rows.slice(1))

    def _metric_(self, label: str, column: str = NET_TOTAL_AGGREGATED) -> float:
        statistics = self.statistics
        if statistics is not None and not statistics.is_empty() and STATISTICS_METRICS_LABEL in statistics.columns and column in statistics.columns:
            row = statistics.filter(pl.col(STATISTICS_METRICS_LABEL) == label)
            if row.height:
                value = row[column].item()
                if value is not None: return float(value)
        return self._account_return_()

    def _record_(self, **fields) -> None:
        self._journal_.append(fields)

    def _tracked_(self) -> list:
        return self.portfolio.EquityCurve.Track if self.portfolio is not None else []

    def _stitch_(self, fold: int, label: str, window: tuple, score, equity: Union[list, None] = None,
                 training: Union[float, None] = None, settings: Union[dict, None] = None) -> None:
        curve = self._tracked_() if equity is None else equity
        if not curve: return
        self._folded_.append({"Fold": fold, "Parameters": label, "Start": window[0], "Stop": window[1],
                              "Training": training, "Validation": score, "Score": score,
                              "Settings": settings or {}, "Equity": curve})

    def _analysis_(self) -> dict:
        _, sheets = analysis(self._journal_, self._folded_)
        return {sheet.name: pl.DataFrame([dict(zip([column.name for column in sheet.columns], row)) for row in sheet.rows], strict=False)
                for sheet in sheets if sheet.rows}

    def _workspace_(self, workspace):
        return searchspace(workspace=workspace, journal=self._journal_, folds=self._folded_, elected=self._tracked_())

    def _account_return_(self) -> float:
        balance = self.portfolio.InitialBalance if self.portfolio is not None else None
        return self.portfolio.Equity / balance - 1.0 if balance else 0.0

    def _fitness_(self) -> float:
        if self._fitness_label_ == FitnessType.AccountReturn.value: return self._account_return_()
        return self._metric_(self._fitness_label_)

    def _walk_forward_(self, deliverables: tuple[bool, bool, bool], fitness: Union[str, FitnessType], selection: Union[str, SelectionMode], election: Union[str, ElectionMode], training: int, validation: int, testing: int, rolling: bool, continuous: bool, purge: Union[int, None], embargo: Union[int, None]) -> None:
        self._deliverables_: tuple[bool, bool, bool] = deliverables
        try: fitness_type = FitnessType(fitness)
        except ValueError: raise ValueError(f"Unknown fitness metric: {fitness} · Expected one of {FitnessType.names()}")
        self._fitness_label_: str = fitness_type.value
        self._selection_: SelectionMode = SelectionMode.parse(selection)
        self._election_: ElectionMode = ElectionMode.parse(election)
        self._training_, self._validation_, self._testing_ = training, validation, testing
        self._rolling_, self._continuous_ = rolling, continuous
        self._purge_, self._embargo_ = purge, embargo
        self._range_start_, self._range_stop_ = self._start_, self._stop_

    def _folds_(self) -> tuple[list, Union[tuple, None]]:
        return SplitAPI.walk_forward_folds(self._range_start_, self._range_stop_, self._training_, self._validation_, self._testing_, self._rolling_, self._purge_, self._embargo_)

    def _replay_(self, start: datetime, stop: datetime) -> float:
        super()._disconnect_()
        self._start_, self._stop_ = start, stop
        with self.quieted():
            self._connect_()
            self.deploy()
        return self._fitness_()

    def _dispatch_(self, parameters: Parameter, start, stop) -> dict:
        return {
            "strategy": self._strategy_,
            "provider": self._security_._provider_.UID,
            "ticker": self._security_._ticker_.UID,
            "timeframe": self._timeframe_.UID,
            "parameters": parameters.data,
            "start": start,
            "stop": stop,
            "account": (self._account_asset_, self._account_balance_, self._account_leverage_, self._bridge_ or None),
            "spread": (self._spread_type_, self._spread_value_),
            "commission": (self._commission_type_, self._commission_value_),
            "swap": (self._swap_type_, self._swap_long_, self._swap_short_),
            "contract": self._security_.Contract.snapshot() if self._security_.Contract is not None else None,
            "risk_free": self._risk_free_,
        }

    @staticmethod
    def _resolve_(payload: dict) -> tuple:
        with PostgresDatabaseAPI(database="Quant") as db:
            security = SecurityAPI(Provider=payload["provider"], Ticker=payload["ticker"], db=db, autoload=True)
            if payload.get("contract") is not None: security.Contract.pin(payload["contract"])
            return security, TimeframeAPI(UID=payload["timeframe"], db=db, autoload=True)

    @classmethod
    def _worker_(cls, payload: dict, log: LoggingAPI) -> tuple:
        log.console.set_level(VerboseLevel.Warning)
        return cls._resolve_(payload)

    def _preload_(self) -> None:
        watch = Timer().start()
        if self._injected_ is not None:
            self._dataset_ = self._injected_
            outcome = "Injected"
        else:
            self._dataset_, reused = self._memoize_(self._PRELOAD_CACHE_, self._PRELOAD_LOCK_, (*self._scope_(), self._window_), self._build_dataset_)
            outcome = "Reused" if reused else "Completed"
        watch.stop()
        self._preload_seconds_ = watch.delta()
        bars, ticks = len(self._dataset_.ExecutionBars), self._dataset_.Ticks.Stamps.size
        self._log_.info(lambda: f"Phase Preload: {outcome} · {watch.result()} · {bars} Bars · {ticks} Ticks · Resolution {'Auto' if self._auto_ else self._resolution_.UID}")

    @staticmethod
    def _mid_rate_(tick: TickAPI) -> float:
        return (tick.Ask.Price + tick.Bid.Price) / 2.0

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

    def _minimum_(self, tick: TickAPI, base_conversion: float, quote_conversion: float) -> float:
        amount, asset = self._contract_.MinCommission or 0.0, self._contract_.MinCommissionAsset
        if not amount or self._commission_type_ != CommissionType.Accurate: return 0.0
        if asset == self._account_asset_: return amount
        if asset == self._quote_asset_: return amount * quote_conversion
        if asset == self._base_asset_: return amount * base_conversion
        return amount * float(TapeAPI.rates(np.array([datetime_to_epoch(tick.Timestamp.DateTime)], dtype=np.int64), self._dataset_.Conversions[2])[1][0])

    def _commission_(self, volume: float, rate: float, base_conversion: float, quote_conversion: float, minimum: float = 0.0) -> float:
        match self._commission_type_:
            case CommissionType.Points:
                return volume * (-(self._commission_value_ or 0.0) * self._contract_.PointSize) * quote_conversion
            case CommissionType.Percentage:
                return -(self._commission_value_ or 0.0) / 100.0 * volume * rate * quote_conversion
            case CommissionType.Amount:
                return -(self._commission_value_ or 0.0)
            case CommissionType.Units:
                return -(self._commission_value_ or 0.0) * volume
            case CommissionType.Lots:
                return -(self._commission_value_ or 0.0) * self._quantity_(volume)
            case CommissionType.Accurate:
                commission = self._contract_.Commission or 0.0
                match self._contract_.CommissionMode:
                    case CommissionMode.BaseAssetPerMillionVolume: amount = volume * (-commission / 1_000_000) * base_conversion
                    case CommissionMode.BaseAssetPerOneLot: amount = self._quantity_(volume) * -commission * base_conversion
                    case CommissionMode.PercentageOfVolume: amount = -commission / 100.0 * volume * rate * quote_conversion
                    case CommissionMode.QuoteAssetPerOneLot: amount = self._quantity_(volume) * -commission * quote_conversion
                    case _: amount = 0.0
                return min(amount, -minimum)
        return 0.0

    def _fee_(self, volume: float, tick: TickAPI) -> float:
        base_conversion, quote_conversion = self._conversions_(tick)
        return quantize(self._commission_(volume, self._mid_rate_(tick), base_conversion, quote_conversion, self._minimum_(tick, base_conversion, quote_conversion)))

    def _schedule_(self) -> tuple[np.ndarray, np.ndarray]:
        rolls = self._contract_.rolls(self._start_, self._stop_) if self._contract_ is not None else []
        return np.array([datetime_to_epoch(moment) for moment, _ in rolls], dtype=np.int64), np.array([days for _, days in rolls], dtype=np.int64)

    def _swap_amount_(self, long: bool, volume: float, price: float, days: int, quote_conversion: float) -> float:
        match self._swap_type_:
            case SwapType.Points: return volume * ((self._swap_long_ if long else self._swap_short_) or 0.0) * self._contract_.PointSize * days * quote_conversion
            case SwapType.Percentage: return volume * price * (((self._swap_long_ if long else self._swap_short_) or 0.0) / 100.0) * (days / 365.0) * quote_conversion
            case SwapType.Amount: return ((self._swap_long_ if long else self._swap_short_) or 0.0) * days
            case SwapType.Accurate: return self._contract_.swap(long, volume, price, days) * quote_conversion
        return 0.0

    def _charge_(self) -> None:
        moment, count, quote = int(self._rolls_[0][self._roll_index_]), int(self._rolls_[1][self._roll_index_]), float(self._roll_rates_[self._roll_index_])
        self._roll_index_ += 1
        if not self._positions_: return
        price, skip, stamps = self._tick_.Bid.Price if self._tick_ is not None else 0.0, int(self._contract_.SwapSkip or 0), self._rolls_[0]
        for position in self._positions_.values():
            entry = datetime_to_epoch(position.EntryTimestamp.DateTime)
            if entry < moment and self._roll_index_ - 1 - int(np.searchsorted(stamps, entry, side="right")) >= skip:
                self.portfolio.charge(position, swap=quantize(self._swap_amount_(position.Direction == Direction.Buy, position.Volume, price, count, quote if quote == quote else 1.0)))

    def _accrue_(self, stamp: int) -> None:
        stamps = self._rolls_[0]
        while self._roll_index_ < stamps.size and stamps[self._roll_index_] <= stamp: self._charge_()

    def _roll_through_(self, bar: BarAPI, stamp: int) -> None:
        stamps = self._rolls_[0]
        while self._roll_index_ < stamps.size and stamps[self._roll_index_] <= stamp:
            moment = int(stamps[self._roll_index_])
            if self._positions_ and moment > self._mark_:
                segment = self._segment_(bar, self._mark_, moment - 1)
                if segment is not None: self.portfolio.update_data(segment)
                self._mark_, self._segmented_ = moment, True
            self._charge_()

    def _next_pid_(self) -> int:
        next(self._tids_)
        return next(self._pids_)

    def _quantity_(self, volume: float) -> float:
        return volume / self._contract_.LotSize if self._contract_.LotSize else 0.0

    def _build_position_(self, direction: Direction, position_type: PositionType, volume: float, tick: TickAPI, sl_price: Union[float, None], tp_price: Union[float, None]) -> PositionAPI:
        ask, bid = self._ask_bid_(tick)
        entry_price = ask if direction == Direction.Buy else bid
        quote_conversion = self._conversions_(tick)[1]
        gross = (bid - ask) * volume * quote_conversion
        commission = self._fee_(volume, tick)
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
            SpreadPnL=gross,
            CommissionPnL=commission,
            SwapPnL=0.0,
            NetPnL=gross + commission,
            UsedMargin=0.0,
            StopLossPrice=sl_price,
            TakeProfitPrice=tp_price,
            Label=self.__class__.__name__,
            Comment=position_type.name
        )

    def _lots_of_(self, position: PositionAPI) -> list:
        lots = self._lots_.get(position.UID)
        if lots is None: lots = self._lots_[position.UID] = [[position.EntryTimestamp.DateTime, position.EntryPrice.Price, position.Volume, position.CommissionPnL.PnL if position.CommissionPnL else 0.0, position.SpreadPnL.PnL if position.SpreadPnL else 0.0]]
        return lots

    def _consume_(self, position: PositionAPI, volume: float) -> tuple[datetime, float, float, float]:
        lots, left, portions, commission, spread = self._lots_of_(position), volume, [], 0.0, 0.0
        while left > EPSILON and lots:
            stamp, price, size, fee, paid = lots[0]
            taken = min(size, left)
            portions.append((stamp, price, taken))
            share = quantize(fee * (taken / size)) if taken < size - EPSILON else fee
            commission, spread, left = commission + share, spread + paid * (taken / size), left - taken
            if taken < size - EPSILON: lots[0] = [stamp, price, size - taken, quantize(fee - share), paid * ((size - taken) / size)]
            else: lots.pop(0)
        entry = portions[0][1] if len(portions) == 1 else sum(price * taken for _, price, taken in portions) / sum(taken for _, _, taken in portions)
        return portions[0][0], entry, commission, spread

    def _build_trade_(self, position: PositionAPI, volume: float, tick: TickAPI, exit_price: float) -> TradeAPI:
        direction = position.Direction
        quote_conversion = self._conversions_(tick)[1]
        opened, entry, commission, spread = self._consume_(position, volume)
        delta = (exit_price - entry) if direction == Direction.Buy else (entry - exit_price)
        gross = delta * volume * quote_conversion
        ratio = volume / position.Volume if position.Volume else 1.0
        conversion = self._contract_.ConversionFee if self._quote_asset_ != self._account_asset_ else None
        commission = quantize(commission + self._fee_(volume, tick) - (conversion / 100.0 * max(gross, 0.0) if conversion else 0.0))
        swap = (position.SwapPnL.PnL if position.SwapPnL else 0.0) * ratio
        return TradeAPI(
            UID=next(self._tids_),
            Position=position.UID,
            Account=self.account,
            Security=self._security_,
            Type=position.Type,
            Direction=direction,
            EntryTimestamp=opened,
            ExitTimestamp=tick.Timestamp.DateTime,
            EntryPrice=entry,
            ExitPrice=exit_price,
            Volume=volume,
            Quantity=self._quantity_(volume),
            GrossPnL=gross,
            SpreadPnL=spread,
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

    def _position_mode_(self) -> PositionMode:
        node = self._parameters_.PortfolioManagement
        value = node.first("PositionMode", MISSING) if node else MISSING
        if value is MISSING: return PositionMode.Hedging
        return value if isinstance(value, PositionMode) else PositionMode[str(value)]

    def _net_position_(self) -> Union[PositionAPI, None]:
        return next(iter(self._positions_.values()), None)

    def _emit_increase_(self, position: PositionAPI, direction: Direction, volume: float) -> None:
        ask, bid = self._ask_bid_(self._tick_)
        fill = ask if direction == Direction.Buy else bid
        quote_conversion = self._conversions_(self._tick_)[1]
        fee, paid = self._fee_(volume, self._tick_), (bid - ask) * volume * quote_conversion
        self._lots_of_(position).append([self._tick_.Timestamp.DateTime, fill, volume, fee, paid])
        total = position.Volume + volume
        position.EntryPrice.Price = (position.EntryPrice.Price * position.Volume + fill * volume) / total
        position.Volume = total
        position.Quantity = self._quantity_(total)
        position.CommissionPnL = quantize((position.CommissionPnL.PnL if position.CommissionPnL else 0.0) + fee)
        position.SpreadPnL = (position.SpreadPnL.PnL if position.SpreadPnL else 0.0) + paid
        self._arm_version_ += 1
        update_id = UpdateID.IncreasedBuyPositionVolume if direction == Direction.Buy else UpdateID.IncreasedSellPositionVolume
        self._enqueue_(update_id, self._bar_, position)

    def _emit_reduce_(self, position: PositionAPI, volume: float) -> None:
        remaining = position.Volume - volume
        trade = self._build_trade_(position, volume, self._tick_, self._exit_price_(position, self._tick_))
        lots = self._lots_of_(position)
        position.Volume = remaining
        position.Quantity = self._quantity_(remaining)
        position.CommissionPnL = quantize(sum(lot[3] for lot in lots))
        position.SpreadPnL = sum(lot[4] for lot in lots)
        position.SwapPnL = (position.SwapPnL.PnL if position.SwapPnL else 0.0) * (remaining / (remaining + volume))
        self._arm_version_ += 1
        update_id = UpdateID.DecreasedBuyPositionVolume if position.Direction == Direction.Buy else UpdateID.DecreasedSellPositionVolume
        self._enqueue_(update_id, position, trade, self._bar_)

    def _emit_net_open_(self, action: Union[OpenBuyPositionActionAPI, OpenSellPositionActionAPI], direction: Direction, volume: float, sl_price, tp_price) -> None:
        position = self._net_position_()
        if position is None:
            self._emit_plain_open_(action, direction, volume, sl_price, tp_price); return
        if position.Direction == direction:
            self._emit_increase_(position, direction, volume); return
        if volume < position.Volume - EPSILON:
            self._emit_reduce_(position, volume); return
        closed = UpdateID.ClosedBuyPosition if position.Direction == Direction.Buy else UpdateID.ClosedSellPosition
        remainder = volume - position.Volume
        self._emit_close_(position, self._tick_, closed)
        if remainder > EPSILON:
            self._emit_plain_open_(action, direction, remainder, sl_price, tp_price)

    def _emit_plain_open_(self, action: Union[OpenBuyPositionActionAPI, OpenSellPositionActionAPI], direction: Direction, volume: float, sl_price, tp_price) -> None:
        position = self._build_position_(direction, action.PositionType, volume, self._tick_, sl_price, tp_price)
        self._positions_[position.UID] = position
        self._arm_version_ += 1
        update_id = UpdateID.OpenedBuyPosition if direction == Direction.Buy else UpdateID.OpenedSellPosition
        self._enqueue_(update_id, self._bar_, position)

    def _emit_open_(self, action: Union[OpenBuyPositionActionAPI, OpenSellPositionActionAPI], direction: Direction) -> None:
        volume = action.Volume
        if volume > self._contract_.VolumeMax or volume < self._contract_.VolumeMin or not equals(volume % self._contract_.VolumeStep, 0.0):
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
        if self._netting_: self._emit_net_open_(action, direction, volume, sl_price, tp_price)
        else: self._emit_plain_open_(action, direction, volume, sl_price, tp_price)

    def _emit_close_(self, position: PositionAPI, tick: TickAPI, update_id: UpdateID) -> None:
        trade = self._build_trade_(position, position.Volume, tick, self._exit_price_(position, tick))
        del self._positions_[position.UID]
        self._lots_.pop(position.UID, None)
        self._arm_version_ += 1
        self._enqueue_(update_id, position, trade, self._bar_)

    def _emit_target_volume_(self, action: ActionAPI, direction: Direction, intent: int) -> None:
        position = self._positions_.get(action.PositionID)
        if position is None: self._log_.error(lambda: "Action Modify Volume: Failed · Due to Position not found"); return
        if equals(action.Volume, 0.0):
            if intent > 0: self._log_.error(lambda: "Action Increase Volume: Failed · Due to target being zero"); return
            self._emit_close_(position, self._tick_, UpdateID.ClosedBuyPosition if direction == Direction.Buy else UpdateID.ClosedSellPosition); return
        delta = action.Volume - position.Volume
        if equals(delta, 0.0): return
        if intent > 0 and delta < 0.0: self._log_.error(lambda: f"Action Increase Volume: Failed · Due to target below current ({action.Volume} < {position.Volume})"); return
        if intent < 0 and delta > 0.0: self._log_.error(lambda: f"Action Decrease Volume: Failed · Due to target above current ({action.Volume} > {position.Volume})"); return
        if delta > 0.0: self._emit_increase_(position, direction, delta)
        else: self._emit_reduce_(position, -delta)

    def _emit_modify_(self, position_id: int, field: str, price: Union[float, None], update_id: UpdateID, label: str) -> None:
        position = self._positions_.get(position_id)
        if position is None: self._log_.error(lambda: f"Action Modify {label}: Failed · Due to Position not found"); return
        setattr(position, field, self._round_(price) if price is not None else None)
        self._arm_version_ += 1
        self._enqueue_(update_id, self._bar_, position)

    def send_action(self, action: ActionAPI) -> None:
        match action.ActionID:
            case ActionID.Complete | ActionID.Init: pass
            case ActionID.Execution: self._enqueue_(UpdateID.Execution)
            case ActionID.OpenBuyPosition: self._touch_(); self._emit_open_(action, Direction.Buy)
            case ActionID.OpenSellPosition: self._touch_(); self._emit_open_(action, Direction.Sell)
            case ActionID.CloseBuyPosition | ActionID.CloseSellPosition:
                self._touch_()
                position = self._positions_.get(action.PositionID)
                if position is None: self._log_.error(lambda: "Action Close: Failed · Due to Position not found"); return
                self._emit_close_(position, self._tick_, UpdateID.ClosedBuyPosition if action.ActionID == ActionID.CloseBuyPosition else UpdateID.ClosedSellPosition)
            case ActionID.IncreaseBuyPositionVolume: self._touch_(); self._emit_target_volume_(action, Direction.Buy, 1)
            case ActionID.IncreaseSellPositionVolume: self._touch_(); self._emit_target_volume_(action, Direction.Sell, 1)
            case ActionID.DecreaseBuyPositionVolume: self._touch_(); self._emit_target_volume_(action, Direction.Buy, -1)
            case ActionID.DecreaseSellPositionVolume: self._touch_(); self._emit_target_volume_(action, Direction.Sell, -1)
            case ActionID.ModifyBuyPositionVolume: self._touch_(); self._emit_target_volume_(action, Direction.Buy, 0)
            case ActionID.ModifySellPositionVolume: self._touch_(); self._emit_target_volume_(action, Direction.Sell, 0)
            case ActionID.ModifyBuyPositionStopLoss: self._emit_modify_(action.PositionID, str(PositionAPI.ID.StopLossPrice), action.StopLoss, UpdateID.ModifiedBuyPositionStopLoss, "Stop-Loss")
            case ActionID.ModifySellPositionStopLoss: self._emit_modify_(action.PositionID, str(PositionAPI.ID.StopLossPrice), action.StopLoss, UpdateID.ModifiedSellPositionStopLoss, "Stop-Loss")
            case ActionID.ModifyBuyPositionTakeProfit: self._emit_modify_(action.PositionID, str(PositionAPI.ID.TakeProfitPrice), action.TakeProfit, UpdateID.ModifiedBuyPositionTakeProfit, "Take-Profit")
            case ActionID.ModifySellPositionTakeProfit: self._emit_modify_(action.PositionID, str(PositionAPI.ID.TakeProfitPrice), action.TakeProfit, UpdateID.ModifiedSellPositionTakeProfit, "Take-Profit")
            case ActionID.AskAboveTarget: self._ask_above_ = action.Ask; self._arm_version_ += 1
            case ActionID.AskBelowTarget: self._ask_below_ = action.Ask; self._arm_version_ += 1
            case ActionID.BidAboveTarget: self._bid_above_ = action.Bid; self._arm_version_ += 1
            case ActionID.BidBelowTarget: self._bid_below_ = action.Bid; self._arm_version_ += 1

    @staticmethod
    def _intrabar_(bar: BarAPI) -> list[TickAPI]:
        ticks = {tick.Timestamp.DateTime: tick for tick in (bar.OpenPoint.BidTick, bar.HighPoint.AskTick, bar.HighPoint.BidTick, bar.LowPoint.AskTick, bar.LowPoint.BidTick, bar.ClosePoint.BidTick)}
        return [ticks[stamp] for stamp in sorted(ticks)]

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

    @staticmethod
    def _epoch_(timestamp: Union[int, datetime]) -> int:
        return timestamp if isinstance(timestamp, int) else datetime_to_epoch(timestamp)

    @staticmethod
    def _datetime_(timestamp: Union[int, datetime]) -> datetime:
        return epoch_to_datetime(timestamp) if isinstance(timestamp, int) else timestamp

    def _conversion_at_(self, timestamp: Union[int, datetime]) -> tuple:
        stamps, (base, quote) = np.array([self._epoch_(timestamp)], dtype=np.int64), self._dataset_.Conversions[:2]
        return tuple(None if math.isnan(rate[0]) else float(rate[0]) for rate in (*TapeAPI.rates(stamps, base), *TapeAPI.rates(stamps, quote)))

    def _rates_(self, stamps: np.ndarray, asks: np.ndarray, bids: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        ones = np.ones(stamps.size)
        if self._needs_conversion_: return (*TapeAPI.rates(stamps, self._dataset_.Conversions[0]), *TapeAPI.rates(stamps, self._dataset_.Conversions[1]))
        if self._account_asset_ == self._quote_asset_: return asks, bids, ones, ones
        if self._account_asset_ == self._base_asset_: return ones, ones, 1.0 / bids, 1.0 / asks
        return ones, ones, ones, ones

    def _tick_conversions_(self, timestamp: Union[int, datetime], raw_ask: float, raw_bid: float) -> tuple:
        if self._needs_conversion_: return self._conversion_at_(timestamp)
        if self._account_asset_ == self._quote_asset_: return raw_ask, raw_bid, 1.0, 1.0
        if self._account_asset_ == self._base_asset_: return 1.0, 1.0, 1.0 / raw_bid, 1.0 / raw_ask
        return 1.0, 1.0, 1.0, 1.0

    def _synth_tick_(self, timestamp: Union[int, datetime], ask: float, bid: float, raw_ask: float, raw_bid: float) -> TickAPI:
        ask_base, bid_base, ask_quote, bid_quote = self._tick_conversions_(timestamp, raw_ask, raw_bid)
        return TickAPI(Security=self._security_, Timestamp=self._datetime_(timestamp), Ask=ask, Bid=bid, AskBaseConversion=ask_base, BidBaseConversion=bid_base, AskQuoteConversion=ask_quote, BidQuoteConversion=bid_quote, Volume=1.0)

    def _span_(self, bar: BarAPI) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if self._walks_ticks_() or self._finer_():
            source = self._dataset_.Ticks if self._walks_ticks_() else self._dataset_.Points
            start, stop = self._bounds_(source.Stamps, bar.OpenPoint.BidTick.Timestamp.DateTime, bar.ClosePoint.BidTick.Timestamp.DateTime)
            return source.Stamps[start:stop], source.Asks[start:stop], source.Bids[start:stop]
        ticks = self._intrabar_(bar)
        return np.array([datetime_to_epoch(tick.Timestamp.DateTime) for tick in ticks], dtype=np.int64), np.array([tick.Ask.Price for tick in ticks]), np.array([tick.Bid.Price for tick in ticks])

    def _segment_(self, bar: BarAPI, first: int, last: int) -> Union[BarAPI, None]:
        stamps, asks, bids = self._span_(bar)
        low, high = int(np.searchsorted(stamps, first, side="left")), int(np.searchsorted(stamps, last, side="right"))
        if high <= low: return None
        extremes = (bar.HighPoint.AskTick, bar.HighPoint.BidTick, bar.LowPoint.AskTick, bar.LowPoint.BidTick)
        covered = all(first <= datetime_to_epoch(tick.Timestamp.DateTime) <= last for tick in extremes)
        if self._positions_ and not covered:
            longs, shorts = any(position.Direction == Direction.Buy for position in self._positions_.values()), any(position.Direction == Direction.Sell for position in self._positions_.values())
            ask_high, ask_low = (low + int(np.argmax(asks[low:high])), low + int(np.argmin(asks[low:high]))) if shorts else (low, low)
            bid_high, bid_low = (low + int(np.argmax(bids[low:high])), low + int(np.argmin(bids[low:high]))) if longs else (low, low)
            points = (low, ask_high, bid_high, ask_low, bid_low, high - 1)
        else: points = (low, low, low, low, low, high - 1)
        index = np.unique(points)
        rates = [[None if rate != rate else float(rate) for rate in column] for column in self._rates_(stamps[index], asks[index], bids[index])]
        ticks = {int(at): TickAPI(Security=self._security_, Timestamp=epoch_to_datetime(int(stamps[at])), Ask=float(asks[at]), Bid=float(bids[at]), AskBaseConversion=rates[0][k], BidBaseConversion=rates[1][k], AskQuoteConversion=rates[2][k], BidQuoteConversion=rates[3][k], Volume=1.0) for k, at in enumerate(index)}
        opened, high_ask, high_bid, low_ask, low_bid, closed = (ticks[point] for point in points)
        if self._positions_ and covered: high_ask, high_bid, low_ask, low_bid = extremes
        return BarAPI(Security=self._security_, Timeframe=self._timeframe_, Timestamp=bar.Timestamp.DateTime, GapPoint=bar.GapPoint, OpenPoint=PointAPI(AskTick=opened, MidTick=opened, BidTick=opened),
                      HighPoint=PointAPI(AskTick=high_ask, BidTick=high_bid), LowPoint=PointAPI(AskTick=low_ask, BidTick=low_bid), ClosePoint=PointAPI(AskTick=closed, MidTick=closed, BidTick=closed), Volume=float(high - low))

    def _cut_(self, stamp: int) -> None:
        self._roll_through_(self._walked_, stamp)
        if self._segmented_ and self._mark_ == stamp: return
        segment = self._segment_(self._walked_, self._mark_, stamp)
        if segment is not None:
            self.portfolio.update_data(segment)
            self._bar_ = segment
        self._mark_, self._segmented_ = stamp, True

    def _touch_(self) -> None:
        stamp = datetime_to_epoch(self._tick_.Timestamp.DateTime)
        if self._walking_: self._cut_(stamp)
        else: self._accrue_(stamp)

    def _walk_(self, timestamp: Union[int, datetime], raw_ask: float, raw_bid: float) -> Iterator:
        ask, bid = self._effective_ask_bid_(raw_ask, raw_bid)
        spread = (raw_ask - raw_bid) if self._spread_type_ in (SpreadType.Accurate, SpreadType.Approximate) else self._spread_value_amount_(raw_ask, raw_bid)
        stamp = self._epoch_(timestamp)
        for position in list(self._positions_.values()):
            if position.UID not in self._positions_: continue
            level, update_id = self._stop_level_(position, ask, bid)
            if level is not None:
                self._cut_(stamp)
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

    @classmethod
    def _bounds_(cls, array: np.ndarray, open_ts: Union[int, datetime], close_ts: Union[int, datetime]) -> tuple[int, int]:
        if array.size == 0: return 0, 0
        return int(np.searchsorted(array, cls._epoch_(open_ts), side="left")), int(np.searchsorted(array, cls._epoch_(close_ts), side="right"))

    def _effective_bounds_(self, raw_ask: Union[float, np.ndarray], raw_bid: Union[float, np.ndarray]) -> tuple:
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

    def _reachable_(self, bid_low: Union[float, np.ndarray], bid_high: Union[float, np.ndarray], ask_low: Union[float, np.ndarray], ask_high: Union[float, np.ndarray]) -> Union[bool, np.ndarray]:
        pad, reach = 10.0 ** -self._digits_, False
        if self._ask_above_ is not None: reach = reach | (ask_high >= self._ask_above_ - pad)
        if self._ask_below_ is not None: reach = reach | (ask_low <= self._ask_below_ + pad)
        if self._bid_above_ is not None: reach = reach | (bid_high >= self._bid_above_ - pad)
        if self._bid_below_ is not None: reach = reach | (bid_low <= self._bid_below_ + pad)
        for position in self._positions_.values():
            sl = self._stored_(position.StopLossPrice)
            tp = self._stored_(position.TakeProfitPrice)
            if position.Direction == Direction.Buy:
                if sl is not None: reach = reach | (bid_low <= sl + pad)
                if tp is not None: reach = reach | (bid_high >= tp - pad)
            else:
                if sl is not None: reach = reach | (ask_high >= sl - pad)
                if tp is not None: reach = reach | (ask_low <= tp + pad)
        return reach

    def _gate_(self, bar: BarAPI) -> bool:
        bid_low, ask_low, _ = self._effective_bounds_(bar.LowPoint.AskTick.Ask.Price, bar.LowPoint.BidTick.Bid.Price)
        bid_high, _, ask_high = self._effective_bounds_(bar.HighPoint.AskTick.Ask.Price, bar.HighPoint.BidTick.Bid.Price)
        return bool(self._reachable_(bid_low, bid_high, ask_low, ask_high))

    def _stream_(self, ticks: TapeAPI, bar: BarAPI) -> Iterator[tuple[int, float, float]]:
        start, stop = self._bounds_(ticks.Stamps, bar.OpenPoint.BidTick.Timestamp.DateTime, bar.ClosePoint.BidTick.Timestamp.DateTime)
        if stop <= start: return
        times, asks, bids = ticks.Stamps[start:stop], ticks.Asks[start:stop], ticks.Bids[start:stop]
        bid, ask_low, ask_high = self._effective_bounds_(asks, bids)
        size, cursor, version, candidates, pointer = stop - start, 0, None, None, 0
        while cursor < size:
            if version != self._arm_version_:
                version = self._arm_version_
                candidates = np.flatnonzero(self._reachable_(bid, bid, ask_low, ask_high))
                pointer = int(np.searchsorted(candidates, cursor, side="left"))
            if pointer >= candidates.size: return
            index = int(candidates[pointer]); pointer += 1
            yield int(times[index]), float(asks[index]), float(bids[index])
            cursor = index + 1

    @staticmethod
    def _points_(tape: TapeAPI, bars: pl.DataFrame) -> TapeAPI:
        rows = np.sort(np.column_stack((bars["Open"].to_numpy(), bars["HighAsk"].to_numpy(), bars["HighBid"].to_numpy(), bars["LowAsk"].to_numpy(), bars["LowBid"].to_numpy(), bars["Close"].to_numpy())), axis=1)
        distinct = np.ones(rows.shape, dtype=bool)
        distinct[:, 1:] = rows[:, 1:] != rows[:, :-1]
        index = rows[distinct]
        return TapeAPI(Security=tape.Security, Stamps=tape.Stamps[index], Asks=tape.Asks[index], Bids=tape.Bids[index], Volumes=tape.Volumes[index])

    def _intrabar_source_(self, bar: BarAPI) -> Iterator[tuple[Union[int, datetime], float, float]]:
        if self._auto_:
            if not self._gate_(bar):
                self._skipped_ += 1
                return
            self._descended_ += 1
            yield from self._stream_(self._dataset_.Ticks, bar)
        elif self._walks_ticks_():
            yield from self._stream_(self._dataset_.Ticks, bar)
        elif self._finer_():
            yield from self._stream_(self._dataset_.Points, bar)
        else:
            for t in self._intrabar_(bar): yield t.Timestamp.DateTime, t.Ask.Price, t.Bid.Price

    def _generate_(self) -> Iterator:
        self._enqueue_(UpdateID.Account, self.account)
        yield
        self._enqueue_(UpdateID.Security, self.security)
        yield
        self._enqueue_(UpdateID.Execution)
        yield
        bars = self._dataset_.ExecutionBars
        total = len(bars)
        tracker = ProgressAPI(total, label=self._identity_(), unit="bars")
        for index, bar in enumerate(bars):
            tracker.advance()
            close = datetime_to_epoch(bar.ClosePoint.BidTick.Timestamp.DateTime)
            if not index: self._walked_, self._mark_ = bar, datetime_to_epoch(bar.OpenPoint.BidTick.Timestamp.DateTime)
            self._roll_through_(bar, close)
            if self._segmented_:
                segment = self._segment_(bar, self._mark_, close) if self._positions_ else None
                if segment is not None: self.portfolio.update_data(segment)
                self._segmented_ = False
            self._bar_ = bar
            self._tick_ = bars[index + 1].OpenPoint.BidTick if index + 1 < total else bar.ClosePoint.BidTick
            self._enqueue_(UpdateID.BarClosed, bar)
            yield
            if index + 1 >= total: continue
            nbar = bars[index + 1]
            self._walked_ = nbar
            self._mark_, self._walking_ = datetime_to_epoch(nbar.OpenPoint.BidTick.Timestamp.DateTime), True
            for timestamp, raw_ask, raw_bid in self._intrabar_source_(nbar):
                for _ in self._walk_(timestamp, raw_ask, raw_bid): yield
            self._walking_ = False
        tracker.close()

    def _settle_(self) -> None:
        self._accrue_(datetime_to_epoch(self._stop_))
        if not self._positions_ or self._tick_ is None: return
        for position in self._positions_.values(): self.portfolio.charge(position, commission=self._fee_(position.Volume, self._tick_))
        self.portfolio.settle()

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
            if self._dataset_.IndicatorResults is None:
                rows = self._dataset_.ExecutionRows
                if rows is not None:
                    update.Market.update_data(rows.slice(self._advance_index_, 1))
                else:
                    update.Market.update_data(update.Bar)
                self._advance_index_ += 1

        def report(update: CompleteUpdateAPI):
            self._settle_()
            self._transition_(self._execution_timer_, "Execution", self._finalization_timer_)
            if self._auto_: self._log_.debug(lambda: f"Phase Resolution: Completed · Auto · {self._descended_} Descended · {self._skipped_} Skipped")
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