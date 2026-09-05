from Library.Utility.Parameter import Parameter
from Library.System.Selection import ElectionMode, SelectionMode, select
from Library.System.Optimization import OptimizationAPI
from Library.System.Space import (
    CandidateAPI,
    apply_candidate,
    build_grid,
    expand_parameter,
    neighborhoods,
    unpack_section,
    flatten_space
)

SPACE = {"MoneyManagement": {"RiskPercentage": [[0.5, 1.0]]},
         "TechnicalManagement": {"Baseline": [["SMA", "EMA"], [10, 20]]}}

def test_expand_parameter_products_every_slot():
    assert expand_parameter([["SMA", "EMA"], [10, 20]]) == [["SMA", 10], ["SMA", 20], ["EMA", 10], ["EMA", 20]]

def test_expand_parameter_keeps_a_single_slot_flat():
    assert expand_parameter([[0.5, 1.0]]) == [[0.5], [1.0]]

def test_build_grid_is_the_product_of_every_parameter():
    grid = build_grid(SPACE)
    assert len(grid) == 8
    assert [candidate.index for candidate in grid] == list(range(8))

def test_build_grid_without_a_space_is_empty():
    assert build_grid({}) == []

def test_every_candidate_carries_every_axis():
    for candidate in build_grid(SPACE):
        assert set(candidate.overrides) == {"MoneyManagement", "TechnicalManagement"}
        assert len(candidate.overrides["TechnicalManagement"]["Baseline"]) == 2

def test_distance_counts_slots_not_parameters():
    grid = build_grid(SPACE)
    baseline = grid[0]
    assert baseline.distance(grid[1]) == 1
    assert baseline.distance(grid[3]) == 2
    assert baseline.distance(baseline) == 0

def test_neighbours_differ_in_exactly_one_slot():
    grid = build_grid(SPACE)
    assert [other.index for other in grid if 0 < grid[0].distance(other) <= 1] == [1, 2, 4]

def test_argmax_takes_the_peak_even_when_isolated():
    grid = build_grid(SPACE)
    scores = {0: 1.0, 1: 9.0, 2: 1.0, 3: 1.0, 4: 4.0, 5: 4.2, 6: 4.1, 7: 3.9}
    chosen, score = select([(c, scores[c.index]) for c in grid], SelectionMode.Best, adjacency=neighborhoods)
    assert chosen.index == 1 and score == 9.0

def test_plateau_prefers_a_stable_region_over_a_lone_spike():
    grid = build_grid(SPACE)
    scores = {0: 1.0, 1: 9.0, 2: 1.0, 3: 1.0, 4: 4.0, 5: 4.2, 6: 4.1, 7: 3.9}
    chosen, _ = select([(c, scores[c.index]) for c in grid], SelectionMode.Plateau, adjacency=neighborhoods)
    assert chosen.index == 5

def test_selection_accepts_the_mode_by_name():
    grid = build_grid(SPACE)
    scored = [(c, float(c.index)) for c in grid]
    assert select(scored, "Best", adjacency=neighborhoods)[0].index == 7

def test_selection_ignores_candidates_without_a_score():
    grid = build_grid(SPACE)
    scored = [(grid[0], None), (grid[1], 2.0), (grid[2], None)]
    assert select(scored, SelectionMode.Best, adjacency=neighborhoods)[0].index == 1

def test_selection_without_any_score_returns_nothing():
    grid = build_grid(SPACE)
    assert select([(candidate, None) for candidate in grid], SelectionMode.Best, adjacency=neighborhoods) is None

def test_unpack_space_ignores_absent_and_empty_sections():
    class Block:

        def __init__(self, data): self.data = data
    class Holder:

        def __init__(self, **sections):
            for name, block in sections.items(): setattr(self, name, block)
    holder = Holder(MoneyManagement=Block({"RiskPercentage": [[0.5, 1.0]], "Ignored": None}),
                    RiskManagement=Block({}))
    space = unpack_section(flatten_space(holder))
    assert space == {"MoneyManagement": {"RiskPercentage": [[0.5, 1.0]]}}

def test_unpack_space_wraps_a_bare_slot_into_options():
    class Block:

        def __init__(self, data): self.data = data
    class Holder:

        def __init__(self, block): self.TechnicalManagement = block
    space = unpack_section(flatten_space(Holder(Block({"ATR": ["ATR", [14, 21]]}))))
    assert space["TechnicalManagement"]["ATR"] == [["ATR"], [14, 21]]

def test_label_is_stable_and_readable():
    grid = build_grid(SPACE)
    assert grid[0].label() == "RiskPercentage=0.5 · Baseline=SMA/10"

