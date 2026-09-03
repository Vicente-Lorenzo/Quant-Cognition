import types

import pytest

from Library.Indicator.Indicator import IndicatorAPI
from Library.System.Optimization import (OptimizationAPI, build_grid, expand_parameter, inherited, measure_plan, resolve_inheritance, rounds_parameter, staged, unpack_plan, unpack_section, unpack_stages)

class Block:

    def __init__(self, **sections) -> None:
        for name, data in sections.items(): setattr(self, name, types.SimpleNamespace(data=data))

    def __getattr__(self, name):
        return None

STAGED = Block(TechnicalManagement={"1": {"Baseline": [["WMA", "HMA", "DEMA"]], "Volatility": ["ATR", 14]},
                                    "2": {"Filter1": [["Overlap", "Momentum"]]},
                                    "3": {"Baseline": ["Result=1"], "Filter2": [["Overlap"]]}},
              MoneyManagement={"1-3": {"RiskPercentage": [2.0]}})
FLAT = Block(TechnicalManagement={"Baseline": [["SMA", "EMA"], [10, 20]]})

def test_a_flat_space_is_not_staged():
    assert staged(FLAT) is False
    assert len(unpack_plan(FLAT)) == 1

def test_a_numbered_space_is_staged():
    assert staged(STAGED) is True
    assert len(unpack_plan(STAGED)) == 3

def test_a_span_applies_to_every_stage_it_covers():
    plan = unpack_stages(STAGED)
    assert all("MoneyManagement" in stage for stage in plan)
    assert [sorted(stage["TechnicalManagement"]) for stage in plan] == [["Baseline", "Volatility"], ["Filter1"], ["Baseline", "Filter2"]]

def test_a_reversed_span_is_rejected():
    with pytest.raises(ValueError):
        unpack_stages(Block(MoneyManagement={"4-2": {"RiskPercentage": [1.0]}}))

def test_a_gap_in_the_numbering_is_rejected():
    with pytest.raises(ValueError):
        unpack_stages(Block(MoneyManagement={"1": {"RiskPercentage": [1.0]}, "3": {"RiskPercentage": [2.0]}}))

def test_a_section_mixing_stages_with_parameters_is_rejected():
    with pytest.raises(ValueError):
        unpack_stages(Block(TechnicalManagement={"1": {"Baseline": [["SMA"]]}, "Filter1": [["TT"]]}))

def test_a_flat_section_is_constant_across_every_stage():
    mixed = Block(TechnicalManagement={"1": {"Baseline": [["SMA"]]}, "2": {"Filter1": [["TT"]]}},
                  MoneyManagement={"RiskPercentage": [[0.5, 1.0]]})
    assert staged(mixed) is True
    plan = unpack_stages(mixed)
    assert [sorted(stage) for stage in plan] == [["MoneyManagement", "TechnicalManagement"]] * 2
    assert all(stage["MoneyManagement"] == {"RiskPercentage": [[0.5, 1.0]]} for stage in plan)

@pytest.mark.parametrize("value, expected", [(["Result=1"], 1), (["Result = 12"], 12), ([["WMA"]], None),
                                             (["ATR", 14], None), (["Results=1"], None), ([], None)])
def test_inheritance_is_recognized_only_in_its_exact_form(value, expected):
    assert inherited(value) == expected

def test_inheritance_pins_an_earlier_winner():
    winners = [{"TechnicalManagement": {"Baseline": ["HMA", 20]}}, {}]
    resolved = resolve_inheritance(unpack_stages(STAGED)[2], winners, 2)
    assert resolved["TechnicalManagement"]["Baseline"] == ["HMA", 20]
    assert build_grid(unpack_section(resolved))[0].overrides["TechnicalManagement"]["Baseline"] == ["HMA", 20]

def test_inheritance_from_a_later_stage_is_rejected():
    with pytest.raises(ValueError):
        resolve_inheritance({"TechnicalManagement": {"Baseline": ["Result=3"]}}, [{}], 1)

def test_inheritance_from_a_barren_stage_is_rejected():
    with pytest.raises(ValueError):
        resolve_inheritance({"TechnicalManagement": {"Baseline": ["Result=1"]}}, [{}], 1)

def test_staging_turns_a_product_into_a_sum():
    product = Block(TechnicalManagement={"Baseline": [["WMA", "HMA", "DEMA"]], "Filter1": [["Overlap", "Momentum"]],
                                         "Filter2": [["Overlap", "Momentum"]]})
    summed = Block(TechnicalManagement={"1": {"Baseline": [["WMA", "HMA", "DEMA"]]}, "2": {"Filter1": [["Overlap", "Momentum"]]},
                                        "3": {"Filter2": [["Overlap", "Momentum"]]}})
    assert measure_plan(unpack_plan(product)) == 12
    assert measure_plan(unpack_plan(summed)) == 7

