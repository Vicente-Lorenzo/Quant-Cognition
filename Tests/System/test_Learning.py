import pickle
import pytest
import torch

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from Library.Database.Dataframe import pl
from Library.Model.Split import SplitAPI
from Library.Statistic.Curve import CurveAPI
from Library.Strategy.Hybrid.DDPG import DDPGStrategyAPI
from Library.Utility.Parameter import Parameter
from Library.Statistic.Label import (
    CALMARRATIOANN,
    NETRETURNANNPERC,
    NET_BUY_AGGREGATED,
    NET_SELL_AGGREGATED,
    NET_TOTAL_AGGREGATED,
    STATISTICS_METRICS_LABEL,
    TOTALTRADESVALUE
)
from Library.Strategy.Model.Reward import RewardType
from Library.Strategy.Strategy import Threshold
from Library.System.Learning import LearningAPI
from Library.System.System import SystemAPI
from Library.Universe.Contract import CommissionType, SpreadType, SwapType
from Library.Utility.IO import mkdir, read_json, read_yaml, write_json
from Library.Utility.Path import traceback_root
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

_LAYOUT_ = {"Account": False, "Momentum": ["MOMFast"], "Overlap": ["MAFast"], "Shape": 22, "Window": 1}

class _FakeStrategy_:

    Agent = None
    Training = False
    Epochs = 1
    Reward = RewardType.LogReturn
    RewardScale = 1.0
    Seed = None
    Weights = None
    _ACTION_SHAPE_ = 1

    @classmethod
    def key(cls) -> str:
        return cls.__name__

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
        exposure = getattr(self, "_exposure_script_", None)
        longs, shorts = exposure.pop(0) if exposure and not training else (1000000.0, 1000000.0)
        self.strategy = SimpleNamespace(_agent_=agent, save=lambda: _persist_(agent), load=agent.load, _observation_=SimpleNamespace(shape=lambda: 23), _sizing_mode_=SimpleNamespace(name="Percentage"), _risk_percentage_=1.0, _atr_scale_=1.5, _reward_=SimpleNamespace(_scale_=1000.0), DirectionalEntryThreshold=Threshold(-0.4, 0.4), DirectionalExitThreshold=Threshold(-0.1, 0.1), _long_bars_=longs, _short_bars_=shorts)
        self.portfolio = SimpleNamespace(Equity=10000.0, InitialBalance=10000.0, EquityCurve=CurveAPI())
        return self._script_.pop(0) if self._script_ else 0.0

    def _trades_(self):
        script = getattr(self, "_trades_script_", None)
        return script.pop(0) if script else 1000000.0

def _persist_(agent: _FakeAgent_) -> None:
    agent.save()
    write_json(Path(_FakeStrategy_.Weights) / DDPGStrategyAPI.LAYOUT, _LAYOUT_, safe=False)

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
        security=SimpleNamespace(UID="EURUSD", _provider_=SimpleNamespace(UID="Spotware(cTrader)"), _ticker_=SimpleNamespace(UID="EURUSD"), Contract=None),
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
    write_json(tmp_path / DDPGStrategyAPI.LAYOUT, _LAYOUT_, safe=False)
    mkdir(tmp_path / "Seed 42")
    mkdir(tmp_path / "Fold 1")
    LearningAPI._export_weights_(harness)
    exports = list(tmp_path.glob("_FakeStrategy_ *"))
    assert len(exports) == 1
    assert (exports[0] / "DDPG" / "actor").read_text() == "w"
    assert read_json(exports[0] / DDPGStrategyAPI.LAYOUT) == _LAYOUT_
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

def test_fold_archive_and_revival_carry_the_observation_layout(tmp_path):
    mkdir(tmp_path / "DDPG")
    (tmp_path / "DDPG" / "actor").write_text("w")
    write_json(tmp_path / DDPGStrategyAPI.LAYOUT, _LAYOUT_, safe=False)
    LearningAPI._archive_(tmp_path, 2)
    assert read_json(tmp_path / "Fold 2" / DDPGStrategyAPI.LAYOUT) == _LAYOUT_
    (tmp_path / "DDPG" / "actor").write_text("x")
    write_json(tmp_path / DDPGStrategyAPI.LAYOUT, {"Momentum": []}, safe=False)
    assert LearningAPI._revive_(tmp_path, "Fold 2")
    assert (tmp_path / "DDPG" / "actor").read_text() == "w" and read_json(tmp_path / DDPGStrategyAPI.LAYOUT) == _LAYOUT_

