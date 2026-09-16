import dash
from dash import html
from dash.exceptions import PreventUpdate

from Library.App.V2 import GlobalAPI, FieldAPI, RefreshAPI, TableAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, SelectAPI, ButtonAPI, StorageAPI, NetworkAPI
from Library.Scheduler import WorkflowAPI, Kind
from Library.Utility.Datetime import zones
from Library.Web.Scheduler.Base import SchedulerBaseAPI, SchedulerGridDetailAPI
from Library.Web.Scheduler.Entity import SchedulerEntityAPI, SchedulerEntityPageAPI

class SchedulerWorkflowAPI(SchedulerEntityAPI):

    _entity_ = "workflow"

    _FIELDS_ = (
        FieldAPI(name="uid", label="UID", identity=True, placeholder="unique-workflow-id", help="Unique identifier of the workflow · immutable once created"),
        FieldAPI(name="name", required=True, help="Human-readable display name shown across the app"),
        FieldAPI(name="owner", required=True, default=lambda page: page.app.actor(), help="Account responsible for the workflow · used for auditing"),
        FieldAPI(name="kind", control="select", default="", options=[{"label": "(derive from Schedule)", "value": ""}] + FieldAPI.choices(Kind.names()), help="Lifecycle · Manual opens a cycle only on demand · Scheduled opens a cycle at each cron occurrence · Service keeps one resident always-on cycle and only accepts Service tasks · empty derives from Schedule"),
        FieldAPI(name="schedule", label="Schedule (cron)", column="Schedule", placeholder="0 22 * * 1-5", wrapper="scheduler-cron-row", suffix=lambda page: [page._cron_(page.F_CRON)], help="Cron that opens a new cycle at each occurrence · required for Scheduled and forbidden otherwise"),
        FieldAPI(name="zone", label="Time Zone", column="Zone", control="select", default="", options=[{"label": "(server zone)", "value": ""}] + FieldAPI.choices(zones()), help="Zone the cron is written in · follows that zone's daylight saving · member task schedules use it too · empty uses the server's zone"),
        FieldAPI(name="description", control="textarea", help="Free text shown on the workflow detail page"),
        FieldAPI(name="waits", control="switch", default=WorkflowAPI.Defaults["Waits"], help="On: an overrunning cycle makes the next occurrence wait for it · Off: the next occurrence kills the open cycle and starts fresh"),
    )
    _FIELD_ = FieldAPI.index(_FIELDS_)

    def _fetch_(self, uid):
        return self._manager_.workflow(uid)

    _new_, _edit_, _save_ = SchedulerEntityAPI.entity_callbacks(_FIELDS_)

