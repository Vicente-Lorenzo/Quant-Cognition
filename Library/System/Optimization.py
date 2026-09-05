from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Union

from Library.Model.Split import SplitAPI
from Library.Strategy.Strategy import StrategyAPI
from Library.System.Backtesting import BacktestingAPI
from Library.System.Learning import FitnessType
from Library.System.Selection import ElectionMode, SelectionMode, elect, select
from Library.System.Space import CandidateAPI, apply_candidate, build_grid, measure_plan, neighborhoods, resolve_inheritance, rounds_space, unpack_plan, unpack_section
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Parameter import Parameter
from Library.Utility.Progress import ProgressAPI
from Library.Utility.Profiler import timer
from Library.Utility.Typing import MISSING, Missing

class OptimizationAPI(BacktestingAPI):

    _CHUNK_: int = 8

    def __init__(self,
                 strategy: type[StrategyAPI],
                 security: SecurityAPI,
                 timeframe: TimeframeAPI,
                 resolution: Union[str, TimeframeAPI, Missing, None],
                 parameters: Parameter,
                 space: Parameter,
                 start: Union[str, date, datetime],
                 stop: Union[str, date, datetime],
                 account: tuple[str, float, float],
                 spread: tuple[SpreadType, Union[float, Missing, None]],
                 commission: tuple[CommissionType, Union[float, Missing, None]],
                 swap: tuple[SwapType, Union[float, Missing, None], Union[float, Missing, None]],
                 fitness: Union[str, FitnessType] = FitnessType.AnnualizedReturn,
                 selection: Union[str, SelectionMode] = SelectionMode.Best,
                 election: Union[str, ElectionMode] = ElectionMode.Frequency,
                 purge: Union[int, None] = None,
                 embargo: Union[int, None] = None,
                 training: int = 0,
                 validation: int = 0,
                 testing: int = 0,
                 rolling: bool = False,
                 continuous: bool = False,
                 workers: int = 1,
                 risk_free: float = 0.0,
                 report: bool = False,
                 export: bool = False,
                 plot: bool = False,
                 run: Union[str, Path, None] = None,
                 description: Union[str, None] = None) -> None:
        super().__init__(
            strategy=strategy,
            security=security,
            timeframe=timeframe,
            resolution=resolution,
            parameters=parameters,
            start=start,
            stop=stop,
            account=account,
            spread=spread,
            commission=commission,
            swap=swap,
            risk_free=risk_free,
            report=False,
            export=False,
            plot=False,
            run=run,
            description=description
        )
        self._deliverables_: tuple[bool, bool, bool] = (report, export, plot)
        self._space_ = space
        self._fitness_label_ = fitness.value if isinstance(fitness, FitnessType) else FitnessType.parse(fitness).value
        self._selection_ = selection if isinstance(selection, SelectionMode) else SelectionMode.parse(selection)
        self._election_ = election if isinstance(election, ElectionMode) else ElectionMode.parse(election)
        self._training_, self._validation_, self._testing_ = training, validation, testing
        self._rolling_, self._continuous_ = rolling, continuous
        self._purge_, self._embargo_ = purge, embargo
        self._workers_ = max(1, int(workers or 1))
        self._baseline_ = self._parameters_
        self._range_start_, self._range_stop_ = self._start_, self._stop_
        self._stages_: list = []
        self._ledger_: dict = {}
        self._trials_: int = 0
        self._carried_: dict = {}
        self._winner_: Union[CandidateAPI, None] = None
        self._verdict_: Union[float, None] = None
        self._outcome_: Union[float, None] = None

    def _fitness_(self) -> float:
        if self._fitness_label_ == FitnessType.AccountReturn.value: return self._account_return_()
        return self._metric_(self._fitness_label_)

    def _evaluate_(self, candidate: CandidateAPI, start, stop) -> Union[float, None]:
        try:
            self._disconnect_()
            self._parameters_ = apply_candidate(self._baseline_, candidate)
            self._start_, self._stop_ = start, stop
            with self.quieted():
                self._connect_()
                self.deploy()
            return self._fitness_()
        except Exception as error:
            self._log_.warning(lambda error=error, candidate=candidate: f"Candidate Optimization: Skipped ({candidate.index}) · {error}")
            return None

    def _payload_(self, start, stop) -> dict:
        return {
            **self._dispatch_(self._baseline_, start, stop),
            "resolution": self._resolution_arg_.UID if isinstance(self._resolution_arg_, TimeframeAPI) else (self._resolution_arg_ if isinstance(self._resolution_arg_, str) else None),
            "fitness": self._fitness_label_,
            "risk_free": self._risk_free_,
        }

    def _sweep_(self, grid: list, start, stop, tracker) -> list:
        ordered = self._ordered_(grid)
        if self._workers_ <= 1 or len(ordered) < 2: return self._serial_(ordered, start, stop, tracker)
        return self._parallel_(ordered, start, stop, tracker)

    @staticmethod
    def _ordered_(grid: list) -> list:
        return sorted(grid, key=lambda candidate: repr(sorted(candidate.overrides.get("TechnicalManagement", {}).items())))

    def _serial_(self, grid: list, start, stop, tracker) -> list:
        scored = []
        for candidate in grid:
            scored.append((candidate, self._evaluate_(candidate, start, stop)))
            if tracker is not None: tracker.advance()
        return scored

    def _warm_(self, start, stop) -> None:
        try:
            self._disconnect_()
            self._start_, self._stop_ = start, stop
            self._connect_()
        except Exception as error:
            self._log_.warning(lambda error=error: f"Warmup Optimization: Failed · {error}")

    def _parallel_(self, grid: list, start, stop, tracker) -> list:
        workers = min(self._workers_, len(grid))
        payload = self._payload_(start, stop)
        ledger = {candidate.index: candidate for candidate in grid}
        scores = {}
        self._warm_(start, stop)
        self._disconnect_()
        with ProcessPoolExecutor(max_workers=workers, initializer=_prepare_, initargs=(payload,)) as pool:
            for index, score in pool.map(_score_, [(c.index, c.overrides) for c in grid], chunksize=self._CHUNK_):
                scores[index] = score
                if tracker is not None: tracker.advance()
        return [(ledger[index], scores.get(index)) for index in sorted(scores)]

    def _stage_(self, fold: int, order: int, stage: dict, winners: list, span: tuple, tracker,
                seeded: Union[dict, None] = None) -> Union[tuple, None]:
        space = unpack_section(resolve_inheritance(stage, winners, order - 1))
        depth = rounds_space(space)
        chosen, outcome, width = seeded, None, 0
        for position in range(1 if seeded is not None and depth > 1 else 0, depth):
            grid = build_grid(space, chosen, position)
            if not grid: break
            scored = self._sweep_(grid, span[0], span[1], tracker)
            self._trials_ += sum(1 for _, score in scored if score is not None)
            for candidate, score in scored:
                self._record_(Fold=fold, Stage=order, Round=position + 1, Candidate=candidate.index, Fitness=score, **candidate.settings())
            picked = select(scored, self._selection_, adjacency=neighborhoods)
            if picked is None: break
            candidate, score = picked
            chosen = candidate.pinned()
            outcome, width = (candidate, score), width + len(grid)
            if depth > 1:
                self._log_.debug(lambda fold=fold, order=order, round=position + 1, candidate=candidate, score=score, size=len(grid):
                                 f"Round Optimization: Refined ({fold}.{order}.{round}) · {candidate.label()} · {size} Candidates · Train {score:+.4f}")
        if outcome is None:
            self._log_.warning(lambda fold=fold, order=order: f"Stage Optimization: Barren ({fold}.{order}) · No candidate produced a fitness")
            return None
        return outcome[0], outcome[1], width, chosen

    def _fold_(self, fold: int, plan: list, span: tuple, tracker) -> Union[tuple, None]:
        winners, accumulated, trail, score = [], {}, [], None
        for order, stage in enumerate(plan, start=1):
            seeded = self._carried_.get(order) if self._continuous_ else None
            outcome = self._stage_(fold, order, stage, winners, span, tracker, seeded)
            if outcome is None:
                winners.append({})
                continue
            candidate, score, width, chosen = outcome
            self._carried_[order] = chosen
            winners.append(deepcopy(candidate.overrides))
            for section, block in candidate.overrides.items(): accumulated.setdefault(section, {}).update(deepcopy(block))
            trail.append({"Stage": order, "Parameters": candidate.label(), "Training": score, "Candidates": width})
            if len(plan) > 1:
                self._log_.info(lambda fold=fold, order=order, candidate=candidate, score=score, width=width:
                                f"Stage Optimization: Selected ({fold}.{order}) · {candidate.label()} · {width} Candidates · Train {score:+.4f}")
        if not accumulated: return None
        return CandidateAPI(index=fold, overrides=accumulated), score, trail

    @timer
    def run(self) -> None:
        folds, test = SplitAPI.walk_forward_folds(self._range_start_, self._range_stop_, self._training_, self._validation_, self._testing_, self._rolling_, self._purge_, self._embargo_)
        plan = unpack_plan(self._space_)
        budget = measure_plan(plan)
        if not budget:
            self._log_.warning(lambda: "Plan Optimization: Empty · No searchable parameters declared")
            return
        self._log_.info(lambda: f"Plan Optimization: Started · {budget} Candidates · {len(plan)} Stages · {len(folds)} Folds · {self._selection_.name}/{self._election_.name}{' · Continuous' if self._continuous_ else ''} · Test {'Yes' if test else 'No'}")
        tracker = ProgressAPI(len(folds) * budget, label=self._identity_(), unit="candidates")
        ProgressAPI.mute()
        try:
            for index, (train, validation) in enumerate(folds, start=1):
                outcome = self._fold_(index, plan, train, tracker)
                if outcome is None:
                    self._log_.warning(lambda index=index: f"Fold Optimization: Barren ({index}) · No candidate produced a fitness")
                    continue
                candidate, score, trail = outcome
                self._ledger_[candidate.label()] = candidate
                verified = self._evaluate_(candidate, validation[0], validation[1]) if validation is not None else None
                if validation is not None:
                    self._stitch_(index, candidate.label(), validation, verified, training=score, settings=candidate.settings())
                self._stages_.append({"Fold": index, "Parameters": candidate.label(), "Training": score,
                                      "Validation": verified, "Trail": trail})
                self._log_.info(lambda index=index, candidate=candidate, score=score, verified=verified:
                                f"Fold Optimization: Selected ({index}) · {candidate.label()} · Train {score:+.4f}"
                                + (f" · Validation {verified:+.4f}" if verified is not None else ""))
        finally:
            ProgressAPI.mute(False)
            tracker.close()
        self._summarize_(test)

    def _elect_(self) -> Union[tuple, None]:
        records = [{"Key": stage["Parameters"], "Score": stage["Validation"] if stage["Validation"] is not None else stage["Training"]}
                   for stage in self._stages_]
        chosen = elect(records, self._election_)
        if chosen is None: return None
        key, evidence = chosen
        candidate = self._ledger_.get(key)
        return (candidate, evidence) if candidate is not None else None

    def _summarize_(self, test) -> None:
        elected = self._elect_()
        if elected is None:
            self._log_.warning(lambda: "Summary Optimization: Empty · No fold produced a selection")
            return
        candidate, evidence = elected
        self._winner_ = candidate
        detail = " · ".join(f"{key} {value}" for key, value in evidence.items())
        self._log_.info(lambda: f"Summary Optimization: Completed · {len(self._stages_)} Folds · {self._trials_} Trials · {detail} · {candidate.label()}")
        self._deliver_(candidate, test)

    def _deliver_(self, candidate: CandidateAPI, test) -> None:
        if test is None and not any(self._deliverables_): return
        if test is not None:
            self._log_.info(lambda: f"Held Out Optimization: Started · {candidate.label()} · {test[0]:%Y-%m-%d} · {test[1]:%Y-%m-%d}")
            with self.quieted():
                self._verdict_ = self._evaluate_(candidate, test[0], test[1])
            if self._verdict_ is None: self._log_.warning(lambda: "Held Out Optimization: Failed · The elected candidate produced no fitness")
            else: self._log_.info(lambda: f"Held Out Optimization: Completed · {self._fitness_label_} {self._verdict_:+.4f}")
        start, stop = self._range_start_, self._range_stop_
        self._log_.info(lambda: f"Final Optimization: Started · {candidate.label()} · {start:%Y-%m-%d} · {stop:%Y-%m-%d}")
        with self.deliverables(*self._deliverables_):
            self._outcome_ = self._evaluate_(candidate, start, stop)
        if self._outcome_ is None:
            self._log_.warning(lambda: "Final Optimization: Failed · The elected candidate produced no fitness")
            return
        if self._verdict_ is None: self._verdict_ = self._outcome_
        if any(self._deliverables_): self._publish_("Parameters.yml", getattr(self._parameters_, "data", None))
        self._log_.info(lambda: f"Final Optimization: Completed · Full Range · {self._fitness_label_} {self._outcome_:+.4f}")

    @property
    def stages(self) -> list:
        return list(self._stages_)

    @property
    def trials(self) -> int:
        return self._trials_

    @property
    def winner(self) -> Union[CandidateAPI, None]:
        return self._winner_

    @property
    def verdict(self) -> Union[float, None]:
        return self._verdict_

    @property
    def outcome(self) -> Union[float, None]:
        return self._outcome_

