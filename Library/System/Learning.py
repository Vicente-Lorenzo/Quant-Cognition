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
from Library.Portfolio.Statistic import NET_TOTAL_AGGREGATED, STATISTICS_METRICS_LABEL
from Library.Strategy.Model import ModelStrategyAPI
from Library.Strategy.Model.Reward import RewardType
from Library.System.Backtesting import BacktestingAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Utility.IO import mkdir, write_json
from Library.Utility.Statistic import Timer, timer
from Library.Utility.Typing import Missing

if TYPE_CHECKING:
    from Library.Parameter import Parameter
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
                 training: int = 0,
                 validation: int = 0,
                 testing: int = 0,
                 rolling: bool = False,
                 fitness: str = "Net Return (%)",
                 patience: int = 0,
                 seed: Union[int, None] = None,
                 seeds: int = 1,
                 workers: int = 1,
                 report: bool = True,
                 export: bool = True) -> None:
        super().__init__(strategy=strategy, security=security, timeframe=timeframe, resolution=timeframe, parameters=parameters, start=start, stop=stop, account=account, spread=spread, commission=commission, swap=swap, report=report, export=export)
        self._reward_type_: RewardType = RewardType.parse(reward) if isinstance(reward, str) else reward
        self._episodes_: int = episodes
        self._epochs_: int = epochs
        self._train_frequency_: int = train_frequency
        self._gradient_steps_: int = gradient_steps
        self._training_: int = training
        self._validation_: int = validation
        self._testing_: int = testing
        self._rolling_: bool = rolling
        self._fitness_label_: str = fitness
        self._patience_: int = patience
        self._seed_: Union[int, None] = seed
        self._seeds_: int = seeds
        self._workers_: int = workers
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
        directory = ModelStrategyAPI._DEFAULT_WEIGHTS_ / f"{self._security_.UID} {self._timeframe_.UID} {self._strategy_.__name__}"
        mkdir(directory)
        return directory

    def _fitness_(self) -> float:
        statistics = self.statistics
        if statistics is not None and not statistics.is_empty() and STATISTICS_METRICS_LABEL in statistics.columns and NET_TOTAL_AGGREGATED in statistics.columns:
            row = statistics.filter(pl.col(STATISTICS_METRICS_LABEL) == self._fitness_label_)
            if row.height:
                value = row[NET_TOTAL_AGGREGATED].item()
                if value is not None: return float(value)
        balance = self.portfolio.InitialBalance if self.portfolio is not None else None
        return self.portfolio.Equity / balance - 1.0 if balance else 0.0

    def _pass_(self, start: datetime, stop: datetime, training: bool) -> float:
        self._strategy_.Training = training
        self._disconnect_()
        self._start_, self._stop_ = start, stop
        key = (start, stop)
        self.inject(self._tapes_.get(key))
        self._connect_()
        self.deploy()
        if key not in self._tapes_: self._tapes_[key] = replace(self.extract(), IndicatorResults=self._capture_())
        return self._fitness_()

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

    def _promote_(self, source: Path) -> None:
        shutil.copytree(source, self._weights_, dirs_exist_ok=True)
        self._log_.info(lambda: f"Checkpoint Learning: Promoted · From {source} · To {self._weights_}")

    def _payload_(self, seed: Union[int, None], directory: Path, folds: list, test: Union[tuple, None]) -> dict:
        return {
            "strategy": self._strategy_,
            "provider": self._security_._provider_.UID,
            "ticker": self._security_._ticker_.UID,
            "timeframe": self._timeframe_.UID,
            "parameters": self._parameters_.data,
            "start": self._range_start_,
            "stop": self._range_stop_,
            "account": (self._account_asset_, self._account_balance_, self._account_leverage_),
            "spread": (self._spread_type_, self._spread_value_),
            "commission": (self._commission_type_, self._commission_value_),
            "swap": (self._swap_type_, self._swap_long_, self._swap_short_),
            "reward": self._reward_type_,
            "episodes": self._episodes_,
            "epochs": self._epochs_,
            "train_frequency": self._train_frequency_,
            "gradient_steps": self._gradient_steps_,
            "training": self._training_,
            "validation": self._validation_,
            "testing": self._testing_,
            "rolling": self._rolling_,
            "fitness": self._fitness_label_,
            "patience": self._patience_,
            "seed": seed,
            "weights": str(directory),
            "folds": folds,
            "test": test,
            "threads": max(1, (os.cpu_count() or self._workers_) // self._workers_)
        }

    def _manifest_(self, results: list, best: Union[float, None]) -> None:
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
            "Fitness": self._fitness_label_,
            "Patience": self._patience_,
            "Seeds": self._seeds_,
            "Workers": self._workers_,
            "ObservationShape": self.strategy._observation_.shape(),
            "ActionShape": self._strategy_._ACTION_SHAPE_,
            "SizingMode": self.strategy._sizing_mode_.name,
            "SizingMax": self.strategy._sizing_max_,
            "SizingDeadzone": self.strategy._sizing_deadzone_,
            "Best": best,
            "Results": results,
            "Weights": str(self._weights_)
        }
        path = self._weights_ / f"{self._strategy_.__name__} Manifest.json"
        write_json(path, manifest)
        self._log_.info(lambda: f"Manifest Learning: Saved · {path}")

    def _train_seed_(self, seed: Union[int, None], directory: Path, folds: list, test: Union[tuple, None]) -> dict:
        self._configure_(seed, directory)
        fold_metrics = []
        for index, (train_window, validation_window) in enumerate(folds, start=1):
            self._strategy_.Agent = None
            best_validation = None
            stale = 0
            for episode in range(1, self._episodes_ + 1):
                train_metric = self._pass_(train_window[0], train_window[1], True)
                if self._strategy_.Agent is None: self._strategy_.Agent = self.strategy._agent_
                selection = self._pass_(validation_window[0], validation_window[1], False) if validation_window is not None else train_metric
                if best_validation is None or selection > best_validation:
                    best_validation = selection
                    self.strategy._agent_.save()
                    stale = 0
                else:
                    stale += 1
                self._log_.info(lambda s=seed, i=index, e=episode, t=train_metric, v=selection: f"Episode Learning: Completed · Seed {s} · Fold {i} · {e}/{self._episodes_} · Train {t:+.4f} · Selection {v:+.4f}")
                if self._patience_ and stale >= self._patience_:
                    self._log_.info(lambda e=episode: f"Episode Learning: Stopped · Early · Patience {self._patience_} · Episode {e}")
                    break
            fold_metrics.append(best_validation)
            self._log_.info(lambda i=index, n=len(folds), b=best_validation: f"Fold Learning: Completed · {i}/{n} · Best {b:+.4f}")
        test_metric = None
        if test is not None:
            if self._strategy_.Agent is not None: self._strategy_.Agent.load()
            test_metric = self._pass_(test[0], test[1], False)
        metric = test_metric if test_metric is not None else (sum(fold_metrics) / len(fold_metrics) if fold_metrics else None)
        self._log_.info(lambda s=seed, m=metric, t=test_metric: f"Seed Learning: Completed · {s} · Metric {m:+.4f}" + (f" · Test {t:+.4f}" if t is not None else ""))
        return {"Seed": seed, "Folds": fold_metrics, "Test": test_metric, "Metric": metric}

    @timer
    def run(self) -> None:
        folds, test = SplitAPI.walk_forward_folds(self._range_start_, self._range_stop_, self._training_, self._validation_, self._testing_, self._rolling_)
        seeds = [self._seed_] if self._seeds_ <= 1 else [(self._seed_ or 0) + offset for offset in range(self._seeds_)]
        self._log_.info(lambda: f"Learning Plan: Started · {len(seeds)} Seeds · {len(folds)} Folds · {self._episodes_} Episodes · Test {'Yes' if test else 'No'}")
        results = []
        best_metric = None
        best_directory = None
        try:
            if self._workers_ > 1 and len(seeds) > 1:
                self._log_.info(lambda: f"Parallel Learning: Started · {min(self._workers_, len(seeds))} Workers · {len(seeds)} Seeds")
                directories = {seed: self._weights_ / f"Seed {seed}" for seed in seeds}
                for directory in directories.values(): mkdir(directory)
                payloads = [self._payload_(seed, directories[seed], folds, test) for seed in seeds]
                with ProcessPoolExecutor(max_workers=min(self._workers_, len(seeds))) as pool:
                    results = list(pool.map(_learn_seed_, payloads))
                for result in results:
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
            if best_directory is not None and best_directory != self._weights_: self._promote_(best_directory)
            self._manifest_(results, best_metric)
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
    from Library.Logging import HandlerLoggingAPI, VerboseLevel
    HandlerLoggingAPI(Class="LearningAPI", Subclass="Worker").set_verbose_level(VerboseLevel.Warning)
    from Library.Database.Postgres.Postgres import PostgresAPI
    from Library.Parameter import Parameter
    from Library.Universe import ProviderAPI, SecurityAPI, TickerAPI, TimeframeAPI
    with PostgresAPI(database="Quant") as db:
        provider = ProviderAPI(UID=payload["provider"], db=db, autoload=True)
        ticker = TickerAPI(UID=payload["ticker"], db=db, autoload=True)
        timeframe = TimeframeAPI(UID=payload["timeframe"], db=db, autoload=True)
        security = SecurityAPI(Provider=provider, Ticker=ticker, db=db, autoload=True)
        learner = LearningAPI(strategy=payload["strategy"], security=security, timeframe=timeframe, parameters=Parameter(payload["parameters"], "."), start=payload["start"], stop=payload["stop"], account=payload["account"], spread=payload["spread"], commission=payload["commission"], swap=payload["swap"], reward=payload["reward"], episodes=payload["episodes"], epochs=payload["epochs"], train_frequency=payload["train_frequency"], gradient_steps=payload["gradient_steps"], training=payload["training"], validation=payload["validation"], testing=payload["testing"], rolling=payload["rolling"], fitness=payload["fitness"], patience=payload["patience"], seed=payload["seed"], seeds=1, workers=1, report=False, export=False)
        try:
            return learner._train_seed_(payload["seed"], Path(payload["weights"]), payload["folds"], payload["test"])
        finally:
            learner._restore_()

__all__ = ["LearningAPI"]