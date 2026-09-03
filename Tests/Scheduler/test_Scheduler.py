import time

import pytest

from datetime import datetime, timedelta

from Library.Auth import UserAPI
from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI, TaskType, Kind, RunStatus, RunEvent, ExecutorAPI, CoordinatorAPI, ManagerAPI, SchedulerAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Scheduler.Runner import load
from Setup.Auth import setup_auth
from Setup.Scheduler import setup_scheduler

DATABASE = "Tests"

def persist(obj):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        obj._db_ = conn
        obj.save(by="Test")
    obj._db_ = None

def opened(uid, wid, status="Running", kind="Scheduled", started=None):
    persist(CycleAPI(UID=uid, WID=wid, Kind=kind, Status=status, StartedAt=started or datetime.now()))

def runs_of(*tids):
    tokens = ", ".join(f":t{index}:" for index in range(len(tids)))
    parameters = {f"t{index}": tid for index, tid in enumerate(tids)}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        frame = conn.select(schema="Scheduler", table="Run", condition=f'"TID" IN ({tokens})', parameters=parameters, legacy=False)
    return {row["TID"]: row for row in frame.to_dicts()}

class SyncSchedulerAPI(SchedulerAPI):

    def _spawn_(self, tid, cycle=None, retry=0):
        with PostgresDatabaseAPI(database=self._database_) as conn:
            task = TaskAPI(UID=tid, db=conn, autoload=True)
            task._db_ = None
        ExecutorAPI(database=self._database_).run(task, cycle=cycle, retry=retry)
        return None

class RecordingSchedulerAPI(SchedulerAPI):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned = []

    @staticmethod
    def _terminate_(pid):
        return None

    def _spawn_(self, tid, cycle=None, retry=0):
        self.spawned.append((tid, cycle))
        return None

@pytest.fixture(scope="module")
def scheduler():
    for cls in (UserAPI, WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI):
        cls.Database = DATABASE
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database=DATABASE): admin.create(database=DATABASE)
    finally:
        admin.disconnect()
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        conn.executeone(QueryAPI('DROP SCHEMA IF EXISTS "Scheduler" CASCADE'))
        conn.executeone(QueryAPI('DROP SCHEMA IF EXISTS "Auth" CASCADE'))
        setup_auth(conn)
        UserAPI(UID="owner", Email="owner@test.com", Name="Administrator", Role="Administrator", Active=True, db=conn).save(by="Test")
        setup_scheduler(conn)
    return DATABASE

def test_run_machine():
    approve = RunAPI.machine()
    approve.perform(RunEvent.Start, None)
    approve.perform(RunEvent.Complete, None)
    assert approve.At.Name == RunStatus.Success.name
    crash = RunAPI.machine()
    crash.perform(RunEvent.Start, None)
    crash.perform(RunEvent.Fail, None)
    assert crash.At.Name == RunStatus.Failure.name
    gated = RunAPI.machine()
    gated.perform(RunEvent.Start, None)
    gated.perform(RunEvent.RequireApproval, None)
    assert gated.At.Name == RunStatus.Approving.name
    gated.perform(RunEvent.Reject, None)
    assert gated.At.Name == RunStatus.Failure.name
    review = RunAPI.machine()
    review.perform(RunEvent.Start, None)
    review.perform(RunEvent.RequireReview, None)
    review.perform(RunEvent.Accept, None)
    assert review.At.Name == RunStatus.Success.name

