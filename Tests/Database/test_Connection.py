import pytest
import threading

from Library.Database.Postgres import PostgresDatabaseAPI

class MockCursor:

    def __init__(self, connection) -> None:
        self.connection = connection
        self.closed = False

    def close(self) -> None:
        self.closed = True

class MockConnection:

    def __init__(self, serial) -> None:
        self.serial = serial
        self.autocommit = True
        self.closed = False
        self.cursors = []

    def cursor(self) -> MockCursor:
        cursor = MockCursor(self)
        self.cursors.append(cursor)
        return cursor

    def close(self) -> None:
        self.closed = True

@pytest.fixture
def dialed(monkeypatch):
    opened = []
    def driver(self, admin: bool = False):
        connection = MockConnection(len(opened))
        opened.append(connection)
        return connection
    monkeypatch.setattr(PostgresDatabaseAPI, "_driver_", driver)
    return opened

def origin(**kwargs):
    db = PostgresDatabaseAPI(database="Quant", **kwargs)
    db.connect()
    return db

def descend(db, **kwargs):
    clone = db.clone(database=db._database_, schema="Market", table="Tick", admin=db._admin_, **kwargs)
    clone.connect()
    return clone

def test_scope_clone_borrows_the_connection(dialed):
    db = origin()
    clone = descend(db)
    assert len(dialed) == 1
    assert clone._connection_ is db._connection_
    assert clone._borrowed_ is True

def test_scope_clone_keeps_its_own_cursor(dialed):
    db = origin()
    clone = descend(db)
    assert clone._cursor_ is not db._cursor_

def test_another_database_dials_out(dialed):
    db = origin()
    clone = db.clone(database="Other", schema="Market", table="Tick", admin=False)
    clone.connect()
    assert len(dialed) == 2
    assert clone._borrowed_ is False

def test_admin_never_borrows(dialed):
    db = origin()
    clone = db.clone(database="Quant", schema="Market", table="Tick", admin=True)
    clone.connect()
    assert len(dialed) == 2
    assert clone._borrowed_ is False

def test_explicit_admin_connect_never_borrows(dialed):
    db = origin()
    clone = db.clone(database="Quant", schema="Market", table="Tick", admin=False)
    clone.connect(admin=True)
    assert len(dialed) == 2
    assert clone._borrowed_ is False

def test_transactional_connection_never_borrows(dialed):
    db = origin(autocommit=False)
    clone = descend(db)
    assert len(dialed) == 2
    assert clone._borrowed_ is False

def test_disconnected_origin_is_not_borrowed_from(dialed):
    db = origin()
    clone = db.clone(database="Quant", schema="Market", table="Tick", admin=False)
    db.disconnect()
    clone.connect()
    assert clone._borrowed_ is False
    assert clone._connection_ is not None

def test_borrowed_clone_leaves_the_connection_open(dialed):
    db = origin()
    clone = descend(db)
    clone.disconnect()
    assert dialed[0].closed is False
    assert db.connected() is True

def test_borrowed_clone_closes_its_own_cursor(dialed):
    db = origin()
    clone = descend(db)
    cursor = clone._cursor_
    clone.disconnect()
    assert cursor.closed is True

def test_origin_closes_the_connection_once(dialed):
    db = origin()
    descend(db)
    db.disconnect()
    assert dialed[0].closed is True
    assert len(dialed) == 1

def test_owned_connection_still_closes(dialed):
    db = origin()
    clone = db.clone(database="Other", schema="Market", table="Tick", admin=False)
    clone.connect()
    clone.disconnect()
    assert dialed[1].closed is True
    assert dialed[0].closed is False

def test_scope_binds_one_connection(dialed):
    with PostgresDatabaseAPI.scope(database="Quant"):
        for _ in range(5):
            with PostgresDatabaseAPI.attach(database="Quant") as db: db.executeone
    assert len(dialed) == 1

def test_scope_is_lazy(dialed):
    with PostgresDatabaseAPI.scope(database="Quant"): pass
    assert len(dialed) == 0

def test_scope_releases_on_exit(dialed):
    with PostgresDatabaseAPI.scope(database="Quant"):
        with PostgresDatabaseAPI.attach(database="Quant"): pass
    assert dialed[0].closed is True

def test_scope_releases_when_the_block_raises(dialed):
    with pytest.raises(RuntimeError):
        with PostgresDatabaseAPI.scope(database="Quant"):
            with PostgresDatabaseAPI.attach(database="Quant"): pass
            raise RuntimeError("boom")
    assert dialed[0].closed is True

def test_attach_without_a_scope_opens_its_own(dialed):
    for _ in range(3):
        with PostgresDatabaseAPI.attach(database="Quant"): pass
    assert len(dialed) == 3
    assert all(connection.closed for connection in dialed)

def test_scope_does_not_serve_another_database(dialed):
    with PostgresDatabaseAPI.scope(database="Quant"):
        with PostgresDatabaseAPI.attach(database="Quant"): pass
        with PostgresDatabaseAPI.attach(database="Other"): pass
    assert len(dialed) == 2

def test_nested_scopes_restore_the_outer_binding(dialed):
    with PostgresDatabaseAPI.scope(database="Quant"):
        with PostgresDatabaseAPI.attach(database="Quant") as outer: first = outer
        with PostgresDatabaseAPI.scope(database="Quant"):
            with PostgresDatabaseAPI.attach(database="Quant") as inner: assert inner is not first
        with PostgresDatabaseAPI.attach(database="Quant") as again: assert again is first
    assert len(dialed) == 2

def test_scope_does_not_leak_across_threads(dialed):
    seen = []
    def worker():
        with PostgresDatabaseAPI.attach(database="Quant") as db: seen.append(db)
    with PostgresDatabaseAPI.scope(database="Quant"):
        with PostgresDatabaseAPI.attach(database="Quant") as mine:
            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()
            assert seen[0] is not mine
    assert len(dialed) == 2