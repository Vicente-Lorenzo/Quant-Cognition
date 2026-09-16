import yaml

import pytest

from Library.Utility.Parameter import Parameter

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

def test_saving_keeps_the_key_order_because_order_can_be_load_bearing(document):
    parameter = Parameter({"TechnicalManagement": {"Zeta": [1], "Alpha": [2]}}, document)
    parameter.TechnicalManagement.Zeta = [3]
    assert list(yaml.safe_load(document.read_text(encoding="utf-8"))["TechnicalManagement"]) == ["Zeta", "Alpha"]