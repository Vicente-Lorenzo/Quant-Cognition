from datetime import datetime

from Library.Database.Dataframe import pl
from Library.Logging.Log import LogAPI
from Setup.Scheduler import migrate_runs

class _RecordAPI_:

    UID = 7

    def __init__(self) -> None:
        self.stopped = None

    def stop(self, content, **kwargs) -> None:
        self.stopped = (content, kwargs)

class _DatabaseAPI_:

    def __init__(self, rows: list) -> None:
        self.rows, self.updates, self.commits = rows, [], 0

    def select(self, **kwargs):
        return pl.DataFrame(self.rows)

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)

    def commit(self) -> None:
        self.commits += 1

def test_migrate_runs_moves_a_legacy_log_file_into_a_log_record(tmp_path, monkeypatch):
    source = tmp_path / "Run.log"
    source.write_text("first\nsecond\n", encoding="utf-8")
    record, started = _RecordAPI_(), datetime(2026, 9, 1, 8, 0)
    monkeypatch.setattr(LogAPI, "start", classmethod(lambda cls, db, **kwargs: record))
    db = _DatabaseAPI_([{"UID": "run", "TID": "task", "Log": str(source), "StartedAt": started, "StoppedAt": started, "Status": "Success"}])
    assert migrate_runs(db) == 1
    assert record.stopped[0] == "first\nsecond\n" and record.stopped[1]["records"] == 2
    assert db.updates[0]["data"] == {"LID": 7} and db.commits == 1

def test_migrate_runs_skips_when_nothing_is_pending():
    assert migrate_runs(_DatabaseAPI_([])) == 0