def test_learning_saves_the_layout_beside_every_seed_and_fold(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, training=12, validation=6, testing=0, rolling=True, seed=42, seeds=2)
    folds, _ = SplitAPI.walk_forward_folds(harness._range_start_, harness._range_stop_, 12, 6, 0, True)
    harness._script_ = [0.01, 0.02] * len(folds) * 2
    harness.run()
    for seed in (42, 43):
        assert read_json(tmp_path / f"Seed {seed}" / DDPGStrategyAPI.LAYOUT) == _LAYOUT_
        assert all(read_json(tmp_path / f"Seed {seed}" / f"Fold {index}" / DDPGStrategyAPI.LAYOUT) == _LAYOUT_ for index in range(1, len(folds) + 1))

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
    assert manifest["Results"][0]["Test"] == 0.10 and manifest["Best"] == 0.06 and manifest["Elected"] == 42

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
    assert manifest["Fitness"] == CALMARRATIOANN and manifest["Best"] == 0.05 and len(manifest["Results"]) == 1
    assert manifest["RiskPercentage"] == 1.0 and manifest["ATRScale"] == 1.5 and manifest["RewardScale"] == 1000.0
    assert manifest["DirectionalEntryThreshold"] == [-0.4, 0.4] and manifest["DirectionalExitThreshold"] == [-0.1, 0.1]

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
    payload = harness._payload_(42, tmp_path, [], None, [], {})
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
    harness.portfolio = SimpleNamespace(Equity=10500.0, InitialBalance=10000.0, EquityCurve=CurveAPI())
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
    assert harness._payload_(42, tmp_path, [], None, [], {})["activity"] == 5

def _mirror_frame_():
    ticks = {
        "OpenPoint.AskTick": ([1.1002, 1.2002], [1.1000, 1.2000], [1, 7]), "OpenPoint.BidTick": ([1.1002, 1.2002], [1.1000, 1.2000], [1, 7]),
        "HighPoint.AskTick": ([1.3004, 1.4004], [1.2998, 1.3998], [2, 8]), "HighPoint.BidTick": ([1.3002, 1.4002], [1.3000, 1.4000], [3, 9]),
        "LowPoint.AskTick": ([1.0001, 1.1001], [0.9999, 1.0999], [4, 10]), "LowPoint.BidTick": ([1.0003, 1.1003], [0.9998, 1.0998], [5, 11]),
        "ClosePoint.AskTick": ([1.2002, 1.3002], [1.2000, 1.3000], [6, 12]), "ClosePoint.BidTick": ([1.2002, 1.3002], [1.2000, 1.3000], [6, 12]),
    }
    columns = {f"{prefix}.{name}": values for prefix, (asks, bids, stamps) in ticks.items() for name, values in (("Ask", asks), ("Bid", bids), ("Timestamp", stamps))}
    conversions = {f"{prefix}.{side}{kind}Conversion": [0.9, 0.8] for prefix in ticks for side in ("Ask", "Bid") for kind in ("Base", "Quote")}
    return pl.DataFrame({**columns, **conversions})