def test_a_flat_space_expands_exactly_as_before():
    assert expand_parameter([["SMA", "EMA"], [10, 20]]) == [["SMA", 10], ["SMA", 20], ["EMA", 10], ["EMA", 20]]
    assert rounds_parameter([["SMA", "EMA"], [10, 20]]) == 1

def test_auto_takes_the_ladder_from_the_indicator():
    assert rounds_parameter([["SMA"], ["Auto"]]) == 3
    assert expand_parameter([["SMA"], ["Auto"]])[:3] == [["SMA", 5], ["SMA", 10], ["SMA", 15]]

def test_a_later_round_refines_around_the_winner():
    assert expand_parameter([["SMA"], ["Auto"]], ["SMA", 20], 1) == [["SMA", value] for value in range(12, 29, 2)]
    assert expand_parameter([["SMA"], ["Auto"]], ["SMA", 20], 2) == [["SMA", value] for value in range(17, 24)]

def test_a_later_round_pins_the_categorical_slots():
    assert expand_parameter([["SMA", "EMA"], ["Auto"]], ["EMA", 20], 2) == [["EMA", value] for value in range(17, 24)]

def test_an_inline_range_needs_no_indicator():
    assert expand_parameter([["ATR"], ["10-30:10"]]) == [["ATR", 10], ["ATR", 20], ["ATR", 30]]
    assert expand_parameter([[1.0], ["0.5..2.0:0.5"]])[0] == [1.0, 0.5]

def test_admits_prunes_an_impossible_cross():
    grid = expand_parameter([["SMAC"], ["Auto"], ["Auto"]])
    assert grid
    assert all(fast < slow for _, fast, slow in grid)

def test_coarse_to_fine_costs_less_than_an_exhaustive_sweep():
    coarse = len(expand_parameter([["SMA"], ["Auto"]]))
    refined = len(expand_parameter([["SMA"], ["Auto"]], ["SMA", 20], 1)) + len(expand_parameter([["SMA"], ["Auto"]], ["SMA", 20], 2))
    assert coarse + refined < len(range(5, 101))

def test_every_indicator_file_is_addressable_by_its_own_name():
    for acronym, module in IndicatorAPI.catalog().items():
        assert module.endswith("." + acronym)
        assert IndicatorAPI.resolve_technical(acronym).__module__ == module

def test_every_indicator_declares_its_slots():
    for acronym in IndicatorAPI.catalog():
        slots = IndicatorAPI.resolve_technical(acronym).Parameters
        assert slots
        assert slots[-1].name == "mode"

def test_every_indicator_builds_from_its_defaults():
    for acronym in IndicatorAPI.catalog():
        assert getattr(IndicatorAPI.parse_technical({"X": [acronym]}), "X", None) is not None

def test_a_cross_inherits_admits_from_its_family():
    for acronym in ("SMAC", "EMAC", "WMAC", "HMAC", "TRIMAC", "KAMAC", "DMAC", "TMAC"):
        indicator = IndicatorAPI.resolve_technical(acronym)
        assert indicator.admits({"fast_window": 5, "slow_window": 20})
        assert not indicator.admits({"fast_window": 20, "slow_window": 5})

def test_an_unconstrained_indicator_admits_everything():
    assert IndicatorAPI.resolve_technical("SMA").admits({"window": 1})
    assert IndicatorAPI.resolve_technical("TT").admits({})

class _Engine_(OptimizationAPI):

    def __init__(self, space) -> None:
        import logging
        from datetime import datetime
        from Library.System.Selection import ElectionMode, SelectionMode
        from Library.Utility.Parameter import Parameter
        self._space_ = space
        self._baseline_ = Parameter({'TechnicalManagement': {'Baseline': ['SMA', 20], 'Filter1': ['TT'], 'Filter2': ['TT']}}, '.')
        self._selection_, self._election_ = SelectionMode.Best, ElectionMode.Frequency
        self._fitness_label_ = 'x'
        self._training_ = self._validation_ = self._testing_ = 0
        self._rolling_ = self._continuous_ = False
        self._purge_ = self._embargo_ = None
        self._workers_ = 1
        self._range_start_, self._range_stop_ = datetime(2020, 1, 1), datetime(2023, 1, 1)
        self._stages_, self._ledger_, self._trials_ = [], {}, 0
        self._carried_, self._journal_, self._folded_ = {}, [], []
        self._winner_ = self._verdict_ = self._outcome_ = None
        self._deliverables_ = (False, False, False)
        self.seen = []
        self._log_ = logging.getLogger('silent')
        self._log_.disabled = True

    def _identity_(self) -> str:
        return 'harness'

    def _evaluate_(self, candidate, start, stop):
        applied = {name: value for block in candidate.overrides.values() for name, value in block.items()}
        self.seen.append(applied)
        return {'WMA': 3.0, 'HMA': 1.0}.get(applied.get('Baseline', [None])[0], 0.0)

    def _deliver_(self, candidate, test) -> None:
        self._winner_ = candidate