def _base_():
    return Parameter({"MoneyManagement": {"RiskPercentage": [1.0], "DrawdownFactor": [1.0]},
                      "TechnicalManagement": {"Baseline": ["SMA", 20]}}, ".")

def test_apply_candidate_overrides_only_named_slots():
    applied = apply_candidate(_base_(), build_grid(SPACE)[0])
    assert applied.data["MoneyManagement"]["RiskPercentage"] == [0.5]
    assert applied.data["TechnicalManagement"]["Baseline"] == ["SMA", 10]
    assert applied.data["MoneyManagement"]["DrawdownFactor"] == [1.0]

def test_apply_candidate_never_mutates_the_base():
    base = _base_()
    apply_candidate(base, build_grid(SPACE)[3])
    assert base.data["MoneyManagement"]["RiskPercentage"] == [1.0]
    assert base.data["TechnicalManagement"]["Baseline"] == ["SMA", 20]

def test_apply_candidate_ignores_parameters_absent_from_the_base():
    candidate = CandidateAPI(index=0, overrides={"MoneyManagement": {"Unknown": [1]}})
    assert "Unknown" not in apply_candidate(_base_(), candidate).data["MoneyManagement"]

def test_neighborhoods_match_pairwise_distance():
    grid = build_grid(SPACE)
    adjacency = neighborhoods(grid)
    for candidate in grid:
        expected = {other.index for other in grid if 0 < candidate.distance(other) <= 1}
        assert adjacency[candidate.index] == expected

def test_neighborhoods_exclude_the_candidate_itself():
    grid = build_grid(SPACE)
    adjacency = neighborhoods(grid)
    assert all(index not in members for index, members in adjacency.items())

def test_plateau_stays_linear_on_a_large_grid():
    import time
    space = {"TechnicalManagement": {"Baseline": [["SMA", "EMA"], list(range(5, 37))], "ATR": [["ATR"], [7, 10, 14, 21]]},
             "MoneyManagement": {"RiskPercentage": [[0.5, 1.0, 1.5, 2.0]]}}
    grid = build_grid(space)
    assert len(grid) == 1024
    scored = [(candidate, float(candidate.index % 7)) for candidate in grid]
    start = time.perf_counter()
    assert select(scored, SelectionMode.Plateau, adjacency=neighborhoods) is not None
    assert time.perf_counter() - start < 1.0

def _elector_(stages: list, ledger: dict, election: ElectionMode = ElectionMode.Frequency) -> OptimizationAPI:
    engine = object.__new__(OptimizationAPI)
    engine._stages_ = stages
    engine._ledger_ = ledger
    engine._election_ = election
    return engine

def _ledger_(*labels) -> dict:
    return {label: CandidateAPI(index=index, overrides={"MoneyManagement": {"RiskPercentage": [label]}})
            for index, label in enumerate(labels, start=1)}

def test_election_takes_the_most_selected_candidate():
    ledger = _ledger_("RiskPercentage=1", "RiskPercentage=2")
    stages = [{"Parameters": "RiskPercentage=1", "Training": 0.1, "Validation": None},
              {"Parameters": "RiskPercentage=2", "Training": 0.9, "Validation": None},
              {"Parameters": "RiskPercentage=2", "Training": 0.2, "Validation": None}]
    candidate, evidence = _elector_(stages, ledger)._elect_()
    assert candidate.index == 2
    assert evidence["Votes"] == 2

def test_election_breaks_a_tie_on_accumulated_fitness():
    ledger = _ledger_("RiskPercentage=1", "RiskPercentage=2")
    stages = [{"Parameters": "RiskPercentage=1", "Training": 0.1, "Validation": 0.2},
              {"Parameters": "RiskPercentage=2", "Training": 0.1, "Validation": 0.9}]
    candidate, evidence = _elector_(stages, ledger)._elect_()
    assert candidate.index == 2
    assert evidence["Votes"] == 1

def test_election_prefers_validation_over_training():
    ledger = _ledger_("RiskPercentage=1", "RiskPercentage=2")
    stages = [{"Parameters": "RiskPercentage=1", "Training": 9.0, "Validation": 0.1},
              {"Parameters": "RiskPercentage=2", "Training": 0.0, "Validation": 0.5}]
    assert _elector_(stages, ledger)._elect_()[0].index == 2

def test_election_without_any_stage_returns_nothing():
    assert _elector_([], {})._elect_() is None

def test_ordering_groups_candidates_sharing_technical_parameters():
    grid = build_grid(SPACE)
    ordered = OptimizationAPI._ordered_(grid)
    assert sorted(c.index for c in ordered) == sorted(c.index for c in grid)
    keys = [repr(sorted(c.overrides["TechnicalManagement"].items())) for c in ordered]
    assert keys == sorted(keys)
    assert len(set(keys)) == 4