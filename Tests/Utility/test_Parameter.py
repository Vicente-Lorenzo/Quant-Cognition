import yaml

import pytest

from Library.Utility.Parameter import Parameter, format_slots, numbered, parse_slots

@pytest.fixture
def document(tmp_path):
    return tmp_path / "Backtesting.yml"

def test_values_are_reachable_by_attribute_and_by_item(document):
    parameter = Parameter({"MoneyManagement": {"RiskPercentage": [1.0]}}, document)
    assert parameter.MoneyManagement.RiskPercentage == [1.0]
    assert parameter["MoneyManagement"]["RiskPercentage"] == [1.0]

def test_a_missing_key_is_none_rather_than_an_error(document):
    parameter = Parameter({"MoneyManagement": {}}, document)
    assert parameter.Absent is None
    assert parameter.MoneyManagement.Absent is None

def test_nested_dictionaries_are_wrapped_eagerly(document):
    parameter = Parameter({"Outer": {"Inner": {"Leaf": 1}}}, document)
    assert isinstance(parameter.Outer, Parameter)
    assert isinstance(parameter.Outer.Inner, Parameter)
    assert parameter.Outer.Inner.Leaf == 1

def test_assignment_persists_to_the_document(document):
    parameter = Parameter({"MoneyManagement": {"RiskPercentage": [1.0]}}, document)
    parameter.MoneyManagement.RiskPercentage = [2.0]
    assert yaml.safe_load(document.read_text(encoding="utf-8"))["MoneyManagement"]["RiskPercentage"] == [2.0]

def test_a_nested_assignment_bubbles_to_the_root(document):
    parameter = Parameter({"Outer": {"Inner": {"Leaf": 1}}}, document)
    parameter.Outer.Inner.Leaf = 9
    assert parameter.data["Outer"]["Inner"]["Leaf"] == 9
    assert yaml.safe_load(document.read_text(encoding="utf-8"))["Outer"]["Inner"]["Leaf"] == 9

def test_deleting_a_key_removes_it(document):
    parameter = Parameter({"A": 1, "B": 2}, document)
    del parameter.A
    assert parameter.A is None and parameter.B == 2

def test_a_clone_is_independent(document):
    parameter = Parameter({"Outer": {"Leaf": 1}}, document)
    clone = parameter.clone()
    clone.data["Outer"]["Leaf"] = 9
    assert parameter.data["Outer"]["Leaf"] == 1

def test_mapping_helpers_expose_the_underlying_data(document):
    parameter = Parameter({"A": 1, "B": 2}, document)
    assert sorted(parameter.keys()) == ["A", "B"]
    assert sorted(parameter.values()) == [1, 2]
    assert dict(parameter.items()) == {"A": 1, "B": 2}

def test_slots_render_with_the_house_separator():
    assert format_slots([["SMA", "EMA"], [10, 20]]) == "SMA|EMA · 10|20"

def test_slots_round_trip_to_an_equivalent_space():
    assert parse_slots(format_slots([["SMA", "EMA"], [10, 20]])) == [["SMA", "EMA"], [10, 20]]
    assert parse_slots(format_slots(["ATR", 14])) == ["ATR", 14]

def test_a_semicolon_is_accepted_because_the_separator_is_not_on_a_keyboard():
    assert parse_slots("SMA|EMA ; 10|20") == parse_slots("SMA|EMA · 10|20")

def test_a_single_option_slot_collapses_to_a_scalar():
    assert parse_slots("SMA · Auto") == ["SMA", "Auto"]

def test_an_empty_slot_text_is_no_slots():
    assert parse_slots("   ") == []

def test_numbers_decode_and_text_survives():
    assert parse_slots("ATR · 14 · 0.5 · Signal") == ["ATR", 14, 0.5, "Signal"]

def test_numbered_recognizes_a_staged_body():
    assert numbered({"1": {}, "2-3": {}}) is True
    assert numbered({"Baseline": []}) is False
    assert numbered({}) is False
    assert numbered(None) is False