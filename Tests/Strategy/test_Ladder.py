import pytest

from Library.Strategy.Hybrid import DDPGStrategyAPI
from Library.Strategy.Ladder import LadderAPI
from Library.Strategy.Rule.Trend import TrendStrategyAPI

RUNGS = ("Spotware(cTrader)", "Forex(Major)", "EURUSD", "Daily")

@pytest.fixture
def ladder(tmp_path):
    return LadderAPI(root=tmp_path)

def test_key_strips_the_class_suffix():
    assert TrendStrategyAPI.key() == "Trend"
    assert DDPGStrategyAPI.key() == "DDPG"

def test_backtesting_inherits_the_realtime_defaults():
    assert TrendStrategyAPI.defaults("Backtesting") == TrendStrategyAPI.defaults("Realtime")

def test_defaults_are_copied_not_shared():
    first = TrendStrategyAPI.defaults("Backtesting")
    first["MoneyManagement"]["RiskPercentage"] = ["mutated"]
    assert TrendStrategyAPI.defaults("Backtesting")["MoneyManagement"]["RiskPercentage"] != ["mutated"]

def test_scopes_walk_from_global_to_most_specific():
    assert LadderAPI.scopes("a", "b") == ((), ("a",), ("a", "b"))

def test_merge_is_key_by_key():
    base = {"Money": {"Risk": [1.0], "Factor": [2.0]}, "Signal": None}
    assert LadderAPI.merge(base, {"Money": {"Risk": [9.0]}}) == {"Money": {"Risk": [9.0], "Factor": [2.0]}, "Signal": None}

def test_merge_never_mutates_the_base():
    base = {"Money": {"Risk": [1.0]}}
    LadderAPI.merge(base, {"Money": {"Risk": [9.0]}})
    assert base == {"Money": {"Risk": [1.0]}}

def test_an_explicit_none_overrides_rather_than_inherits():
    assert LadderAPI.merge({"Risk": {"Stop": [1.5]}}, {"Risk": None}) == {"Risk": None}

def test_a_missing_override_resolves_to_defaults(ladder):
    sections, trail = ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)
    assert sections == TrendStrategyAPI.defaults("Backtesting")
    assert trail == [LadderAPI._ORIGIN_]

def test_an_unconfigured_security_does_not_fail(ladder):
    sections, trail = ladder.resolve(TrendStrategyAPI, "Realtime", "Broker", "Category", "NOSUCH", "Minute")
    assert sections and trail == [LadderAPI._ORIGIN_]

def test_a_partial_override_keeps_every_other_value(ladder):
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [2.5]}}, *RUNGS)
    sections, trail = ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)
    defaults = TrendStrategyAPI.defaults("Backtesting")
    assert sections["MoneyManagement"]["RiskPercentage"] == [2.5]
    assert sections["MoneyManagement"]["DrawdownFactor"] == defaults["MoneyManagement"]["DrawdownFactor"]
    assert sections["RiskManagement"] == defaults["RiskManagement"]
    assert len(trail) == 2

def test_a_narrower_scope_beats_a_broader_one(ladder):
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [9.9]}}, "Spotware(cTrader)")
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [2.5]}}, *RUNGS)
    sections, trail = ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)
    assert sections["MoneyManagement"]["RiskPercentage"] == [2.5]
    assert len(trail) == 3

def test_one_strategy_override_does_not_reach_another(ladder):
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [2.5]}}, *RUNGS)
    sections, trail = ladder.resolve(DDPGStrategyAPI, "Backtesting", *RUNGS)
    assert sections == DDPGStrategyAPI.defaults("Backtesting")
    assert trail == [LadderAPI._ORIGIN_]

def test_provenance_reports_the_declared_origin(ladder):
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [2.5]}}, *RUNGS, origin="Optimization run abc123")
    assert ladder.provenance(TrendStrategyAPI, "Backtesting", *RUNGS) == "Optimization run abc123"

def test_provenance_falls_back_to_defaults(ladder):
    assert ladder.provenance(TrendStrategyAPI, "Backtesting", *RUNGS) == LadderAPI._ORIGIN_

def test_promotion_leaves_other_strategies_in_the_same_file(ladder):
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [2.5]}}, *RUNGS)
    ladder.promote(DDPGStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [3.5]}}, *RUNGS)
    assert ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)[0]["MoneyManagement"]["RiskPercentage"] == [2.5]
    assert ladder.resolve(DDPGStrategyAPI, "Backtesting", *RUNGS)[0]["MoneyManagement"]["RiskPercentage"] == [3.5]

def test_a_corrupt_override_is_survived(ladder, tmp_path):
    path = ladder.override("Backtesting", *RUNGS)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not: valid: yaml", encoding="utf-8")
    sections, trail = ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)
    assert sections == TrendStrategyAPI.defaults("Backtesting")
    assert trail == [LadderAPI._ORIGIN_]

