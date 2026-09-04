from __future__ import annotations

import math
import os
import shutil

from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Type, Union, TYPE_CHECKING

from Library.Database.Dataframe import np, pl
from Library.Model.Split import SplitAPI
from Library.Portfolio.Statistic import CALMARRATIO, MAXEQUITYDRAWDOWNPERC, NETRETURNANNPERC, NETRETURNPERC, NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, SHARPERATIO, SORTINORATIO, STERLINGRATIO, TOTALTRADESVALUE
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.Strategy.Model.Reward import RewardType
from Library.System.Backtesting import BacktestingAPI, DatasetAPI
from Library.System.Selection import ElectionMode, SelectionMode, elect, select
from Library.Utility.Enumeration import EnumerationAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Utility.IO import mkdir, write_json
from Library.Utility.Progress import ProgressAPI
from Library.Utility.Statistic import timer
from Library.Utility.Typing import Missing

if TYPE_CHECKING:
    from Library.Utility.Parameter import Parameter
    from Library.Strategy.Strategy import StrategyAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Timeframe import TimeframeAPI

class _FrozenResultAPI_:

    def __init__(self, values: np.ndarray, cursor: list) -> None:
        self._values_ = values
        self._cursor_ = cursor

    def last(self, shift: int = 0, dataframe: bool = False):
        index = self._cursor_[0] - shift
        if index < 0 or index >= self._values_.size: return None
        value = self._values_[index]
        return None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)

class _FrozenIndicatorAPI_:

    def __init__(self, name: str, values: np.ndarray, cursor: list) -> None:
        self.Name = name
        self.Result = _FrozenResultAPI_(values, cursor)

class _FrozenTechnicalAPI_:

    def __init__(self, results: dict) -> None:
        self._cursor_ = [-1]
        self._indicators_ = []
        for name, values in results.items():
            indicator = _FrozenIndicatorAPI_(name, values, self._cursor_)
            self._indicators_.append(indicator)
            setattr(self, name, indicator)

    def init_data(self, market=None) -> None:
        self._cursor_[0] = -1

    def update_data(self, market=None) -> None:
        self._cursor_[0] += 1

    def update_offset(self, offset: int = 1) -> None:
        pass

class FitnessType(EnumerationAPI):
    AnnualizedReturn = NETRETURNANNPERC
    SharpeRatio = SHARPERATIO
    SortinoRatio = SORTINORATIO
    CalmarRatio = CALMARRATIO
    SterlingRatio = STERLINGRATIO
    AccountReturn = "Account Return"