def test_stages_without_result_do_not_propagate():
    space = Block(TechnicalManagement={'1': {'Baseline': [['WMA', 'HMA']]},
                                       '2': {'Filter1': [['TT', 'TF']]},
                                       '3': {'Filter2': [['TT', 'TF']]}})
    engine = _Engine_(space)
    engine.run()
    assert all(set(applied) == {'Baseline'} for applied in engine.seen[:2])
    assert all(set(applied) == {'Filter1'} for applied in engine.seen[2:4])
    assert all(set(applied) == {'Filter2'} for applied in engine.seen[4:6])

def test_a_repeated_stage_searches_independently_again():
    space = Block(TechnicalManagement={'1': {'Baseline': [['WMA', 'HMA']]},
                                       '2': {'Filter1': [['TT', 'TF']]},
                                       '3': {'Baseline': [['WMA', 'HMA']]}})
    engine = _Engine_(space)
    engine.run()
    assert all(set(applied) == {'Baseline'} for applied in engine.seen[4:6])

def test_only_result_pulls_an_earlier_winner_into_a_later_stage():
    space = Block(TechnicalManagement={'1': {'Baseline': [['WMA', 'HMA']]},
                                       '2': {'Baseline': ['Result=1'], 'Filter1': [['TT', 'TF']]}})
    engine = _Engine_(space)
    engine.run()
    assert all(set(applied) == {'Baseline', 'Filter1'} for applied in engine.seen[2:])
    assert all(applied['Baseline'] == ['WMA'] for applied in engine.seen[2:])

def test_the_fold_winner_is_the_union_of_every_stage_decision():
    space = Block(TechnicalManagement={'1': {'Baseline': [['WMA', 'HMA']]},
                                       '2': {'Filter1': [['TT', 'TF']]}})
    engine = _Engine_(space)
    engine.run()
    overrides = engine.stages[0]['Parameters']
    assert 'Baseline=WMA' in overrides and 'Filter1=' in overrides

def test_a_range_in_the_leading_slot_expands():
    options = unpack_section({'MoneyManagement': {'RiskPercentage': ['0.5..3.0:0.5']}})['MoneyManagement']['RiskPercentage']
    assert [value[0] for value in expand_parameter(options)] == [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

def test_a_range_in_the_leading_slot_refines():
    options = unpack_section({'MoneyManagement': {'RiskPercentage': ['0.5..3.0:0.5']}})['MoneyManagement']['RiskPercentage']
    assert rounds_parameter(options) == 3
    assert [value[0] for value in expand_parameter(options, [1.5], 1)] == [1.0, 1.25, 1.5, 1.75, 2.0]

def test_a_plain_list_in_the_leading_slot_is_untouched():
    options = unpack_section({'MoneyManagement': {'RiskPercentage': [[0.5, 1.0, 1.5]]}})['MoneyManagement']['RiskPercentage']
    assert rounds_parameter(options) == 1
    assert [value[0] for value in expand_parameter(options)] == [0.5, 1.0, 1.5]

def test_auto_without_a_ladder_is_refused_not_taken_literally():
    options = unpack_section({'MoneyManagement': {'RiskPercentage': ['Auto']}})['MoneyManagement']['RiskPercentage']
    with pytest.raises(ValueError, match="leading slot is Auto"):
        expand_parameter(options)

def test_auto_on_a_head_that_declares_no_ladder_is_refused():
    with pytest.raises(ValueError, match="declares no ladder"):
        expand_parameter([["RiskPercentage"], ["Auto"]])

def test_the_refusal_names_the_offending_parameter():
    with pytest.raises(ValueError, match=r"MoneyManagement\.RiskPercentage"):
        build_grid({"MoneyManagement": {"RiskPercentage": [["Auto"]]}})

def test_auto_still_expands_wherever_a_ladder_exists():
    assert len(expand_parameter([["SMA"], ["Auto"]])) == 20
    assert len(expand_parameter([["SMA", "EMA"], ["Auto"]])) == 40