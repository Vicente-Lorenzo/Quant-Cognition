import dash
import pytest

from Library.App.V2 import NetworkAPI
from Library.Auth import AccessLevel, AccessAPI, RoleAPI
from Library.Scheduler import ManagerAPI
from Library.Web.Scheduler.Task import SchedulerTaskAPI
from Library.Web.Scheduler.Workflow import SchedulerWorkflowAPI

@pytest.fixture(scope="module")
def tasks(application):
    return application._pages_["/scheduler/task/"]

@pytest.fixture(scope="module")
def workflows(application):
    return application._pages_["/scheduler/workflow/"]

@pytest.fixture(scope="module")
def workflow(application):
    return application._pages_["/scheduler/workflow/:uid/"]

_CHAIN_ = [{"UID": "Environment", "After": None}, {"UID": "Web", "After": "Environment"}, {"UID": "Solo", "After": None}]

def _values_(page, **chosen) -> list:
    values = [entry.initial(page) if not callable(entry.default) else "owner@test.com" for entry in SchedulerWorkflowAPI._FIELDS_]
    names = [entry.name for entry in SchedulerWorkflowAPI._FIELDS_]
    for name, value in chosen.items(): values[names.index(name)] = value
    return values

def _empty_(page) -> dict:
    labels = {}
    for entry in page._FIELDS_:
        if entry.control.value != "select" or entry.initial(page) != "": continue
        options = entry.choose(page)
        labels[entry.name] = (entry.build(page)[0].placeholder, next(option["label"] for option in options if option["value"] == ""))
    return labels

@pytest.mark.parametrize("name", ["tasks", "workflows"])
def test_every_empty_select_shows_its_label_instead_of_a_blank(name, request):
    labels = _empty_(request.getfixturevalue(name))
    assert labels and all(shown == label for shown, label in labels.values())
    assert set(labels) >= ({"runrole", "editrole", "workflow"} if name == "tasks" else {"runrole", "editrole", "kind", "zone", "after"})

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

def test_the_grid_shows_the_upstream_workflow(workflows):
    assert "After" in SchedulerWorkflowAPI._WORKFLOW_COLUMNS_
    assert workflows._workflow_row_({"UID": "Web", "After": "Environment"}, "Waiting")["After"] == "Environment"

def test_the_after_field_offers_every_other_workflow(workflows, monkeypatch):
    monkeypatch.setattr(workflows._manager_, "workflows", lambda **kwargs: _CHAIN_)
    field = SchedulerWorkflowAPI._FIELD_["after"]
    assert field.dynamic and field.column == "After" and field.initial(workflows) == ""
    assert [option["value"] for option in field.choose(workflows)] == ["", "Environment", "Web", "Solo"]
    assert [option["value"] for option in field.choose(workflows, {"UID": "Web"})] == ["", "Environment", "Solo"]
    assert field.write("") is None and field.read({"After": None}) == "" and field.read({"After": "Environment"}) == "Environment"

def test_opening_the_form_refreshes_the_upstream_choices(workflows, monkeypatch):
    monkeypatch.setattr(workflows._manager_, "workflows", lambda **kwargs: _CHAIN_)
    monkeypatch.setattr(workflows, "_fetch_", lambda uid: {"UID": uid, "Name": uid, "After": "Environment"})
    blank, prefilled = workflows._blank_(), workflows._prefill_(["Web"])
    assert len(blank) == len(prefilled) == len(SchedulerWorkflowAPI._outputs_(SchedulerWorkflowAPI._FIELDS_))
    assert [option["value"] for option in blank[-1]] == ["", "Environment", "Web", "Solo"]
    assert [option["value"] for option in prefilled[-1]] == ["", "Environment", "Solo"]
    assert prefilled[3 + [entry.name for entry in SchedulerWorkflowAPI._FIELDS_].index("after")] == "Environment"