class LearningAPI(BacktestingAPI):

    def __init__(self,
                 strategy: Type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 parameters: Parameter,
                 start: Union[str, date, datetime],
                 stop: Union[str, date, datetime],
                 account: tuple[str, float, float],
                 spread: tuple[SpreadType, Union[float, Missing, None]],
                 commission: tuple[CommissionType, Union[float, Missing, None]],
                 swap: tuple[SwapType, Union[float, Missing, None], Union[float, Missing, None]],
                 reward: Union[str, RewardType],
                 episodes: int,
                 epochs: int = 1,
                 train_frequency: int = 1,
                 gradient_steps: int = 1,
                 purge: Union[int, None] = None,
                 embargo: Union[int, None] = None,
                 training: int = 0,
                 validation: int = 0,
                 testing: int = 0,
                 rolling: bool = False,
                 continuous: bool = False,
                 fitness: Union[str, FitnessType] = FitnessType.AnnualizedReturn,
                 selection: Union[str, SelectionMode] = SelectionMode.Best,
                 election: Union[str, ElectionMode] = ElectionMode.Last,
                 patience: int = 0,
                 activity: int = 0,
                 balance: int = 0,
                 ratio: float = 0.0,
                 mirror: bool = False,
                 mirror_ratio: float = 0.5,
                 final: bool = False,
                 seed: Union[int, None] = None,
                 seeds: int = 1,
                 workers: int = 1,
                 threads: Union[int, None] = None,
                 benchmark: Union[str, list, None] = None,
                 report: bool = True,
                 export: bool = True,
                 plot: bool = False,
                 run: Union[str, Path, None] = None,
                 description: Union[str, None] = None) -> None:
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, resolution=timeframe, parameters=parameters, start=start, stop=stop, account=account, spread=spread, commission=commission, swap=swap, benchmark=benchmark, report=False, export=False, plot=False, run=run, description=description)
        self._deliverables_: tuple[bool, bool, bool] = (report, export, plot)
        self._reward_type_: RewardType = RewardType.parse(reward) if isinstance(reward, str) else reward
        self._episodes_: int = episodes
        self._tracker_: Union[ProgressAPI, None] = None
        self._epochs_: int = epochs
        self._train_frequency_: int = train_frequency
        self._gradient_steps_: int = gradient_steps
        self._training_: int = training
        self._validation_: int = validation
        self._testing_: int = testing
        self._rolling_: bool = rolling
        self._purge_, self._embargo_ = purge, embargo
        self._continuous_: bool = continuous
        try: fitness_type = FitnessType(fitness)
        except ValueError: raise ValueError(f"Unknown fitness metric: {fitness} · Expected one of {[member.name for member in FitnessType]}")
        self._fitness_label_: str = fitness_type.value
        self._selection_ = selection if isinstance(selection, SelectionMode) else SelectionMode.parse(selection)
        self._election_ = election if isinstance(election, ElectionMode) else ElectionMode.parse(election)
        self._patience_: int = patience
        self._activity_: int = activity
        self._balance_: int = balance
        self._ratio_: float = ratio
        self._mirror_: bool = mirror
        self._mirror_ratio_: float = mirror_ratio
        self._final_: bool = final
        self._seed_: Union[int, None] = seed
        self._seeds_: int = seeds
        self._workers_: int = workers
        self._threads_: Union[int, None] = threads
        self._range_start_: datetime = self._start_
        self._range_stop_: datetime = self._stop_
        self._weights_: Path = self._weights_directory_()
        self._tapes_: dict = {}

    def _connect_(self) -> None:
        super()._connect_()
        dataset = getattr(self, "_dataset_", None)
        if dataset is not None and dataset.IndicatorResults:
            frozen = _FrozenTechnicalAPI_(dataset.IndicatorResults)
            self.indicator.Technical = frozen
            self.technical = frozen

    def _weights_directory_(self) -> Path:
        directory = DDPGStrategyAPI._DEFAULT_WEIGHTS_ / f"{self._security_.UID} {self._timeframe_.UID} {self._strategy_.__name__}"
        mkdir(directory)
        return directory

    def _fitness_(self) -> float:
        if self._fitness_label_ == FitnessType.AccountReturn.value:
            return self._account_return_()
        return self._metric_(self._fitness_label_)

    def _net_return_(self) -> float:
        return self._metric_(NETRETURNPERC)

    def _trades_(self) -> float:
        return self._metric_(TOTALTRADESVALUE)

    def _exposure_directions_(self) -> tuple[float, float]:
        strategy = self.strategy
        if strategy is None: return 0.0, 0.0
        return float(strategy._long_bars_), float(strategy._short_bars_)

    def _pass_(self, start: datetime, stop: datetime, training: bool, mirror: bool = False) -> float:
        self._strategy_.Training = training
        self._disconnect_()
        self._start_, self._stop_ = start, stop
        key = (start, stop, mirror)
        if mirror and key not in self._tapes_:
            source = self._tapes_.get((start, stop, False))
            if source is not None: self._tapes_[key] = self._mirror_dataset_(source)
        self.inject(self._tapes_.get(key))
        with self.quieted():
            self._connect_()
            self.deploy()
        if key not in self._tapes_: self._tapes_[key] = replace(self.extract(), IndicatorResults=self._capture_() if not mirror else None)
        return self._fitness_()

    _MIRROR_TICKS_ = ("GapTick", "OpenTick", "HighTick", "LowTick", "CloseTick")
    _MIRROR_SWAP_ = {"HighTick": "LowTick", "LowTick": "HighTick"}
    _MIRROR_CONVERSIONS_ = ("AskBaseConversion", "BidBaseConversion", "AskQuoteConversion", "BidQuoteConversion")

    @staticmethod
    def _mirror_frame_(frame: Union[pl.DataFrame, None], anchor: float) -> Union[pl.DataFrame, None]:
        if frame is None or frame.is_empty(): return frame
        columns = []
        for prefix in LearningAPI._MIRROR_TICKS_:
            source = LearningAPI._MIRROR_SWAP_.get(prefix, prefix)
            if f"{prefix}.Ask" not in frame.columns: continue
            columns.append((anchor / pl.col(f"{source}.Bid")).alias(f"{prefix}.Ask"))
            columns.append((anchor / pl.col(f"{source}.Ask")).alias(f"{prefix}.Bid"))
            if f"{prefix}.Mid" in frame.columns: columns.append((anchor / pl.col(f"{source}.Mid")).alias(f"{prefix}.Mid"))
            columns.append(pl.col(f"{source}.Timestamp").alias(f"{prefix}.Timestamp"))
            if f"{prefix}.Volume" in frame.columns: columns.append(pl.col(f"{source}.Volume").alias(f"{prefix}.Volume"))
            for conversion in LearningAPI._MIRROR_CONVERSIONS_:
                if f"{prefix}.{conversion}" in frame.columns: columns.append(pl.lit(None, dtype=pl.Float64).alias(f"{prefix}.{conversion}"))
        return frame.with_columns(columns)

    def _mirror_dataset_(self, dataset: DatasetAPI) -> DatasetAPI:
        rows = dataset.ExecutionRows if dataset.ExecutionRows is not None else None
        warmup = dataset.WarmupBars
        source = warmup if warmup is not None and warmup.height else rows
        anchor_price = source["CloseTick.Bid"][0] if source is not None and source.height else 1.0
        anchor = anchor_price * anchor_price
        mirrored_warmup = self._mirror_frame_(warmup, anchor)
        mirrored_rows = self._mirror_frame_(rows, anchor)
        bars = [self._row_to_bar_(row) for row in mirrored_rows.to_dicts()] if mirrored_rows is not None else list(dataset.ExecutionBars)
        return replace(dataset, WarmupBars=mirrored_warmup, ExecutionRows=mirrored_rows, ExecutionBars=bars, IndicatorResults=None)

    def _capture_(self) -> Union[dict, None]:
        indicators = getattr(self.technical, "_indicators_", None)
        if not indicators: return None
        total = len(self._dataset_.ExecutionBars)
        results = {}
        for indicator in indicators:
            values = indicator.Result.dataframe().to_numpy()
            results[indicator.Name] = values[-total:] if total and values.size >= total else values
        return results or None

    def _configure_(self, seed: Union[int, None], weights: Path) -> None:
        self._strategy_.Training = True
        self._strategy_.Reward = self._reward_type_
        self._strategy_.Epochs = self._epochs_
        self._strategy_.TrainFrequency = self._train_frequency_
        self._strategy_.GradientSteps = self._gradient_steps_
        self._strategy_.Seed = seed
        self._strategy_.Weights = weights
        self._strategy_.Agent = None

    def _restore_(self) -> None:
        self._strategy_.Training = False
        self._strategy_.Agent = None

    _RESERVED_ = ("Fold ", "Episode ")

    @classmethod
    def _stash_(cls, directory: Path, label: str) -> Path:
        target = directory / label
        if target.exists(): shutil.rmtree(target)
        mkdir(target)
        for item in directory.iterdir():
            if item.is_dir() and not item.name.startswith(cls._RESERVED_): shutil.copytree(item, target / item.name)
        return target

    @classmethod
    def _archive_(cls, directory: Path, index: int) -> None:
        cls._stash_(directory, f"Fold {index}")

    @classmethod
    def _revive_(cls, directory: Path, label: str) -> bool:
        source = directory / label
        if not source.is_dir(): return False
        for item in source.iterdir():
            target = directory / item.name
            if target.exists(): shutil.rmtree(target)
            shutil.copytree(item, target)
        return True

    def _promote_(self, source: Path) -> None:
        shutil.copytree(source, self._weights_, dirs_exist_ok=True, ignore=shutil.ignore_patterns("Fold *"))
        self._log_.info(lambda: f"Checkpoint Learning: Promoted · From {source} · To {self._weights_}")

    def _export_weights_(self) -> None:
        directory = (self._run_ / self._OUTPUT_ / "Weights") if self._run_ is not None else (self._parameters_.path.parent / f"{self._strategy_.__name__.removesuffix('StrategyAPI')} {datetime.now():%Y-%m-%d %H-%M-%S}")
        shutil.copytree(self._weights_, directory, dirs_exist_ok=True, ignore=shutil.ignore_patterns("Seed *", "Fold *"))
        self._log_.info(lambda: f"Weights Learning: Exported · To {directory}")

    def _payload_(self, seed: Union[int, None], directory: Path, folds: list, test: Union[tuple, None]) -> dict:
        return {
            **self._dispatch_(self._parameters_, self._range_start_, self._range_stop_),
            "reward": self._reward_type_,
            "episodes": self._episodes_,
            "epochs": self._epochs_,
            "train_frequency": self._train_frequency_,
            "gradient_steps": self._gradient_steps_,
            "training": self._training_,
            "validation": self._validation_,
            "testing": self._testing_,
            "rolling": self._rolling_,
            "continuous": self._continuous_,
            "fitness": self._fitness_label_,
            "patience": self._patience_,
            "activity": self._activity_,
            "balance": self._balance_,
            "ratio": self._ratio_,
            "mirror": self._mirror_,
            "mirror_ratio": self._mirror_ratio_,
            "final": self._final_,
            "seed": seed,
            "weights": str(directory),
            "folds": folds,
            "test": test,
            "threads": self._threads_ if self._threads_ else max(1, (os.cpu_count() or self._workers_) // self._workers_)
        }

    def _full_range_(self) -> Union[dict, None]:
        self._restore_()
        self._strategy_.Weights = self._weights_
        try:
            with self.deliverables(*self._deliverables_):
                self._pass_(self._range_start_, self._range_stop_, False)
        finally:
            self._strategy_.Weights = None
        return {
            "Start": self._range_start_.isoformat(),
            "Stop": self._range_stop_.isoformat(),
            "NetReturn": self._net_return_(),
            "AccountReturn": (self.portfolio.Equity / self.portfolio.InitialBalance - 1.0) * 100.0 if self.portfolio is not None and self.portfolio.InitialBalance else None,
            "AnnualizedReturn": self._metric_(NETRETURNANNPERC),
            "Sharpe": self._metric_(SHARPERATIO),
            "Sortino": self._metric_(SORTINORATIO),
            "Calmar": self._metric_(CALMARRATIO),
            "MaxDrawdown": self._metric_(MAXEQUITYDRAWDOWNPERC),
            "Trades": self._metric_(TOTALTRADESVALUE),
            "BuyTrades": self._metric_(TOTALTRADESVALUE, NET_BUY_AGGREGATED),
            "SellTrades": self._metric_(TOTALTRADESVALUE, NET_SELL_AGGREGATED),
            "LongBars": self._exposure_directions_()[0],
            "ShortBars": self._exposure_directions_()[1]
        }

    def _manifest_(self, results: list, best: Union[float, None], full_range: Union[dict, None] = None) -> None:
        manifest = {
            "Strategy": self._strategy_.__name__,
            "Security": str(self._security_.UID),
            "Timeframe": str(self._timeframe_.UID),
            "Start": self._range_start_.isoformat(),
            "Stop": self._range_stop_.isoformat(),
            "Reward": self._reward_type_.name,
            "RewardScale": self._strategy_.RewardScale,
            "Episodes": self._episodes_,
            "Epochs": self._epochs_,
            "TrainFrequency": self._train_frequency_,
            "GradientSteps": self._gradient_steps_,
            "Training": self._training_,
            "Validation": self._validation_,
            "Testing": self._testing_,
            "Rolling": self._rolling_,
            "Continuous": self._continuous_,
            "Fitness": self._fitness_label_,
            "Patience": self._patience_,
            "Activity": self._activity_,
            "Balance": self._balance_,
            "Ratio": self._ratio_,
            "Mirror": self._mirror_,
            "MirrorRatio": self._mirror_ratio_,
            "Final": self._final_,
            "Seeds": self._seeds_,
            "Workers": self._workers_,
            "ObservationShape": self.strategy._observation_.shape(),
            "ActionShape": self._strategy_._ACTION_SHAPE_,
            "RiskPercentage": self.strategy._risk_percentage_,
            "ATRScale": self.strategy._atr_scale_,
            "DirectionalEntryThreshold": list(self.strategy.DirectionalEntryThreshold),
            "DirectionalExitThreshold": list(self.strategy.DirectionalExitThreshold),
            "Best": best,
            "FullRange": full_range,
            "Results": results,
            "Weights": str(self._weights_)
        }
        path = self._weights_ / f"{self._strategy_.__name__} Manifest.json"
        write_json(path, manifest)
        self._log_.info(lambda: f"Manifest Learning: Saved · {path}")

    def _train_seed_(self, seed: Union[int, None], directory: Path, folds: list, test: Union[tuple, None]) -> dict:
        self._configure_(seed, directory)
        self._folded_, self._journal_ = [], []
        fold_metrics = []
        fold_returns = []
        for index, (train_window, validation_window) in enumerate(folds, start=1):
            if self._continuous_ and self._strategy_.Agent is not None:
                self._strategy_.Agent.load()
            else:
                self._strategy_.Agent = None
            best_validation = None
            best_return = None
            best_curve = []
            best_train = None
            best_eligible = False
            stale = 0
            online = self._selection_ in (SelectionMode.Best, SelectionMode.Worst, SelectionMode.Plateau)
            ascending = self._selection_ is not SelectionMode.Worst
            attempts = []
            for episode in range(1, self._episodes_ + 1):
                if self._tracker_ is not None: self._tracker_.advance()
                train_metric = self._pass_(train_window[0], train_window[1], True, mirror=self._mirror_ and int(episode * self._mirror_ratio_) != int((episode - 1) * self._mirror_ratio_))
                if self._strategy_.Agent is None: self._strategy_.Agent = self.strategy._agent_
                selection = self._pass_(validation_window[0], validation_window[1], False) if validation_window is not None else train_metric
                longs, shorts = self._exposure_directions_()
                active = self._activity_ <= 0 or self._trades_() >= self._activity_
                balanced = self._balance_ <= 0 or (min(longs, shorts) >= self._balance_ and (self._ratio_ <= 0 or min(longs, shorts) >= self._ratio_ * max(longs, shorts)))
                eligible = validation_window is None or (active and balanced)
                improved = best_validation is None or (selection > best_validation if ascending else selection < best_validation)
                if not online:
                    attempts.append((episode, selection, self._net_return_(), self._tracked_(), train_metric))
                    self.strategy._agent_.save()
                    self._stash_(directory, f"Episode {episode}")
                if (eligible and not best_eligible) or (eligible == best_eligible and improved):
                    best_validation = selection
                    best_return = self._net_return_()
                    best_curve = self._tracked_()
                    best_train = train_metric
                    best_eligible = eligible
                    if online: self.strategy._agent_.save()
                    stale = 0
                else:
                    stale += 1
                if self._final_: self.strategy._agent_.save()
                self._record_(Fold=index, Seed=seed, Episode=episode, Train=train_metric, Validation=selection, Return=self._net_return_(), Longs=longs, Shorts=shorts, Eligible=eligible)
                self._log_.info(lambda s=seed, i=index, e=episode, t=train_metric, v=selection: f"Episode Learning: Completed · Seed {s} · Fold {i} · {e}/{self._episodes_} · Train {t:+.4f} · Selection {v:+.4f}")
                if self._patience_ and stale >= self._patience_:
                    self._log_.info(lambda e=episode: f"Episode Learning: Stopped · Early · Patience {self._patience_} · Episode {e}")
                    break
            if not online and attempts:
                chosen = select([((episode, score, gain, curve, train), score) for episode, score, gain, curve, train in attempts], self._selection_)
                if chosen is not None:
                    (episode, best_validation, best_return, best_curve, best_train), _ = chosen
                    self._revive_(directory, f"Episode {episode}")
                    self._log_.info(lambda e=episode, m=self._selection_: f"Episode Learning: Selected · {m.name} · Episode {e}")
                for spent in directory.glob("Episode *"):
                    shutil.rmtree(spent, ignore_errors=True)
            fold_metrics.append(best_validation)
            fold_returns.append(best_return)
            if validation_window is not None:
                self._stitch_(index, f"Fold {index}", validation_window, best_validation, best_curve, training=best_train)
            self._archive_(directory, index)
            self._log_.info(lambda i=index, n=len(folds), b=best_validation: f"Fold Learning: Completed · {i}/{n} · Best {b:+.4f}")
        if len(folds) > 1 and fold_metrics:
            records = [{"Key": position, "Score": score} for position, score in enumerate(fold_metrics, start=1)]
            chosen = elect(records, self._election_)
            if chosen is not None:
                position, evidence = chosen
                if self._revive_(directory, f"Fold {position}"):
                    self._log_.info(lambda p=position, e=evidence: f"Fold Learning: Elected · {self._election_.name} · Fold {p} · {e.get('Reason')}")
        test_metric = None
        test_return = None
        if test is not None:
            if self._strategy_.Agent is not None: self._strategy_.Agent.load()
            test_metric = self._pass_(test[0], test[1], False)
            test_return = self._net_return_()
        metric = test_metric if test_metric is not None else (sum(fold_metrics) / len(fold_metrics) if fold_metrics else None)
        self._log_.info(lambda s=seed, m=metric, t=test_metric: f"Seed Learning: Completed · {s} · Metric {m:+.4f}" + (f" · Test {t:+.4f}" if t is not None else ""))
        return {"Seed": seed, "Folds": fold_metrics, "FoldsReturn": fold_returns, "Test": test_metric, "TestReturn": test_return,
                "Metric": metric, "Stitched": list(self._folded_), "Journal": list(self._journal_)}

    @timer
    def run(self) -> None:
        folds, test = SplitAPI.walk_forward_folds(self._range_start_, self._range_stop_, self._training_, self._validation_, self._testing_, self._rolling_, self._purge_, self._embargo_)
        seeds = [self._seed_] if self._seeds_ <= 1 else [(self._seed_ or 0) + offset for offset in range(self._seeds_)]
        self._log_.info(lambda: f"Learning Plan: Started · {len(seeds)} Seeds · {len(folds)} Folds · {self._episodes_} Episodes · Test {'Yes' if test else 'No'}")
        parallel = self._workers_ > 1 and len(seeds) > 1
        self._tracker_ = (ProgressAPI(len(seeds), label=self._identity_(), unit="seeds") if parallel
                          else ProgressAPI(len(seeds) * max(1, len(folds)) * self._episodes_, label=self._identity_(), unit="episodes"))
        results = []
        best_metric = None
        best_directory = None
        try:
            if parallel:
                self._log_.info(lambda: f"Parallel Learning: Started · {min(self._workers_, len(seeds))} Workers · {len(seeds)} Seeds")
                directories = {seed: self._weights_ / f"Seed {seed}" for seed in seeds}
                for directory in directories.values(): mkdir(directory)
                payloads = [self._payload_(seed, directories[seed], folds, test) for seed in seeds]
                with ProcessPoolExecutor(max_workers=min(self._workers_, len(seeds))) as pool:
                    results = list(pool.map(_learn_seed_, payloads))
                for result in results:
                    self._tracker_.advance()
                    if result["Metric"] is not None and (best_metric is None or result["Metric"] > best_metric):
                        best_metric = result["Metric"]
                        best_directory = directories[result["Seed"]]
            else:
                for seed in seeds:
                    directory = self._weights_ if len(seeds) <= 1 else self._weights_ / f"Seed {seed}"
                    mkdir(directory)
                    result = self._train_seed_(seed, directory, folds, test)
                    results.append(result)
                    if result["Metric"] is not None and (best_metric is None or result["Metric"] > best_metric):
                        best_metric = result["Metric"]
                        best_directory = directory
            self._tracker_.close()
            elected = next((result for result in results if result["Metric"] == best_metric), None)
            self._folded_ = list(elected.get("Stitched") or []) if elected is not None else []
            self._journal_ = [record for result in results for record in (result.get("Journal") or [])]
            if best_directory is not None and best_directory != self._weights_: self._promote_(best_directory)
            self._manifest_(results, best_metric, self._full_range_())
            self._export_weights_()
            self._aggregate_(results, best_metric)
        finally:
            self._restore_()

    def _aggregate_(self, results: list, best: Union[float, None]) -> None:
        metrics = [result["Metric"] for result in results if result["Metric"] is not None]
        if not metrics: return
        mean = sum(metrics) / len(metrics)
        deviation = (sum((metric - mean) ** 2 for metric in metrics) / len(metrics)) ** 0.5
        self._log_.info(lambda: f"Learning Summary: Completed · {len(metrics)} Seeds · Mean {mean:+.4f} · Std {deviation:.4f} · Best {best:+.4f}")

def _learn_seed_(payload: dict) -> dict:
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    import torch
    torch.set_num_threads(payload.get("threads") or torch.get_num_threads())
    from Library.Logging import LoggingAPI, VerboseLevel
    log = LoggingAPI("Worker")
    log.console.set_level(VerboseLevel.Warning)
    log.file.set_level(VerboseLevel.Debug)
    from Library.Utility.Parameter import Parameter
    security, timeframe = LearningAPI._resolve_(payload)
    learner = LearningAPI(strategy=payload["strategy"], security=security, timeframe=timeframe, parameters=Parameter(payload["parameters"], "."), start=payload["start"], stop=payload["stop"], account=payload["account"], spread=payload["spread"], commission=payload["commission"], swap=payload["swap"], reward=payload["reward"], episodes=payload["episodes"], epochs=payload["epochs"], train_frequency=payload["train_frequency"], gradient_steps=payload["gradient_steps"], training=payload["training"], validation=payload["validation"], testing=payload["testing"], rolling=payload["rolling"], continuous=payload["continuous"], fitness=payload["fitness"], patience=payload["patience"], activity=payload.get("activity", 0), balance=payload.get("balance", 0), ratio=payload.get("ratio", 0.0), mirror=payload.get("mirror", False), mirror_ratio=payload.get("mirror_ratio", 0.5), final=payload.get("final", False), seed=payload["seed"], seeds=1, workers=1, report=False, export=False)
    try:
        return learner._train_seed_(payload["seed"], Path(payload["weights"]), payload["folds"], payload["test"])
    finally:
        learner._restore_()

__all__ = ["LearningAPI"]