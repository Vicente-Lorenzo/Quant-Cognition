import pickle

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from Library.Database.Dataframe import pl
from Library.Model.Split import SplitAPI
from Library.Parameter import Parameter
from Library.Portfolio.Statistic import CALMARRATIO, NETRETURNANNPERC, NET_BUY_AGGREGATED, NET_SELL_AGGREGATED, NET_TOTAL_AGGREGATED, STATISTICS_METRICS_LABEL
from Library.Strategy.Model.Reward import RewardType
from Library.System.Learning import LearningAPI
from Library.System.System import SystemAPI
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

    def _export_weights_(self) -> None:
        self._exported_ = True

    def _promote_(self, source: Path) -> None:
        self._promoted_ = source

    def _pass_(self, start, stop, training, mirror=False):
        self._passes_ = getattr(self, "_passes_", [])
        self._passes_.append((start, stop, training, mirror))
        self._epochs_seen_ = self._strategy_.Epochs
        agent = self._strategy_.Agent if self._strategy_.Agent is not None else _FakeAgent_()
        self.strategy = SimpleNamespace(_agent_=agent, _observation_=SimpleNamespace(shape=lambda: 23), _sizing_mode_=SimpleNamespace(name="Percentage"), _sizing_min_=0.0, _sizing_max_=100.0, _entry_threshold_=(-0.4, 0.4), _exit_threshold_=(-0.1, 0.1))
        self.portfolio = SimpleNamespace(Equity=10000.0, InitialBalance=10000.0)
        return self._script_.pop(0) if self._script_ else 0.0

    def _trades_(self):
        script = getattr(self, "_trades_script_", None)
        return script.pop(0) if script else 1000000.0

    def _directions_(self):
        script = getattr(self, "_directions_script_", None)
        return script.pop(0) if script else (1000000.0, 1000000.0)

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

def test_export_copies_promoted_weights_without_seed_and_fold_dirs(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, seeds=1)
    harness._parameters_ = Parameter({}, tmp_path / "Learning.yml")
    mkdir(tmp_path / "DDPG")
    (tmp_path / "DDPG" / "actor").write_text("w")
    mkdir(tmp_path / "Seed 42")
    mkdir(tmp_path / "Fold 1")
    LearningAPI._export_weights_(harness)
    exports = list(tmp_path.glob("_FakeStrategy_ *"))
    assert len(exports) == 1
    assert (exports[0] / "DDPG" / "actor").read_text() == "w"
    assert not (exports[0] / "Seed 42").exists() and not (exports[0] / "Fold 1").exists()

def test_report_export_hook_is_not_shadowed():
    assert LearningAPI._export_ is SystemAPI._export_

def test_fold_archive_copies_model_weights(tmp_path):
    seed_dir = tmp_path / "Seed 42"
    mkdir(seed_dir / "DDPG")
    (seed_dir / "DDPG" / "actor").write_text("w")
    LearningAPI._archive_(seed_dir, 3)
    assert (seed_dir / "Fold 3" / "DDPG" / "actor").read_text() == "w"
    LearningAPI._archive_(seed_dir, 4)
    assert (seed_dir / "Fold 4" / "DDPG" / "actor").read_text() == "w"
    assert not (seed_dir / "Fold 4" / "Fold 3").exists()

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
    assert len(harness._passes_) == 4
    assert _FakeAgent_.saves == 2 and _FakeAgent_.loads == 0
    assert not hasattr(harness, "_promoted_")
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["FullRange"] is not None and "NetReturn" in manifest["FullRange"]

def test_validation_checkpoint_and_early_stop(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=5, training=0, validation=6, testing=0, patience=2)
    harness._script_ = [0.0, 0.01, 0.0, 0.05, 0.0, 0.03, 0.0, 0.02]
    harness.run()
    assert len(harness._passes_) == 9
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
    assert _FakeAgent_.instances == 3
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
    assert manifest["Fitness"] == CALMARRATIO and manifest["Best"] == 0.05 and len(manifest["Results"]) == 1
    assert manifest["SizingMin"] == 0.0 and manifest["SizingMax"] == 100.0
    assert manifest["NormalEntryThreshold"] == [-0.4, 0.4] and manifest["NormalExitThreshold"] == [-0.1, 0.1]

def test_scratch_builds_fresh_agent_per_fold(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, training=12, validation=6, testing=0, rolling=True, seeds=1)
    folds, _ = SplitAPI.walk_forward_folds(harness._range_start_, harness._range_stop_, 12, 6, 0, True)
    harness._script_ = [0.01, 0.02] * len(folds)
    harness.run()
    assert _FakeAgent_.instances == len(folds) + 1 and _FakeAgent_.loads == 0

def test_continuous_rolls_single_agent_across_folds(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, training=12, validation=6, testing=0, rolling=True, continuous=True, seeds=1)
    folds, _ = SplitAPI.walk_forward_folds(harness._range_start_, harness._range_stop_, 12, 6, 0, True)
    harness._script_ = [0.01, 0.02] * len(folds)
    harness.run()
    assert _FakeAgent_.instances == 2
    assert _FakeAgent_.loads == len(folds) - 1
    assert _FakeAgent_.saves == len(folds)