class SchedulerWorkflowPageAPI(SchedulerWorkflowAPI, SchedulerEntityPageAPI, TableAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/workflow", button="Workflow", icon="bi bi-calendar2-week", description="Group tasks into scheduled dependency workflows")

    def ids(self) -> None:
        super().ids()
        self._entity_ids_()
        self._field_ids_()

    def _columns_(self) -> list:
        return self._WORKFLOW_COLUMNS_

    def _rows_(self) -> list:
        cycled = self._manager_.cycled()
        return [self._workflow_row_(workflow, cycled.get(workflow.get("UID"))) for workflow in self._manager_.workflows()]

    def _fingerprint_(self):
        return self._manager_.fingerprint("Scheduler", "Workflow")

    def _actions_(self) -> list:
        return self._lifecycle_buttons_()

class SchedulerWorkflowDetailPageAPI(SchedulerWorkflowAPI, SchedulerGridDetailAPI):

    DAG_GRAPH_ID: ComponentID | dict = ComponentID()
    CYCLE_TABLE_ID: ComponentID | dict = ComponentID()
    CYCLE_CARRIER_ID: ComponentID | dict = ComponentID()
    LINK_PRED: ComponentID | dict = ComponentID()
    LINK_SUCC: ComponentID | dict = ComponentID()
    LINK_BTN: ComponentID | dict = ComponentID()
    UNLINK_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/workflow/:uid", button="Workflow", icon="bi bi-calendar2-week", parametric=True)

    def ids(self) -> None:
        self._entity_ids_()
        self._field_ids_()
        self._detail_ids_()
        self.DAG_GRAPH_ID = self.register(type="graph", name="dag")
        self._grid_ids_("tasks", "task")
        self.CYCLE_TABLE_ID = self.register(type="grid", name="cycles")
        self.CYCLE_CARRIER_ID = self.register(type="script", name="cycles-payload")
        self.LINK_PRED = self.register(type="field", name="link-predecessor")
        self.LINK_SUCC = self.register(type="field", name="link-successor")
        self.LINK_BTN = self.register(type="button", name="link")
        self.UNLINK_BTN = self.register(type="button", name="unlink")

    def _fingerprint_(self) -> str:
        return self._manager_.fingerprint("Scheduler", "Task", "Run")

    def _links_(self) -> html.Div:
        return html.Div([
            *SelectAPI(id=self.LINK_PRED, options=[], placeholder="Predecessor", style={"maxWidth": "180px"}).build(),
            html.Span("→", className="scheduler-arrow"),
            *SelectAPI(id=self.LINK_SUCC, options=[], placeholder="Successor", style={"maxWidth": "180px"}).build(),
            *ButtonAPI(id=self.LINK_BTN, label=self._icon_("bi bi-link-45deg", "Link", tint="primary"), background="secondary", tooltip="Make the successor wait for the predecessor").build(),
            *ButtonAPI(id=self.UNLINK_BTN, label=self._icon_("bi bi-scissors", "Unlink", tint="danger"), background="secondary", tooltip="Remove the dependency between the two tasks").build(),
        ], className="scheduler-link-row")

    def _open_task_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.SUB_OPEN_BTN, label=self._icon_("bi bi-box-arrow-up-right", "Open Task"), background="secondary", tooltip="Open the selected tasks · one opens here · several open in new tabs")

    def _pair_(self, predecessor, successor, target) -> str | None:
        uid = target[0] if target else None
        if uid is None: return None
        if not predecessor or not successor or predecessor == successor:
            self.app.notify.warning("Pick two distinct tasks", header="Invalid Dependency")
            return None
        return uid

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            self.toolbar([self._refresh_button_(), self._open_task_button_()] + self._lifecycle_buttons_(insert=False) + [self._links_()]),
            html.Div([
                html.Div(id=self.FIELDS_ID, className="scheduler-split-detail"),
                html.Div(NetworkAPI(id=self.DAG_GRAPH_ID, figure=self._empty_figure_("Loading dependency graph"), anchor="/scheduler/task", style={"height": f"{self._DAG_FLOOR_}px"}).build(), className="scheduler-split-graph scheduler-panel"),
            ], className="scheduler-split"),
            *self._grid_(self.SUB_TABLE_ID, self.SUB_CARRIER_ID, "Tasks", self._MEMBER_COLUMNS_, "/scheduler/task", self.SUB_STATE_STORE_ID),
            *self._grid_(self.CYCLE_TABLE_ID, self.CYCLE_CARRIER_ID, "Cycles", self._CYCLE_COLUMNS_),
            self._legend_(),
            self._modal_(),
            StorageAPI(id=self.MODE_STORE_ID, data={}),
            *self._hidden_(),
        ]

    @serverside_callback(
        Output(SchedulerBaseAPI.BREADCRUMB_ID, "children"),
        Output(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        Output(SchedulerBaseAPI.FIELDS_ID, "children"),
        Output(DAG_GRAPH_ID, "figure"),
        Output(DAG_GRAPH_ID, "style"),
        Output(SchedulerGridDetailAPI.SUB_CARRIER_ID, "children"),
        Output(CYCLE_CARRIER_ID, "children"),
        Output(LINK_PRED, "options"),
        Output(LINK_SUCC, "options"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        State(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
    )
    def _populate_(self, token, pathname):
        uid = self.capture(pathname)
        if uid is None: raise PreventUpdate
        workflow = self._manager_.workflow(uid)
        if workflow is None:
            blank = self._payload_("Tasks", self._MEMBER_COLUMNS_, [], "/scheduler/task", self.SUB_STATE_STORE_ID).encode()
            return self._breadcrumb_(uid, None), [uid], self._details_([("Status", "Workflow not found")]), self._empty_figure_("Workflow not found"), {"height": f"{self._DAG_FLOOR_}px"}, blank, self._payload_("Cycles", self._CYCLE_COLUMNS_, []).encode(), [], []
        latest = self._manager_.latest()
        edges = self._edges_(uid)
        members = self._sequenced_(self._manager_.tasks(workflow=uid), latest, edges)
        nodes = self._nodes_(members, latest)
        graph = NetworkAPI.graph(nodes, edges) if nodes else None
        cycles = [self._cycle_row_(cycle) for cycle in self._manager_.cycles(workflow=uid, limit=10)]
        pairs = self._pairs_(workflow, self._FIELDS_, [("Enabled", workflow.get("Enabled")), ("Tasks", len(members))])
        rows = [self._task_row_(member, latest.get(member["UID"])) for member in members]
        options = FieldAPI.choices([member["UID"] for member in members])
        tasks = self._payload_("Tasks", self._MEMBER_COLUMNS_, rows, "/scheduler/task", self.SUB_STATE_STORE_ID).encode()
        return self._breadcrumb_(uid, workflow), [uid], self._details_(pairs), self._figure_(nodes, edges, graph), self._canvas_(nodes, edges, graph), tasks, self._payload_("Cycles", self._CYCLE_COLUMNS_, cycles).encode(), options, options

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(LINK_BTN, "n_clicks"),
        State(LINK_PRED, "value"),
        State(LINK_SUCC, "value"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _link_(self, clicks, predecessor, successor, target):
        uid = self._pair_(predecessor, successor, target)
        if uid is None: return dash.no_update
        if self._manager_.link(uid, predecessor, successor) is None:
            self.app.notify.error("Link rejected — it would create a cycle", header="Invalid Dependency")
            return dash.no_update
        self.app.notify.success(f"Linked {predecessor} → {successor}", header="Done")
        return self.token()

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(UNLINK_BTN, "n_clicks"),
        State(LINK_PRED, "value"),
        State(LINK_SUCC, "value"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _unlink_(self, clicks, predecessor, successor, target):
        uid = self._pair_(predecessor, successor, target)
        if uid is None: return dash.no_update
        self._manager_.unlink(uid, predecessor, successor)
        self.app.notify.success(f"Unlinked {predecessor} → {successor}", header="Done")
        return self.token()