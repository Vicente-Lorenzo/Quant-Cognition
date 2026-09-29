import pytest

import Script.Setup.Workflows as Workflows
from Library.Auth import UserAPI
from Library.Utility.Datetime import utc_now
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI, ManagerAPI, CoordinatorAPI, Kind, TaskType
from Script.Install import OWNER, register
from Script.Setup.Auth import setup_auth
from Script.Setup.Scheduler import setup_scheduler

DATABASE = "Tests"
LAYOUT = ("Environment", "Market", "Web", "Data")

def _clear_(db) -> None:
    tasks = db.select(schema=TaskAPI.Schema, table=TaskAPI.Table, columns=["UID"], condition='"WID" IN (\'Environment\', \'Market\', \'Web\', \'Data\')', legacy=False)["UID"].to_list()
    for uid in tasks + list(Workflows.RENAMES) + list(Workflows.RENAMES.values()):
        db.remove(schema=RunAPI.Schema, table=RunAPI.Table, condition='"TID" = :uid:', parameters={"uid": uid})
        db.remove(schema=DependencyAPI.Schema, table=DependencyAPI.Table, condition='"Predecessor" = :uid: OR "Successor" = :uid:', parameters={"uid": uid})
        db.remove(schema=TaskAPI.Schema, table=TaskAPI.Table, condition='"UID" = :uid:', parameters={"uid": uid})
    for uid in LAYOUT:
        db.remove(schema=CycleAPI.Schema, table=CycleAPI.Table, condition='"WID" = :uid:', parameters={"uid": uid})
        db.remove(schema=WorkflowAPI.Schema, table=WorkflowAPI.Table, condition='"UID" = :uid:', parameters={"uid": uid})

@pytest.fixture
def layout():
    with PostgresDatabaseAPI(database=DATABASE) as db:
        setup_auth(db)
        setup_scheduler(db)
        if db.first(schema=UserAPI.Schema, table=UserAPI.Table, condition='"UID" = :uid:', parameters={"uid": OWNER}) is None: UserAPI(UID=OWNER, Email=OWNER, Name="Administrator", Role="Administrator", Active=True, db=db).save(by="Test")
        _clear_(db)
        for uid, schedule in (("Environment", "0 4 * * *"), ("Market", "0 6 * * *")): WorkflowAPI(UID=uid, Name=uid, Owner=OWNER, Kind=Kind.Scheduled.name, Schedule=schedule, Enabled=True, Waits=True, db=db).save(by="Test")
        for uid, kind in (("Environment.Cache", Kind.Scheduled), ("Environment.Retention", Kind.Scheduled), ("Environment.Version", Kind.Scheduled), ("Environment.Update", Kind.Scheduled), ("Environment.Credential", Kind.Scheduled), ("Environment.Tunnel", Kind.Service), ("Environment.Server", Kind.Service), ("Market.Calendar", Kind.Scheduled)):
            TaskAPI(UID=uid, Name=uid, Owner=OWNER, WID=uid.split(".")[0], Type=TaskType.Python.name, Kind=kind.name, Path=f"Script/{uid.replace('.', '/')}.py", Enabled=True, Waits=True, Tolerates=True, MaxRetry=0, RetryDelay=15 if kind is Kind.Service else 0, db=db).save(by="Test")
        for predecessor, successor in (("Environment.Cache", "Environment.Retention"), ("Environment.Retention", "Environment.Version"), ("Environment.Version", "Environment.Update"), ("Environment.Update", "Environment.Credential"), ("Environment.Credential", "Environment.Tunnel"), ("Environment.Tunnel", "Environment.Server")): CoordinatorAPI.link(db, "Environment", predecessor, successor)
        CycleAPI(UID="market-cycle", WID="Market", Kind=Kind.Scheduled.name, Status="Success", StartedAt=utc_now(), StoppedAt=utc_now(), db=db).save(by="Test")
        RunAPI(UID="calendar-run", TID="Market.Calendar", CID="market-cycle", Status="Success", Retry=0, StartedAt=utc_now(), db=db).save(by="Test")
        RunAPI(UID="server-run", TID="Environment.Server", Status="Success", Retry=0, StartedAt=utc_now(), db=db).save(by="Test")
    yield
    with PostgresDatabaseAPI(database=DATABASE) as db: _clear_(db)

def test_the_split_moves_every_task_with_its_runs_and_retires_market(layout):
    with PostgresDatabaseAPI(database=DATABASE) as db: plan = Workflows._plan_(db)
    assert [(old, new) for old, new, _ in plan] == list(Workflows.RENAMES.items())
    Workflows._apply_(DATABASE, plan)
    manager = ManagerAPI(database=DATABASE)
    assert manager.task("Environment.Server") is None and manager.task("Market.Calendar") is None and manager.workflow("Market") is None
    assert manager.task("Web.Server")["WID"] == "Web" and manager.task("Web.Server")["Path"] == "Script/Web/Server.py"
    assert manager.task("Data.Calendar")["WID"] == "Data" and manager.task("Data.Calendar")["Path"] == "Script/Data/Calendar.py"
    assert manager.run("server-run")["TID"] == "Web.Server" and manager.run("calendar-run")["TID"] == "Data.Calendar"
    assert manager.cycle("market-cycle")["WID"] == "Data" and manager.workflow("Data")["Name"] == "Data Intelligence"
    with PostgresDatabaseAPI(database=DATABASE) as db: assert Workflows._plan_(db) == []

def test_registration_after_the_split_leaves_exactly_the_declared_layout(layout):
    with PostgresDatabaseAPI(database=DATABASE) as db: Workflows._apply_(DATABASE, Workflows._plan_(db))
    manager = ManagerAPI(database=DATABASE)
    register(manager)
    edges = {uid: sorted((row["Predecessor"], row["Successor"]) for row in manager.dependencies(uid)) for uid in ("Environment", "Web", "Data")}
    assert edges == {"Environment": [("Environment.Cache", "Environment.Retention"), ("Environment.Update", "Environment.Cache")], "Web": [("Web.Tunnel", "Web.Server"), ("Web.Version", "Web.Tunnel")], "Data": [("Data.Credential", "Data.Calendar"), ("Data.Credential", "Data.Universe"), ("Data.Market", "Data.Portfolio"), ("Data.Universe", "Data.Market")]}
    assert sorted(task["UID"] for task in manager.tasks(workflow="Environment")) == ["Environment.Cache", "Environment.Retention", "Environment.Update"]
    assert manager.workflow("Web")["Name"] == "Web Application" and manager.workflow("Web")["After"] is None