def test_mirror_frame_negates_returns_and_swaps_extremes():
    frame = _mirror_frame_()
    anchor = 1.2 * 1.2
    mirrored = LearningAPI._mirror_frame_(frame, anchor)
    assert abs(mirrored["ClosePoint.BidTick.Bid"][0] - anchor / 1.2002) < 1e-12
    assert abs(mirrored["ClosePoint.AskTick.Ask"][0] - anchor / 1.2000) < 1e-12
    assert (mirrored["ClosePoint.AskTick.Ask"] > mirrored["ClosePoint.BidTick.Bid"]).all()
    assert abs(mirrored["HighPoint.AskTick.Ask"][0] - anchor / 0.9998) < 1e-12 and mirrored["HighPoint.AskTick.Timestamp"][0] == 5
    assert abs(mirrored["HighPoint.BidTick.Bid"][0] - anchor / 1.0001) < 1e-12 and mirrored["HighPoint.BidTick.Timestamp"][0] == 4
    assert abs(mirrored["LowPoint.AskTick.Ask"][0] - anchor / 1.3000) < 1e-12 and mirrored["LowPoint.AskTick.Timestamp"][0] == 3
    assert abs(mirrored["LowPoint.BidTick.Bid"][0] - anchor / 1.3004) < 1e-12 and mirrored["LowPoint.BidTick.Timestamp"][0] == 2
    assert (mirrored["HighPoint.BidTick.Bid"] > mirrored["LowPoint.BidTick.Bid"]).all()
    assert mirrored["ClosePoint.BidTick.AskBaseConversion"][0] == 0.9 and mirrored["ClosePoint.BidTick.BidQuoteConversion"][1] == 0.8
    import math
    original_return = math.log(1.3000 / 1.2000)
    mirrored_return = math.log(mirrored["ClosePoint.BidTick.Bid"][1] / mirrored["ClosePoint.BidTick.Bid"][0])
    assert abs(mirrored_return + math.log(1.3002 / 1.2002)) < 1e-9
    assert mirrored_return < 0.0 < original_return

def test_a_mirrored_tape_converts_through_its_own_mirrored_prices():
    frame, anchor = _mirror_frame_(), 1.2 * 1.2
    owned = LearningAPI._mirror_frame_(frame, anchor, quote=True)
    assert owned["ClosePoint.BidTick.AskQuoteConversion"][0] == pytest.approx(1.0 / owned["ClosePoint.BidTick.Bid"][0], rel=1e-12)
    assert owned["ClosePoint.BidTick.BidQuoteConversion"][0] == pytest.approx(1.0 / owned["ClosePoint.BidTick.Ask"][0], rel=1e-12)
    assert owned["ClosePoint.BidTick.AskBaseConversion"][0] == 0.9
    owned = LearningAPI._mirror_frame_(frame, anchor, base=True)
    assert owned["HighPoint.BidTick.AskBaseConversion"][0] == owned["HighPoint.BidTick.Ask"][0] and owned["HighPoint.BidTick.BidBaseConversion"][0] == owned["HighPoint.BidTick.Bid"][0]
    assert owned["HighPoint.BidTick.AskQuoteConversion"][0] == 0.9

def test_mirror_frame_mirrors_each_mid_tick_with_its_point():
    frame = _mirror_frame_()
    mids = {"HighPoint.MidTick": (1.3003, 1.2999, 13), "LowPoint.MidTick": (1.0002, 0.9999, 14), "ClosePoint.MidTick": (1.2002, 1.2000, 6)}
    frame = frame.with_columns([pl.lit(value).alias(f"{prefix}.{name}") for prefix, values in mids.items() for name, value in zip(("Ask", "Bid", "Timestamp"), values)])
    anchor = 1.2 * 1.2
    mirrored = LearningAPI._mirror_frame_(frame, anchor)
    assert (mirrored["HighPoint.MidTick.Ask"][0], mirrored["HighPoint.MidTick.Bid"][0], mirrored["HighPoint.MidTick.Timestamp"][0]) == (anchor / 0.9999, anchor / 1.0002, 14)
    assert (mirrored["LowPoint.MidTick.Ask"][0], mirrored["LowPoint.MidTick.Bid"][0], mirrored["LowPoint.MidTick.Timestamp"][0]) == (anchor / 1.2999, anchor / 1.3003, 13)
    assert mirrored["ClosePoint.MidTick.Timestamp"][0] == mirrored["ClosePoint.BidTick.Timestamp"][0] and mirrored["ClosePoint.MidTick.Bid"][0] == mirrored["ClosePoint.BidTick.Bid"][0]

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
    harness._exposure_script_ = [(9.0, 0.0), (3.0, 4.0), (0.0, 9.0)]
    harness.run()
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Best"] == 0.01 and manifest["Balance"] == 2
    assert harness._payload_(42, tmp_path, [], None, [], {})["balance"] == 2