def test_merge_blends_two_flat_bodies():
    blended = LadderAPI.merge({"Technical": {"Baseline": ["SMA"], "Filter1": ["TT"]}}, {"Technical": {"Baseline": ["EMA"]}})
    assert blended == {"Technical": {"Baseline": ["EMA"], "Filter1": ["TT"]}}

def test_merge_lets_a_staged_body_replace_a_flat_one():
    blended = LadderAPI.merge({"Technical": {"Baseline": ["SMA"], "Filter1": ["TT"]}},
                              {"Technical": {"1": {"Baseline": [["EMA", "WMA"]]}}})
    assert blended == {"Technical": {"1": {"Baseline": [["EMA", "WMA"]]}}}

def test_merge_still_blends_two_staged_bodies():
    blended = LadderAPI.merge({"Technical": {"1": {"Baseline": ["SMA"]}, "2": {"Filter1": ["TT"]}}},
                              {"Technical": {"1": {"Baseline": ["EMA"]}}})
    assert blended == {"Technical": {"1": {"Baseline": ["EMA"]}, "2": {"Filter1": ["TT"]}}}

def test_sparse_returns_only_what_the_file_holds(tmp_path):
    ladder = LadderAPI(root=tmp_path)
    assert ladder.sparse(TrendStrategyAPI, "Optimization") == {}
    ladder.promote(TrendStrategyAPI, "Optimization", {"MoneyManagement": {"RiskPercentage": [[1.0]]}})
    assert ladder.sparse(TrendStrategyAPI, "Optimization") == {"MoneyManagement": {"RiskPercentage": [[1.0]]}}

def test_sparse_hands_back_a_copy(tmp_path):
    ladder = LadderAPI(root=tmp_path)
    ladder.promote(TrendStrategyAPI, "Optimization", {"MoneyManagement": {"RiskPercentage": [[1.0]]}})
    lifted = ladder.sparse(TrendStrategyAPI, "Optimization")
    lifted["MoneyManagement"]["RiskPercentage"] = [[9.9]]
    assert ladder.sparse(TrendStrategyAPI, "Optimization") == {"MoneyManagement": {"RiskPercentage": [[1.0]]}}

def test_backtesting_inherits_realtime_overrides(ladder):
    ladder.promote(TrendStrategyAPI, "Realtime", {"MoneyManagement": {"RiskPercentage": [9.9]}}, *RUNGS)
    resolved, _ = ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)
    assert resolved["MoneyManagement"]["RiskPercentage"] == [9.9]

def test_a_backtesting_override_diverges_without_touching_realtime(ladder):
    ladder.promote(TrendStrategyAPI, "Realtime", {"MoneyManagement": {"RiskPercentage": [9.9]}}, *RUNGS)
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [0.5]}}, *RUNGS)
    assert ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)[0]["MoneyManagement"]["RiskPercentage"] == [0.5]
    assert ladder.resolve(TrendStrategyAPI, "Realtime", *RUNGS)[0]["MoneyManagement"]["RiskPercentage"] == [9.9]

def test_realtime_never_inherits_backtesting(ladder):
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [0.5]}}, *RUNGS)
    resolved, _ = ladder.resolve(TrendStrategyAPI, "Realtime", *RUNGS)
    assert resolved["MoneyManagement"]["RiskPercentage"] != [0.5]

def test_a_more_specific_backtesting_override_beats_a_broader_realtime_one(ladder):
    ladder.promote(TrendStrategyAPI, "Realtime", {"MoneyManagement": {"RiskPercentage": [9.9]}}, *RUNGS[:1])
    ladder.promote(TrendStrategyAPI, "Backtesting", {"MoneyManagement": {"RiskPercentage": [0.5]}}, *RUNGS)
    assert ladder.resolve(TrendStrategyAPI, "Backtesting", *RUNGS)[0]["MoneyManagement"]["RiskPercentage"] == [0.5]

def test_optimization_and_learning_stay_independent(ladder):
    ladder.promote(TrendStrategyAPI, "Realtime", {"MoneyManagement": {"RiskPercentage": [9.9]}}, *RUNGS)
    resolved, _ = ladder.resolve(TrendStrategyAPI, "Optimization", *RUNGS)
    assert resolved["MoneyManagement"]["RiskPercentage"] != [9.9]

def test_lineage_is_one_directional():
    assert TrendStrategyAPI.lineage("Backtesting") == ("Realtime", "Backtesting")
    assert TrendStrategyAPI.lineage("Realtime") == ("Realtime",)
    assert TrendStrategyAPI.lineage("Optimization") == ("Optimization",)

def test_provenance_names_the_kind_it_came_through(ladder):
    ladder.promote(TrendStrategyAPI, "Realtime", {"MoneyManagement": {"RiskPercentage": [9.9]}}, *RUNGS)
    assert "via Realtime" in ladder.provenance(TrendStrategyAPI, "Backtesting", *RUNGS)