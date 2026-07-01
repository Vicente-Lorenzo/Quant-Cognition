import pickle

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from Library.Database.Dataframe import pl
from Library.Model.Split import SplitAPI
from Library.Parameter import Parameter
from Library.Portfolio.Statistic import NET_TOTAL_AGGREGATED, STATISTICS_METRICS_LABEL
from Library.Strategy.Model.Reward import RewardType
from Library.System.Learning import LearningAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Utility.IO import mkdir, read_json
from Library.Utility.Typing import MISSING

class _FakeAgent_:

    instances = 0
    saves = 0
    loads = 0

    def __init__(self):
        type(self).instances += 1

    def save(self):
        type(self).saves += 1

    def load(self):
        type(self).loads += 1

class _FakeStrategy_:

    Agent = None
    Training = False
    Epochs = 1
    Reward = RewardType.LogReturn
    RewardScale = 1.0
    Seed = None
    Weights = None
    _ACTION_SHAPE_ = 1

class _Harness_(LearningAPI):

    WEIGHTS = None

    def _weights_directory_(self) -> Path:
        mkdir(self.WEIGHTS)
        return self.WEIGHTS

    def _promote_(self, source: Path) -> None:
        self._promoted_ = source

    def _pass_(self, start, stop, training):
        self._passes_ = getattr(self, "_passes_", [])
        self._passes_.append((start, stop, training))
        self._epochs_seen_ = self._strategy_.Epochs
        agent = self._strategy_.Agent if self._strategy_.Agent is not None else _FakeAgent_()
        self.strategy = SimpleNamespace(_agent_=agent, _observation_=SimpleNamespace(shape=lambda: 23), _sizing_mode_=SimpleNamespace(name="Percentage"), _sizing_max_=100.0, _sizing_deadzone_=0.1)
        self.portfolio = SimpleNamespace(Equity=10000.0, InitialBalance=10000.0)
        return self._script_.pop(0) if self._script_ else 0.0

def _reset_(weights: Path) -> None:
    _FakeAgent_.instances = 0
    _FakeAgent_.saves = 0
    _FakeAgent_.loads = 0
    _FakeStrategy_.Agent = None
    _FakeStrategy_.Training = False
    _FakeStrategy_.Epochs = 1
    _FakeStrategy_.Seed = None
    _FakeStrategy_.Weights = None
    _Harness_.WEIGHTS = weights

def _make_(**kwargs) -> _Harness_:
    defaults = dict(reward="LogReturn", episodes=3, seed=42)
    defaults.update(kwargs)
    return _Harness_(
        strategy=_FakeStrategy_,
        security=SimpleNamespace(UID="EURUSD", _provider_=SimpleNamespace(UID="Spotware(cTrader)"), _ticker_=SimpleNamespace(UID="EURUSD")),
        timeframe=SimpleNamespace(UID="D1"),
        parameters=Parameter({}, "."),
        start="2020-01-01",
        stop="2024-01-01",
        account=("EUR", 10000.0, 100.0),
        spread=(SpreadType.Auto, MISSING),
        commission=(CommissionType.Auto, MISSING),
        swap=(SwapType.Auto, MISSING, MISSING),
        report=False,
        export=False,
        **defaults
    )

def test_walk_forward_single_window():
    folds, test = SplitAPI.walk_forward_folds(datetime(2020, 1, 1), datetime(2024, 1, 1), 0, 0, 0, False)
    assert len(folds) == 1 and folds[0][1] is None and test is None

def test_walk_forward_train_test_only():
    folds, test = SplitAPI.walk_forward_folds(datetime(2020, 1, 1), datetime(2024, 1, 1), 0, 0, 12, False)
    assert len(folds) == 1 and folds[0][1] is None
    assert test is not None and test[1] == datetime(2024, 1, 1) and folds[0][0][1] == test[0]

def test_walk_forward_single_train_validation():
    folds, test = SplitAPI.walk_forward_folds(datetime(2020, 1, 1), datetime(2024, 1, 1), 0, 6, 0, False)
    assert len(folds) == 1 and folds[0][1] is not None and test is None
    assert folds[0][1][1] == datetime(2024, 1, 1)

def test_walk_forward_rolling_folds():
    folds, _ = SplitAPI.walk_forward_folds(datetime(2020, 1, 1), datetime(2024, 1, 1), 12, 6, 0, True)
    assert len(folds) > 1
    assert folds[0][0] == (datetime(2020, 1, 1), datetime(2021, 1, 1))
    assert folds[0][1] == (datetime(2021, 1, 1), datetime(2021, 7, 1))
    assert folds[1][0][0] == datetime(2020, 7, 1)