def test_metric_reads_buy_and_sell_columns(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1)
    harness.portfolio = SimpleNamespace(Equity=10000.0, InitialBalance=10000.0, EquityCurve=CurveAPI())
    harness.statistics = pl.DataFrame({STATISTICS_METRICS_LABEL: [TOTALTRADESVALUE], NET_BUY_AGGREGATED: [7.0], NET_SELL_AGGREGATED: [5.0], NET_TOTAL_AGGREGATED: [12.0]})
    assert harness._metric_(TOTALTRADESVALUE, NET_BUY_AGGREGATED) == 7.0
    assert harness._metric_(TOTALTRADESVALUE, NET_SELL_AGGREGATED) == 5.0
    assert harness._metric_(TOTALTRADESVALUE) == 12.0

def test_parallel_payload_is_picklable(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=2, training=12, validation=6, testing=12, seeds=4, workers=4, rolling=True)
    folds, test = SplitAPI.walk_forward_folds(harness._range_start_, harness._range_stop_, 12, 6, 12, True)
    payload = harness._payload_(43, tmp_path / "Seed 43", folds, test, [(7, "Tape", 3, (0, 1))], {folds[0][0][0]: (pl.DataFrame({"Close": [1.1, 1.2]}), 2)})
    restored = pickle.loads(pickle.dumps(payload))
    assert restored["strategy"] is _FakeStrategy_ and restored["reward"] is RewardType.LogReturn
    assert restored["provider"] == "Spotware(cTrader)" and restored["ticker"] == "EURUSD"
    assert restored["seed"] == 43 and restored["weights"].endswith("Seed 43")
    assert restored["rolling"] is True and restored["folds"] == folds and restored["test"] == test
    assert restored["spread"][1] is None and restored["account"] == ("EUR", 10000.0, 100.0, None)
    assert restored["shelf"] == [(7, "Tape", 3, (0, 1))]
    assert restored["history"][folds[0][0][0]][0]["Close"].to_list() == [1.1, 1.2] and restored["history"][folds[0][0][0]][1] == 2

def test_a_worker_seed_selects_and_elects_as_the_run_asked(tmp_path, monkeypatch):
    _reset_(tmp_path)
    harness = _make_(episodes=1, training=12, validation=6, testing=0, seeds=2, workers=2, selection="Median", election="Mean")
    payload = harness._payload_(43, tmp_path / "Seed 43", [], None, [], {})
    assert payload["selection"] == "Median" and payload["election"] == "Mean"
    captured = {}
    def _capture_(self, **kwargs):
        captured.update(kwargs)
        raise RuntimeError("Captured")
    monkeypatch.setattr(torch, "set_num_threads", lambda threads: None)
    monkeypatch.setattr("Library.Logging.LoggingAPI", lambda *tags: SimpleNamespace(file=SimpleNamespace(set_level=lambda level: None)))
    monkeypatch.setattr(LearningAPI, "_worker_", staticmethod(lambda payload, log: (None, None)))
    monkeypatch.setattr(LearningAPI, "__init__", _capture_)
    with pytest.raises(RuntimeError): LearningAPI._learn_seed_(payload)
    assert captured["selection"] == "Median" and captured["election"] == "Mean"

def test_a_serial_run_trains_on_the_threads_it_was_given(tmp_path, monkeypatch):
    threads = []
    monkeypatch.setattr(torch, "set_num_threads", threads.append)
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, seeds=2, workers=1, threads=1)
    harness._script_ = [0.01, 0.02]
    harness.run()
    assert threads == [1]
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, seeds=1)
    harness._script_ = [0.01]
    harness.run()
    assert threads == [1]

def test_seeds_are_elected_on_validation_never_on_the_held_out_window(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=12, seed=42, seeds=2)
    harness._script_ = [0.08, 0.01, 0.02, 0.50]
    harness.run()
    assert harness._promoted_ == tmp_path / "Seed 42"
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest["Best"] == 0.08 and manifest["Elected"] == 42
    assert [result["Test"] for result in manifest["Results"]] == [0.01, 0.50]

