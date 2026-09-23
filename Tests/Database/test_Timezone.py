import pytest

from datetime import datetime

from Library.Database import PrimaryKey, QueryAPI
from Library.Database.Dataframe import pl
from Library.Database.Oracle import OracleDatabaseAPI
from Library.Database.Postgres import PostgresDatabaseAPI
from Library.Database.Microsoft import MicrosoftDatabaseAPI

@pytest.mark.parametrize("driver", (PostgresDatabaseAPI, MicrosoftDatabaseAPI, OracleDatabaseAPI))
def test_every_driver_declares_a_zoned_datetime_apart_from_a_naive_one(driver):
    zoned, naive = PrimaryKey(pl.Datetime(time_zone="UTC")), PrimaryKey(pl.Datetime())
    for mapping in (driver._CHECK_DATATYPE_MAPPING_, driver._CREATE_DATATYPE_MAPPING_):
        assert driver._mapped_(mapping, zoned) != driver._mapped_(mapping, naive)

def test_every_postgres_session_runs_in_utc(db):
    assert db.executeone(QueryAPI("SHOW TimeZone")).fetchall(legacy=False).item() == "UTC"

def test_a_zoned_datetime_declares_timestamptz_and_round_trips_as_naive_utc(db):
    structure = {"UID": PrimaryKey(pl.Int64), "Stamp": pl.Datetime(time_zone="UTC")}
    db.migrate(schema="Probe", table="Zoned", structure=structure)
    try:
        declared = db.executeone(QueryAPI("SELECT data_type FROM information_schema.columns WHERE table_schema = 'Probe' AND table_name = 'Zoned' AND column_name = 'Stamp'")).fetchall(legacy=False).item()
        assert declared == "timestamp with time zone"
        assert not db.diff(schema="Probe", table="Zoned", structure=structure)
        stamp = datetime(2016, 3, 27, 1, 30, 15, 250000)
        db.upsert(schema="Probe", table="Zoned", data={"UID": 1, "Stamp": stamp}, key=["UID"])
        loaded = db.executeone(QueryAPI('SELECT "Stamp" FROM "Probe"."Zoned"')).fetchall(legacy=False).item()
        assert loaded == stamp and loaded.tzinfo is None
        epoch = db.executeone(QueryAPI('SELECT EXTRACT(EPOCH FROM "Stamp") AS "Epoch" FROM "Probe"."Zoned"')).fetchall(legacy=False).item()
        assert float(epoch) == 1459042215.25
    finally:
        db.executeone(QueryAPI('DROP SCHEMA IF EXISTS "Probe" CASCADE'))