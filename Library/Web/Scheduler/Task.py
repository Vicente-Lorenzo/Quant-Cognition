from pathlib import Path

import dash
from dash import html
from dash.exceptions import PreventUpdate

from Library.App.V2 import GlobalAPI, FieldAPI, CrumbAPI, RefreshAPI, TableAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback, SwitchAPI, ButtonAPI, StorageAPI
from Library.Scheduler import TaskAPI, TaskType, Kind
from Library.Utility.Path import traceback_root
from Library.Web.Scheduler.Base import SchedulerBaseAPI, SchedulerSelectionAPI, SchedulerDetailAPI
from Library.Web.Scheduler.Entity import SchedulerEntityAPI

class SchedulerTaskAPI(SchedulerEntityAPI):

    _entity_ = "task"
    _ROOT_ = traceback_root()

    _FIELDS_ = (
        FieldAPI(name="uid", label="UID", identity=True, placeholder="unique-task-id", help="Unique identifier of the task · immutable once created"),
        FieldAPI(name="name", required=True, help="Human-readable display name shown across the app"),
        FieldAPI(name="owner", required=True, default=lambda page: page._current_owner_(), help="Account responsible for the task · used for auditing"),
        FieldAPI(name="type", control="select", group="kind", default=TaskAPI.Defaults["Type"], options=[{"label": member.name, "value": member.name} for member in TaskType], help="Artifact interpreter · Batch runs a Windows batch file · Shell runs a shell command · Python runs a Python script"),
        FieldAPI(name="kind", control="select", group="kind", default=TaskAPI.Defaults["Kind"], options=[{"label": member.name, "value": member.name} for member in Kind], help="Execution style · Manual runs only on demand · Scheduled runs to completion when triggered · Service is kept always-on and respawned if it dies"),
        FieldAPI(name="path", required=True, placeholder="Script/Example.py", wrapper="scheduler-path-row", suffix=lambda page: page._browse_(), help="Artifact the runner executes · stored absolute unless Relative is on"),
        FieldAPI(name="schedule", label="Schedule (cron)", column="Schedule", placeholder="0 22 * * 1-5", wrapper="scheduler-cron-row", suffix=lambda page: [page._cron_(page.F_CRON)], help="Cron expression · inside a workflow it is the earliest-start gate within each cycle · standalone it triggers the task directly"),
        FieldAPI(name="workflow", column="WID", control="select", default="", decode=lambda row: row.get("WID") or "", help="Optional membership · the task then runs inside the workflow cycles honoring its dependencies"),
        FieldAPI(name="description", control="textarea", help="Free text shown on the task detail page"),
        FieldAPI(name="maxretry", label="Max Retry", column="MaxRetry", control="number", group="retry", default=TaskAPI.Defaults["MaxRetry"], minimum=0, step=1, help="Extra attempts after a crash · for a Service 0 means respawn forever while a positive value halts it after that many consecutive short-lived crashes"),
        FieldAPI(name="retrydelay", label="Retry Delay (s)", column="RetryDelay", control="number", group="retry", default=TaskAPI.Defaults["RetryDelay"], minimum=0, step=1, help="Seconds to wait before the next retry attempt or service respawn"),
        FieldAPI(name="approval", label="Requires Approval", column="RequiresApproval", control="switch", group="gates", default=TaskAPI.Defaults["RequiresApproval"], help="A successful run pauses as Approving until a moderator accepts or rejects it · downstream tasks wait meanwhile"),
        FieldAPI(name="review", label="Requires Review", column="RequiresReview", control="switch", group="gates", default=TaskAPI.Defaults["RequiresReview"], help="A crashed run pauses as Reviewing until a moderator resolves it instead of failing outright"),
        FieldAPI(name="waits", control="switch", group="rules", default=TaskAPI.Defaults["Waits"], help="On: wait for every predecessor to finish before starting · Off: start at the gate time even if predecessors are still running"),
        FieldAPI(name="tolerates", control="switch", group="rules", default=TaskAPI.Defaults["Tolerates"], help="On: accept any predecessor outcome including Failure · Off: demand Success from every predecessor"),
        FieldAPI(name="relative", control="switch", stored=False, rendered=False, default=False, decode=lambda row: bool(row.get("Path")) and not Path(row.get("Path")).is_absolute()),
    )
    _FIELD_ = FieldAPI.index(_FIELDS_)

    F_CRON: ComponentID | dict = ComponentID()
    F_BROWSE: ComponentID | dict = ComponentID()
    F_UPLOAD: ComponentID | dict = ComponentID()
    SKIP_BTN: ComponentID | dict = ComponentID()
    F_FAILURE: ComponentID | dict = ComponentID()

    def _task_ids_(self) -> None:
        self._field_ids_()
        self.F_CRON = self.register(type="link", name="cron")
        self.F_BROWSE = self.register(type="button", name="browse")
        self.F_UPLOAD = self.register(type="upload", name="browse")
        self.SKIP_BTN = self.register(type="button", name="skip")
        self.F_FAILURE = self.register(type="field", name="failure")

    def _fetch_(self, uid):
        return self._manager_.task(uid)

    def _lineage_(self, uid: str) -> list:
        task = self._manager_.task(uid) or {}
        workflow = self._manager_.workflow(task.get("WID")) if task.get("WID") else None
        trail = [CrumbAPI(label="Workflow", href="/scheduler/workflow")]
        if workflow: trail.append(CrumbAPI(label=self._label_(workflow, task["WID"]), href=f"/scheduler/workflow/{task['WID']}"))
        return trail + [CrumbAPI(label="Task", href="/scheduler/task")]

    def _crumb_(self, uid: str) -> str:
        return self._label_(self._manager_.task(uid), uid)

    def _intervention_buttons_(self) -> list:
        return [
            ButtonAPI(id=self.SKIP_BTN, label=self._icon_("bi bi-skip-forward", "Skip", tint="warning"), background="secondary", tooltip="Record a result for the selected tasks without executing them · uses the As Failure switch"),
            SwitchAPI(id=self.F_FAILURE, label="As Failure", value=False, classname="app-switch", tooltip="Outcome recorded by Skip · off records Success · on records Failure", placement="top"),
        ]

    @classmethod
    def _relative_(cls, path: str) -> str:
        try:
            return Path(path).resolve().relative_to(cls._ROOT_).as_posix()
        except ValueError:
            return str(Path(path))

    @staticmethod
    def _format_(path: Path, relative) -> str:
        return SchedulerTaskAPI._relative_(str(path)) if relative else str(path)

    @classmethod
    def _locate_(cls, filename: str) -> Path | None:
        for folder in ("Script", "Setup", "Library", "Sources"):
            base = cls._ROOT_ / folder
            if not base.is_dir(): continue
            matches = [match for match in base.rglob(filename) if "__pycache__" not in match.parts]
            if matches: return min(matches, key=lambda match: len(match.parts))
        direct = cls._ROOT_ / filename
        return direct if direct.is_file() else None

    def _browse_(self) -> list:
        return [*ButtonAPI(id=self.F_BROWSE, upload=self.F_UPLOAD, label=self._icon_("bi bi-folder2-open", "Browse"), background="secondary", tooltip="Pick the artifact with the system file dialog").build(),
                *SwitchAPI(id=self._FIELD_["relative"].bind(self), label="Relative", value=False, classname="app-switch", tooltip="Store the path relative to the project root · off keeps the full absolute path", placement="top").build()]

    @serverside_callback(
        Output(_FIELD_["workflow"].id, "options"),
        on_enter=InjectionType.Hidden,
    )
    def _options_(self):
        return [{"label": "(none)", "value": ""}] + [{"label": workflow["UID"], "value": workflow["UID"]} for workflow in self._manager_.workflows()]

    @clientside_callback(
        Output(F_CRON, "href"),
        Input(_FIELD_["schedule"].id, "value"),
    )
    def _cron_link_(self):
        return self.app.asset("Callbacks/Cron.js", url=False)

    @serverside_callback(
        Output(_FIELD_["path"].id, "value"),
        Input(F_UPLOAD, "filename"),
        State(_FIELD_["relative"].id, "value"),
    )
    def _pick_(self, filename, relative):
        if not filename: raise PreventUpdate
        found = self._locate_(filename)
        if found is None:
            self.app.notify.warning(f"'{filename}' was not found inside the project · type its path manually", header="Not Located")
            return dash.no_update
        return self._format_(found, relative)

    @serverside_callback(
        Output(_FIELD_["path"].id, "value"),
        Input(_FIELD_["relative"].id, "value"),
        State(_FIELD_["path"].id, "value"),
    )
    def _convert_(self, relative, path):
        if not path: raise PreventUpdate
        chosen = Path(path) if Path(path).is_absolute() else self._ROOT_ / path
        return self._format_(chosen, relative)

    @clientside_callback(
        Output(SKIP_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_skip_(self):
        return self.app.asset("Callbacks/GateSkip.js", url=False)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(SKIP_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        State(F_FAILURE, "value"),
        on_click=InjectionType.Hidden,
    )
    def _skip_(self, clicks, target, failure):
        return self._intervene_("task", "skip", target, failure, "No selected task is skippable · a workflow member needs an open cycle")

    @serverside_callback(
        *SchedulerEntityAPI._outputs_(_FIELDS_),
        Input(SchedulerEntityAPI.INSERT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _new_(self, clicks):
        return self._blank_()

    @serverside_callback(
        *SchedulerEntityAPI._outputs_(_FIELDS_),
        Input(SchedulerEntityAPI.EDIT_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _edit_(self, clicks, target):
        return self._populate_(target)

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(SchedulerEntityAPI.SAVE_BTN, "n_clicks"),
        State(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        *SchedulerEntityAPI._states_(_FIELDS_),
        on_click=InjectionType.Hidden,
    )
    def _save_(self, clicks, mode, *values):
        return self._submit_(mode, values)

class SchedulerTaskPageAPI(SchedulerTaskAPI, SchedulerSelectionAPI, TableAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/task", button="Task", icon="bi bi-list-check", description="Create, schedule and monitor tasks")

    def ids(self) -> None:
        super().ids()
        self._entity_ids_()
        self._task_ids_()

    def _columns_(self) -> list:
        return self._TASK_COLUMNS_

    def _detail_base_(self):
        return self.anchor

    def _rows_(self) -> list:
        latest = self._manager_.latest()
        return [self._task_row_(task, latest.get(task.get("UID"))) for task in self._manager_.tasks()]

    def _fingerprint_(self):
        return self._manager_.fingerprint("Scheduler", "Task")

    def _actions_(self) -> list:
        return self._lifecycle_buttons_() + self._intervention_buttons_()

    def _extras_(self) -> list:
        return [self._legend_(), self._modal_(), StorageAPI(id=self.MODE_STORE_ID, data={}), StorageAPI(id=self.TARGET_STORE_ID, data=None)]

class SchedulerTaskDetailPageAPI(SchedulerTaskAPI, SchedulerDetailAPI):

    SUB_TABLE_ID: ComponentID | dict = ComponentID()
    SUB_CARRIER_ID: ComponentID | dict = ComponentID()
    SUB_STATE_STORE_ID: ComponentID | dict = ComponentID()
    SUB_OPEN_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/task/:uid", button="Task", icon="bi bi-list-check", parametric=True)

    def ids(self) -> None:
        self._entity_ids_()
        self._task_ids_()
        self._detail_ids_()
        self.SUB_TABLE_ID = self.register(type="grid", name="runs")
        self.SUB_CARRIER_ID = self.register(type="script", name="runs-payload")
        self.SUB_STATE_STORE_ID = self.register(type="store", name="runs-state")
        self.SUB_OPEN_BTN = self.register(type="button", name="run-open")

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            self._toolbar_([self._refresh_button_()] + self._lifecycle_buttons_(insert=False) + self._intervention_buttons_()),
            html.Div(id=self.FIELDS_ID),
            *self._grid_(self.SUB_TABLE_ID, self.SUB_CARRIER_ID, "Runs", self._TASK_RUN_COLUMNS_, "/scheduler/run", self.SUB_STATE_STORE_ID, height="40vh"),
            self._toolbar_([ButtonAPI(id=self.SUB_OPEN_BTN, label=self._icon_("bi bi-box-arrow-up-right", "Open Run"), background="secondary", tooltip="Open the selected runs · one opens here · several open in new tabs")], "table-bar"),
            self._legend_(),
            self._modal_(),
            StorageAPI(id=self.MODE_STORE_ID, data={}),
            *self._hidden_(),
        ]

    @serverside_callback(
        Output(SchedulerBaseAPI.BREADCRUMB_ID, "children"),
        Output(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        Output(SchedulerBaseAPI.FIELDS_ID, "children"),
        Output(SUB_CARRIER_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        State(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
    )
    def _populate_(self, token, pathname):
        uid = self.capture(pathname)
        if uid is None: raise PreventUpdate
        task = self._manager_.task(uid)
        if task is None:
            return self._breadcrumb_(uid), [uid], self._details_([("Status", "Task not found")]), self._payload_("Runs", self._TASK_RUN_COLUMNS_, [], "/scheduler/run", self.SUB_STATE_STORE_ID).encode()
        pairs = self._pairs_(task, self._FIELDS_, [("Enabled", task.get("Enabled"))])
        runs = [self._run_row_(run) for run in self._manager_.runs(task=uid, limit=50)]
        return self._breadcrumb_(uid), [uid], self._details_(pairs), self._payload_("Runs", self._TASK_RUN_COLUMNS_, runs, "/scheduler/run", self.SUB_STATE_STORE_ID).encode()

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        Input(SUB_OPEN_BTN, "n_clicks"),
        State(SUB_STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _subopen_(self):
        return self.app.asset("Callbacks/Open.js", url=False)