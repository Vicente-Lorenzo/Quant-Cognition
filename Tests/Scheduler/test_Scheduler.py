import sys
import time
import threading
from pathlib import Path

import pytest

from types import SimpleNamespace
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone

from Library.Utility.Datetime import utc_now, utc_to_local
from Library.Auth import UserAPI
from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI, TaskType, Kind, RunStatus, RunEvent, ExecutorAPI, CoordinatorAPI, ManagerAPI, SchedulerAPI
from Library.Scheduler.Main import SchedulerCommandAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Scheduler.Runner import RunnerCommandAPI
from Library.Scheduler.Tray import TrayAPI
from Script.Setup.Auth import setup_auth
from Script.Setup.Scheduler import setup_scheduler

DATABASE = "Tests"

def persist(obj):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        obj._db_ = conn
        obj.save(by="Test")
    obj._db_ = None

def opened(uid, wid, status="Running", kind="Scheduled", started=None):
    persist(CycleAPI(UID=uid, WID=wid, Kind=kind, Status=status, StartedAt=started or utc_now()))

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

def test_a_finished_run_still_shows_its_log(scheduler, tmp_path):
    script = tmp_path / "chatty.py"
    script.write_text("print('Chatty Output Line')\n")
    task = TaskAPI(UID="task-chatty", Name="Chatty", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    run = ExecutorAPI(database=DATABASE).run(task)
    assert not (ExecutorAPI.settle(run.UID) / ExecutorAPI.console()).exists()
    assert "Chatty Output Line" in ManagerAPI(database=DATABASE).log(run.UID)
    assert ManagerAPI(database=DATABASE).log("missing-run") is None

def test_runner_load_roundtrip(scheduler, tmp_path):
    script = tmp_path / "loaded.py"
    script.write_text("import sys\nsys.exit(0)\n")
    task = TaskAPI(UID="task-loaded", Name="Loaded", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    loaded = RunnerCommandAPI.load(DATABASE, "task-loaded")
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

def test_fits_accepts_a_zone():
    assert CoordinatorAPI.fits("0 8 * * *", "0 10 * * *", zone="Asia/Tokyo")
    assert not CoordinatorAPI.fits("0 8 * * *", "0 10 * * 3", zone="Asia/Tokyo")

def test_due_evaluates_the_cron_in_the_workflow_zone():
    last = datetime(2026, 7, 1, 13, 0, 1)
    assert not SchedulerAPI._due_("0 9 * * *", last, datetime(2026, 7, 2, 12, 59), "America/New_York")
    assert SchedulerAPI._due_("0 9 * * *", last, datetime(2026, 7, 2, 13, 0), "America/New_York")

def test_timely_gates_member_tasks_in_the_workflow_zone():
    opened = datetime(2026, 1, 15, 14)
    assert not SchedulerAPI._timely_("30 9 * * *", opened, datetime(2026, 1, 15, 14, 29), "America/New_York")
    assert SchedulerAPI._timely_("30 9 * * *", opened, datetime(2026, 1, 15, 14, 30), "America/New_York")

def test_reaping_waits_one_lease_after_the_daemon_was_suspended():
    sched = SchedulerAPI(database=DATABASE)
    slept = datetime(2026, 9, 16, 9, 53)
    assert not sched._suspended_(slept)
    assert not sched._suspended_(slept + timedelta(seconds=5))
    woke = slept + timedelta(hours=6)
    assert sched._suspended_(woke)
    assert sched._suspended_(woke + timedelta(seconds=30))
    assert sched._suspended_(woke + timedelta(seconds=60))
    assert not sched._suspended_(woke + timedelta(seconds=sched._lease_ + 1))

def test_reaping_waits_one_lease_after_ticks_went_unobserved():
    sched = SchedulerAPI(database=DATABASE)
    tick = datetime(2026, 9, 27, 4, 30, 30)
    assert not sched._suspended_(tick)
    assert not sched._suspended_(tick + timedelta(seconds=30))
    assert sched._suspended_(tick + timedelta(seconds=130))
    assert sched._suspended_(tick + timedelta(seconds=160))
    assert sched._suspended_(tick + timedelta(seconds=190))
    assert not sched._suspended_(tick + timedelta(seconds=130 + sched._lease_ + 1))

def test_a_long_polling_interval_is_not_mistaken_for_a_suspension():
    sched = SchedulerAPI(database=DATABASE, interval=90)
    tick = datetime(2026, 9, 16, 9, 53)
    assert not any(sched._suspended_(tick + timedelta(seconds=100 * step)) for step in range(10))
    assert sched._suspended_(tick + timedelta(seconds=900 + 90 + sched._lease_ + 1))

def test_manager_rejects_an_unknown_zone():
    with pytest.raises(ValueError, match="Unknown time zone"):
        ManagerAPI._zoned_("Mars/Olympus")
    for zone in (None, "", "Europe/London"): ManagerAPI._zoned_(zone)

def test_cli_carries_the_workflow_zone(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["Scheduler", "workflow", "update", "--uid", "wf-zone", "--zone", "Asia/Tokyo"])
    assert SchedulerCommandAPI._fields_(SchedulerCommandAPI().parse(), WorkflowAPI) == {"UID": "wf-zone", "Zone": "Asia/Tokyo"}
    monkeypatch.setattr(sys, "argv", ["Scheduler", "workflow", "create", "--uid", "wf-zone", "--name", "Zone", "--owner", "owner"])
    assert SchedulerCommandAPI._fields_(SchedulerCommandAPI().parse(), WorkflowAPI)["Zone"] is None

def test_cli_carries_the_workflow_upstream(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["Scheduler", "workflow", "update", "--uid", "Web", "--after", "Environment"])
    assert SchedulerCommandAPI._fields_(SchedulerCommandAPI().parse(), WorkflowAPI) == {"UID": "Web", "After": "Environment"}
    monkeypatch.setattr(sys, "argv", ["Scheduler", "workflow", "update", "--uid", "Web", "--after", ""])
    assert SchedulerCommandAPI._fields_(SchedulerCommandAPI().parse(), WorkflowAPI) == {"UID": "Web", "After": ""}
    monkeypatch.setattr(sys, "argv", ["Scheduler", "workflow", "create", "--uid", "Web", "--name", "Web", "--owner", "owner"])
    assert SchedulerCommandAPI._fields_(SchedulerCommandAPI().parse(), WorkflowAPI)["After"] is None

def _repeated_(zone):
    for minute in range(15, 36 * 60, 15):
        moment = datetime(2026, 10, 24, 12, tzinfo=timezone.utc) + timedelta(minutes=minute)
        before, after = (moment - timedelta(minutes=15)).astimezone(zone).utcoffset(), moment.astimezone(zone).utcoffset()
        if after < before: return moment.replace(tzinfo=None), before - after
    return None

def _fired_(schedule, zone, start, hours):
    last, fired = None, []
    for minute in range(0, hours * 60, 5):
        tick = start + timedelta(minutes=minute, seconds=5)
        if not SchedulerAPI._due_(schedule, last, tick, zone): continue
        last = SchedulerAPI._previous_(schedule, tick, zone)
        fired.append(last)
    return fired

@pytest.mark.parametrize("zone", ["Europe/London", None])
def test_due_does_not_refire_after_a_cycle_inside_a_repeated_hour(zone):
    repeated = _repeated_(ZoneInfo(zone) if zone else None)
    if repeated is None: pytest.skip("Zone repeats no hour around 2026-10-25")
    transition, width = repeated
    wall = utc_to_local(transition + width / 2, zone)
    schedule, last = f"{wall.minute} {wall.hour} * * *", transition + width / 6
    assert not any(SchedulerAPI._due_(schedule, last, last + timedelta(minutes=minute), zone) for minute in range(1, 12 * 60))
    assert SchedulerAPI._due_(schedule, last, transition + width + timedelta(days=1), zone)

@pytest.mark.parametrize("zone", ["Europe/London", None])
def test_a_daily_schedule_fires_once_per_local_day_across_both_transitions(zone):
    for start in (datetime(2026, 10, 24, 12), datetime(2026, 3, 28, 12)):
        fired = _fired_("30 1 * * *", zone, start, 48)
        assert len(fired) == 3 and fired == sorted(set(fired))
        assert len({utc_to_local(moment, zone).date() for moment in fired}) == 3

def test_a_daily_schedule_follows_london_across_both_transitions():
    assert _fired_("30 1 * * *", "Europe/London", datetime(2026, 10, 24, 12), 48) == [datetime(2026, 10, 24, 0, 30), datetime(2026, 10, 25, 0, 30), datetime(2026, 10, 26, 1, 30)]
    assert _fired_("30 1 * * *", "Europe/London", datetime(2026, 3, 28, 12), 48) == [datetime(2026, 3, 28, 1, 30), datetime(2026, 3, 29, 1, 30), datetime(2026, 3, 30, 0, 30)]

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
    stale = utc_now() - timedelta(minutes=10)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="r-fail", Name="RFail", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, RequiresReview=False, db=conn).save(by="Test")
        TaskAPI(UID="r-review", Name="RReview", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, RequiresReview=True, db=conn).save(by="Test")
        RunAPI(UID="orphan-fail", TID="r-fail", Status="Running", Retry=0, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
        RunAPI(UID="orphan-review", TID="r-review", Status="Running", Retry=0, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
        RunAPI(UID="orphan-fresh", TID="r-fail", Status="Running", Retry=0, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SchedulerAPI(database=DATABASE)._reap_(conn, utc_now())
        rows = conn.select(schema="Scheduler", table="Run", condition='"UID" IN (:a:, :b:, :c:)', parameters={"a": "orphan-fail", "b": "orphan-review", "c": "orphan-fresh"}, legacy=False).to_dicts()
    statuses = {row["UID"]: row["Status"] for row in rows}
    assert statuses["orphan-fail"] == RunStatus.Failure.name
    assert statuses["orphan-review"] == RunStatus.Reviewing.name
    assert statuses["orphan-fresh"] == RunStatus.Running.name

def test_reaper_retries_before_terminal(scheduler):
    stale = utc_now() - timedelta(minutes=10)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="r-retry", Name="RRetry", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, MaxRetry=2, RetryDelay=600, db=conn).save(by="Test")
        RunAPI(UID="orphan-retry", TID="r-retry", Status="Running", Retry=0, StartedAt=stale, Heartbeat=stale, db=conn).save(by="Test")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        SchedulerAPI(database=DATABASE)._reap_(conn, utc_now())
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
        SyncSchedulerAPI(database=DATABASE)._retry_(conn, utc_now(), 8)
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
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
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
    assert manager.approve("m-run-approve", by="owner") is True
    assert manager.run("m-run-approve")["Status"] == RunStatus.Success.name
    assert manager.reject("m-run-review", by="owner") is True
    assert manager.run("m-run-review")["Status"] == RunStatus.Failure.name
    assert manager.approve("m-run-approve", by="owner") is False

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
        RunAPI(UID="cancel-run", TID="sk-a", CID="sk-cycle", Status="Running", Retry=0, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
        RunAPI(UID="cancel-bad", TID="sk-a", CID="sk-cycle", Status="Running", Retry=0, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
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
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
        first = manager.cycles(workflow="wf-resident")
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
        second = manager.cycles(workflow="wf-resident")
    assert sched.spawned == []
    assert len(first) == 1 and first[0]["Status"] == RunStatus.Running.name and first[0]["Kind"] == Kind.Service.name
    assert len(second) == 1

def _chain_(uid: str) -> tuple:
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID=uid, Name=uid, Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID=f"{uid}-version", Name="Version", Owner="owner", WID=uid, Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID=f"{uid}-other", Name="Other", Owner="owner", WID=uid, Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID=f"{uid}-tunnel", Name="Tunnel", Owner="owner", WID=uid, Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID=f"{uid}-server", Name="Server", Owner="owner", WID=uid, Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, uid, f"{uid}-version", f"{uid}-tunnel")
        CoordinatorAPI.link(conn, uid, f"{uid}-tunnel", f"{uid}-server")
    opened(f"{uid}-cycle", uid)
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == uid]
    return sched, {task["UID"]: task for task in members}, {task["UID"]: Kind.parse(task["Kind"]) for task in members}

def test_a_service_awaits_only_its_own_ancestors_in_the_open_cycle(scheduler):
    sched, members, kinds = _chain_("wf-await")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert sched._awaited_(conn, members["wf-await-server"], kinds, {}) == "wf-await-version"
        persist(RunAPI(UID="await-other", TID="wf-await-other", CID="wf-await-cycle", Status="Running", StartedAt=utc_now()))
        persist(RunAPI(UID="await-version", TID="wf-await-version", CID="wf-await-cycle", Status="Running", StartedAt=utc_now()))
        assert sched._awaited_(conn, members["wf-await-tunnel"], kinds, {}) == "wf-await-version"
        persist(RunAPI(UID="await-version", TID="wf-await-version", CID="wf-await-cycle", Status="Approving", StartedAt=utc_now()))
        assert sched._awaited_(conn, members["wf-await-tunnel"], kinds, {}) is None
        persist(RunAPI(UID="await-version", TID="wf-await-version", CID="wf-await-cycle", Status="Success", StartedAt=utc_now()))
        assert sched._awaited_(conn, members["wf-await-server"], kinds, {}) is None

def test_a_service_starts_only_once_its_ancestors_ran_in_the_open_cycle(scheduler):
    sched, members, kinds = _chain_("wf-flap")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        sched._service_(conn, list(members.values()), utc_now())
        assert sched.spawned == []
        persist(RunAPI(UID="flap-version", TID="wf-flap-version", CID="wf-flap-cycle", Status="Success", StartedAt=utc_now()))
        sched._service_(conn, list(members.values()), utc_now())
        assert [tid for tid, _ in sched.spawned] == ["wf-flap-tunnel"]

class _Resident_:

    pid = 4242

    def poll(self):
        return None

def test_service_suspension_closes_the_run_as_success(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-susp", Name="Susp", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="susp-update", Name="Update", Owner="owner", WID="wf-susp", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="susp-tunnel", Name="Tunnel", Owner="owner", WID="wf-susp", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="susp-run", TID="susp-tunnel", Status="Running", Retry=0, PID=4242, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-susp", "susp-update", "susp-tunnel")
    opened("susp-cycle", "wf-susp")
    persist(RunAPI(UID="susp-update-run", TID="susp-update", CID="susp-cycle", Status="Running", StartedAt=utc_now()))
    sched = RecordingSchedulerAPI(database=DATABASE)
    sched._services_["susp-tunnel"] = _Resident_()
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-susp"]
        sched._service_(conn, members, utc_now())
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="susp-run", db=conn, autoload=True)
    assert run.Status == RunStatus.Success.name
    assert run.StoppedAt is not None
    assert run.Duration is not None

def test_service_crash_is_not_laundered_into_success(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="susp-crash", Name="Crashed", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, RetryDelay=0, db=conn).save(by="Test")
        RunAPI(UID="susp-crash-run", TID="susp-crash", Status="Running", Retry=0, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["UID"] == "susp-crash"]
        sched._service_(conn, members, utc_now())
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="susp-crash-run", db=conn, autoload=True)
    assert run.Status == RunStatus.Running.name

def test_service_crash_cap(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="svc-flaky", Name="Flaky", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, MaxRetry=1, RetryDelay=0, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["UID"] == "svc-flaky"]
        now = utc_now()
        sched._service_(conn, members, now)
        sched._service_(conn, members, now)
        sched._service_(conn, members, now)
        sched._service_(conn, members, now)
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
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
    assert [tid for tid, _ in sched.spawned] == ["boot-update"]
    assert sched.spawned[0][1] != "boot-old"
    assert sched._launch_ == set()

def test_boot_launch_continues_an_open_cycle_instead_of_opening_a_second(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-resume", Name="Resume", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="resume-update", Name="Update", Owner="owner", WID="wf-resume", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="resume-credential", Name="Credential", Owner="owner", WID="wf-resume", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-resume", "resume-update", "resume-credential")
    opened("resume-cycle", "wf-resume", started=utc_now() - timedelta(minutes=5))
    persist(RunAPI(UID="resume-update-run", TID="resume-update", CID="resume-cycle", Status="Success", StartedAt=utc_now() - timedelta(minutes=5), StoppedAt=utc_now()))
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    sched._launch_ = {"wf-resume"}
    workflow = {"UID": "wf-resume", "Name": "Resume", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-resume"]
        sched._advance_(conn, workflow, members, CoordinatorAPI.edges(conn, "wf-resume"), utc_now(), 8)
    assert sched.spawned == [("resume-credential", "resume-cycle")]
    assert sched._launch_ == set()

def test_stopping_the_scheduler_suspends_its_services_instead_of_failing_them(scheduler, monkeypatch):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="stop-svc", Name="Stopped", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, RetryDelay=0, db=conn).save(by="Test")
        RunAPI(UID="stop-svc-run", TID="stop-svc", Status="Running", Retry=0, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
    killed = []
    monkeypatch.setattr("Library.Scheduler.Scheduler.terminate", lambda pid: killed.append(pid))
    sched = SchedulerAPI(database=DATABASE)
    sched._services_ = {"stop-svc": SimpleNamespace(pid=4242, poll=lambda: None), "stop-gone": SimpleNamespace(pid=4343, poll=lambda: 1)}
    sched.stop()
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        run = RunAPI(UID="stop-svc-run", db=conn, autoload=True)
    assert killed == [4242] and sched._services_ == {}
    assert run.Status == RunStatus.Success.name and run.UpdatedBy == "Suspend"

def test_the_tray_restarts_through_the_launcher_on_the_base_interpreter(monkeypatch, tmp_path):
    base = tmp_path / "conda"
    (base / "condabin").mkdir(parents=True)
    monkeypatch.setattr(sys, "executable", str(base / "envs" / "Quant" / "pythonw.exe"))
    command = TrayAPI.launcher()
    assert command[0] == str(base / "pythonw.exe") and command[1].endswith(str(Path("Script") / "Scheduler.py"))

def _upstream_(uid: str, after: str, *, running: bool) -> dict:
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID=after, Name=after, Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        WorkflowAPI(UID=uid, Name=uid, Owner="owner", Schedule="0 0 1 1 *", After=after, Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID=f"{uid}-task", Name="Task", Owner="owner", WID=uid, Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    opened(f"{after}-cycle", after, status="Running" if running else "Success")
    return {"UID": uid, "Name": uid, "Schedule": "0 0 1 1 *", "After": after, "Kind": None, "Waits": None}

def test_a_workflow_waits_for_its_upstream_then_runs(scheduler):
    workflow = _upstream_("wf-after", "wf-before", running=True)
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    sched._launch_ = {"wf-after"}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-after"]
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
        waiting = sched._cycle_(conn, "wf-after")
        assert waiting["Status"] == RunStatus.Waiting.name and sched.spawned == []
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
        assert sched.spawned == [] and sched._cycle_(conn, "wf-after")["UID"] == waiting["UID"]
        sched._record_(conn, sched._cycle_(conn, "wf-before"), RunStatus.Success.name, utc_now(), "Test")
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
        released = sched._cycle_(conn, "wf-after")
    assert released["UID"] == waiting["UID"] and released["Status"] == RunStatus.Running.name
    assert sched.spawned == [("wf-after-task", waiting["UID"])]

def test_a_manual_run_waits_for_the_upstream_too(scheduler):
    _upstream_("wf-manual-after", "wf-manual-before", running=True)
    manager = ManagerAPI(database=DATABASE)
    spawned = []
    manager._spawn_ = lambda tid, **kwargs: spawned.append(tid)
    cid = manager.run_workflow("wf-manual-after")
    assert manager.cycle(cid)["Status"] == RunStatus.Waiting.name and spawned == []

def test_a_disabled_upstream_holds_nothing(scheduler):
    workflow = _upstream_("wf-free", "wf-idle", running=True)
    ManagerAPI(database=DATABASE).disable_workflow("wf-idle")
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert CoordinatorAPI.held(conn, workflow) is None

def test_after_refuses_itself_an_unknown_workflow_and_a_loop_and_clears_on_empty(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_workflow(UID="wf-a", Name="A", Owner="owner", Kind="Manual")
    manager.create_workflow(UID="wf-b", Name="B", Owner="owner", Kind="Manual", After="wf-a")
    with pytest.raises(ValueError, match="cannot run after itself"): manager.update_workflow("wf-a", After="wf-a")
    with pytest.raises(ValueError, match="Unknown workflow"): manager.update_workflow("wf-a", After="wf-nowhere")
    with pytest.raises(ValueError, match="a loop is refused"): manager.update_workflow("wf-a", After="wf-b")
    manager.update_workflow("wf-b", After="")
    assert manager.workflow("wf-b")["After"] is None

def test_deleting_an_upstream_frees_its_dependents(scheduler):
    manager = ManagerAPI(database=DATABASE)
    manager.create_workflow(UID="wf-gone", Name="Gone", Owner="owner", Kind="Manual")
    manager.create_workflow(UID="wf-left", Name="Left", Owner="owner", Kind="Manual", After="wf-gone")
    manager.delete_workflow("wf-gone")
    assert manager.workflow("wf-left")["After"] is None

def test_launch_brings_the_upstream_of_every_service_workflow(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-launch-env", Name="Env", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        WorkflowAPI(UID="wf-launch-web", Name="Web", Owner="owner", Schedule="0 0 1 1 *", After="wf-launch-env", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="launch-server", Name="Server", Owner="owner", WID="wf-launch-web", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert {"wf-launch-env", "wf-launch-web"} <= sched._launchable_(conn, sched._tasks_(conn))

def test_a_service_does_not_start_while_its_upstream_runs(scheduler):
    _upstream_("wf-held", "wf-holder", running=True)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="held-server", Name="Server", Owner="owner", WID="wf-held", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["UID"] == "held-server"]
        sched._service_(conn, members, utc_now())
        assert sched.spawned == []
        sched._record_(conn, sched._cycle_(conn, "wf-holder"), RunStatus.Success.name, utc_now(), "Test")
        sched._service_(conn, members, utc_now())
    assert sched.spawned == [("held-server", None)]

def test_a_predecessor_finished_in_the_workflows_latest_cycle_counts_after_a_restart(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-restart", Name="Restart", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="restart-version", Name="Version", Owner="owner", WID="wf-restart", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="restart-server", Name="Server", Owner="owner", WID="wf-restart", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-restart", "restart-version", "restart-server")
    before = utc_now() - timedelta(minutes=5)
    opened("restart-cycle", "wf-restart", status="Success", started=before)
    persist(RunAPI(UID="restart-version-run", TID="restart-version", CID="restart-cycle", Status="Success", StartedAt=before, StoppedAt=before))
    sched = RecordingSchedulerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-restart"]
        sched._service_(conn, members, utc_now())
    assert sched.spawned == [("restart-server", None)]

def test_service_orders_after_maintenance(scheduler):
    early = utc_now() - timedelta(minutes=5)
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
        sched._service_(conn, members, utc_now())
        assert sched.spawned == []
        RunAPI(UID="ord-fresh", TID="ord-update", Status="Success", StartedAt=utc_now(), db=conn).save(by="Test")
        sched._service_(conn, members, utc_now())
        assert [tid for tid, _ in sched.spawned] == ["ord-tunnel"]
        sched._services_["ord-tunnel"] = FakeHandle()
        RunAPI(UID="ord-tunnel-run", TID="ord-tunnel", Kind="Service", Status="Initializing", StartedAt=utc_now(), db=conn).save(by="Test")
        sched._service_(conn, members, utc_now())
        assert [tid for tid, _ in sched.spawned] == ["ord-tunnel"]
        RunAPI(UID="ord-tunnel-run", TID="ord-tunnel", Kind="Service", Status="Running", StartedAt=utc_now(), db=conn).save(by="Test")
        sched._service_(conn, members, utc_now())
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
    early = utc_now() - timedelta(minutes=5)
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
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
    assert sched.spawned == [("gt-b", "wr-gt")]

def test_advance_waits_false_fires_at_time(scheduler):
    early = utc_now() - timedelta(minutes=5)
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
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
    assert ("nw-b", "wr-nw") in sched.spawned

def test_advance_tolerates_governs_after_failure(scheduler):
    early = utc_now() - timedelta(minutes=5)
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
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
    assert sched.spawned == [("ar-b", "wr-ar")]

def test_advance_latest_attempt_governs(scheduler):
    early = utc_now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-attempt", Name="Attempt", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="att-a", Name="A", Owner="owner", WID="wf-attempt", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", MaxRetry=1, Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="att-b", Name="B", Owner="owner", WID="wf-attempt", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-attempt", "att-a", "att-b")
    opened("wr-att", "wf-attempt", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="att-run-1", TID="att-a", CID="wr-att", Status="Retrying", Retry=0, StartedAt=early, db=conn).save(by="Test")
        RunAPI(UID="att-run-2", TID="att-a", CID="wr-att", Status="Success", Retry=1, StartedAt=utc_now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-attempt", "Name": "Attempt", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-attempt"]
        edges = CoordinatorAPI.edges(conn, "wf-attempt")
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
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
    early = utc_now() - timedelta(minutes=5)
    manager = ManagerAPI(database=DATABASE)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="lat-a", Name="A", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="lat-run-1", TID="lat-a", Status="Failure", StartedAt=early, db=conn).save(by="Test")
        RunAPI(UID="lat-run-2", TID="lat-a", Status="Success", StartedAt=utc_now(), db=conn).save(by="Test")
    latest = manager.latest()
    assert latest["lat-a"] == "Success"

def test_workflow_reset_on_overrun(scheduler):
    early = utc_now() - timedelta(minutes=5)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-reset", Name="Reset", Owner="owner", Schedule="* * * * *", Waits=False, Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="rs-a", Name="A", Owner="owner", WID="wf-reset", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    opened("wr-rs", "wf-reset", started=early)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="rs-run-a", TID="rs-a", CID="wr-rs", Status="Running", Retry=0, StartedAt=early, Heartbeat=utc_now(), db=conn).save(by="Test")
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-reset", "Name": "Reset", "Schedule": "* * * * *", "Kind": None, "Waits": False}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-reset"]
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
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
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
    tids = [tid for tid, _ in sched.spawned]
    assert "root-update" in tids and "root-server" not in tids

def test_advance_skips_downstream_services(scheduler):
    early = utc_now() - timedelta(minutes=5)
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
        sched._advance_(conn, workflow, members, edges, utc_now(), 8)
    assert "svc-server" in CoordinatorAPI.eligible(["svc-update", "svc-server"], edges, {"svc-update": "Success"})
    assert "svc-server" not in [tid for tid, _ in sched.spawned]

def test_latest_ignores_runs_that_never_started(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        TaskAPI(UID="unstarted", Name="Unstarted", Owner="owner", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        RunAPI(UID="unstarted-live", TID="unstarted", Status="Running", Retry=0, StartedAt=utc_now(), Heartbeat=utc_now(), db=conn).save(by="Test")
        RunAPI(UID="unstarted-stale", TID="unstarted", Status="Failure", Retry=0, db=conn).save(by="Test")
    manager, sched = ManagerAPI(database=DATABASE), SchedulerAPI(database=DATABASE)
    assert manager.latest()["unstarted"] == "Running"
    assert manager.runs(task="unstarted")[0]["UID"] == "unstarted-live"
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        assert sched._latest_(conn, "unstarted")["UID"] == "unstarted-live"
        sched._suspend_(conn, "unstarted", utc_now())
    assert manager.run("unstarted-live")["Status"] == RunStatus.Success.name

def _fold_(uid, started):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID=uid, Name="Fold", Owner="owner", Schedule="30 1 * * *", Zone="Europe/London", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID=f"{uid}-a", Name="A", Owner="owner", WID=uid, Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    opened(f"{uid}-cycle", uid, status="Success", started=started)
    return {"UID": uid, "Name": "Fold", "Schedule": "30 1 * * *", "Zone": "Europe/London", "Kind": None, "Waits": None}

def test_advance_opens_no_cycle_after_one_inside_a_repeated_hour(scheduler):
    workflow = _fold_("wf-fold", datetime(2026, 10, 25, 1, 10))
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-fold"]
        for now in (datetime(2026, 10, 25, 1, 11), datetime(2026, 10, 25, 1, 31), datetime(2026, 10, 25, 23, 59)): sched._advance_(conn, workflow, members, [], now, 8)
        assert sched.spawned == []
        sched._advance_(conn, workflow, members, [], datetime(2026, 10, 26, 1, 31), 8)
        cycle = sched._cycle_(conn, "wf-fold")
    assert cycle["StartedAt"] == datetime(2026, 10, 26, 1, 30)
    assert sched.spawned == [("wf-fold-a", cycle["UID"])]

def test_advance_never_opens_a_cycle_before_the_latest_one(scheduler):
    workflow = _fold_("wf-wake", datetime(2026, 10, 24, 0, 30))
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    woke = datetime(2026, 10, 25, 1, 2)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-wake"]
        sched._advance_(conn, workflow, members, [], woke, 8)
        cycle = sched._cycle_(conn, "wf-wake")
        sched._record_(conn, cycle, RunStatus.Success.name, woke, "Test")
        for now in (datetime(2026, 10, 25, 1, 3), datetime(2026, 10, 25, 1, 40), datetime(2026, 10, 25, 12)): sched._advance_(conn, workflow, members, [], now, 8)
    assert cycle["StartedAt"] == woke
    assert len(ManagerAPI(database=DATABASE).cycles(workflow="wf-wake")) == 2
    assert sched.spawned == [("wf-wake-a", cycle["UID"])]

def test_a_run_reports_its_phases(scheduler, tmp_path):
    script = tmp_path / "phased.py"
    script.write_text("import time\nfrom Library.Utility.Progress import Phase, ProgressAPI\ntime.sleep(1.5)\nProgressAPI.phase(Phase.Running)\ntime.sleep(2.5)\nProgressAPI.phase(Phase.Terminating)\ntime.sleep(1.5)\n")
    task = TaskAPI(UID="task-phased", Name="Phased", Owner="owner", Type=TaskType.Python, Kind=Kind.Scheduled, Path=str(script), Enabled=True, RequiresApproval=False, RequiresReview=False)
    persist(task)
    seen, result = [], {}
    worker = threading.Thread(target=lambda: result.update(run=ExecutorAPI(database=DATABASE, poll=0.05).run(task)))
    worker.start()
    with PostgresDatabaseAPI(database=DATABASE) as db:
        while worker.is_alive():
            row = db.first(schema="Scheduler", table="Run", condition='"TID" = :tid:', order='"StartedAt" DESC NULLS LAST', parameters={"tid": "task-phased"})
            if row is not None and (not seen or seen[-1] != row["Status"]): seen.append(row["Status"])
            time.sleep(0.05)
    worker.join()
    assert [status for status in seen if status in RunAPI.Phases] == [RunStatus.Initializing.name, RunStatus.Running.name, RunStatus.Terminating.name]
    assert result["run"].Status == RunStatus.Success.name

def test_a_phase_never_returns_to_initializing():
    assert ExecutorAPI._advance_(RunStatus.Initializing.name, RunStatus.Running.name) == RunStatus.Running.name
    assert ExecutorAPI._advance_(RunStatus.Running.name, RunStatus.Terminating.name) == RunStatus.Terminating.name
    assert ExecutorAPI._advance_(RunStatus.Terminating.name, RunStatus.Running.name) == RunStatus.Running.name
    assert ExecutorAPI._advance_(RunStatus.Running.name, RunStatus.Initializing.name) == RunStatus.Running.name
    assert ExecutorAPI._advance_(RunStatus.Success.name, RunStatus.Running.name) == RunStatus.Success.name
    assert ExecutorAPI._advance_(RunStatus.Running.name, "Unknown") == RunStatus.Running.name

def test_every_phase_counts_as_alive():
    for phase in RunAPI.Phases:
        assert phase in RunAPI.Busy and phase in RunAPI.Live and phase in RunAPI.Active and phase in RunAPI.Open

def test_a_scheduled_successor_waits_for_a_useful_service(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-useful", Name="Gate", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="gate-service", Name="Feed", Owner="owner", WID="wf-useful", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="gate-report", Name="Report", Owner="owner", WID="wf-useful", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-useful", "gate-service", "gate-report")
        sched = RecordingSchedulerAPI(database=DATABASE)
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-useful"]
        edges = CoordinatorAPI.edges(conn, "wf-useful")
        tids = [member["UID"] for member in members]
        assert CoordinatorAPI.eligible(tids, edges, sched._gate_(conn, members, {})) == ["gate-service"]
        sched._services_["gate-service"] = FakeHandle()
        RunAPI(UID="gate-run", TID="gate-service", Kind="Service", Status="Initializing", StartedAt=utc_now(), db=conn).save(by="Test")
        assert "gate-report" not in CoordinatorAPI.eligible(tids, edges, sched._gate_(conn, members, {}))
        RunAPI(UID="gate-run", TID="gate-service", Kind="Service", Status="Running", StartedAt=utc_now(), db=conn).save(by="Test")
        assert "gate-report" in CoordinatorAPI.eligible(tids, edges, sched._gate_(conn, members, {}))

def test_a_successor_that_does_not_wait_starts_at_once(scheduler):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-nowait", Name="NoWait", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="nowait-first", Name="First", Owner="owner", WID="wf-nowait", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="nowait-second", Name="Second", Owner="owner", WID="wf-nowait", Type=TaskType.Python, Kind=Kind.Service, Path="x", Enabled=True, Waits=False, db=conn).save(by="Test")
        CoordinatorAPI.link(conn, "wf-nowait", "nowait-first", "nowait-second")
        sched = RecordingSchedulerAPI(database=DATABASE)
        tasks = {task["UID"]: task for task in sched._tasks_(conn)}
        kinds = {uid: Kind.parse(task["Kind"]) for uid, task in tasks.items()}
        assert sched._ready_(conn, tasks["nowait-second"], kinds, {})
        assert not sched._ready_(conn, {**tasks["nowait-second"], "Waits": True}, kinds, {})

def test_a_run_in_a_status_the_daemon_does_not_know_keeps_its_cycle_open(scheduler, monkeypatch):
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        WorkflowAPI(UID="wf-skew", Name="Skew", Owner="owner", Schedule="0 0 1 1 *", Enabled=True, db=conn).save(by="Test")
        TaskAPI(UID="skew-task", Name="Task", Owner="owner", WID="wf-skew", Type=TaskType.Python, Kind=Kind.Scheduled, Path="x", Enabled=True, db=conn).save(by="Test")
    opened("wf-skew-cycle", "wf-skew")
    with PostgresDatabaseAPI(database=DATABASE) as conn: RunAPI(UID="skew-run", CID="wf-skew-cycle", TID="skew-task", Status=RunStatus.Initializing.name, StartedAt=utc_now(), db=conn).save(by="Test")
    for name, statuses in (("Busy", (RunStatus.Waiting.name, RunStatus.Running.name)), ("Active", (RunStatus.Waiting.name, RunStatus.Running.name, RunStatus.Approving.name, RunStatus.Reviewing.name, RunStatus.Retrying.name))):
        monkeypatch.setattr(RunAPI, name, statuses)
    sched = RecordingSchedulerAPI(database=DATABASE, concurrency=8)
    workflow = {"UID": "wf-skew", "Name": "Skew", "Schedule": "0 0 1 1 *", "Kind": None, "Waits": None}
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        members = [task for task in sched._tasks_(conn) if task["WID"] == "wf-skew"]
        sched._advance_(conn, workflow, members, [], utc_now(), 8)
        cycle = sched._cycle_(conn, "wf-skew")
        assert cycle["UID"] == "wf-skew-cycle" and cycle["Status"] == RunStatus.Running.name and sched.spawned == []
        assert sched._dedup_(conn, "skew-task")