_WORKER_: Union[OptimizationAPI, None] = None

def _prepare_(payload: dict) -> None:
    global _WORKER_
    from Library.Logging import LoggingAPI, VerboseLevel
    log = LoggingAPI("Worker")
    log.console.set_level(VerboseLevel.Warning)
    ProgressAPI.mute()
    security, timeframe = OptimizationAPI._resolve_(payload)
    _WORKER_ = OptimizationAPI(
        strategy=payload["strategy"],
        security=security,
        timeframe=timeframe,
        resolution=payload["resolution"] if payload["resolution"] else MISSING,
        parameters=Parameter(payload["parameters"], "."),
        space=Parameter({}, "."),
        start=payload["start"],
        stop=payload["stop"],
        account=payload["account"],
        spread=payload["spread"],
        commission=payload["commission"],
        swap=payload["swap"],
        fitness=FitnessType.AnnualizedReturn,
        risk_free=payload["risk_free"],
        report=False
    )
    _WORKER_._fitness_label_ = payload["fitness"]

def _score_(work: tuple) -> tuple:
    index, overrides = work
    if _WORKER_ is None: return index, None
    candidate = CandidateAPI(index=index, overrides=overrides)
    return index, _WORKER_._evaluate_(candidate, _WORKER_._range_start_, _WORKER_._range_stop_)

__all__ = ["OptimizationAPI"]