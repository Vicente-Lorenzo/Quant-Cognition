import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging.Log import LogAPI
from Library.Scheduler.Workflow import WorkflowAPI
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Dependency import DependencyAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Scheduler.Run import RunAPI
from Library.Scheduler.Scheduler import SchedulerAPI
from Library.Database import QueryAPI
from Library.Logging import LoggingAPI
from Library.Utility.IO import read_text
from Setup.Auth import setup_auth
from Setup.Logging import setup_logging
from Setup.Task import migrate, provision

def setup_notify(db):
    schema, channel = WorkflowAPI.Schema, SchedulerAPI.Channel
    db.executeone(QueryAPI(f'CREATE OR REPLACE FUNCTION "{schema}"."Notify"() RETURNS TRIGGER AS $$ BEGIN PERFORM pg_notify(\'{channel}\', \'\'); RETURN NULL; END $$ LANGUAGE plpgsql'))
    for table in (WorkflowAPI.Table, TaskAPI.Table, DependencyAPI.Table):
        db.executeone(QueryAPI(f'DROP TRIGGER IF EXISTS "Notify" ON "{schema}"."{table}"'))
        db.executeone(QueryAPI(f'CREATE TRIGGER "Notify" AFTER INSERT OR UPDATE OR DELETE ON "{schema}"."{table}" FOR EACH STATEMENT EXECUTE FUNCTION "{schema}"."Notify"()'))
    for table in (CycleAPI.Table, RunAPI.Table):
        db.executeone(QueryAPI(f'DROP TRIGGER IF EXISTS "Notify" ON "{schema}"."{table}"'))
        db.executeone(QueryAPI(f'CREATE TRIGGER "Notify" AFTER INSERT OR DELETE ON "{schema}"."{table}" FOR EACH STATEMENT EXECUTE FUNCTION "{schema}"."Notify"()'))
        db.executeone(QueryAPI(f'DROP TRIGGER IF EXISTS "NotifyStatus" ON "{schema}"."{table}"'))
        db.executeone(QueryAPI(f'CREATE TRIGGER "NotifyStatus" AFTER UPDATE ON "{schema}"."{table}" FOR EACH ROW WHEN (OLD."Status" IS DISTINCT FROM NEW."Status") EXECUTE FUNCTION "{schema}"."Notify"()'))

def setup_index(db):
    schema = WorkflowAPI.Schema
    db.executeone(QueryAPI(f'CREATE INDEX IF NOT EXISTS "Run_TID_StartedAt_idx" ON "{schema}"."{RunAPI.Table}" ("TID", "StartedAt" DESC)'))
    db.executeone(QueryAPI(f'CREATE INDEX IF NOT EXISTS "Run_CID_idx" ON "{schema}"."{RunAPI.Table}" ("CID")'))
    db.executeone(QueryAPI(f'CREATE INDEX IF NOT EXISTS "Run_Status_idx" ON "{schema}"."{RunAPI.Table}" ("Status")'))
    db.executeone(QueryAPI(f'CREATE INDEX IF NOT EXISTS "Cycle_WID_StartedAt_idx" ON "{schema}"."{CycleAPI.Table}" ("WID", "StartedAt" DESC)'))

def migrate_runs(db):
    schema, table = RunAPI.Schema, RunAPI.Table
    pending = db.select(schema=schema, table=table, columns=["UID", "TID", "Log", "StartedAt", "StoppedAt", "Status"], condition='"LID" IS NULL AND "Log" IS NOT NULL')
    if pending.is_empty(): return 0
    migrated = 0
    for row in pending.iter_rows(named=True):
        source = Path(row["Log"])
        if not source.is_file(): continue
        try: content = read_text(source, safe=False, errors="replace")
        except OSError: continue
        record = LogAPI.start(db, source=row["TID"], level=row["Status"], path=source, started=row["StartedAt"], by="Migration")
        record.stop(content, records=content.count("\n"), dropped=0, truncated=False, by="Migration", stopped=row["StoppedAt"])
        db.update(schema=schema, table=table, data={"LID": record.UID}, condition='"UID" = :uid:', parameters={"uid": row["UID"]})
        migrated += 1
    db.commit()
    return migrated

def setup_scheduler(db):
    setup_logging(db)
    db.create(schema=WorkflowAPI.Schema)
    migrate(db, WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI)
    setup_index(db)
    setup_notify(db)
    migrate_runs(db)

def setup_all(db):
    setup_auth(db)
    setup_scheduler(db)

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Scheduler", setup_all, database=database, detail="Schema + 4 Tables")

if __name__ == "__main__":
    raise SystemExit(main())