def test_the_after_field_saves_and_clears(workflows, monkeypatch):
    calls = []
    monkeypatch.setattr(workflows.app, "actor", lambda: "owner@test.com")
    monkeypatch.setattr(workflows.app.notify, "success", lambda message, **kwargs: None)
    monkeypatch.setattr(workflows._manager_, "update_workflow", lambda uid, by=None, **fields: calls.append((uid, fields["After"])))
    workflows._submit_({"mode": "update", "uid": "Web"}, _values_(workflows, uid="Web", name="Web", after="Environment"))
    workflows._submit_({"mode": "update", "uid": "Web"}, _values_(workflows, uid="Web", name="Web", after=""))
    assert calls == [("Web", "Environment"), ("Web", None)]

def test_a_loop_is_refused_through_the_page(workflows, monkeypatch):
    errors, rows = [], {row["UID"]: row for row in _CHAIN_}
    manager = workflows._manager_
    monkeypatch.setattr(workflows.app, "actor", lambda: "owner@test.com")
    monkeypatch.setattr(workflows.app.notify, "error", lambda message, **kwargs: errors.append(message))
    monkeypatch.setattr(manager, "workflow", lambda uid: rows.get(uid))
    monkeypatch.setattr(manager, "update_workflow", lambda uid, by=None, **fields: ManagerAPI._upstream_(manager, uid, fields, None))
    assert workflows._submit_({"mode": "update", "uid": "Environment"}, _values_(workflows, uid="Environment", name="Environment", after="Web")) == (dash.no_update, dash.no_update)
    assert errors == ["Workflow 'Web' already runs after 'Environment' · a loop is refused"]

def test_the_workflow_dag_draws_its_neighbours_as_squares_that_open_them(workflow):
    nodes = [{"uid": "a", "color": None}, {"uid": "b", "color": None}]
    nodes, edges = workflow._bridged_(nodes, [("a", "b")], "Environment", ["Data", "Web"], {"Environment": "Success", "Web": "Waiting"})
    assert ("workflow:Environment", "a") in edges and ("b", "workflow:Data") in edges and ("b", "workflow:Web") in edges and ("workflow:Environment", "b") not in edges
    trace = workflow._figure_(nodes, edges, NetworkAPI.graph(nodes, edges)).data[1]
    shapes = dict(zip(trace.text, trace.marker.symbol))
    links = {pair[0]: pair[1] for pair in trace.customdata}
    colors = dict(zip(trace.text, trace.marker.color))
    assert shapes == {"a": "circle", "b": "circle", "Environment": "square", "Data": "square", "Web": "square"}
    assert links["workflow:Environment"] == "/scheduler/workflow/Environment" and links["a"] == ""
    assert colors["Environment"] == workflow._STATUS_COLOR_["Success"] and colors["Web"] == workflow._STATUS_COLOR_["Waiting"]

def test_a_workflow_without_neighbours_draws_only_its_tasks(workflow):
    nodes, edges = workflow._bridged_([{"uid": "a"}], [], None, [], {})
    assert nodes == [{"uid": "a"}] and edges == []

def test_the_overview_draws_every_workflow_as_a_square_in_layers(workflows, monkeypatch):
    monkeypatch.setattr(workflows._manager_, "workflows", lambda **kwargs: _CHAIN_)
    monkeypatch.setattr(workflows._manager_, "cycled", lambda: {"Environment": "Running", "Web": "Waiting"})
    figure, style = workflows._overview_("token")
    trace = figure.data[1]
    assert list(trace.marker.symbol) == ["square"] * 3
    assert {pair[0]: pair[1] for pair in trace.customdata} == {uid: f"/scheduler/workflow/{uid}" for uid in ("Environment", "Web", "Solo")}
    assert len(figure.layout.annotations) == 1 and figure.layout.xaxis.fixedrange and figure.layout.dragmode is False
    heights = dict(zip(trace.text, trace.y))
    assert heights["Environment"] == heights["Solo"] != heights["Web"]
    assert style == workflows._layered_(2)

def test_the_overview_follows_cycles_as_well_as_workflows(workflows, monkeypatch):
    seen = []
    monkeypatch.setattr(workflows._manager_, "fingerprint", lambda schema, *tables, **kwargs: seen.append(tables))
    workflows._fingerprint_()
    assert seen == [("Workflow", "Cycle")]