import pytest

from datetime import datetime

import Script.Setup.Timezone as Timezone
from Library.Database.Query import QueryAPI
from Library.Utility.IO import read_json, write_json
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI

DATABASE = "Tests"
SCHEMA = "TimezoneMigration"

def _stamp_(table):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        return conn.first(schema=SCHEMA, table=table)["Stamp"]

@pytest.fixture
def migration(tmp_path, monkeypatch):
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database=DATABASE): admin.create(database=DATABASE)
    finally:
        admin.disconnect()
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        conn.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
        conn.executeone(QueryAPI(f'CREATE SCHEMA "{SCHEMA}"'))
        conn.executeone(QueryAPI(f'CREATE TABLE "{SCHEMA}"."Clean" ("Stamp" TIMESTAMP)'))
        conn.executeone(QueryAPI(f'CREATE TABLE "{SCHEMA}"."Strict" ("Stamp" TIMESTAMP CHECK ("Stamp" >= make_timestamp(2026, 7, 1, 0, 0, 0)))'))
        conn.executeone(QueryAPI(f'INSERT INTO "{SCHEMA}"."Clean" VALUES (make_timestamp(2026, 7, 1, 12, 0, 0))'))
        conn.executeone(QueryAPI(f'INSERT INTO "{SCHEMA}"."Strict" VALUES (make_timestamp(2026, 7, 1, 0, 30, 0))'))
    monkeypatch.setattr(Timezone, "MARKER", tmp_path / "timezone-utc.json")
    yield Timezone.MARKER
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        conn.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))

def test_a_dry_run_writes_nothing(migration, monkeypatch):
    monkeypatch.setattr(Timezone, "COLUMNS", {(SCHEMA, "Clean"): ("Stamp",)})
    assert Timezone.main(database=DATABASE) == 0
    assert _stamp_("Clean") == datetime(2026, 7, 1, 12)
    assert not migration.exists()

def test_apply_converts_every_planned_column_and_marks_it(migration, monkeypatch):
    monkeypatch.setattr(Timezone, "COLUMNS", {(SCHEMA, "Clean"): ("Stamp",), (SCHEMA, "Absent"): ("Stamp",)})
    assert Timezone.main(database=DATABASE, apply=True) == 0
    assert _stamp_("Clean") == datetime(2026, 7, 1, 11)
    assert {key: read_json(migration)[key] for key in ("Columns", "Rows", "Zone")} == {"Columns": 1, "Rows": 1, "Zone": "Europe/London"}

def test_a_failing_column_rolls_back_every_column_and_marks_nothing(migration, monkeypatch):
    monkeypatch.setattr(Timezone, "COLUMNS", {(SCHEMA, "Clean"): ("Stamp",), (SCHEMA, "Strict"): ("Stamp",)})
    assert Timezone.main(database=DATABASE, apply=True) == 1
    assert (_stamp_("Clean"), _stamp_("Strict")) == (datetime(2026, 7, 1, 12), datetime(2026, 7, 1, 0, 30))
    assert not migration.exists()

def test_an_applied_migration_is_refused_unless_forced(migration, monkeypatch):
    monkeypatch.setattr(Timezone, "COLUMNS", {(SCHEMA, "Clean"): ("Stamp",)})
    write_json(migration, {"Applied": "2026-09-16 01:09:07"})
    assert Timezone.main(database=DATABASE, apply=True) == 1
    assert _stamp_("Clean") == datetime(2026, 7, 1, 12)
    assert Timezone.main(database=DATABASE, apply=True, force=True) == 0
    assert _stamp_("Clean") == datetime(2026, 7, 1, 11)