def test_auth_columns(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as db:
        user = db.select(schema="Auth", table="User", limit=0, legacy=False)
        team = db.select(schema="Auth", table="Team", limit=0, legacy=False)
        office = db.select(schema="Auth", table="Office", limit=0, legacy=False)
    assert {"Forename", "Middlename", "Surname", "Telephone", "Team", "Office"}.issubset(set(user.columns))
    assert {"UID", "Name", "Abbreviation", "Email"}.issubset(set(team.columns))
    assert {"UID", "Name", "Address", "ZipCode", "City", "Country", "Region"}.issubset(set(office.columns))

def test_scheduler_tables(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as db:
        workflow = db.select(schema="Scheduler", table="Workflow", limit=0, legacy=False)
        task = db.select(schema="Scheduler", table="Task", limit=0, legacy=False)
        dependency = db.select(schema="Scheduler", table="Dependency", limit=0, legacy=False)
        cycle = db.select(schema="Scheduler", table="Cycle", limit=0, legacy=False)
        run = db.select(schema="Scheduler", table="Run", limit=0, legacy=False)
    assert {"UID", "Enabled", "Schedule", "Waits", "Name", "Owner"}.issubset(set(workflow.columns))
    assert {"UID", "WID", "Enabled", "Schedule", "Kind", "Type", "Name", "Owner", "Path", "RequiresApproval", "RequiresReview", "MaxRetry", "RetryDelay", "Waits", "Tolerates"}.issubset(set(task.columns))
    assert {"WID", "Predecessor", "Successor"}.issubset(set(dependency.columns))
    assert {"UID", "WID", "Kind", "Status", "StartedAt", "StoppedAt"}.issubset(set(cycle.columns))
    assert {"UID", "CID", "TID", "Kind", "Status", "ExitCode", "Retry", "Duration", "Memory", "PID", "Auditor", "Log", "StartedAt", "StoppedAt", "Heartbeat"}.issubset(set(run.columns))

def test_administrator_survives(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as db:
        rows = db.select(schema="Auth", table="User", condition='"UID" = :uid:', parameters={"uid": "owner"}, legacy=False)
    assert rows.height == 1
    assert rows.row(0, named=True)["Role"] == "Administrator"

def test_execute_success(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-ok", Name="Ok", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    run = ExecutorAPI(database=DATABASE).run(task)
    assert run.Status == RunStatus.Success.name
    assert run.ExitCode == 0
    assert run.PID is not None
    assert run.Duration is not None and run.Duration > 0
    assert run.Memory is not None and run.Memory >= 0
    with PostgresDatabaseAPI(database=DATABASE) as db:
        rows = db.select(schema="Scheduler", table="Run", condition='"UID" = :uid:', parameters={"uid": run.UID}, legacy=False)
    assert rows.height == 1 and rows.row(0, named=True)["Status"] == RunStatus.Success.name

def test_execute_failure(scheduler, tmp_path):
    script = tmp_path / "bad.py"
    script.write_text("import sys\nsys.exit(3)\n")
    task = TaskAPI(UID="task-bad", Name="Bad", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    run = ExecutorAPI(database=DATABASE).run(task)
    assert run.Status == RunStatus.Failure.name
    assert run.ExitCode == 3

def test_runner_load_roundtrip(scheduler, tmp_path):
    script = tmp_path / "loaded.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-loaded", Name="Loaded", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    loaded = load(DATABASE, "task-loaded")
    assert isinstance(loaded.Type, str)
    run = ExecutorAPI(database=DATABASE).run(loaded)
    assert run.Status == RunStatus.Success.name and run.ExitCode == 0

def test_execute_approval_gate(scheduler, tmp_path):
    script = tmp_path / "gate.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-gate", Name="Gate", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=True, RequiresReview=False)
    persist(task)
    run = ExecutorAPI(database=DATABASE).run(task)
    assert run.Status == RunStatus.Approving.name
    assert run.ExitCode == 0

def test_coordinator_logic():
    nodes = ["A", "B", "C", "D"]
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")]
    assert CoordinatorAPI.acyclic(nodes, edges)
    assert not CoordinatorAPI.acyclic(nodes, edges + [("D", "A")])
    assert not CoordinatorAPI.acyclic(["A"], [("A", "A")])
    assert sorted(CoordinatorAPI.eligible(nodes, edges, {})) == ["A"]
    assert sorted(CoordinatorAPI.eligible(nodes, edges, {"A": "Success"})) == ["B", "C"]
    assert CoordinatorAPI.eligible(nodes, edges, {"A": "Approving"}) == []
    assert sorted(CoordinatorAPI.eligible(nodes, edges, {"A": "Failure"})) == ["B", "C"]
    assert CoordinatorAPI.eligible(nodes, edges, {"A": "Failure"}, tolerates={"B": False, "C": False}) == []
    assert CoordinatorAPI.eligible(nodes, edges, {"A": "Success", "B": "Success", "C": "Success"}) == ["D"]

def test_eligible_flag_matrix():
    nodes, edges = ["a", "b"], [("a", "b")]
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Failure"}) == ["b"]
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Failure"}, tolerates={"b": False}) == []
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Running"}) == []
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Success"}, tolerates={"b": False}) == ["b"]
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Running"}, waits={"b": False}) == ["b"]
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Failure"}, waits={"b": False}, tolerates={"b": False}) == []
    assert CoordinatorAPI.eligible(nodes, edges, {"a": "Failure"}, waits={"b": False}) == ["b"]
    assert CoordinatorAPI.eligible(nodes, edges, {}, waits={"b": False}) == ["a", "b"]

def test_fits():
    assert CoordinatorAPI.fits("0 8 * * *", "0 10 * * *")
    assert CoordinatorAPI.fits("0 8 * * *", "*/30 * * * *")
    assert not CoordinatorAPI.fits("0 8 * * *", "0 10 * * 3")
    assert not CoordinatorAPI.fits("0 4 * * 0", "0 6 1 * *")
    assert CoordinatorAPI.fits(None, "0 10 * * *")
    assert CoordinatorAPI.fits("0 8 * * *", None)

def test_cycle_detection_on_link(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-cyc", Name="Cyc", Owner="owner", Enabled=True, db=conn).save(by="Test")
        for tid in ("cyc-a", "cyc-b"):
            TaskAPI(UID=tid, Name=tid, Owner="owner", WID="wf-cyc", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        first = CoordinatorAPI.link(conn, "wf-cyc", "cyc-a", "cyc-b")
        second = CoordinatorAPI.link(conn, "wf-cyc", "cyc-b", "cyc-a")
        edges = CoordinatorAPI.edges(conn, "wf-cyc")
    assert first is not None
    assert second is None
    assert edges == [("cyc-a", "cyc-b")]

def test_gate_accept_reject(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="gate-task", Name="Gate", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="gate-approve", TID="gate-task", Status="Approving", db=conn).save(by="Test")
        RunAPI(UID="gate-review", TID="gate-task", Status="Reviewing", db=conn).save(by="Test")
        RunAPI(UID="gate-done", TID="gate-task", Status="Success", db=conn).save(by="Test")
        approve = RunAPI(UID="gate-approve", db=conn, autoload=True)
        assert approve.accept("owner") is True
        review = RunAPI(UID="gate-review", db=conn, autoload=True)
        assert review.reject("owner") is True
        done = RunAPI(UID="gate-done", db=conn, autoload=True)
        assert done.accept("owner") is False
        results = conn.select(schema="Scheduler", table="Run", condition='"UID" IN (:a:, :b:, :c:)', parameters={"a": "gate-approve", "b": "gate-review", "c": "gate-done"}, legacy=False).to_dicts()
    statuses = {row["UID"]: (row["Status"], row["Auditor"]) for row in results}
    assert statuses["gate-approve"] == ("Success", "owner")
    assert statuses["gate-review"] == ("Failure", "owner")
    assert statuses["gate-done"][0] == "Success"

def test_reaper_marks_terminal(scheduler):
    stale = datetime.now() - timedelta(minutes=10)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="r-fail", Name="RFail", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, RequiresReview=False, db=conn).save(by="Test")
        TaskAPI(UID="r-review", Name="RReview", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, RequiresReview=True, db=conn).save(by="Test")
        RunAPI(UID="orphan-fail", TID="r-fail", Status="Running", Retry=0, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
        RunAPI(UID="orphan-review", TID="r-review", Status="Running", Retry=0, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
        RunAPI(UID="orphan-fresh", TID="r-fail", Status="Running", Retry=0, StartedAt=datetime.now(), Heartbeat=datetime.now(), db=conn).save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SchedulerAPI(database=DATABASE)._reap_(conn, datetime.now())
        rows = conn.select(schema="Scheduler", table="Run", condition='"UID" IN (:a:, :b:, :c:)', parameters={"a": "orphan-fail", "b": "orphan-review", "c": "orphan-fresh"}, legacy=False).to_dicts()
    statuses = {row["UID"]: row["Status"] for row in rows}
    assert statuses["orphan-fail"] == RunStatus.Failure.name
    assert statuses["orphan-review"] == RunStatus.Reviewing.name
    assert statuses["orphan-fresh"] == RunStatus.Running.name

def test_reaper_retries_before_terminal(scheduler):
    stale = datetime.now() - timedelta(minutes=10)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="r-retry", Name="RRetry", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, MaxRetry=2, RetryDelay=600, db=conn).save(by="Test")
        RunAPI(UID="orphan-retry", TID="r-retry", Status="Running", Retry=0, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SchedulerAPI(database=DATABASE)._reap_(conn, datetime.now())
        row = conn.select(schema="Scheduler", table="Run", condition='"UID" = :uid:', parameters={"uid": "orphan-retry"}, legacy=False).row(0, named=True)
    assert row["Status"] == RunStatus.Retrying.name

def test_retry_exhaustion(scheduler, tmp_path):
    script = tmp_path / "crash.py"
    script.write_text("import sys\nsys.exit(1)\n")
    task = TaskAPI(UID="task-retry", Name="Retry", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresReview=False, MaxRetry=1, RetryDelay=0)
    persist(task)
    first = ExecutorAPI(database=DATABASE).run(task, retry=0)
    assert first.Status == RunStatus.Retrying.name and first.Retry == 0
    second = ExecutorAPI(database=DATABASE).run(task, retry=1)
    assert second.Status == RunStatus.Failure.name and second.Retry == 1

def test_retry_dispatch(scheduler, tmp_path):
    script = tmp_path / "crash2.py"
    script.write_text("import sys\nsys.exit(1)\n")
    task = TaskAPI(UID="task-redispatch", Name="Redispatch", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, MaxRetry=2, RetryDelay=0)
    persist(task)
    ExecutorAPI(database=DATABASE).run(task, retry=0)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SyncSchedulerAPI(database=DATABASE)._retry_(conn, datetime.now(), 8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        rows = conn.select(schema="Scheduler", table="Run", condition='"TID" = :tid:', parameters={"tid": "task-redispatch"}, legacy=False).to_dicts()
    assert sorted(row["Retry"] for row in rows) == [0, 1]
    assert all(row["Status"] == RunStatus.Retrying.name for row in rows)

def test_workflow_chain_executes(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-chain", Name="Chain", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        for tid in ("c-a", "c-b", "c-c"):
            TaskAPI(UID=tid, Name=tid, Owner="owner", WID="wf-chain", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-chain", "c-a", "c-b")
        CoordinatorAPI.link(conn, "wf-chain", "c-b", "c-c")
    sched = SyncSchedulerAPI(database=DATABASE, concurrency=8)
    for _ in range(4):
        sched._tick_()
    result = runs_of("c-a", "c-b", "c-c")
    assert {tid: row["Status"] for tid, row in result.items()} == {"c-a": "Success", "c-b": "Success", "c-c": "Success"}
    assert len({row["CID"] for row in result.values()}) == 1
    cycles = ManagerAPI(database=DATABASE).cycles(workflow="wf-chain")
    assert len(cycles) == 1 and cycles[0]["Status"] == RunStatus.Success.name and cycles[0]["StoppedAt"] is not None

def test_approval_blocks_downstream(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-gate", Name="Gate", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="g-a", Name="A", Owner="owner", WID="wf-gate", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=True, db=conn).save(by="Test")
        TaskAPI(UID="g-b", Name="B", Owner="owner", WID="wf-gate", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-gate", "g-a", "g-b")
    sched = SyncSchedulerAPI(database=DATABASE, concurrency=8)
    sched._tick_()
    blocked = runs_of("g-a", "g-b")
    assert blocked["g-a"]["Status"] == RunStatus.Approving.name
    assert "g-b" not in blocked
    cycles = ManagerAPI(database=DATABASE).cycles(workflow="wf-gate")
    assert cycles[0]["Status"] in (RunStatus.Approving.name, RunStatus.Running.name)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID=blocked["g-a"]["UID"], db=conn, autoload=True).accept("owner")
    sched._tick_()
    resolved = runs_of("g-a", "g-b")
    assert resolved["g-a"]["Status"] == RunStatus.Success.name
    assert resolved["g-b"]["Status"] == RunStatus.Success.name

def test_manual_cycle_advances(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-manual", Name="Manual", Owner="owner", Enabled=True, db=conn).save(by="Test")
        for tid in ("man-a", "man-b", "man-c"):
            TaskAPI(UID=tid, Name=tid, Owner="owner", WID="wf-manual", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-manual", "man-a", "man-b")
        CoordinatorAPI.link(conn, "wf-manual", "man-b", "man-c")
        task = TaskAPI(UID="man-a", db=conn, autoload=True)
    task._db_ = None
    opened("manual0000", "wf-manual", kind="Manual")
    ExecutorAPI(database=DATABASE).run(task, cycle="manual0000")
    sched = SyncSchedulerAPI(database=DATABASE, concurrency=8)
    for _ in range(4):
        sched._tick_()
    result = runs_of("man-a", "man-b", "man-c")
    assert {tid: row["Status"] for tid, row in result.items()} == {"man-a": "Success", "man-b": "Success", "man-c": "Success"}
    assert {row["CID"] for row in result.values()} == {"manual0000"}
    cycles = ManagerAPI(database=DATABASE).cycles(workflow="wf-manual")
    assert cycles[0]["Status"] == RunStatus.Success.name

def test_scheduleless_workflow_is_manual_only(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-idle", Name="Idle", Owner="owner", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="idle-a", Name="A", Owner="owner", WID="wf-idle", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Schedule="* * * * *", Enabled=True, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-idle", "Name": "Idle", "Schedule": None, "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-idle"]
        sched._advance_(conn, workflow, members, [], datetime.now(), 8)
    assert sched.spawned == []

def test_manager_task_crud(scheduler, tmp_path):
    manager = ManagerAPI(database=DATABASE)
    script = tmp_path / "m.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = manager.create_task(UID="m-task", Name="M", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, Schedule="0 0 * * *")
    assert task.UID == "m-task"
    assert manager.task("m-task")["Name"] == "M"
    assert manager.update_task("m-task", Name="M2", RetryDelay=120) is not None
    row = manager.task("m-task")
    assert row["Name"] == "M2" and row["RetryDelay"] == 120 and row["Schedule"] == "0 0 * * *"
    assert manager.disable_task("m-task") and manager.task("m-task")["Enabled"] is False
    assert manager.enable_task("m-task") and manager.task("m-task")["Enabled"] is True
    assert any(item["UID"] == "m-task" for item in manager.tasks())
    assert any(item["UID"] == "m-task" for item in manager.tasks(workflow=None))
    assert all(item["WID"] is None for item in manager.tasks(workflow=None))
    assert manager.delete_task("m-task") is True
    assert manager.task("m-task") is None
    assert manager.delete_task("m-task") is False

def test_manager_workflow_and_link(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_workflow(UID="m-wf", Name="MWF", Owner="owner", Schedule="0 0 1 1 *", Enabled=True)
    assert manager.workflow("m-wf")["Name"] == "MWF"
    for tid in ("m-a", "m-b"):
        manager.create_task(UID=tid, Name=tid, Owner="owner", WID="m-wf", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True)
    assert manager.link("m-wf", "m-a", "m-b") is not None
    assert manager.link("m-wf", "m-b", "m-a") is None
    deps = manager.dependencies("m-wf")
    assert len(deps) == 1 and deps[0]["Predecessor"] == "m-a" and deps[0]["Successor"] == "m-b"
    assert manager.delete_workflow("m-wf") is True
    assert manager.workflow("m-wf") is None
    assert manager.task("m-a")["WID"] is None
    manager.delete_task("m-a")
    manager.delete_task("m-b")

def test_manager_fitness_validation(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_workflow(UID="wf-fit", Name="Fit", Owner="owner", Schedule="0 8 * * *", Enabled=True)
    manager.create_task(UID="fit-ok", Name="Ok", Owner="owner", WID="wf-fit", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Schedule="0 10 * * *", Enabled=True)
    with pytest.raises(ValueError):
        manager.create_task(UID="fit-bad", Name="Bad", Owner="owner", WID="wf-fit", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Schedule="0 10 * * 3", Enabled=True)
    with pytest.raises(ValueError):
        manager.update_workflow("wf-fit", Schedule="0 */2 * * *")
    manager.delete_task("fit-ok")
    manager.delete_workflow("wf-fit")

def test_manager_approve_reject(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_task(UID="m-gate", Name="MGate", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="m-run-approve", TID="m-gate", Status="Approving", db=conn).save(by="Test")
        RunAPI(UID="m-run-review", TID="m-gate", Status="Reviewing", db=conn).save(by="Test")
    assert manager.approve("m-run-approve", "owner") is True
    assert manager.run("m-run-approve")["Status"] == RunStatus.Success.name
    assert manager.reject("m-run-review", "owner") is True
    assert manager.run("m-run-review")["Status"] == RunStatus.Failure.name
    assert manager.approve("m-run-approve", "owner") is False

def test_manager_run_task_wait(scheduler, tmp_path):
    manager = ManagerAPI(database=DATABASE)
    script = tmp_path / "w.py"
    script.write_text("import sys\nsys.exit(0)\n")
    manager.create_task(UID="m-run", Name="MRun", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True)
    run = manager.run_task("m-run", wait=True)
    assert run is not None and run.Status == RunStatus.Success.name
    assert manager.run_task("missing", wait=True) is None

def test_manager_skip_and_cancel(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_workflow(UID="wf-skip", Name="Skip", Owner="owner", Schedule="0 0 1 1 *", Enabled=True)
    manager.create_task(UID="sk-a", Name="A", Owner="owner", WID="wf-skip", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True)
    manager.create_task(UID="sk-gated", Name="Gated", Owner="owner", WID="wf-skip", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, RequiresApproval=True, RequiresReview=True)
    assert manager.skip("sk-a") is None
    opened("sk-cycle", "wf-skip", kind="Manual")
    passed = manager.skip("sk-a")
    assert passed is not None and passed.Status == RunStatus.Success.name and passed.CID == "sk-cycle" and passed.Kind == Kind.Manual.name
    failed = manager.skip("sk-a", failure=True)
    assert failed is not None and failed.Status == RunStatus.Failure.name
    gated = manager.skip("sk-gated")
    assert gated.Status == RunStatus.Approving.name
    reviewed = manager.skip("sk-gated", failure=True)
    assert reviewed.Status == RunStatus.Reviewing.name
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="cancel-run", TID="sk-a", CID="sk-cycle", Status="Running", Retry=0, StartedAt=datetime.now(), Heartbeat=datetime.now(), db=conn).save(by="Test")
        RunAPI(UID="cancel-bad", TID="sk-a", CID="sk-cycle", Status="Running", Retry=0, StartedAt=datetime.now(), Heartbeat=datetime.now(), db=conn).save(by="Test")
    assert manager.cancel("cancel-run", by="owner") is True
    assert manager.run("cancel-run")["Status"] == RunStatus.Success.name
    assert manager.run("cancel-run")["Kind"] == Kind.Manual.name
    assert manager.cancel("cancel-bad", failure=True, by="owner") is True
    assert manager.run("cancel-bad")["Status"] == RunStatus.Failure.name
    assert manager.cancel("cancel-run", by="owner") is False
    manager.create_task(UID="sk-svc", Name="Svc", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True)
    assert manager.skip("sk-svc") is None
    assert manager.run_task("sk-svc") is None

def test_manager_early_run_joins_cycle(scheduler, tmp_path):
    manager = ManagerAPI(database=DATABASE)
    script = tmp_path / "early.py"
    script.write_text("import sys\nsys.exit(0)\n")
    manager.create_workflow(UID="wf-early", Name="Early", Owner="owner", Schedule="0 0 1 1 *", Enabled=True)
    manager.create_task(UID="early-a", Name="A", Owner="owner", WID="wf-early", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Schedule="0 10 * * *", Enabled=True)
    opened("early-cycle", "wf-early")
    run = manager.run_task("early-a", wait=True)
    assert run.Status == RunStatus.Success.name
    assert run.CID == "early-cycle"
    assert run.Kind == Kind.Manual.name

def test_workflow_kind_validation(scheduler):
    manager = ManagerAPI(database=DATABASE)
    with pytest.raises(ValueError):
        manager.create_workflow(UID="wf-badkind", Name="Bad", Owner="owner", Kind=Kind.Scheduled, Enabled=True)
    with pytest.raises(ValueError):
        manager.create_workflow(UID="wf-badkind", Name="Bad", Owner="owner", Kind=Kind.Manual, Schedule="0 8 * * *", Enabled=True)
    manager.create_workflow(UID="wf-pure", Name="Pure", Owner="owner", Kind=Kind.Service, Enabled=True)
    with pytest.raises(ValueError):
        manager.create_task(UID="pure-bad", Name="Bad", Owner="owner", WID="wf-pure", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True)
    manager.create_task(UID="pure-ok", Name="Ok", Owner="owner", WID="wf-pure", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True)
    with pytest.raises(ValueError):
        manager.create_task(UID="lone-bad", Name="Bad", Owner="owner", Type=TaskType.Python, Kind=Kind.Manual, Path="x", Schedule="0 8 * * *", Enabled=True)
    manager.delete_task("pure-ok")
    manager.delete_workflow("wf-pure")

def test_service_workflow_resident_cycle(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-resident", Name="Resident", Owner="owner", Kind=Kind.Service, Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="res-server", Name="Server", Owner="owner", WID="wf-resident", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-resident", "Name": "Resident", "Schedule": None, "Kind": "Service", "Waits": None}
    manager = ManagerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-resident"]
        sched._advance_(conn, workflow, members, [], datetime.now(), 8)
        first = manager.cycles(workflow="wf-resident")
        sched._advance_(conn, workflow, members, [], datetime.now(), 8)
        second = manager.cycles(workflow="wf-resident")
    assert sched.spawned == []
    assert len(first) == 1 and first[0]["Status"] == RunStatus.Running.name and first[0]["Kind"] == Kind.Service.name
    assert len(second) == 1

def test_paused_governs_services(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-env", Name="Env", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="env-update", Name="Update", Owner="owner", WID="wf-env", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="env-server", Name="Server", Owner="owner", WID="wf-env", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="env-run", TID="env-update", Status="Running", db=conn).save(by="Test")
    sched = SchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert "wf-env" in sched._paused_(conn, sched._tasks_(conn))
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="env-run", db=conn, autoload=True)
        run.Status = "Approving"
        run.save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert "wf-env" not in sched._paused_(conn, sched._tasks_(conn))
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="env-run", db=conn, autoload=True)
        run.Status = "Success"
        run.save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert "wf-env" not in sched._paused_(conn, sched._tasks_(conn))

def test_service_supervises_and_pauses(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-svc2", Name="Svc2", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc2-update", Name="Update", Owner="owner", WID="wf-svc2", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc2-server", Name="Server", Owner="owner", WID="wf-svc2", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
    active = RecordingSchedulerAPI(database=DATABASE)
    suspended = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in active._tasks_(conn) if task["WID"] == "wf-svc2"]
        active._service_(conn, members, set(), datetime.now())
        suspended._service_(conn, members, {"wf-svc2"}, datetime.now())
    assert ("svc2-server", None) in active.spawned
    assert "svc2-update" not in [tid for tid, _ in active.spawned]
    assert suspended.spawned == []

class _Resident_:

    pid = 4242

    def poll(self):
        return None

def test_service_suspension_closes_the_run_as_success(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-susp", Name="Susp", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="susp-update", Name="Update", Owner="owner", WID="wf-susp", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="susp-tunnel", Name="Tunnel", Owner="owner", WID="wf-susp", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="susp-run", TID="susp-tunnel", Status="Running", Retry=0, PID=4242, StartedAt=datetime.now(), Heartbeat=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    sched._services_["susp-tunnel"] = _Resident_()
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-susp"]
        sched._service_(conn, members, {"wf-susp"}, datetime.now())
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="susp-run", db=conn, autoload=True)
    assert run.Status == RunStatus.Success.name
    assert run.StoppedAt is not None
    assert run.Duration is not None

def test_service_crash_is_not_laundered_into_success(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="susp-crash", Name="Crashed", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, RetryDelay=0, db=conn).save(by="Test")
        RunAPI(UID="susp-crash-run", TID="susp-crash", Status="Running", Retry=0, StartedAt=datetime.now(), Heartbeat=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["UID"] == "susp-crash"]
        sched._service_(conn, members, set(), datetime.now())
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="susp-crash-run", db=conn, autoload=True)
    assert run.Status == RunStatus.Running.name

def test_service_crash_cap(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="svc-flaky", Name="Flaky", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, MaxRetry=1, RetryDelay=0, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["UID"] == "svc-flaky"]
        now = datetime.now()
        sched._service_(conn, members, set(), now)
        sched._service_(conn, members, set(), now)
        sched._service_(conn, members, set(), now)
        sched._service_(conn, members, set(), now)
    assert len(sched.spawned) == 2
    assert sched._crashes_["svc-flaky"] > 1

def test_boot_launch_fires_once(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-boot", Name="Boot", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="boot-update", Name="Update", Owner="owner", WID="wf-boot", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="boot-server", Name="Server", Owner="owner", WID="wf-boot", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-boot", "boot-update", "boot-server")
    opened("boot-old", "wf-boot", status="Success")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    sched._launch_ = {"wf-boot"}
    workflow = {"UID": "wf-boot", "Name": "Boot", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-boot"]
        edges = CoordinatorAPI.edges(conn, "wf-boot")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert [tid for tid, _ in sched.spawned] == ["boot-update"]
    assert sched.spawned[0][1] != "boot-old"
    assert sched._launch_ == set()

def test_service_orders_after_maintenance(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-ord", Name="Ord", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ord-update", Name="Update", Owner="owner", WID="wf-ord", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ord-tunnel", Name="Tunnel", Owner="owner", WID="wf-ord", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ord-server", Name="Server", Owner="owner", WID="wf-ord", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-ord", "ord-update", "ord-tunnel")
        CoordinatorAPI.link(conn, "wf-ord", "ord-tunnel", "ord-server")
        RunAPI(UID="ord-stale", TID="ord-update", Status="Success", StartedAt=early, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-ord"]
        sched._service_(conn, members, set(), datetime.now())
        assert sched.spawned == []
        RunAPI(UID="ord-fresh", TID="ord-update", Status="Success", StartedAt=datetime.now(), db=conn).save(by="Test")
        sched._service_(conn, members, set(), datetime.now())
        assert [tid for tid, _ in sched.spawned] == ["ord-tunnel"]
        sched._services_["ord-tunnel"] = FakeHandle()
        sched._service_(conn, members, set(), datetime.now())
    assert [tid for tid, _ in sched.spawned] == ["ord-tunnel", "ord-server"]

def test_notify_wakes_listener(scheduler):
    sched = SchedulerAPI(database=DATABASE, interval=10)
    sched._listener_ = sched._listen_()
    assert sched._listener_ is not None
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="notify-task", Name="Notify", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    started = time.perf_counter()
    sched._wait_()
    assert time.perf_counter() - started < 5
    sched._listener_.disconnect()

class FakeHandle:

    @staticmethod
    def poll():
        return None

def test_advance_time_gate(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-gatetime", Name="GateTime", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="gt-a", Name="A", Owner="owner", WID="wf-gatetime", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="gt-b", Name="B", Owner="owner", WID="wf-gatetime", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Schedule="* * * * *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="gt-c", Name="C", Owner="owner", WID="wf-gatetime", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-gatetime", "gt-a", "gt-b")
        CoordinatorAPI.link(conn, "wf-gatetime", "gt-a", "gt-c")
    opened("wr-gt", "wf-gatetime", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="gt-run-a", TID="gt-a", CID="wr-gt", Status="Success", StartedAt=early, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-gatetime", "Name": "GateTime", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-gatetime"]
        edges = CoordinatorAPI.edges(conn, "wf-gatetime")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert sched.spawned == [("gt-b", "wr-gt")]

def test_advance_waits_false_fires_at_time(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-nowait", Name="NoWait", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="nw-a", Name="A", Owner="owner", WID="wf-nowait", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="nw-b", Name="B", Owner="owner", WID="wf-nowait", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Schedule="* * * * *", Waits=False, Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-nowait", "nw-a", "nw-b")
    opened("wr-nw", "wf-nowait", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="nw-run-a", TID="nw-a", CID="wr-nw", Status="Running", StartedAt=early, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-nowait", "Name": "NoWait", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-nowait"]
        edges = CoordinatorAPI.edges(conn, "wf-nowait")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert ("nw-b", "wr-nw") in sched.spawned

def test_advance_tolerates_governs_after_failure(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-anyres", Name="AnyRes", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ar-a", Name="A", Owner="owner", WID="wf-anyres", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ar-b", Name="B", Owner="owner", WID="wf-anyres", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ar-c", Name="C", Owner="owner", WID="wf-anyres", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Tolerates=False, Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-anyres", "ar-a", "ar-b")
        CoordinatorAPI.link(conn, "wf-anyres", "ar-a", "ar-c")
    opened("wr-ar", "wf-anyres", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="ar-run-a", TID="ar-a", CID="wr-ar", Status="Failure", StartedAt=early, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-anyres", "Name": "AnyRes", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-anyres"]
        edges = CoordinatorAPI.edges(conn, "wf-anyres")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert sched.spawned == [("ar-b", "wr-ar")]

def test_advance_latest_attempt_governs(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-attempt", Name="Attempt", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="att-a", Name="A", Owner="owner", WID="wf-attempt", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", MaxRetry=1, Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="att-b", Name="B", Owner="owner", WID="wf-attempt", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-attempt", "att-a", "att-b")
    opened("wr-att", "wf-attempt", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="att-run-1", TID="att-a", CID="wr-att", Status="Retrying", Retry=0, StartedAt=early, db=conn).save(by="Test")
        RunAPI(UID="att-run-2", TID="att-a", CID="wr-att", Status="Success", Retry=1, StartedAt=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-attempt", "Name": "Attempt", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-attempt"]
        edges = CoordinatorAPI.edges(conn, "wf-attempt")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert sched.spawned == [("att-b", "wr-att")]

def test_create_defaults(scheduler):
    manager = ManagerAPI(database=DATABASE)
    task = manager.create_task(UID="def-task", Name="Defaults", Owner="owner", Type=TaskType.Python.name, Path="x")
    row = manager.task("def-task")
    assert row["Enabled"] is True
    assert row["Kind"] == Kind.Scheduled.name
    assert row["Type"] == TaskType.Python.name
    assert row["RequiresApproval"] is False
    assert row["RequiresReview"] is False
    assert row["MaxRetry"] == 0
    assert row["RetryDelay"] == 0
    assert row["Waits"] is True
    assert row["Tolerates"] is True
    manual = manager.create_workflow(UID="def-manual", Name="Defaults", Owner="owner")
    scheduled = manager.create_workflow(UID="def-scheduled", Name="Defaults", Owner="owner", Schedule="0 0 1 1 *")
    assert manager.workflow("def-manual")["Kind"] == Kind.Manual.name
    assert manager.workflow("def-manual")["Waits"] is True
    assert manager.workflow("def-scheduled")["Kind"] == Kind.Scheduled.name
    manager.delete_task("def-task")
    manager.delete_workflow("def-manual")
    manager.delete_workflow("def-scheduled")

def test_latest(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    manager = ManagerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="lat-a", Name="A", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="lat-run-1", TID="lat-a", Status="Failure", StartedAt=early, db=conn).save(by="Test")
        RunAPI(UID="lat-run-2", TID="lat-a", Status="Success", StartedAt=datetime.now(), db=conn).save(by="Test")
    latest = manager.latest()
    assert latest["lat-a"] == "Success"

def test_workflow_reset_on_overrun(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-reset", Name="Reset", Owner="owner", Schedule="* * * * *", Waits=False, Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="rs-a", Name="A", Owner="owner", WID="wf-reset", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    opened("wr-rs", "wf-reset", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="rs-run-a", TID="rs-a", CID="wr-rs", Status="Running", Retry=0, StartedAt=early, Heartbeat=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-reset", "Name": "Reset", "Schedule": "* * * * *", "Kind": None, "Waits": False}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-reset"]
        sched._advance_(conn, workflow, members, [], datetime.now(), 8)
    manager = ManagerAPI(database=DATABASE)
    assert manager.run("rs-run-a")["Status"] == RunStatus.Failure.name
    assert manager.cycle("wr-rs")["Status"] == RunStatus.Failure.name
    assert len(sched.spawned) == 1 and sched.spawned[0][0] == "rs-a" and sched.spawned[0][1] != "wr-rs"

def test_advance_skips_service_roots(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-svcroot", Name="SvcRoot", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="root-server", Name="Server", Owner="owner", WID="wf-svcroot", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="root-update", Name="Update", Owner="owner", WID="wf-svcroot", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-svcroot", "Name": "SvcRoot", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-svcroot"]
        sched._advance_(conn, workflow, members, [], datetime.now(), 8)
    tids = [tid for tid, _ in sched.spawned]
    assert "root-update" in tids and "root-server" not in tids

def test_advance_skips_downstream_services(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-svc", Name="Svc", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc-update", Name="Update", Owner="owner", WID="wf-svc", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc-server", Name="Server", Owner="owner", WID="wf-svc", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-svc", "svc-update", "svc-server")
    opened("wr-svc", "wf-svc", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="svc-update-run", TID="svc-update", CID="wr-svc", Status="Success", StartedAt=early, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-svc", "Name": "Svc", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-svc"]
        edges = CoordinatorAPI.edges(conn, "wf-svc")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert "svc-server" in CoordinatorAPI.eligible(["svc-update", "svc-server"], edges, {"svc-update": "Success"})
    assert "svc-server" not in [tid for tid, _ in sched.spawned]