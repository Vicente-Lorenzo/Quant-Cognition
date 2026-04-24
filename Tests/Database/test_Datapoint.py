import pytest
from datetime import datetime
from dataclasses import dataclass
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI

@dataclass
class MockDatapoint(DatapointAPI):
    Database = DatapointAPI.Database
    Schema = "TestSchema"
    Table = "MockDatapoint"

    TestID: int | None = None
    Value: str | None = None
    Other: float | None = None

    @property
    def Key(self) -> dict:
        return {self.ID.TestID: PrimaryKey(pl.Int64)}

    @property
    def Columns(self) -> dict:
        return {
            self.ID.Value: pl.String(),
            self.ID.Other: pl.Float64(),
            **super().Columns
        }

    def __post_init__(self, db, migrate, autosave, autoload, autooverload):
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

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
    assert loaded_obj.CreatedBy == "Tester"

def test_datapoint_overload(test_db):
    obj = MockDatapoint(TestID=2, Value="Test2", Other=1.0, db=test_db, migrate=True)
    obj.save(by="Tester")
    
    overload_obj = MockDatapoint(TestID=2, Value="NewValue", db=test_db)
    overload_obj.overload()
    
    assert overload_obj.Value == "Test2"
    assert overload_obj.Other == 1.0

def test_datapoint_autosave(test_db):
    obj = MockDatapoint(TestID=3, Value="Initial", db=test_db, migrate=True, autosave=True)
    obj.save(by="Tester")
    
    obj.Value = "Autosaved"
    
    check_obj = MockDatapoint(TestID=3, db=test_db)
    check_obj.load()
    
    assert check_obj.Value == "Autosaved"
