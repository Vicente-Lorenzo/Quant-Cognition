from datetime import datetime, timedelta
from typing import ClassVar, Union
from dataclasses import dataclass

import pytest

from Library.Database import BufferAPI
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI

SCHEMA = "BufferTest"

@dataclass
class _ParentAPI_(DatapointAPI):

    Schema: ClassVar[str] = SCHEMA
    Table: ClassVar[str] = "Parent"

    UID: Union[int, None] = None
    Value: Union[float, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.Int64),
            self.ID.Value: pl.Float64(),
            **super().Structure
        }

@dataclass
class _ChildAPI_(DatapointAPI):

    Schema: ClassVar[str] = SCHEMA
    Table: ClassVar[str] = "Child"

    Timestamp: Union[datetime, None] = None
    First: Union[_ParentAPI_, None] = None
    Last: Union[_ParentAPI_, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.Timestamp: PrimaryKey(pl.Datetime),
            self.ID.First: ForeignKey(pl.Int64, reference=_ParentAPI_.reference()),
            self.ID.Last: ForeignKey(pl.Int64, reference=_ParentAPI_.reference()),
            **super().Structure
        }

@pytest.fixture
def tables(db):
    db.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))
    db.executeone(QueryAPI(f'CREATE SCHEMA "{SCHEMA}"'))
    _ParentAPI_(db=db, migrate=True)
    _ChildAPI_(db=db, migrate=True)
    yield db
    db.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE'))

def _family_(at: datetime, base: int) -> tuple[list, _ChildAPI_]:
    parents = [_ParentAPI_(UID=base + index, Value=1.1 + index / 1000) for index in range(5)]
    return parents, _ChildAPI_(Timestamp=at, First=parents[0], Last=parents[-1])

def _child_(db, at: datetime) -> dict:
    row = db.select(schema=SCHEMA, table=_ChildAPI_.Table, condition='"Timestamp" = :at:', parameters={"at": at}, limit=1, legacy=False)
    assert not row.is_empty()
    return row.row(0, named=True)

def _count_(db, table: str) -> int:
    return db.executeone(QueryAPI(f'SELECT count(*) AS n FROM "{SCHEMA}"."{table}"')).fetchall(legacy=False).row(0, named=True)["n"]

def test_buffer_writes_parents_before_the_child_that_references_them(tables):
    at = datetime(2025, 1, 1, 12)
    parents, child = _family_(at, 100)
    buf = BufferAPI(types=[_ParentAPI_, _ChildAPI_], batch=10, interval=0.0, workers=1, db=lambda: tables)
    for parent in parents: buf.add(parent)
    buf.add(child)
    buf.flush()
    buf._consume_(tables)
    persisted = _child_(tables, at)
    assert (persisted["First"], persisted["Last"]) == (100, 104)

def test_buffer_keeps_every_child_with_its_own_parents(tables):
    base = datetime(2025, 2, 1, 12)
    families = [_family_(base + timedelta(minutes=index), 200 + 10 * index) for index in range(3)]
    buf = BufferAPI(types=[_ParentAPI_, _ChildAPI_], batch=100, interval=0.0, workers=1, db=lambda: tables)
    for parents, _ in families:
        for parent in parents: buf.add(parent)
    for _, child in families: buf.add(child)
    buf.flush()
    buf._consume_(tables)
    for index in range(3):
        persisted = _child_(tables, base + timedelta(minutes=index))
        assert (persisted["First"], persisted["Last"]) == (200 + 10 * index, 204 + 10 * index)

class _RaceInjector_:

    def __init__(self, inner, buf, parents, child):
        self._inner_ = inner
        self._buf_ = buf
        self._parents_ = parents
        self._child_ = child
        self._injected_ = False

    def __getattr__(self, name):
        return getattr(self._inner_, name)

    def merge(self, **kwargs):
        result = self._inner_.merge(**kwargs)
        if not self._injected_ and kwargs.get("table") == _ParentAPI_.Table:
            self._injected_ = True
            self._buf_._queue_[_ParentAPI_].put(list(self._parents_))
            self._buf_._queue_[_ChildAPI_].put([self._child_])
        return result

def test_buffer_never_drains_a_child_before_its_parents(tables):
    a, b = datetime(2025, 4, 1, 12), datetime(2025, 4, 1, 12, 1)
    parents_a, child_a = _family_(a, 300)
    parents_b, child_b = _family_(b, 400)
    buf = BufferAPI(types=[_ParentAPI_, _ChildAPI_], batch=1000, interval=0.0, workers=1, bulk=True, db=lambda: tables)
    for parent in parents_a: buf.add(parent)
    buf.add(child_a)
    buf.flush()
    race = _RaceInjector_(tables, buf, parents_b, child_b)
    buf._consume_(race)
    buf._consume_(race)
    assert _count_(tables, _ChildAPI_.Table) == 2
    _child_(tables, a)
    _child_(tables, b)

def test_bulk_merge_is_idempotent(tables):
    at = datetime(2025, 3, 1, 12)
    parents, child = _family_(at, 500)
    for _ in range(2):
        buf = BufferAPI(types=[_ParentAPI_, _ChildAPI_], batch=10, interval=0.0, workers=1, bulk=True, db=lambda: tables)
        for parent in parents: buf.add(parent)
        buf.add(child)
        buf.flush()
        buf._consume_(tables)
    assert _count_(tables, _ParentAPI_.Table) == 5
    persisted = _child_(tables, at)
    assert (persisted["First"], persisted["Last"]) == (500, 504)