def test_walk_forward_anchored_fixes_train_start():
    folds, _ = SplitAPI.walk_forward_folds(datetime(2020, 1, 1), datetime(2024, 1, 1), 12, 6, 0, False)
    assert len(folds) > 1 and all(train[0] == datetime(2020, 1, 1) for train, _ in folds)

def test_walk_forward_short_range_falls_back():
    folds, _ = SplitAPI.walk_forward_folds(datetime(2020, 1, 1), datetime(2020, 3, 1), 12, 6, 0, False)
    assert len(folds) == 1 and folds[0][1] is None

def test_single_window_checkpoints_on_train(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=3, validation=0, testing=0, seeds=1)
    harness._script_ = [0.01, 0.05, 0.02]
    harness.run()
    assert len(harness._passes_) == 3
    assert _FakeAgent_.saves == 2 and _FakeAgent_.loads == 0
    assert not hasattr(harness, "_promoted_")

def test_validation_checkpoint_and_early_stop(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=5, training=0, validation=6, testing=0, patience=2)
    harness._script_ = [0.0, 0.01, 0.0, 0.05, 0.0, 0.03, 0.0, 0.02]
    harness.run()
    assert len(harness._passes_) == 8
    assert _FakeAgent_.saves == 2

def test_test_pass_loads_best_then_evaluates(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=2, validation=0, testing=12, seeds=1)
    harness._script_ = [0.03, 0.06, 0.10]
    harness.run()
    assert _FakeAgent_.loads == 1
    assert harness._passes_[-1][2] is False
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Results"][0]["Test"] == 0.10 and manifest["Best"] == 0.10

def test_multi_seed_promotes_best(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, seed=42, seeds=2)
    harness._script_ = [0.02, 0.08]
    harness.run()
    assert _FakeAgent_.instances == 2
    assert harness._promoted_ == tmp_path / "Seed 43"

def test_epochs_plumbed_as_noop(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=2, epochs=5, validation=0, testing=0)
    harness._script_ = [0.01, 0.02]
    harness.run()
    assert _FakeStrategy_.Epochs == 5 and harness._epochs_seen_ == 5

def test_manifest_records_configuration(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=2, epochs=3, train_frequency=2, gradient_steps=3, training=24, validation=0, testing=0, seeds=1, fitness="Calmar Ratio")
    harness._script_ = [0.01, 0.05]
    harness.run()
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Episodes"] == 2 and manifest["Epochs"] == 3 and manifest["Training"] == 24
    assert manifest["TrainFrequency"] == 2 and manifest["GradientSteps"] == 3
    assert manifest["Validation"] == 0 and manifest["Testing"] == 0 and manifest["Seeds"] == 1
    assert manifest["Fitness"] == "Calmar Ratio" and manifest["Best"] == 0.05 and len(manifest["Results"]) == 1

def test_restores_training_flag(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0)
    harness._script_ = [0.01]
    harness.run()
    assert _FakeStrategy_.Training is False and _FakeStrategy_.Agent is None

def test_fitness_reads_metric_then_falls_back(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1)
    harness.portfolio = SimpleNamespace(Equity=10500.0, InitialBalance=10000.0)
    harness.statistics = pl.DataFrame({STATISTICS_METRICS_LABEL: ["Net Return (%)"], NET_TOTAL_AGGREGATED: [0.07]})
    assert abs(harness._fitness_() - 0.07) < 1e-9
    harness.statistics = None
    assert abs(harness._fitness_() - 0.05) < 1e-9

def test_parallel_payload_is_picklable(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=2, training=12, validation=6, testing=12, seeds=4, workers=4, rolling=True)
    folds, test = SplitAPI.walk_forward_folds(harness._range_start_, harness._range_stop_, 12, 6, 12, True)
    payload = harness._payload_(43, tmp_path / "Seed 43", folds, test)
    restored = pickle.loads(pickle.dumps(payload))
    assert restored["strategy"] is _FakeStrategy_ and restored["reward"] is RewardType.LogReturn
    assert restored["provider"] == "Spotware(cTrader)" and restored["ticker"] == "EURUSD"
    assert restored["seed"] == 43 and restored["weights"].endswith("Seed 43")
    assert restored["rolling"] is True and restored["folds"] == folds and restored["test"] == test
    assert restored["spread"][1] is None and restored["account"] == ("EUR", 10000.0, 100.0)