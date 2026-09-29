import sys
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Datetime import utc_now
from Library.Utility.Path import inspect_persistent
from Library.Utility.IO import read_json, write_json
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Database import PostgresDatabaseAPI
from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI
from Script.Install import GUARD, OWNER, WORKFLOWS

MARKER = inspect_persistent("Migrations") / "workflows-split.json"
RENAMES = {
    "Environment.Version": "Web.Version",
    "Environment.Tunnel": "Web.Tunnel",
    "Environment.Server": "Web.Server",
    "Environment.Credential": "Data.Credential",
    "Market.Calendar": "Data.Calendar"
}
RETIRED = {"Market": "Data"}

def _declared_() -> tuple:
    return {workflow["uid"]: workflow for workflow in WORKFLOWS}, {task["uid"]: task for workflow in WORKFLOWS for task in workflow["tasks"]}

def _plan_(db) -> list:
    plan = []
    for old, new in RENAMES.items():
        if db.first(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"UID" = :uid:', parameters={"uid": old}) is None: continue
        runs = db.select(schema=RunAPI.Schema, table=RunAPI.Table, columns=["UID"], condition='"TID" = :tid:', parameters={"tid": old}, legacy=False).height
        plan.append((old, new, runs))
    return plan

def _apply_(database: str, plan: list) -> None:
    workflows, tasks = _declared_()
    with PostgresDatabaseAPI(database=database) as db:
        for uid in sorted({new.split(".")[0] for _, new, _ in plan}):
            if db.first(schema=WorkflowAPI.Schema, table=WorkflowAPI.Table, condition='"UID" = :uid:', parameters={"uid": uid}) is not None: continue
            workflow = workflows[uid]
            WorkflowAPI(UID=uid, Name=workflow["name"], Owner=OWNER, RunRole=GUARD, EditRole=GUARD, Kind=workflow["kind"].name, Description=workflow["description"], Schedule=workflow["schedule"], Enabled=True, Waits=True, db=db).save(by="Migration")
        for old, new, _ in plan:
            row = db.first(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"UID" = :uid:', parameters={"uid": old})
            fields = {key: value for key, value in row.items() if key not in ("UpdatedAt", "UpdatedBy")}
            if db.first(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"UID" = :uid:', parameters={"uid": new}) is None: TaskAPI(**{**fields, "UID": new, "WID": new.split(".")[0], "Path": tasks[new]["path"], "Name": tasks[new]["name"], "Description": tasks[new]["description"]}, db=db).save(by="Migration")
            db.update(schema=RunAPI.Schema, table=RunAPI.Table, data={"TID": new}, condition='"TID" = :old:', parameters={"old": old})
            db.remove(schema=DependencyAPI.Schema, table=DependencyAPI.Table, condition='"Predecessor" = :old: OR "Successor" = :old:', parameters={"old": old})
            db.remove(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"UID" = :old:', parameters={"old": old})
        for retired, heir in RETIRED.items():
            if db.first(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"WID" = :wid:', parameters={"wid": retired}) is not None: continue
            db.update(schema=CycleAPI.Schema, table=CycleAPI.Table, data={"WID": heir}, condition='"WID" = :wid:', parameters={"wid": retired})
            db.remove(schema=DependencyAPI.Schema, table=DependencyAPI.Table, condition='"WID" = :wid:', parameters={"wid": retired})
            db.remove(schema=WorkflowAPI.Schema, table=WorkflowAPI.Table, condition='"UID" = :wid:', parameters={"wid": retired})

def main(database: str = "Quant", apply: bool = False, force: bool = False) -> int:
    with LoggingAPI() as log:
        applied = read_json(MARKER).get("Applied")
        if apply and not force and applied:
            log.error(lambda: f"Workflows Migration: Refused · Already Applied {applied}")
            return 1
        with PostgresDatabaseAPI(database=database) as db: plan = _plan_(db)
        for old, new, runs in plan: log.info(lambda old=old, new=new, runs=runs: f"Workflows Task: {'Moving' if apply else 'Planned'} ({old}) → {new} · {runs} Runs")
        if not apply:
            log.info(lambda: f"Workflows Migration: Planned · {len(plan)} Tasks · Pass --apply to Write")
            return 0
        try: _apply_(database, plan)
        except Exception as error:
            log.failure(lambda error=error: f"Workflows Migration: Failed · Due to {error} · Rolled Back")
            return 1
        if database == "Quant": write_json(MARKER, {"Applied": str(utc_now()), "Database": database, "Tasks": len(plan)})
        log.info(lambda: f"Workflows Migration: Completed · {len(plan)} Tasks · {sum(runs for _, _, runs in plan)} Runs")
        return 0

if __name__ == "__main__":
    parser = ArgumentParser(prog="Workflows", description="Moves the web and data tasks out of Environment and Market into their own workflows, keeping every run")
    parser.add_argument("--database", default="Quant")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Debug)
    raise SystemExit(main(database=arguments.database, apply=arguments.apply, force=arguments.force))