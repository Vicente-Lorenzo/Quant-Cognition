import sys

import pytest

from Library.Auth import AccessLevel, RoleAPI, UserAPI
from Library.Scheduler import WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI, TaskType, Kind, RunStatus, ExecutorAPI, ManagerAPI
from Library.Scheduler.Main import _fields_, _parse_
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Script.Setup.Auth import setup_auth
from Script.Setup.Scheduler import setup_scheduler

DATABASE = "Tests"

ADMIN = "admin"
MODERATOR = "moderator"
EDITOR = "editor"
VIEWER = "viewer"

class RecordingManagerAPI(ManagerAPI):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned = []

    def _spawn_(self, tid, cycle=None, retry=0, manual=False, arguments=None, auditor=None):
        self.spawned.append((tid, auditor))

@pytest.fixture(scope="module")
def manager():
    for cls in (UserAPI, WorkflowAPI, TaskAPI, DependencyAPI, CycleAPI, RunAPI): cls.Database = DATABASE
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
        for uid, role in ((ADMIN, RoleAPI.Administrator), (MODERATOR, RoleAPI.Moderator), (EDITOR, RoleAPI.Editor), (VIEWER, RoleAPI.Viewer)):
            UserAPI(UID=uid, Email=f"{uid}@test.com", Name=uid, Role=role.name, Active=True, db=conn).save(by="Test")
        setup_scheduler(conn)
    return RecordingManagerAPI(database=DATABASE)

@pytest.fixture
def clean(manager):
    yield
    manager.spawned.clear()
    for row in manager.tasks(): manager.delete_task(row["UID"])
    for row in manager.workflows(): manager.delete_workflow(row["UID"])

def task(manager, uid, *, by, **fields):
    return manager.create_task(by=by, **{"UID": uid, "Name": uid, "Type": TaskType.Python, "Kind": Kind.Scheduled, "Path": "x", **fields})

def test_a_created_task_is_owned_and_owner_only(manager, clean):
    created = task(manager, "t-own", by=EDITOR)
    assert created.Owner == EDITOR and created.RunRole is None and created.EditRole is None
    row = manager.task("t-own")
    assert manager.access(row, manager.principal(EDITOR)) == AccessLevel.Edit
    assert manager.access(row, manager.principal(MODERATOR)) == AccessLevel.Denied
    assert manager.access(row, manager.principal(ADMIN)) == AccessLevel.Edit
    with pytest.raises(PermissionError, match="may not run"):
        manager.run_task("t-own", by=MODERATOR)

def test_a_threshold_opens_running_but_not_editing(manager, clean):
    task(manager, "t-run", by=EDITOR, RunRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name)
    row = manager.task("t-run")
    assert manager.access(row, manager.principal(VIEWER)) == AccessLevel.Run
    manager.run_task("t-run", by=VIEWER)
    assert manager.spawned == [("t-run", VIEWER)]
    for action in (lambda: manager.update_task("t-run", by=VIEWER, Name="Renamed"), lambda: manager.disable_task("t-run", by=VIEWER), lambda: manager.delete_task("t-run", by=VIEWER)):
        with pytest.raises(PermissionError, match="may not edit"):
            action()
    assert manager.update_task("t-run", by=MODERATOR, Name="Renamed") is not None

def test_a_threshold_cannot_exceed_the_setter(manager, clean):
    with pytest.raises(ValueError, match="above your own role Editor"):
        task(manager, "t-high", by=EDITOR, RunRole=RoleAPI.Editor.name, EditRole=RoleAPI.Moderator.name)
    with pytest.raises(ValueError, match="cannot be Public"):
        task(manager, "t-public", by=ADMIN, RunRole=RoleAPI.Public.name)

def test_an_unknown_user_is_refused_and_the_framework_is_trusted(manager, clean):
    with pytest.raises(PermissionError, match="signed-in user"):
        task(manager, "t-stranger", by="stranger")
    created = task(manager, "t-framework", by=None, Owner=ADMIN, RunRole=RoleAPI.Administrator.name, EditRole=RoleAPI.Administrator.name)
    assert RoleAPI.parse(created.RunRole) is RoleAPI.Administrator
    with pytest.raises(PermissionError):
        manager.run_task("t-framework", by="stranger")
    manager.run_task("t-framework")
    assert manager.spawned == [("t-framework", None)]

def test_a_non_administrator_may_not_plant_an_owner(manager, clean):
    with pytest.raises(PermissionError, match="may only own what they create"):
        task(manager, "t-planted", by=EDITOR, Owner=VIEWER)
    assert task(manager, "t-assigned", by=ADMIN, Owner=VIEWER).Owner == VIEWER

def test_create_never_overwrites_a_task_the_caller_cannot_edit(manager, clean):
    task(manager, "t-mine", by=ADMIN)
    with pytest.raises(PermissionError, match="may not edit"):
        task(manager, "t-mine", by=EDITOR)
    assert manager.task("t-mine")["Owner"] == ADMIN

