import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Scheduler.Workflow import WorkflowAPI
from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Dependency import DependencyAPI
from Library.Scheduler.Cycle import CycleAPI
from Library.Scheduler.Run import RunAPI
from Library.Scheduler.Scheduler import SchedulerAPI
from Library.Database import PostgresDatabaseAPI, QueryAPI
from Library.Logging import HandlerLoggingAPI
from Setup.Auth import setup_auth

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

def setup_scheduler(db):
    db.create(schema=WorkflowAPI.Schema)
    WorkflowAPI(db=db, migrate=True, autosave=False, autoload=False)
    TaskAPI(db=db, migrate=True, autosave=False, autoload=False)
    DependencyAPI(db=db, migrate=True, autosave=False, autoload=False)
    CycleAPI(db=db, migrate=True, autosave=False, autoload=False)
    RunAPI(db=db, migrate=True, autosave=False, autoload=False)
    setup_index(db)
    setup_notify(db)

def main(database="Quant"):
    with HandlerLoggingAPI(Class="Setup", Subclass="Scheduler") as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                setup_auth(db)
                setup_scheduler(db)
            log.info(lambda: "Scheduler Setup: Completed · Schema + 4 Tables")
            return 0
        except Exception as error:
            log.exception(lambda: f"Scheduler Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())