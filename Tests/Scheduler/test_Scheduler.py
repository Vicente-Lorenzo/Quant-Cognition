import pytest

from datetime import datetime, timedelta

from Library.Auth import UserAPI
from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, RunAPI, TaskType, TaskKind, RunStatus, RunEvent, ExecutorAPI, CoordinatorAPI, ManagerAPI, SchedulerAPI
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

def runs_of(*tids):
    tokens = ", ".join(f":t{index}:" for index in range(len(tids)))
    parameters = {f"t{index}": tid for index, tid in enumerate(tids)}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        frame = conn.select(schema="Scheduler", table="Run", condition=f'"TID" IN ({tokens})', parameters=parameters, legacy=False)
    return {row["TID"]: row for row in frame.to_dicts()}

class SyncSchedulerAPI(SchedulerAPI):

    def _spawn_(self, tid, workflow_run=None, attempt=1):
        with PostgresDatabaseAPI(database=self._database_) as conn:
            task = TaskAPI(UID=tid, db=conn, autoload=True)
            task._db_ = None
        ExecutorAPI(database=self._database_).run(task, workflow_run=workflow_run, attempt=attempt)
        return None

class RecordingSchedulerAPI(SchedulerAPI):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned = []

    @staticmethod
    def _terminate_(handle):
        return None

    def _spawn_(self, tid, workflow_run=None, attempt=1):
        self.spawned.append((tid, workflow_run))
        return None

@pytest.fixture(scope="module")
def scheduler():
    for cls in (UserAPI, WorkflowAPI, TaskAPI, DependencyAPI, RunAPI):
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
        run = db.select(schema="Scheduler", table="Run", limit=0, legacy=False)
    assert {"UID", "Name", "Owner", "Enabled"}.issubset(set(workflow.columns))
    assert {"UID", "Name", "Owner", "WID", "Kind", "Type", "Path", "Schedule", "RequiresApproval", "RequiresReview"}.issubset(set(task.columns))
    assert {"WID", "Predecessor", "Successor"}.issubset(set(dependency.columns))
    assert {"UID", "TID", "WorkflowRun", "Status", "Duration", "Memory", "ExitCode", "Approver"}.issubset(set(run.columns))