def test_only_the_owner_or_an_administrator_transfers(manager, clean):
    task(manager, "t-hand", by=MODERATOR, RunRole=RoleAPI.Editor.name, EditRole=RoleAPI.Editor.name)
    with pytest.raises(PermissionError, match="Only the owner or an Administrator"):
        manager.update_task("t-hand", by=EDITOR, Owner=EDITOR)
    assert manager.update_task("t-hand", by=MODERATOR, Owner=EDITOR) is not None
    assert manager.task("t-hand")["Owner"] == EDITOR

def test_joining_a_workflow_needs_edit_on_it(manager, clean):
    manager.create_workflow(by=ADMIN, UID="w-admin", Name="Admin", Kind=Kind.Manual.name)
    with pytest.raises(PermissionError, match="Workflow Join: Failed"):
        task(manager, "t-join", by=EDITOR, WID="w-admin")
    manager.create_workflow(by=EDITOR, UID="w-editor", Name="Editor", Kind=Kind.Manual.name)
    assert task(manager, "t-join", by=EDITOR, WID="w-editor").WID == "w-editor"
    with pytest.raises(PermissionError, match="Workflow Join: Failed"):
        manager.update_task("t-join", by=EDITOR, WID="w-admin")

def test_a_workflow_is_linked_and_run_under_its_own_thresholds(manager, clean):
    manager.create_workflow(by=EDITOR, UID="w-run", Name="Run", Kind=Kind.Manual.name, RunRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name)
    for uid in ("t-a", "t-b"): task(manager, uid, by=EDITOR, WID="w-run")
    with pytest.raises(PermissionError, match="Workflow Link: Failed"):
        manager.link("w-run", "t-a", "t-b", by=VIEWER)
    assert manager.link("w-run", "t-a", "t-b", by=EDITOR) is not None
    cycle = manager.run_workflow("w-run", by=VIEWER)
    assert cycle and manager.spawned == [("t-a", VIEWER)]
    with pytest.raises(PermissionError, match="Workflow Unlink: Failed"):
        manager.unlink("w-run", "t-a", "t-b", by=VIEWER)
    with pytest.raises(PermissionError, match="Workflow Delete: Failed"):
        manager.delete_workflow("w-run", by=VIEWER)

def test_resolving_a_run_needs_run_on_its_task(manager, clean):
    task(manager, "t-gate", by=EDITOR, RunRole=RoleAPI.Editor.name, EditRole=RoleAPI.Editor.name, RequiresApproval=True)
    with PostgresDatabaseAPI(database=DATABASE) as conn:
        RunAPI(UID="r-approve", TID="t-gate", Status="Approving", db=conn).save(by="Test")
        RunAPI(UID="r-reject", TID="t-gate", Status="Reviewing", db=conn).save(by="Test")
    with pytest.raises(PermissionError, match="Task Approve: Failed"):
        manager.approve("r-approve", by=VIEWER)
    assert manager.approve("r-approve", by=EDITOR) is True
    assert manager.run("r-approve")["Auditor"] == EDITOR
    with pytest.raises(PermissionError, match="Task Reject: Failed"):
        manager.reject("r-reject", by=VIEWER)
    with pytest.raises(PermissionError, match="Task Delete: Failed"):
        manager.delete_run("r-approve", by=VIEWER)
    assert manager.delete_run("r-approve", by=EDITOR) is True

def test_skipping_records_the_principal(manager, clean):
    task(manager, "t-skip", by=EDITOR, RunRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name)
    with pytest.raises(PermissionError, match="Task Skip: Failed"):
        manager.skip("t-skip", by="stranger")
    assert manager.skip("t-skip", by=VIEWER).Auditor == VIEWER

def test_a_run_records_its_auditor_and_acts_as_its_owner(manager, clean, tmp_path):
    script = tmp_path / "argv.py"
    script.write_text("import sys\nprint('ARGV ' + ' '.join(sys.argv[1:]))\n")
    created = task(manager, "t-argv", by=EDITOR, Path=str(script), RunRole=RoleAPI.Viewer.name, EditRole=RoleAPI.Editor.name)
    run = manager.run_task("t-argv", wait=True, arguments="--description probe", by=VIEWER)
    assert run.Status == RunStatus.Success.name and run.Auditor == VIEWER
    output = manager.log(run.UID)
    assert "--description probe" in output and f"--user {created.Owner}" in output and "--run" in output

def test_the_executor_appends_the_owner_only_to_argument_runs():
    assert ExecutorAPI._scoped_("", "folder", "owner") == ""
    assert ExecutorAPI._scoped_("--x 1", "folder", None) == '--x 1 --run "folder"'
    assert ExecutorAPI._scoped_("--x 1", "folder", "owner") == '--x 1 --run "folder" --user "owner"'
    assert ExecutorAPI._scoped_('--x 1 --run "kept"', "folder", "owner") == '--x 1 --run "kept" --user "owner"'

def test_the_cli_carries_the_user_and_thresholds(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["Scheduler", "--user", EDITOR, "task", "update", "--uid", "t", "--run-role", "Owner", "--edit-role", "Editor"])
    args = _parse_()
    assert args.user == EDITOR
    assert _fields_(args, TaskAPI) == {"UID": "t", "RunRole": None, "EditRole": "Editor"}
    monkeypatch.setattr(sys, "argv", ["Scheduler", "workflow", "update", "--uid", "w"])
    assert _fields_(_parse_(), WorkflowAPI) == {"UID": "w"}