import pytest
from dataclasses import dataclass, InitVar
from enum import Enum
from Library.Utility.Typing import MISSING
from Library.Database.Dataclass import DataclassAPI

class TestEnum(Enum):
    A = 1
    B = 2

@dataclass(kw_only=True)
class NestedClass(DataclassAPI):
    name: str

@dataclass(kw_only=True)
class ParentClass(DataclassAPI):
    value: int
    enum_val: TestEnum
    nested: NestedClass
    init_val: InitVar[int]

    def __post_init__(self, init_val):
        self._init_val = init_val

    @property
    def computed(self):
        return self.value * 2

def test_dataclass_initialization():
    obj = ParentClass(UID=100, value=10, enum_val=TestEnum.A, nested=NestedClass(name="Test"), init_val=5)
    assert obj.UID == 100
    assert obj.value == 10

def test_datameta_api_attributes():
    assert ParentClass.ID.UID == "UID"
    assert ParentClass.ID.value == "value"
    assert ParentClass.ID.nested.name == "nested"
    assert ParentClass.ID.computed == "computed"
    
    with pytest.raises(AttributeError):
        _ = ParentClass.ID.does_not_exist

def test_dataclass_parse():
    nested = NestedClass(UID="n1", name="Nested")
    obj = ParentClass(UID=1, value=5, enum_val=TestEnum.B, nested=nested, init_val=0)
    
    assert obj._parse_("value") == 5
    assert obj._parse_("enum_val") == "B"
    assert obj._parse_("nested") == "n1"
    
def test_dataclass_data_structures():
    nested = NestedClass(UID="n1", name="Nested")
    obj = ParentClass(UID=1, value=5, enum_val=TestEnum.B, nested=nested, init_val=0)
    
    d = obj.dict()
    assert "UID" in d
    assert "value" in d
    assert d["value"] == 5
    assert d["enum_val"] == "B"
    assert d["nested"] == "n1"

    l = obj.list()
    assert 5 in l
    assert "B" in l
    assert "n1" in l

    t = obj.tuple()
    assert 5 in t
    assert "B" in t
    assert "n1" in t