def test_administrator_survives(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as db:
        rows = db.select(schema="Auth", table="User", condition='"UID" = :uid:', parameters={"uid": "owner"}, legacy=False)
    assert rows.height == 1
    assert rows.row(0, named=True)["Role"] == "Administrator"

def test_execute_success(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-ok", Name="Ok", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    run = ExecutorAPI(database=DATABASE).run(task)
    assert run.Status == RunStatus.Success.name
    assert run.ExitCode == 0
    assert run.Duration is not None and run.Duration > 0
    assert run.Memory is not None and run.Memory > 0
    with PostgresDatabaseAPI(database=DATABASE) as db:
        rows = db.select(schema="Scheduler", table="Run", condition='"UID" = :uid:', parameters={"uid": run.UID}, legacy=False)
    assert rows.height == 1 and rows.row(0, named=True)["Status"] == RunStatus.Success.name

def test_execute_failure(scheduler, tmp_path):
    script = tmp_path / "bad.py"
    script.write_text("import sys\nsys.exit(3)\n")
    task = TaskAPI(UID="task-bad", Name="Bad", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    run = ExecutorAPI(database=DATABASE).run(task)
    assert run.Status == RunStatus.Failure.name
    assert run.ExitCode == 3

def test_runner_load_roundtrip(scheduler, tmp_path):
    script = tmp_path / "loaded.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-loaded", Name="Loaded", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    loaded = load(DATABASE, "task-loaded")
    assert isinstance(loaded.Type, str)
    run = ExecutorAPI(database=DATABASE).run(loaded)
    assert run.Status == RunStatus.Success.name and run.ExitCode == 0

def test_execute_approval_gate(scheduler, tmp_path):
    script = tmp_path / "gate.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-gate", Name="Gate", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=True, RequiresReview=False)
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
    assert CoordinatorAPI.eligible(nodes, edges, {"A": "Failure"}) == []
    assert CoordinatorAPI.eligible(nodes, edges, {"A": "Success", "B": "Success", "C": "Success"}) == ["D"]

def test_cycle_detection_on_link(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-cyc", Name="Cyc", Owner="owner", Enabled=True, db=conn).save(by="Test")
        for tid in ("cyc-a", "cyc-b"):
            TaskAPI(UID=tid, Name=tid, Owner="owner", WID="wf-cyc", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        first = CoordinatorAPI.link(conn, "wf-cyc", "cyc-a", "cyc-b")
        second = CoordinatorAPI.link(conn, "wf-cyc", "cyc-b", "cyc-a")
        edges = CoordinatorAPI.edges(conn, "wf-cyc")
    assert first is not None
    assert second is None
    assert edges == [("cyc-a", "cyc-b")]

def test_gate_accept_reject(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="gate-task", Name="Gate", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
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
    statuses = {row["UID"]: (row["Status"], row["Approver"]) for row in results}
    assert statuses["gate-approve"] == ("Success", "owner")
    assert statuses["gate-review"] == ("Failure", "owner")
    assert statuses["gate-done"][0] == "Success"

def test_reaper_marks_terminal(scheduler):
    stale = datetime.now() - timedelta(minutes=10)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="r-fail", Name="RFail", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, RequiresReview=False, db=conn).save(by="Test")
        TaskAPI(UID="r-review", Name="RReview", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, RequiresReview=True, db=conn).save(by="Test")
        RunAPI(UID="orphan-fail", TID="r-fail", Status="Running", Attempt=1, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
        RunAPI(UID="orphan-review", TID="r-review", Status="Running", Attempt=1, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
        RunAPI(UID="orphan-fresh", TID="r-fail", Status="Running", Attempt=1, StartedAt=datetime.now(), Heartbeat=datetime.now(), db=conn).save(by="Test")
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
        TaskAPI(UID="r-retry", Name="RRetry", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, MaxAttempts=3, RetryDelay=600, db=conn).save(by="Test")
        RunAPI(UID="orphan-retry", TID="r-retry", Status="Running", Attempt=1, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SchedulerAPI(database=DATABASE)._reap_(conn, datetime.now())
        row = conn.select(schema="Scheduler", table="Run", condition='"UID" = :uid:', parameters={"uid": "orphan-retry"}, legacy=False).row(0, named=True)
    assert row["Status"] == RunStatus.Retrying.name

def test_retry_exhaustion(scheduler, tmp_path):
    script = tmp_path / "crash.py"
    script.write_text("import sys\nsys.exit(1)\n")
    task = TaskAPI(UID="task-retry", Name="Retry", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, RequiresReview=False, MaxAttempts=2, RetryDelay=0)
    persist(task)
    first = ExecutorAPI(database=DATABASE).run(task, attempt=1)
    assert first.Status == RunStatus.Retrying.name and first.Attempt == 1
    second = ExecutorAPI(database=DATABASE).run(task, attempt=2)
    assert second.Status == RunStatus.Failure.name and second.Attempt == 2

def test_retry_dispatch(scheduler, tmp_path):
    script = tmp_path / "crash2.py"
    script.write_text("import sys\nsys.exit(1)\n")
    task = TaskAPI(UID="task-redispatch", Name="Redispatch", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, MaxAttempts=3, RetryDelay=0)
    persist(task)
    ExecutorAPI(database=DATABASE).run(task, attempt=1)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SyncSchedulerAPI(database=DATABASE)._retry_(conn, datetime.now(), 8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        rows = conn.select(schema="Scheduler", table="Run", condition='"TID" = :tid:', parameters={"tid": "task-redispatch"}, legacy=False).to_dicts()
    assert sorted(row["Attempt"] for row in rows) == [1, 2]
    assert all(row["Status"] == RunStatus.Retrying.name for row in rows)

def test_workflow_chain_executes(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-chain", Name="Chain", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        for tid in ("c-a", "c-b", "c-c"):
            TaskAPI(UID=tid, Name=tid, Owner="owner", WID="wf-chain", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-chain", "c-a", "c-b")
        CoordinatorAPI.link(conn, "wf-chain", "c-b", "c-c")
    sched = SyncSchedulerAPI(database=DATABASE, concurrency=8)
    for _ in range(4):
        sched._tick_()
    result = runs_of("c-a", "c-b", "c-c")
    assert {tid: row["Status"] for tid, row in result.items()} == {"c-a": "Success", "c-b": "Success", "c-c": "Success"}
    assert len({row["WorkflowRun"] for row in result.values()}) == 1

def test_approval_blocks_downstream(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-gate", Name="Gate", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="g-a", Name="A", Owner="owner", WID="wf-gate", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=True, db=conn).save(by="Test")
        TaskAPI(UID="g-b", Name="B", Owner="owner", WID="wf-gate", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-gate", "g-a", "g-b")
    sched = SyncSchedulerAPI(database=DATABASE, concurrency=8)
    sched._tick_()
    blocked = runs_of("g-a", "g-b")
    assert blocked["g-a"]["Status"] == RunStatus.Approving.name
    assert "g-b" not in blocked
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID=blocked["g-a"]["UID"], db=conn, autoload=True).accept("owner")
    sched._tick_()
    resolved = runs_of("g-a", "g-b")
    assert resolved["g-a"]["Status"] == RunStatus.Success.name
    assert resolved["g-b"]["Status"] == RunStatus.Success.name

def test_manual_workflow_advances(scheduler, tmp_path):
    script = tmp_path / "ok.py"
    script.write_text("import sys\nsys.exit(0)\n")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-manual", Name="Manual", Owner="owner", Enabled=True, db=conn).save(by="Test")
        for tid in ("man-a", "man-b", "man-c"):
            TaskAPI(UID=tid, Name=tid, Owner="owner", WID="wf-manual", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-manual", "man-a", "man-b")
        CoordinatorAPI.link(conn, "wf-manual", "man-b", "man-c")
        task = TaskAPI(UID="man-a", db=conn, autoload=True)
    task._db_ = None
    ExecutorAPI(database=DATABASE).run(task, workflow_run="manual0000")
    sched = SyncSchedulerAPI(database=DATABASE, concurrency=8)
    for _ in range(4):
        sched._tick_()
    result = runs_of("man-a", "man-b", "man-c")
    assert {tid: row["Status"] for tid, row in result.items()} == {"man-a": "Success", "man-b": "Success", "man-c": "Success"}
    assert {row["WorkflowRun"] for row in result.values()} == {"manual0000"}

def test_manager_task_crud(scheduler, tmp_path):
    manager = ManagerAPI(database=DATABASE)
    script = tmp_path / "m.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = manager.create_task(UID="m-task", Name="M", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True, Schedule="0 0 * * *")
    assert task.UID == "m-task"
    assert manager.task("m-task")["Name"] == "M"
    assert manager.update_task("m-task", Name="M2", RetryDelay=120) is not None
    row = manager.task("m-task")
    assert row["Name"] == "M2" and row["RetryDelay"] == 120 and row["Schedule"] == "0 0 * * *"
    assert manager.disable_task("m-task") and manager.task("m-task")["Enabled"] is False
    assert manager.enable_task("m-task") and manager.task("m-task")["Enabled"] is True
    assert any(item["UID"] == "m-task" for item in manager.tasks())
    assert manager.delete_task("m-task") is True
    assert manager.task("m-task") is None
    assert manager.delete_task("m-task") is False

def test_manager_workflow_and_link(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_workflow(UID="m-wf", Name="MWF", Owner="owner", Schedule="0 0 1 1 *", Enabled=True)
    assert manager.workflow("m-wf")["Name"] == "MWF"
    for tid in ("m-a", "m-b"):
        manager.create_task(UID=tid, Name=tid, Owner="owner", WID="m-wf", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True)
    assert manager.link("m-wf", "m-a", "m-b") is not None
    assert manager.link("m-wf", "m-b", "m-a") is None
    deps = manager.dependencies("m-wf")
    assert len(deps) == 1 and deps[0]["Predecessor"] == "m-a" and deps[0]["Successor"] == "m-b"
    assert manager.delete_workflow("m-wf") is True
    assert manager.workflow("m-wf") is None
    assert manager.task("m-a")["WID"] is None
    manager.delete_task("m-a")
    manager.delete_task("m-b")

def test_manager_approve_reject(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_task(UID="m-gate", Name="MGate", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True)
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
    manager.create_task(UID="m-run", Name="MRun", Owner="owner", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path=str(script), Enabled=True)
    run = manager.run_task("m-run", wait=True)
    assert run is not None and run.Status == RunStatus.Success.name
    assert manager.run_task("missing", wait=True) is None

def test_paused_governs_services(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-env", Name="Env", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="env-update", Name="Update", Owner="owner", WID="wf-env", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="env-server", Name="Server", Owner="owner", WID="wf-env", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="env-run", TID="env-update", WorkflowRun="wr-env", Status="Running", db=conn).save(by="Test")
    sched = SchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert "wf-env" in sched._paused_(conn, sched._tasks_(conn))
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="env-run", db=conn, autoload=True)
        run.Status = "Success"
        run.save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert "wf-env" not in sched._paused_(conn, sched._tasks_(conn))

def test_service_supervises_and_pauses(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-svc2", Name="Svc2", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc2-update", Name="Update", Owner="owner", WID="wf-svc2", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc2-server", Name="Server", Owner="owner", WID="wf-svc2", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
    active = RecordingSchedulerAPI(database=DATABASE)
    suspended = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in active._tasks_(conn) if task["WID"] == "wf-svc2"]
        active._service_(conn, members, set())
        suspended._service_(conn, members, {"wf-svc2"})
    assert ("svc2-server", None) in active.spawned
    assert "svc2-update" not in [tid for tid, _ in active.spawned]
    assert suspended.spawned == []

def test_advance_skips_service_roots(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-svcroot", Name="SvcRoot", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="root-server", Name="Server", Owner="owner", WID="wf-svcroot", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="root-update", Name="Update", Owner="owner", WID="wf-svcroot", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-svcroot"]
        sched._advance_(conn, {"Name": "SvcRoot", "Schedule": "0 0 1 1 *"}, members, [], datetime.now(), 8)
    tids = [tid for tid, _ in sched.spawned]
    assert "root-update" in tids and "root-server" not in tids

class FakeHandle:

    @staticmethod
    def poll():
        return None

def test_boot_launch_fires_once(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-boot", Name="Boot", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="boot-update", Name="Update", Owner="owner", WID="wf-boot", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="boot-server", Name="Server", Owner="owner", WID="wf-boot", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-boot", "boot-update", "boot-server")
        RunAPI(UID="boot-old", TID="boot-update", WorkflowRun="wr-boot-old", Status="Success", StartedAt=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    sched._launch_ = {"wf-boot"}
    workflow = {"UID": "wf-boot", "Name": "Boot", "Schedule": "0 0 1 1 *"}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-boot"]
        edges = CoordinatorAPI.edges(conn, "wf-boot")
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
        sched._advance_(conn, workflow, members, edges, datetime.now(), 8)
    assert [tid for tid, _ in sched.spawned] == ["boot-update"]
    assert sched.spawned[0][1] != "wr-boot-old"
    assert sched._launch_ == set()

def test_service_orders_after_maintenance(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-ord", Name="Ord", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ord-update", Name="Update", Owner="owner", WID="wf-ord", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ord-tunnel", Name="Tunnel", Owner="owner", WID="wf-ord", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="ord-server", Name="Server", Owner="owner", WID="wf-ord", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-ord", "ord-update", "ord-tunnel")
        CoordinatorAPI.link(conn, "wf-ord", "ord-tunnel", "ord-server")
        RunAPI(UID="ord-stale", TID="ord-update", WorkflowRun="wr-ord-old", Status="Success", StartedAt=early, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-ord"]
        sched._service_(conn, members, set())
        assert sched.spawned == []
        RunAPI(UID="ord-fresh", TID="ord-update", WorkflowRun="wr-ord-new", Status="Success", StartedAt=datetime.now(), db=conn).save(by="Test")
        sched._service_(conn, members, set())
        assert [tid for tid, _ in sched.spawned] == ["ord-tunnel"]
        sched._services_["ord-tunnel"] = FakeHandle()
        sched._service_(conn, members, set())
    assert [tid for tid, _ in sched.spawned] == ["ord-tunnel", "ord-server"]

def test_advance_latest_attempt_governs(scheduler):
    early = datetime.now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-attempt", Name="Attempt", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="att-a", Name="A", Owner="owner", WID="wf-attempt", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, MaxAttempts=2, db=conn).save(by="Test")
        TaskAPI(UID="att-b", Name="B", Owner="owner", WID="wf-attempt", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-attempt", "att-a", "att-b")
        RunAPI(UID="att-run-1", TID="att-a", WorkflowRun="wr-att", Status="Retrying", Attempt=1, StartedAt=early, db=conn).save(by="Test")
        RunAPI(UID="att-run-2", TID="att-a", WorkflowRun="wr-att", Status="Success", Attempt=2, StartedAt=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-attempt"]
        edges = CoordinatorAPI.edges(conn, "wf-attempt")
        sched._advance_(conn, {"Name": "Attempt", "Schedule": "0 0 1 1 *"}, members, edges, datetime.now(), 8)
    assert ("att-b", "wr-att") in sched.spawned

def test_advance_skips_downstream_services(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-svc", Name="Svc", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc-update", Name="Update", Owner="owner", WID="wf-svc", Type=TaskType.Python, Kind=TaskKind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="svc-server", Name="Server", Owner="owner", WID="wf-svc", Type=TaskType.Python, Kind=TaskKind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-svc", "svc-update", "svc-server")
        RunAPI(UID="svc-update-run", TID="svc-update", WorkflowRun="wr-svc", Status="Success", StartedAt=datetime.now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-svc"]
        edges = CoordinatorAPI.edges(conn, "wf-svc")
        sched._advance_(conn, {"Name": "Svc", "Schedule": "0 0 1 1 *"}, members, edges, datetime.now(), 8)
    assert "svc-server" in CoordinatorAPI.eligible(["svc-update", "svc-server"], edges, {"svc-update": "Success"})
    assert "svc-server" not in [tid for tid, _ in sched.spawned]