def test_continuous_recorded_in_manifest_and_payload(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, continuous=True, seeds=1)
    harness._script_ = [0.01]
    harness.run()
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Continuous"] is True
    payload = harness._payload_(42, tmp_path, [], None)
    assert payload["continuous"] is True
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, seeds=1)
    harness._script_ = [0.01]
    harness.run()
    assert read_json(tmp_path / "_FakeStrategy_ Manifest.json")["Continuous"] is False

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
    harness.statistics = pl.DataFrame({STATISTICS_METRICS_LABEL: [NETRETURNANNPERC], NET_TOTAL_AGGREGATED: [0.07]})
    assert abs(harness._fitness_() - 0.07) < 1e-9
    harness.statistics = None
    assert abs(harness._fitness_() - 0.05) < 1e-9

def test_activity_floor_prefers_active_checkpoints(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=3, training=0, validation=6, testing=0, activity=5)
    harness._script_ = [0.0, 0.05, 0.0, 0.01, 0.0, 0.09]
    harness._trades_script_ = [0.0, 10.0, 0.0]
    harness.run()
    assert _FakeAgent_.saves == 2
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Best"] == 0.01 and manifest["Activity"] == 5
    assert harness._payload_(42, tmp_path, [], None)["activity"] == 5

def _mirror_frame_():
    return pl.DataFrame({
        "OpenTick.Ask": [1.1002, 1.2002], "OpenTick.Bid": [1.1000, 1.2000], "OpenTick.Timestamp": [1, 5],
        "HighTick.Ask": [1.3002, 1.4002], "HighTick.Bid": [1.3000, 1.4000], "HighTick.Timestamp": [2, 6],
        "LowTick.Ask": [1.0002, 1.1002], "LowTick.Bid": [1.0000, 1.1000], "LowTick.Timestamp": [3, 7],
        "CloseTick.Ask": [1.2002, 1.3002], "CloseTick.Bid": [1.2000, 1.3000], "CloseTick.Timestamp": [4, 8],
        "CloseTick.AskBaseConversion": [1.0, 1.0]
    })

def test_mirror_frame_negates_returns_and_swaps_extremes():
    frame = _mirror_frame_()
    anchor = 1.2 * 1.2
    mirrored = LearningAPI._mirror_frame_(frame, anchor)
    assert abs(mirrored["CloseTick.Bid"][0] - anchor / 1.2002) < 1e-12
    assert abs(mirrored["CloseTick.Ask"][0] - anchor / 1.2000) < 1e-12
    assert (mirrored["CloseTick.Ask"] > mirrored["CloseTick.Bid"]).all()
    assert abs(mirrored["HighTick.Bid"][0] - anchor / 1.0002) < 1e-12
    assert mirrored["HighTick.Timestamp"][0] == 3 and mirrored["LowTick.Timestamp"][0] == 2
    assert (mirrored["HighTick.Bid"] > mirrored["LowTick.Bid"]).all()
    assert mirrored["CloseTick.AskBaseConversion"][0] is None
    import math
    original_return = math.log(1.3000 / 1.2000)
    mirrored_return = math.log(mirrored["CloseTick.Bid"][1] / mirrored["CloseTick.Bid"][0])
    assert abs(mirrored_return + math.log(1.3002 / 1.2002)) < 1e-9
    assert mirrored_return < 0.0 < original_return

def test_mirror_alternates_training_episodes_only(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=4, training=0, validation=6, testing=0, mirror=True)
    harness._script_ = [0.0] * 8
    harness.run()
    trains = [p for p in harness._passes_ if p[2] is True]
    validations = [p for p in harness._passes_ if p[2] is False]
    assert [p[3] for p in trains[:4]] == [False, True, False, True]
    assert all(p[3] is False for p in validations)
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Mirror"] is True

def test_balance_floor_requires_both_directions(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=3, training=0, validation=6, testing=0, balance=2)
    harness._script_ = [0.0, 0.09, 0.0, 0.01, 0.0, 0.07]
    harness._directions_script_ = [(9.0, 0.0), (3.0, 4.0), (0.0, 9.0)]
    harness.run()
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Best"] == 0.01 and manifest["Balance"] == 2
    assert harness._payload_(42, tmp_path, [], None)["balance"] == 2

def test_metric_reads_buy_and_sell_columns(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1)
    harness.portfolio = SimpleNamespace(Equity=10000.0, InitialBalance=10000.0)
    harness.statistics = pl.DataFrame({STATISTICS_METRICS_LABEL: ["Nr Total of Trades"], NET_BUY_AGGREGATED: [7.0], NET_SELL_AGGREGATED: [5.0], NET_TOTAL_AGGREGATED: [12.0]})
    assert harness._metric_("Nr Total of Trades", NET_BUY_AGGREGATED) == 7.0
    assert harness._metric_("Nr Total of Trades", NET_SELL_AGGREGATED) == 5.0
    assert harness._metric_("Nr Total of Trades") == 12.0

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