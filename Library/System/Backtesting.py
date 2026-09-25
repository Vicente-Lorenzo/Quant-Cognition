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
from Library.Universe.Contract import CommissionMode, CommissionType, SpreadType, SwapMode, SwapType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import Weekday, datetime_to_epoch, epoch_to_datetime, parse_datetime
from Library.Utility.Math import EPSILON, equals, truncate
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
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, parameters=parameters, universe=(0, 0.0, 0, 0), portfolio=(0, 0.0, 0, 0), risk_free=risk_free, benchmark=benchmark, report=report, export=export, plot=plot, run=run, description=description)
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

        self._pids_: count = count(start=-1, step=-1)
        self._tids_: count = count(start=-1, step=-1)
        self._positions_: dict[int, PositionAPI] = {}
        self._ask_above_: Union[float, None] = None
        self._ask_below_: Union[float, None] = None
        self._bid_above_: Union[float, None] = None
        self._bid_below_: Union[float, None] = None

        self._preload_seconds_: float = 0.0

    def _connect_(self) -> None:
        if self._spawns_(): self._publish_()
        stack = contextlib.ExitStack()
        stack.__enter__()
        self._stack_ = stack
        try:
            self._db_ = stack.enter_context(PostgresDatabaseAPI(database="Quant"))
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
            stack.__exit__(None, None, None)
            raise
        self._advance_index_ = 0
        self._descended_, self._skipped_ = 0, 0
        self._positions_ = {}
        self._ask_above_ = None
        self._ask_below_ = None
        self._bid_above_ = None
        self._bid_below_ = None
        self._arm_version_ += 1
        self._uid_queue_ = deque()
        self._arg_queue_ = deque()
        self._feed_ = self._generate_()
        super()._connect_()

    def _disconnect_(self) -> None:
        super()._disconnect_()
        if self._stack_: self._stack_.__exit__(None, None, None)

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
                AskBaseConversion=row.get(f"{prefix}.AskBaseConversion"),
                BidBaseConversion=row.get(f"{prefix}.BidBaseConversion"),
                AskQuoteConversion=row.get(f"{prefix}.AskQuoteConversion"),
                BidQuoteConversion=row.get(f"{prefix}.BidQuoteConversion"),
                Volume=row.get(f"{prefix}.Volume")
            )
        def point(prefix: str) -> PointAPI:
            bid = tick(f"{prefix}.BidTick")
            return PointAPI(AskTick=bid if row[f"{prefix}.AskTick.Timestamp"] == row[f"{prefix}.BidTick.Timestamp"] else tick(f"{prefix}.AskTick"), BidTick=bid)
        return BarAPI(
            Security=self._security_,
            Timeframe=self._timeframe_,
            Timestamp=row.get("Timestamp"),
            GapPoint=point("GapPoint"),
            OpenPoint=point("OpenPoint"),
            HighPoint=point("HighPoint"),
            LowPoint=point("LowPoint"),
            ClosePoint=point("ClosePoint"),
            Volume=row.get("Volume")
        )

    def _pair_(self, db: PostgresDatabaseAPI, ticker: str) -> Union[int, None]:
        condition, parameters = db.where(Provider=self._security_.Provider.UID, Ticker=ticker)
        row = db.first(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition=condition, parameters=parameters)
        return row[str(SecurityAPI.ID.UID)] if row else None

    def _route_(self, db: PostgresDatabaseAPI, asset: str) -> Union[tuple[int, bool, str], None]:
        account = self._account_asset_
        if asset == account: return None
        for ticker, inverse in ((f"{asset}{account}", False), (f"{account}{asset}", True)):
            if ticker == self._security_.Ticker.UID: return self._security_.UID, inverse, ticker
            security = self._pair_(db, ticker)
            if security is not None: return security, inverse, ticker
        raise ValueError(f"Conversion {asset} to {account}: Failed · Due to no direct pair ({asset}{account} or {account}{asset})")

    def _source_(self, asset: str, tape: TapeAPI) -> Union[tuple[TapeAPI, bool], None]:
        route = self._route_(self._db_, asset)
        if route is None: return None
        security, inverse, ticker = route
        if security == self._security_.UID: return tape, inverse
        source = TapeAPI.read(self._db_, security, epoch_to_datetime(int(tape.Stamps[0])) - timedelta(days=7), epoch_to_datetime(int(tape.Stamps[-1])), workers=self._readers_, shelf=self._shelf_.get(security, MISSING))
        if not source.Stamps.size or source.Stamps[0] > tape.Stamps[0]: raise ValueError(f"Conversion {asset} to {self._account_asset_}: Failed · Due to no {ticker} quote before {epoch_to_datetime(int(tape.Stamps[0]))}")
        return source, inverse

    def _share_(self, start: datetime, stop: datetime) -> ShareAPI:
        first, last = TapeAPI.reach(start, stop, self._timeframe_)
        with PostgresDatabaseAPI(database="Quant") as db:
            securities = {self._security_.UID: first}
            for asset in (self._security_.Ticker.BaseAsset, self._security_.Ticker.QuoteAsset):
                route = self._route_(db, asset)
                if route is not None and route[0] not in securities: securities[route[0]] = first - timedelta(days=7)
            share = ShareAPI([TapeAPI.read(db, security, begin, last, workers=self._readers_, shared=True) for security, begin in securities.items()])
        self._log_.debug(lambda: f"Shared Tapes: Published · {len(securities)} Tapes · {memory_to_string(share.size())}")
        return share

    def _spawns_(self) -> bool:
        return False

    def _publish_(self) -> ShareAPI:
        if self._shared_ is None:
            self._shared_ = self._share_(self._range_start_, self._range_stop_)
            self._shelf_ = {**self._shelf_, **self._shared_.tapes()}
        return self._shared_

    def _bars_(self, share: ShareAPI, scopes: list) -> dict:
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
        conversions = (self._source_(self._base_asset_, tape), self._source_(self._quote_asset_, tape)) if tape.Stamps.size else (None, None)
        start = datetime_to_epoch(self._start_)
        early = tape.materialize(bars.filter(pl.col("Timestamp") < start), self._timeframe_)
        executed = bars.filter(pl.col("Timestamp") >= start)
        rows = tape.materialize(executed, self._timeframe_, *conversions) if executed.height else None
        if executed.height < 2: return early, (None, None), rows, [], TapeAPI.empty(tape.Security), None, [None]
        window = tape.slice(int(executed["Open"][1]), int(executed["Close"][-1]))
        points = self._points_(window, window.bars(self._resolution_, workers=self._readers_)) if self._finer_() else None
        walked = [self._row_to_bar_(row) for row in rows.slice(1).to_dicts()]
        if self._walks_ticks_(): return early, conversions, rows, walked, window, points, [None]
        visited = executed.slice(1)
        stamps = points.Stamps if points is not None else np.unique(tape.Stamps[np.concatenate((visited["Open"].to_numpy(), visited["HighAsk"].to_numpy(), visited["HighBid"].to_numpy(), visited["LowAsk"].to_numpy(), visited["LowBid"].to_numpy(), visited["Close"].to_numpy()))])
        return early, (self._reduce_(conversions[0], stamps), self._reduce_(conversions[1], stamps)), rows, walked, TapeAPI.empty(tape.Security), points, [None]

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
        return self._security_.UID, self._start_, self._stop_, self._timeframe_.UID, self._resolution_.UID, self._account_asset_

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
        self._disconnect_()
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
            "account": (self._account_asset_, self._account_balance_, self._account_leverage_),
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
        overnights = 0
        for rollover in TapeAPI.rollovers(entry, exit):
            match rollover.weekday():
                case day if day == self._contract_.SwapExtraDay.value: overnights += 3
                case day if day in (Weekday.Saturday.value, Weekday.Sunday.value): overnights += 0
                case _: overnights += 1
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
        rate = self._mid_rate_(tick)
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
        rate = self._mid_rate_(tick)
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
        rate = self._mid_rate_(self._tick_)
        base_conversion, quote_conversion = self._conversions_(self._tick_)
        total = position.Volume + volume
        position.EntryPrice.Price = self._round_((position.EntryPrice.Price * position.Volume + fill * volume) / total)
        position.Volume = total
        position.Quantity = self._quantity_(total)
        previous = position.CommissionPnL.PnL if position.CommissionPnL else 0.0
        position.CommissionPnL = previous + truncate(self._commission_(volume, rate, base_conversion, quote_conversion))
        self._arm_version_ += 1
        update_id = UpdateID.IncreasedBuyPositionVolume if direction == Direction.Buy else UpdateID.IncreasedSellPositionVolume
        self._enqueue_(update_id, self._bar_, position)

    def _emit_reduce_(self, position: PositionAPI, volume: float) -> None:
        initial_commission = position.CommissionPnL.PnL if position.CommissionPnL else 0.0
        remaining = position.Volume - volume
        trade = self._build_trade_(position, volume, self._tick_, self._exit_price_(position, self._tick_))
        position.Volume = remaining
        position.Quantity = self._quantity_(remaining)
        position.CommissionPnL = initial_commission * (remaining / (remaining + volume))
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
            case ActionID.OpenBuyPosition: self._emit_open_(action, Direction.Buy)
            case ActionID.OpenSellPosition: self._emit_open_(action, Direction.Sell)
            case ActionID.CloseBuyPosition | ActionID.CloseSellPosition:
                position = self._positions_.get(action.PositionID)
                if position is None: self._log_.error(lambda: "Action Close: Failed · Due to Position not found"); return
                self._emit_close_(position, self._tick_, UpdateID.ClosedBuyPosition if action.ActionID == ActionID.CloseBuyPosition else UpdateID.ClosedSellPosition)
            case ActionID.IncreaseBuyPositionVolume: self._emit_target_volume_(action, Direction.Buy, 1)
            case ActionID.IncreaseSellPositionVolume: self._emit_target_volume_(action, Direction.Sell, 1)
            case ActionID.DecreaseBuyPositionVolume: self._emit_target_volume_(action, Direction.Buy, -1)
            case ActionID.DecreaseSellPositionVolume: self._emit_target_volume_(action, Direction.Sell, -1)
            case ActionID.ModifyBuyPositionVolume: self._emit_target_volume_(action, Direction.Buy, 0)
            case ActionID.ModifySellPositionVolume: self._emit_target_volume_(action, Direction.Sell, 0)
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
        stamps, (base, quote) = np.array([self._epoch_(timestamp)], dtype=np.int64), self._dataset_.Conversions
        return tuple(None if math.isnan(rate[0]) else float(rate[0]) for rate in (*TapeAPI.rates(stamps, base), *TapeAPI.rates(stamps, quote)))

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
            self._bar_ = bar
            self._tick_ = bars[index + 1].OpenPoint.BidTick if index + 1 < total else bar.ClosePoint.BidTick
            self._enqueue_(UpdateID.BarClosed, bar)
            yield
            if index + 1 >= total: continue
            nbar = bars[index + 1]
            self._bar_ = nbar
            for timestamp, raw_ask, raw_bid in self._intrabar_source_(nbar):
                for _ in self._walk_(timestamp, raw_ask, raw_bid): yield
        tracker.close()

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
            if self.strategy.Transform.Market and self._dataset_.IndicatorResults is None:
                rows = self._dataset_.ExecutionRows
                if rows is not None:
                    update.Market.update_data(rows.slice(self._advance_index_, 1))
                else:
                    update.Market.update_data(update.Bar)
                self._advance_index_ += 1

        def report(update: CompleteUpdateAPI):
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