def test_a_run_keeps_every_seed_in_its_own_folder(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, validation=0, testing=0, seeds=1)
    harness._run_ = tmp_path / "Run"
    assert LearningAPI._weights_directory_(harness) == tmp_path / "Run" / SystemAPI.OUTPUT / "Weights"
    assert (tmp_path / "Run" / SystemAPI.OUTPUT / "Weights").is_dir()
    harness._weights_ = tmp_path / "Run" / SystemAPI.OUTPUT / "Weights"
    mkdir(harness._weights_ / "Seed 42")
    LearningAPI._export_weights_(harness)
    assert (harness._weights_ / "Seed 42").is_dir() and not list(tmp_path.glob("_FakeStrategy_ *"))

def test_a_walk_forward_run_writes_its_manifest(tmp_path):
    _reset_(tmp_path)
    harness = _make_(episodes=1, training=12, validation=6, testing=0, seeds=1)
    harness._tracked_ = lambda: [(0, 10000.0)]
    harness._script_ = [0.01, 0.02] * 8
    harness.run()
    manifest = read_json(tmp_path / "_FakeStrategy_ Manifest.json")
    assert manifest is not None and "Stitched" not in manifest["Results"][0] and len(manifest["Results"][0]["Folds"]) > 1

def test_a_three_to_one_rolling_split_validates_every_year_and_tests_the_last_from_midnight():
    folds, test = SplitAPI.walk_forward_folds(datetime(2015, 1, 1), datetime(2026, 1, 1, 23, 59, 59, 999999), 36, 12, 12, True)
    assert [validation[0].year for _, validation in folds] == list(range(2018, 2025))
    assert all(train[0].year + 3 == train[1].year for train, _ in folds)
    assert test == (datetime(2025, 1, 1), datetime(2026, 1, 1, 23, 59, 59, 999999))

def test_the_ddpg_defaults_are_the_thesis_recipe():
    golden = read_yaml(traceback_root() / "Tests" / "Golden" / "Consistency" / "DDPG" / "Parameters.yml")
    for kind, rebalance in (("Learning", 0.0), ("Backtesting", 0.2)):
        defaults = DDPGStrategyAPI.defaults(kind)
        assert list(defaults["TechnicalManagement"].items()) == list(golden["TechnicalManagement"].items())
        assert defaults["PortfolioManagement"]["PositionMode"] == ["Netting"] and defaults["SignalManagement"]["RebalanceThreshold"] == [rebalance]
        assert defaults["SignalManagement"]["DecisionSchedule"] == ["D1"] and defaults["SignalManagement"]["AccountFeatures"] == [False]
        for key in ("HiddenShape1", "HiddenShape2", "ActorRegularization", "BatchSize", "NormalizeWindow", "ObservationWindow"):
            assert defaults["SignalManagement"][key] == golden["SignalManagement"][key], key
    learning = DDPGStrategyAPI.defaults("Learning")["SignalManagement"]
    assert learning["DiscountFactor"] == [0.9995] and learning["WarmupSteps"] == [3000] and learning["RewardScale"] == [1000.0] and learning["RewardClip"] == [1.0]

def test_every_scope_a_seed_replays_has_its_history_published():
    folds = [((datetime(2023, 1, 1), datetime(2023, 5, 1)), (datetime(2023, 5, 1), datetime(2023, 7, 1))), ((datetime(2023, 3, 1), datetime(2023, 7, 1)), None)]
    assert LearningAPI._starts_(folds, (datetime(2023, 9, 1), datetime(2023, 11, 1))) == [datetime(2023, 1, 1), datetime(2023, 5, 1), datetime(2023, 3, 1), datetime(2023, 9, 1)]
    assert LearningAPI._starts_([], None) == []

def test_the_widest_window_is_the_one_the_engine_warms_to():
    parameters = Parameter({"TechnicalManagement": {"Baseline": ["SMA", 20], "Volatility": ["ATR", 14]}}, ".")
    assert SystemAPI._widest_(parameters) == 20