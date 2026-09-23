import dash
import pytest

from Library.Auth import AccessLevel, AccessAPI, RoleAPI
from Library.Web.Scheduler.Task import SchedulerTaskAPI
from Library.Web.Scheduler.Workflow import SchedulerWorkflowAPI

@pytest.fixture(scope="module")
def tasks(application):
    return application._pages_["/scheduler/task/"]

@pytest.fixture(scope="module")
def workflows(application):
    return application._pages_["/scheduler/workflow/"]

@pytest.mark.parametrize("entity", [SchedulerTaskAPI, SchedulerWorkflowAPI])
def test_both_entities_offer_run_and_edit_thresholds(entity):
    for name, column in (("runrole", "RunRole"), ("editrole", "EditRole")):
        field = entity._FIELD_[name]
        assert field.column == column and field.initial(None) == ""
        assert [option["value"] for option in field.options] == ["", *AccessAPI.roles()]
        assert field.write("") is None and field.write("Editor") == "Editor"
        assert field.read({column: None}) == "" and field.read({column: "Moderator"}) == "Moderator"

@pytest.mark.parametrize("columns", [SchedulerTaskAPI._TASK_COLUMNS_, SchedulerWorkflowAPI._WORKFLOW_COLUMNS_])
def test_the_grids_show_owner_thresholds_and_access(columns):
    assert {"Owner", "Run", "Edit", "Access"}.issubset(columns)

def test_a_row_carries_the_readers_access(tasks):
    row = {"UID": "t", "Name": "T", "Owner": "owner", "RunRole": RoleAPI.Viewer.name, "EditRole": None, "Kind": "Scheduled"}
    shown = tasks._task_row_(row, "Success", ("someone", RoleAPI.Viewer))
    assert shown["Run"] == "Viewer" and shown["Edit"] == AccessAPI.label(None) and shown["Access"] == AccessLevel.Run.name
    assert tasks._task_row_(row, "Success", ("owner", RoleAPI.Viewer))["Access"] == AccessLevel.Edit.name
    assert tasks._task_row_(row, "Success", ("someone", RoleAPI.Public))["Access"] == AccessLevel.Denied.name

def test_a_detail_shows_the_option_label(workflows):
    pairs = dict(workflows._pairs_({"UID": "w", "Name": "W", "RunRole": None, "EditRole": "Editor", "Kind": None}, SchedulerWorkflowAPI._FIELDS_))
    assert pairs["Run Role"] == AccessAPI.label(None) and pairs["Edit Role"] == "Editor"

def test_saving_acts_as_the_signed_in_user(tasks, monkeypatch):
    calls = []
    monkeypatch.setattr(tasks.app, "actor", lambda: "editor@test.com")
    monkeypatch.setattr(tasks._manager_, "create_task", lambda **fields: calls.append(fields))
    monkeypatch.setattr(tasks.app.notify, "success", lambda message, **kwargs: None)
    values = [entry.initial(tasks) if not callable(entry.default) else "editor@test.com" for entry in SchedulerTaskAPI._FIELDS_]
    values[[entry.name for entry in SchedulerTaskAPI._FIELDS_].index("uid")] = "t-new"
    values[[entry.name for entry in SchedulerTaskAPI._FIELDS_].index("name")] = "New"
    values[[entry.name for entry in SchedulerTaskAPI._FIELDS_].index("path")] = "Script/Example.py"
    tasks._submit_({"mode": "create"}, values)
    assert calls and calls[0]["by"] == "editor@test.com" and calls[0]["RunRole"] is None and calls[0]["EditRole"] is None

def test_a_refused_action_is_reported_not_raised(tasks, monkeypatch):
    messages = []
    monkeypatch.setattr(tasks.app, "actor", lambda: "viewer@test.com")
    monkeypatch.setattr(tasks.app.notify, "error", lambda message, **kwargs: messages.append(message))
    def refuse(uid, by=None): raise PermissionError(f"Task Delete: Failed · {by} may not edit {uid}")
    monkeypatch.setattr(tasks._manager_, "delete_task", refuse)
    assert tasks._apply_("task", "delete", {"selected": ["t"]}) is dash.no_update
    assert messages == ["Task Delete: Failed · viewer@test.com may not edit t"]

def test_a_tally_reports_every_failure_once(tasks, monkeypatch):
    errors, warnings = [], []
    monkeypatch.setattr(tasks.app.notify, "error", lambda message, **kwargs: errors.append(message))
    monkeypatch.setattr(tasks.app.notify, "warning", lambda message, **kwargs: warnings.append(message))
    def refuse(key): raise PermissionError("Refused")
    assert tasks._tally_(["a", "b"], refuse, "done", "blocked") is dash.no_update
    assert errors == ["Refused"] and warnings == []

def test_the_gate_reads_the_access_column(application):
    script = application.asset("Callbacks/Gate.js", url=False)
    assert "row.Access" in script and "Service" in script
    assert "row.Access" in application.asset("Callbacks/GateAccess.js", url=False)