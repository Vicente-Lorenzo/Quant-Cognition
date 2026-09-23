from typing import Union
import pytest
from dataclasses import dataclass
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI

@dataclass
class MockDatapoint(DatapointAPI):

    Database = DatapointAPI.Database
    Schema = "TestSchema"
    Table = "MockDatapoint"
    TestID: Union[int, None] = None
    Value: Union[str, None] = None
    Other: Union[float, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.TestID: PrimaryKey(pl.Int64),
            self.ID.Value: pl.String(),
            self.ID.Other: pl.Float64(),
            **super().Structure
        }

    def __post_init__(self, db, migrate, autoload, autooverload, autosave):
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

@pytest.fixture
def test_db(db):
    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'CREATE SCHEMA IF NOT EXISTS "{MockDatapoint.Schema}"'))
    db.commit()
    yield db
    db.executeone(QueryAPI(f'DROP TABLE IF EXISTS "{MockDatapoint.Schema}"."{MockDatapoint.Table}" CASCADE'))
    db.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{MockDatapoint.Schema}" CASCADE'))
    db.commit()

def test_datapoint_migration(test_db):
    obj = MockDatapoint(db=test_db, migrate=True)
    assert test_db.exists(schema=MockDatapoint.Schema, table=MockDatapoint.Table)

def test_datapoint_save_and_load(test_db):
    obj = MockDatapoint(TestID=1, Value="Test", Other=3.14, db=test_db, migrate=True)
    obj.save(by="Tester")
    loaded_obj = MockDatapoint(TestID=1, db=test_db)
    loaded_obj.load()
    assert loaded_obj.Value == "Test"
    assert loaded_obj.Other == pytest.approx(3.14)
    assert loaded_obj.UpdatedBy == "Tester"

def test_datapoint_overload(test_db):
    obj = MockDatapoint(TestID=2, Value="Test2", Other=1.0, db=test_db, migrate=True)
    obj.save()
    overload_obj = MockDatapoint(TestID=2, Value="NewValue", db=test_db)
    overload_obj.overload()
    assert overload_obj.Value == "Test2"
    assert overload_obj.Other == 1.0

def test_assigning_a_field_never_writes_to_the_database(test_db):
    obj = MockDatapoint(TestID=3, Value="Initial", db=test_db, migrate=True)
    obj.save()
    obj.Value = "Assigned"
    check_obj = MockDatapoint(TestID=3, db=test_db)
    check_obj.load()
    assert check_obj.Value == "Initial"

@dataclass
class QuietDatapoint(MockDatapoint):

    Table = "QuietDatapoint"

def test_autosave_writes_every_public_assignment(test_db):
    obj = MockDatapoint(TestID=7, Value="First", db=test_db, migrate=True, autosave=True)
    obj.Value = "Second"
    loaded = MockDatapoint(TestID=7, db=test_db, autoload=True)
    assert loaded.Value == "Second" and loaded.UpdatedBy == "Autosave"

def test_autosave_is_armed_only_on_the_class_that_asks(test_db):
    from Library.Market.Tick import TickAPI
    MockDatapoint(TestID=8, db=test_db, migrate=True, autosave=True)
    assert MockDatapoint.__setattr__ is DatapointAPI._autosaving_
    assert QuietDatapoint.__setattr__ is DatapointAPI._autosaving_
    assert TickAPI.__setattr__ is object.__setattr__ and DatapointAPI.__setattr__ is object.__setattr__

def test_an_armed_class_saves_only_the_instances_that_asked(test_db, monkeypatch):
    MockDatapoint(TestID=9, db=test_db, migrate=True, autosave=True)
    writes = []
    monkeypatch.setattr(MockDatapoint, "_execute_", lambda self, by: writes.append(self.TestID))
    silent = MockDatapoint(TestID=10, db=test_db)
    silent.Value = "Unsaved"
    armed = MockDatapoint(TestID=11, db=test_db, autosave=True)
    armed.Value = "Saved"
    armed.save(by="Tester")
    assert writes == [11, 11]

def test_loading_an_armed_instance_writes_nothing(test_db, monkeypatch):
    MockDatapoint(TestID=12, Value="Stored", db=test_db, migrate=True).save(by="Tester")
    writes = []
    monkeypatch.setattr(MockDatapoint, "_execute_", lambda self, by: writes.append(self.TestID))
    loaded = MockDatapoint(TestID=12, db=test_db, autoload=True, autosave=True)
    assert loaded.Value == "Stored" and writes == []