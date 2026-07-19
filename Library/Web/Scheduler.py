import re
import uuid
from pathlib import Path
from datetime import datetime

import dash
import networkx as nx
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc

from Library.App.V2 import PageAPI, TableAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback, IconAPI, InputAPI, SelectAPI, SwitchAPI, TextareaAPI, ButtonAPI, ModalAPI, StorageAPI, IntervalAPI, PlotlyAPI
from Library.Auth import RoleAPI
from Library.Scheduler import ManagerAPI, WorkflowAPI, TaskAPI, TaskType, Kind
from Library.Utility.Path import traceback_root

class SchedulerBaseAPI(PageAPI):

    _WORKFLOW_COLUMNS_ = ["UID", "Name", "Owner", "Enabled", "Kind", "Waits", "Schedule"]
    _TASK_COLUMNS_ = ["Status", "UID", "Name", "Type", "Kind", "Enabled", "Waits", "Tolerates", "Schedule", "WID", "MaxRetry"]
    _MEMBER_COLUMNS_ = ["Status", "UID", "Name", "Type", "Kind", "Enabled"]
    _RUN_COLUMNS_ = ["Status", "UID", "CID", "TID", "Kind", "Retry", "StartedAt", "StoppedAt", "Duration", "ExitCode", "PID", "Auditor"]
    _TASK_RUN_COLUMNS_ = ["Status", "UID", "Kind", "Retry", "StartedAt", "StoppedAt", "Duration", "ExitCode", "PID", "Auditor"]
    _CYCLE_COLUMNS_ = ["Status", "UID", "Kind", "StartedAt", "StoppedAt"]
    _MARKDOWN_COLUMNS_ = {"Status"}
    _STATUS_COLOR_ = {"Success": "#2f9e44", "Failure": "#ef5350", "Running": "#2962ff", "Waiting": "#868993", "Approving": "#ffb300", "Reviewing": "#ff7043", "Retrying": "#ab47bc"}
    _UNRUN_COLOR_ = "#565a66"
    _NEUTRAL_ = "#868993"
    _LEGEND_ = [("Success", "success"), ("Running", "running"), ("Waiting", "waiting"), ("Approving", "approving"), ("Reviewing", "reviewing"), ("Retrying", "retrying"), ("Failure", "failure"), ("No run", "none")]
    _VERBS_ = {"run": "dispatched", "enable": "enabled", "disable": "disabled", "delete": "deleted"}

    def __init__(self, *, app, **kwargs) -> None:
        super().__init__(app=app, **kwargs)
        self._manager_ = ManagerAPI(database="Quant")

    @staticmethod
    def _icon_(icon: str, label: str = None, tint: str = None) -> list:
        return TableAPI._icon_(icon, label, tint)

    @staticmethod
    def _toolbar_(buttons: list, classname: str = "table-toolbar") -> html.Div:
        return TableAPI.toolbar(buttons, classname)

    @staticmethod
    def _table_(id: dict, columns: list, markdown=(), **over):
        return TableAPI.table(id, columns, markdown, **over)

    @staticmethod
    def _config_(base: str, key: str = "UID") -> dict:
        return {"base": base, "key": key, "navigable": True}

    def _help_(self, help: str) -> list:
        self._helps_ = getattr(self, "_helps_", 0) + 1
        identifier = self.register(type="icon", name=f"help-{self._helps_}")
        return IconAPI(id=identifier, icon="bi bi-question-circle", classname="scheduler-help", tooltip=help, placement="right").build()

    def _field_(self, label: str, control, help: str = None) -> html.Div:
        caption = [dbc.Label(label)]
        if help: caption += self._help_(help)
        control = control if isinstance(control, list) else [control]
        return html.Div([html.Div(caption, className="scheduler-field-label"), *control], className="scheduler-field")

    def _switch_(self, id: dict, label: str, value, help: str) -> html.Div:
        return html.Div([*SwitchAPI(id=id, label=label, value=value).build(), *self._help_(help)], className="scheduler-switch-field")

    @classmethod
    def _legend_(cls) -> html.Div:
        return html.Div([html.Span([html.Span(className=f"led led-{key}"), label]) for label, key in cls._LEGEND_], className="scheduler-legend")

    @classmethod
    def _led_(cls, status) -> str:
        key = status if status in cls._STATUS_COLOR_ else None
        return f'<span class="led led-{key.lower() if key else "none"}"></span>{key or "—"}'

    @classmethod
    def _led_dot_(cls, status):
        key = status if status in cls._STATUS_COLOR_ else None
        return html.Span([html.Span(className=f"led led-{key.lower() if key else 'none'}"), key or "—"])

    @staticmethod
    def _fired_(cid: dict) -> bool:
        return dash.ctx.triggered_id == cid

    @staticmethod
    def _current_owner_():
        from flask_login import current_user
        return getattr(current_user, "Username", None) or getattr(current_user, "Name", None)

    @staticmethod
    def _stamp_(value):
        if isinstance(value, datetime): return value.isoformat(sep=" ", timespec="seconds")
        return value

    def _apply_(self, entity: str, verb: str, uids):
        uids = [uids] if isinstance(uids, str) else list(uids or [])
        if not uids:
            self.app.notify.warning(f"Select a {entity} first", header="No Selection")
            return dash.no_update
        done, error = [], None
        for uid in uids:
            try:
                getattr(self._manager_, f"{verb}_{entity}")(uid)
                done.append(uid)
            except Exception as reason:
                error = str(reason)
        if error: self.app.notify.error(error, header="Action Failed")
        if not done: return dash.no_update
        detail = f"{entity.capitalize()} '{done[0]}'" if len(done) == 1 else f"{len(done)} {entity}s"
        self.app.notify.success(f"{detail} {self._VERBS_[verb]}", header="Done")
        return uuid.uuid4().hex

    def _task_row_(self, task: dict, status) -> dict:
        row = {column: self._stamp_(task.get(column)) for column in self._TASK_COLUMNS_}
        row["Status"] = self._led_(status)
        row["Waits"] = task.get("Waits") is not False
        row["Tolerates"] = task.get("Tolerates") is not False
        return row

    def _run_row_(self, run: dict) -> dict:
        row = {}
        for column in self._RUN_COLUMNS_:
            value = self._stamp_(run.get(column))
            row[column] = round(value, 2) if column == "Duration" and isinstance(value, (int, float)) else value
        row["Status"] = self._led_(run.get("Status"))
        return row

    def _workflow_row_(self, workflow: dict) -> dict:
        row = {column: self._stamp_(workflow.get(column)) for column in self._WORKFLOW_COLUMNS_}
        row["Waits"] = workflow.get("Waits") is not False
        return row

    def _cycle_row_(self, cycle: dict) -> dict:
        row = {column: self._stamp_(cycle.get(column)) for column in self._CYCLE_COLUMNS_}
        row["Status"] = self._led_(cycle.get("Status"))
        return row

    @staticmethod
    def _details_(pairs) -> html.Div:
        rows = []
        for label, value in pairs:
            if value is None or value == "": continue
            display = str(value) if isinstance(value, (str, int, float, bool)) else value
            rows.append(html.Div([html.Span(label, className="scheduler-detail-key"), html.Span(display, className="scheduler-detail-val")], className="scheduler-detail-row"))
        return html.Div(rows, className="scheduler-detail")

    def capture(self, pathname: str):
        if not pathname or self.parent is None: return None
        endpoint = self.app.anchorize(path=pathname, relative=False)
        prefix = self.parent.anchor
        if not endpoint.startswith(prefix + "/"): return None
        return endpoint[len(prefix) + 1:].split("/")[0] or None

    def _breadcrumb_(self, uid: str) -> html.Div:
        parent = self.parent
        return html.Div([dcc.Link(parent.button, href=parent.anchor or parent.endpoint, className="scheduler-crumb"), html.Span("›", className="scheduler-crumb-sep"), html.Span(uid, className="scheduler-crumb-current")], className="scheduler-breadcrumb")

    @classmethod
    def _empty_figure_(cls, text: str):
        figure = go.Figure()
        figure.update_layout(annotations=[dict(text=text, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5, font=dict(color=cls._NEUTRAL_, size=13))], margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False))
        return figure

    def _figure_(self, wid: str, members: list, latest: dict):
        if not members: return self._empty_figure_("Workflow has no tasks")
        nodes = [task["UID"] for task in members]
        edges = [(row["Predecessor"], row["Successor"]) for row in self._manager_.dependencies(wid) if row["Predecessor"] in nodes and row["Successor"] in nodes]
        graph = nx.DiGraph()
        graph.add_nodes_from(nodes)
        graph.add_edges_from(edges)
        if not nx.is_directed_acyclic_graph(graph): return self._empty_figure_("Dependency cycle detected")
        for layer, layer_nodes in enumerate(nx.topological_generations(graph)):
            for node in layer_nodes: graph.nodes[node]["layer"] = layer
        position = nx.multipartite_layout(graph, subset_key="layer")
        ordered = list(graph.nodes())
        edge_x, edge_y, annotations = [], [], []
        for predecessor, successor in graph.edges():
            ax, ay = position[predecessor]
            bx, by = position[successor]
            edge_x += [ax, bx, None]
            edge_y += [ay, by, None]
            annotations.append(dict(ax=ax, ay=ay, x=bx, y=by, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1.4, arrowwidth=1, arrowcolor=self._NEUTRAL_, opacity=0.7))
        node_x = [position[node][0] for node in ordered]
        node_y = [position[node][1] for node in ordered]
        colors = [self._STATUS_COLOR_.get(latest.get(node), self._UNRUN_COLOR_) for node in ordered]
        hovers = [f"{node}<br>{latest.get(node) or 'No run'}" for node in ordered]
        figure = go.Figure()
        figure.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(color=self._NEUTRAL_, width=1), hoverinfo="none"))
        figure.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text", marker=dict(size=26, color=colors, line=dict(color=self._NEUTRAL_, width=1.5)), text=ordered, textposition="bottom center", textfont=dict(color=self._NEUTRAL_, size=11), hovertext=hovers, hoverinfo="text"))
        figure.update_layout(showlegend=False, annotations=annotations, margin=dict(l=8, r=8, t=8, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False, autorange="reversed"), font=dict(color=self._NEUTRAL_))
        return figure

class SchedulerSelectionAPI:

    @clientside_callback(
        Output("TARGET_STORE_ID", "data"),
        Input("TABLE_ID", "selected_rows"),
        State("TABLE_ID", "data"),
    )
    def _target_sync_(self):
        return self.app.asset("Callbacks/Select.js", url=False)

class SchedulerDetailAPI(SchedulerBaseAPI):

    RELOAD_STORE_ID: ComponentID | dict = ComponentID()
    FINGERPRINT_STORE_ID: ComponentID | dict = ComponentID()
    INTERVAL_ID: ComponentID | dict = ComponentID()
    REFRESH_BTN: ComponentID | dict = ComponentID()
    BREADCRUMB_ID: ComponentID | dict = ComponentID()
    TITLE_ID: ComponentID | dict = ComponentID()
    FIELDS_ID: ComponentID | dict = ComponentID()

    def _detail_ids_(self) -> None:
        self.RELOAD_STORE_ID = self.register(type="store", name="reload")
        self.FINGERPRINT_STORE_ID = self.register(type="store", name="fingerprint")
        self.INTERVAL_ID = self.register(type="interval", name="poll")
        self.REFRESH_BTN = self.register(type="button", name="refresh")
        self.BREADCRUMB_ID = self.register(type="div", name="breadcrumb")
        self.TITLE_ID = self.register(type="text", name="title")
        self.FIELDS_ID = self.register(type="div", name="fields")

    def _refresh_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.REFRESH_BTN, label=self._icon_("bi bi-arrow-clockwise", "Refresh"), background="secondary", tooltip="Reload this page from the database")

    def _fingerprint_(self) -> str:
        return self._manager_.fingerprint("Scheduler", "Run")

    def _hidden_(self) -> list:
        return [StorageAPI(id=self.TARGET_STORE_ID, data=None), StorageAPI(id=self.RELOAD_STORE_ID, data=None), StorageAPI(id=self.FINGERPRINT_STORE_ID, data=None), IntervalAPI(id=self.INTERVAL_ID, interval=10000, intervals=0)]

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Output(FINGERPRINT_STORE_ID, "data"),
        on_enter=InjectionType.Hidden,
    )
    def _enter_(self):
        return uuid.uuid4().hex, (self._fingerprint_() or dash.no_update)

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Input(REFRESH_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _refresh_(self, clicks):
        return uuid.uuid4().hex

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Output(FINGERPRINT_STORE_ID, "data"),
        Input(INTERVAL_ID, "n_intervals"),
        State(FINGERPRINT_STORE_ID, "data"),
    )
    def _tick_(self, intervals, previous):
        from dash.exceptions import PreventUpdate
        if not intervals: raise PreventUpdate
        token = self._fingerprint_()
        if token is not None and token == previous: raise PreventUpdate
        return uuid.uuid4().hex, (dash.no_update if token is None else token)

class SchedulerEntityAPI(SchedulerBaseAPI):

    _entity_ = ""

    TARGET_STORE_ID: ComponentID | dict = ComponentID()
    MODE_STORE_ID: ComponentID | dict = ComponentID()
    MODAL_ID: ComponentID | dict = ComponentID()
    MODAL_TITLE_ID: ComponentID | dict = ComponentID()
    INSERT_BTN: ComponentID | dict = ComponentID()
    EDIT_BTN: ComponentID | dict = ComponentID()
    RUN_BTN: ComponentID | dict = ComponentID()
    ENABLE_BTN: ComponentID | dict = ComponentID()
    DISABLE_BTN: ComponentID | dict = ComponentID()
    DELETE_BTN: ComponentID | dict = ComponentID()
    DISCARD_BTN: ComponentID | dict = ComponentID()
    SAVE_BTN: ComponentID | dict = ComponentID()
    F_UNSCHEDULE: ComponentID | dict = ComponentID()

    def _entity_ids_(self) -> None:
        self.TARGET_STORE_ID = self.register(type="store", name="target")
        self.MODE_STORE_ID = self.register(type="store", name="mode")
        self.MODAL_ID = self.register(type="modal", name=self._entity_)
        self.MODAL_TITLE_ID = self.register(type="text", name=f"{self._entity_}-title")
        self.INSERT_BTN = self.register(type="button", name="insert")
        self.EDIT_BTN = self.register(type="button", name="edit")
        self.RUN_BTN = self.register(type="button", name="run")
        self.ENABLE_BTN = self.register(type="button", name="enable")
        self.DISABLE_BTN = self.register(type="button", name="disable")
        self.DELETE_BTN = self.register(type="button", name="delete")
        self.DISCARD_BTN = self.register(type="button", name="discard")
        self.SAVE_BTN = self.register(type="button", name="save")
        self.F_UNSCHEDULE = self.register(type="button", name="unschedule")

    def _lifecycle_buttons_(self, insert: bool = True) -> list:
        entity = self._entity_
        buttons = []
        if insert: buttons.append(ButtonAPI(id=self.INSERT_BTN, label=self._icon_("bi bi-plus-lg", "Insert", tint="primary"), background="secondary", tooltip=f"Create a new {entity}"))
        buttons.append(ButtonAPI(id=self.EDIT_BTN, label=self._icon_("bi bi-pencil", "Edit"), background="secondary", tooltip=f"Edit the selected {entity}"))
        buttons.append(ButtonAPI(id=self.RUN_BTN, label=self._icon_("bi bi-play-fill", "Run", tint="success"), background="secondary", tooltip=f"Run the selected {entity} now"))
        buttons.append(ButtonAPI(id=self.ENABLE_BTN, label=self._icon_("bi bi-check-circle", "Enable", tint="success"), background="secondary", tooltip=f"Enable the selected {entity}"))
        buttons.append(ButtonAPI(id=self.DISABLE_BTN, label=self._icon_("bi bi-x-circle", "Disable", tint="danger"), background="secondary", tooltip=f"Disable the selected {entity} · the daemon skips it"))
        buttons.append(ButtonAPI(id=self.DELETE_BTN, label=self._icon_("bi bi-trash3", "Delete", tint="danger"), background="secondary", tooltip=f"Delete the selected {entity} permanently"))
        return buttons

    def _cron_(self, link: dict) -> html.Div:
        return html.Div([
            html.A([html.I(className="bi bi-box-arrow-up-right"), html.Span("Validate on crontab.guru")], id=link, href="https://crontab.guru/", target="_blank", className="scheduler-cron"),
            *ButtonAPI(id=self.F_UNSCHEDULE, size="sm", label=self._icon_("bi bi-eraser", "Clear"), background="secondary", tooltip="Remove the schedule · no cron means on-demand only").build(),
        ], className="scheduler-cron-actions")

    def _footer_(self) -> list:
        return [
            *ButtonAPI(id=self.DISCARD_BTN, label=self._icon_("bi bi-x-lg", "Discard", tint="danger"), background="secondary", tooltip="Close without saving changes").build(),
            *ButtonAPI(id=self.SAVE_BTN, label=self._icon_("bi bi-check-lg", "Apply", tint="success"), background="secondary", tooltip=f"Save the {self._entity_}").build(),
        ]

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Input(DISCARD_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _discard_(self, clicks):
        return False

    @clientside_callback(
        Output("F_SCHEDULE", "value"),
        Input(F_UNSCHEDULE, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _unschedule_(self):
        return self.app.asset("Callbacks/Blank.js", url=False)

    @clientside_callback(
        Output(EDIT_BTN, "disabled"),
        Output(RUN_BTN, "disabled"),
        Output(ENABLE_BTN, "disabled"),
        Output(DISABLE_BTN, "disabled"),
        Output(DELETE_BTN, "disabled"),
        Input("TABLE_ID", "selected_rows"),
        State("TABLE_ID", "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_(self):
        return self.app.asset("Callbacks/Gate.js", url=False)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(RUN_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _run_(self, clicks, target):
        return self._apply_(self._entity_, "run", target)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(ENABLE_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _enable_(self, clicks, target):
        return self._apply_(self._entity_, "enable", target)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(DISABLE_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _disable_(self, clicks, target):
        return self._apply_(self._entity_, "disable", target)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(DELETE_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _delete_(self, clicks, target):
        return self._apply_(self._entity_, "delete", target)

class SchedulerTaskAPI(SchedulerEntityAPI):

    _entity_ = "task"
    _ROOT_ = traceback_root()

    F_UID: ComponentID | dict = ComponentID()
    F_NAME: ComponentID | dict = ComponentID()
    F_OWNER: ComponentID | dict = ComponentID()
    F_TYPE: ComponentID | dict = ComponentID()
    F_KIND: ComponentID | dict = ComponentID()
    F_PATH: ComponentID | dict = ComponentID()
    F_SCHEDULE: ComponentID | dict = ComponentID()
    F_WORKFLOW: ComponentID | dict = ComponentID()
    F_DESCRIPTION: ComponentID | dict = ComponentID()
    F_APPROVAL: ComponentID | dict = ComponentID()
    F_REVIEW: ComponentID | dict = ComponentID()
    F_MAXRETRY: ComponentID | dict = ComponentID()
    F_RETRYDELAY: ComponentID | dict = ComponentID()
    F_WAITS: ComponentID | dict = ComponentID()
    F_TOLERATES: ComponentID | dict = ComponentID()
    F_CRON: ComponentID | dict = ComponentID()
    F_RELATIVE: ComponentID | dict = ComponentID()
    F_BROWSE: ComponentID | dict = ComponentID()
    F_UPLOAD: ComponentID | dict = ComponentID()
    SKIP_BTN: ComponentID | dict = ComponentID()
    F_FAILURE: ComponentID | dict = ComponentID()

    def _task_ids_(self) -> None:
        self.F_UID = self.register(type="field", name="uid")
        self.F_NAME = self.register(type="field", name="name")
        self.F_OWNER = self.register(type="field", name="owner")
        self.F_TYPE = self.register(type="field", name="type")
        self.F_KIND = self.register(type="field", name="kind")
        self.F_PATH = self.register(type="field", name="path")
        self.F_SCHEDULE = self.register(type="field", name="schedule")
        self.F_WORKFLOW = self.register(type="field", name="workflow")
        self.F_DESCRIPTION = self.register(type="field", name="description")
        self.F_APPROVAL = self.register(type="field", name="approval")
        self.F_REVIEW = self.register(type="field", name="review")
        self.F_MAXRETRY = self.register(type="field", name="maxretry")
        self.F_RETRYDELAY = self.register(type="field", name="retrydelay")
        self.F_WAITS = self.register(type="field", name="waits")
        self.F_TOLERATES = self.register(type="field", name="tolerates")
        self.F_CRON = self.register(type="link", name="cron")
        self.F_RELATIVE = self.register(type="field", name="relative")
        self.F_BROWSE = self.register(type="button", name="browse")
        self.F_UPLOAD = self.register(type="upload", name="browse")
        self.SKIP_BTN = self.register(type="button", name="skip")
        self.F_FAILURE = self.register(type="field", name="failure")

    def _fetch_(self, uid):
        return self._manager_.task(uid)

    def _intervention_buttons_(self) -> list:
        return [
            ButtonAPI(id=self.SKIP_BTN, label=self._icon_("bi bi-skip-forward", "Skip", tint="warning"), background="secondary", tooltip="Record a result for the selected tasks without executing them · uses the As Failure switch"),
            SwitchAPI(id=self.F_FAILURE, label="As Failure", value=False, classname="scheduler-switch", tooltip="Outcome recorded by Skip · off records Success · on records Failure", placement="top"),
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
        for folder in ("Scripts", "Setup", "Library", "Sources"):
            base = cls._ROOT_ / folder
            if not base.is_dir(): continue
            matches = [match for match in base.rglob(filename) if "__pycache__" not in match.parts]
            if matches: return min(matches, key=lambda match: len(match.parts))
        direct = cls._ROOT_ / filename
        return direct if direct.is_file() else None

    def _modal_(self) -> ModalAPI:
        return ModalAPI(id=self.MODAL_ID, size="lg", centered=True, scrollable=True, open=False,
            header=[html.Span("Insert Task", id=self.MODAL_TITLE_ID, className="modal-title")],
            body=[
                self._field_("UID", InputAPI(id=self.F_UID, type="text", placeholder="unique-task-id").build(), help="Unique identifier of the task · immutable once created"),
                self._field_("Name", InputAPI(id=self.F_NAME, type="text").build(), help="Human-readable display name shown across the app"),
                self._field_("Owner", InputAPI(id=self.F_OWNER, type="text").build(), help="Account responsible for the task · used for auditing"),
                html.Div([
                    self._field_("Type", SelectAPI(id=self.F_TYPE, options=[{"label": member.name, "value": member.name} for member in TaskType]).build(), help="Artifact interpreter · Batch runs a Windows batch file · Shell runs a shell command · Python runs a Python script"),
                    self._field_("Kind", SelectAPI(id=self.F_KIND, options=[{"label": member.name, "value": member.name} for member in Kind]).build(), help="Execution style · Manual runs only on demand · Scheduled runs to completion when triggered · Service is kept always-on and respawned if it dies"),
                ], className="scheduler-field-row"),
                self._field_("Path", html.Div([
                    *InputAPI(id=self.F_PATH, type="text", placeholder="Scripts/Example.py").build(),
                    *ButtonAPI(id=self.F_BROWSE, upload=self.F_UPLOAD, label=self._icon_("bi bi-folder2-open", "Browse"), background="secondary", tooltip="Pick the artifact with the system file dialog").build(),
                    *SwitchAPI(id=self.F_RELATIVE, label="Relative", value=False, classname="scheduler-switch", tooltip="Store the path relative to the project root · off keeps the full absolute path", placement="top").build(),
                ], className="scheduler-path-row"), help="Artifact the runner executes · stored absolute unless Relative is on"),
                self._field_("Schedule (cron)", html.Div([*InputAPI(id=self.F_SCHEDULE, type="text", placeholder="0 22 * * 1-5").build(), self._cron_(self.F_CRON)], className="scheduler-cron-row"), help="Cron expression · inside a workflow it is the earliest-start gate within each cycle · standalone it triggers the task directly"),
                self._field_("Workflow", SelectAPI(id=self.F_WORKFLOW, options=[]).build(), help="Optional membership · the task then runs inside the workflow cycles honoring its dependencies"),
                self._field_("Description", TextareaAPI(id=self.F_DESCRIPTION).build(), help="Free text shown on the task detail page"),
                html.Div([
                    self._field_("Max Retry", InputAPI(id=self.F_MAXRETRY, type="number", value=TaskAPI.DEFAULTS["MaxRetry"], min=0, step=1).build(), help="Extra attempts after a crash · for a Service 0 means respawn forever while a positive value halts it after that many consecutive short-lived crashes"),
                    self._field_("Retry Delay (s)", InputAPI(id=self.F_RETRYDELAY, type="number", value=TaskAPI.DEFAULTS["RetryDelay"], min=0, step=1).build(), help="Seconds to wait before the next retry attempt or service respawn"),
                ], className="scheduler-field-row"),
                html.Div([
                    self._switch_(self.F_APPROVAL, "Requires Approval", TaskAPI.DEFAULTS["RequiresApproval"], "A successful run pauses as Approving until a moderator accepts or rejects it · downstream tasks wait meanwhile"),
                    self._switch_(self.F_REVIEW, "Requires Review", TaskAPI.DEFAULTS["RequiresReview"], "A crashed run pauses as Reviewing until a moderator resolves it instead of failing outright"),
                ], className="scheduler-field-row"),
                html.Div([
                    self._switch_(self.F_WAITS, "Waits", TaskAPI.DEFAULTS["Waits"], "On: wait for every predecessor to finish before starting · Off: start at the gate time even if predecessors are still running"),
                    self._switch_(self.F_TOLERATES, "Tolerates", TaskAPI.DEFAULTS["Tolerates"], "On: accept any predecessor outcome including Failure · Off: demand Success from every predecessor"),
                ], className="scheduler-field-row"),
            ],
            footer=self._footer_())

    @serverside_callback(
        Output(F_WORKFLOW, "options"),
        on_enter=InjectionType.Hidden,
    )
    def _options_(self):
        return [{"label": "(none)", "value": ""}] + [{"label": workflow["UID"], "value": workflow["UID"]} for workflow in self._manager_.workflows()]

    @clientside_callback(
        Output(F_CRON, "href"),
        Input(F_SCHEDULE, "value"),
    )
    def _cron_link_(self):
        return self.app.asset("Callbacks/Cron.js", url=False)

    @serverside_callback(
        Output(F_PATH, "value"),
        Input(F_UPLOAD, "filename"),
        State(F_RELATIVE, "value"),
    )
    def _pick_(self, filename, relative):
        from dash.exceptions import PreventUpdate
        if not filename: raise PreventUpdate
        found = self._locate_(filename)
        if found is None:
            self.app.notify.warning(f"'{filename}' was not found inside the project · type its path manually", header="Not Located")
            return dash.no_update
        return self._format_(found, relative)

    @serverside_callback(
        Output(F_PATH, "value"),
        Input(F_RELATIVE, "value"),
        State(F_PATH, "value"),
    )
    def _convert_(self, relative, path):
        from dash.exceptions import PreventUpdate
        if not path: raise PreventUpdate
        chosen = Path(path) if Path(path).is_absolute() else self._ROOT_ / path
        return self._format_(chosen, relative)

    @clientside_callback(
        Output(SKIP_BTN, "disabled"),
        Input("TABLE_ID", "selected_rows"),
        State("TABLE_ID", "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_skip_(self):
        return self.app.asset("Callbacks/GateSkip.js", url=False)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(SKIP_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        State(F_FAILURE, "value"),
        on_click=InjectionType.Hidden,
    )
    def _skip_(self, clicks, target, failure):
        uids = [target] if isinstance(target, str) else list(target or [])
        if not uids:
            self.app.notify.warning("Select a task first", header="No Selection")
            return dash.no_update
        by = self._current_owner_() or "UI"
        skipped = 0
        for uid in uids:
            if self._manager_.skip(uid, failure=bool(failure), by=by) is not None: skipped += 1
        if not skipped:
            self.app.notify.warning("No selected task is skippable · a workflow member needs an open cycle", header="No Action")
            return dash.no_update
        outcome = "Failure" if failure else "Success"
        self.app.notify.success(f"{skipped} task(s) skipped as {outcome}", header="Done")
        return uuid.uuid4().hex

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        Output(SchedulerEntityAPI.MODAL_TITLE_ID, "children"),
        Output(F_UID, "value"),
        Output(F_UID, "disabled"),
        Output(F_NAME, "value"),
        Output(F_OWNER, "value"),
        Output(F_TYPE, "value"),
        Output(F_KIND, "value"),
        Output(F_PATH, "value"),
        Output(F_SCHEDULE, "value"),
        Output(F_WORKFLOW, "value"),
        Output(F_DESCRIPTION, "value"),
        Output(F_APPROVAL, "value"),
        Output(F_REVIEW, "value"),
        Output(F_MAXRETRY, "value"),
        Output(F_RETRYDELAY, "value"),
        Output(F_WAITS, "value"),
        Output(F_TOLERATES, "value"),
        Output(F_RELATIVE, "value"),
        Input(SchedulerEntityAPI.INSERT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _new_(self, clicks):
        defaults = TaskAPI.DEFAULTS
        return (True, {"mode": "create", "uid": None}, "Insert Task",
                "", False, "", self._current_owner_(),
                defaults["Type"], defaults["Kind"], "", "",
                "", "", defaults["RequiresApproval"], defaults["RequiresReview"],
                defaults["MaxRetry"], defaults["RetryDelay"], defaults["Waits"], defaults["Tolerates"], False)

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        Output(SchedulerEntityAPI.MODAL_TITLE_ID, "children"),
        Output(F_UID, "value"),
        Output(F_UID, "disabled"),
        Output(F_NAME, "value"),
        Output(F_OWNER, "value"),
        Output(F_TYPE, "value"),
        Output(F_KIND, "value"),
        Output(F_PATH, "value"),
        Output(F_SCHEDULE, "value"),
        Output(F_WORKFLOW, "value"),
        Output(F_DESCRIPTION, "value"),
        Output(F_APPROVAL, "value"),
        Output(F_REVIEW, "value"),
        Output(F_MAXRETRY, "value"),
        Output(F_RETRYDELAY, "value"),
        Output(F_WAITS, "value"),
        Output(F_TOLERATES, "value"),
        Output(F_RELATIVE, "value"),
        Input(SchedulerEntityAPI.EDIT_BTN, "n_clicks"),
        State(SchedulerEntityAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _edit_(self, clicks, target):
        uid = target[0] if target and len(target) == 1 else None
        row = self._fetch_(uid) if uid else None
        if row is None:
            self.app.notify.warning("Select a single task to edit", header="Selection")
            return (dash.no_update,) * 20
        defaults = TaskAPI.DEFAULTS
        return (True, {"mode": "update", "uid": row.get("UID")}, "Edit Task",
                row.get("UID"), True, row.get("Name"), row.get("Owner"),
                row.get("Type") or defaults["Type"], row.get("Kind") or defaults["Kind"], row.get("Path"), row.get("Schedule"),
                row.get("WID") or "", row.get("Description"),
                bool(row.get("RequiresApproval")), bool(row.get("RequiresReview")),
                row.get("MaxRetry") if row.get("MaxRetry") is not None else defaults["MaxRetry"],
                row.get("RetryDelay") if row.get("RetryDelay") is not None else defaults["RetryDelay"],
                row.get("Waits") is not False, row.get("Tolerates") is not False,
                bool(row.get("Path")) and not Path(row.get("Path")).is_absolute())

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output("RELOAD_STORE_ID", "data"),
        Input(SchedulerEntityAPI.SAVE_BTN, "n_clicks"),
        State(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        State(F_UID, "value"),
        State(F_NAME, "value"),
        State(F_OWNER, "value"),
        State(F_TYPE, "value"),
        State(F_KIND, "value"),
        State(F_PATH, "value"),
        State(F_SCHEDULE, "value"),
        State(F_WORKFLOW, "value"),
        State(F_DESCRIPTION, "value"),
        State(F_APPROVAL, "value"),
        State(F_REVIEW, "value"),
        State(F_MAXRETRY, "value"),
        State(F_RETRYDELAY, "value"),
        State(F_WAITS, "value"),
        State(F_TOLERATES, "value"),
        on_click=InjectionType.Hidden,
    )
    def _save_(self, clicks, mode, uid, name, owner, kind_type, kind, path, schedule, workflow, description, approval, review, retry, delay, waits, tolerates):
        if not name or not owner or not path:
            self.app.notify.error("Name, Owner and Path are required", header="Invalid Task")
            return dash.no_update, dash.no_update
        fields = dict(Name=name, Owner=owner, Type=kind_type, Kind=kind, Path=path, Schedule=schedule or None, WID=workflow or None, Description=description or None, RequiresApproval=bool(approval), RequiresReview=bool(review), MaxRetry=retry or 0, RetryDelay=delay or 0, Waits=bool(waits), Tolerates=bool(tolerates))
        try:
            if mode and mode.get("mode") == "update":
                self._manager_.update_task(mode["uid"], **fields)
                self.app.notify.success(f"Task '{mode['uid']}' updated", header="Saved")
            else:
                if not uid:
                    self.app.notify.error("UID is required", header="Invalid Task")
                    return dash.no_update, dash.no_update
                self._manager_.create_task(UID=uid, Enabled=True, **fields)
                self.app.notify.success(f"Task '{uid}' created", header="Saved")
        except Exception as error:
            self.app.notify.error(str(error), header="Save Failed")
            return dash.no_update, dash.no_update
        return False, uuid.uuid4().hex

class SchedulerWorkflowAPI(SchedulerEntityAPI):

    _entity_ = "workflow"

    F_UID: ComponentID | dict = ComponentID()
    F_NAME: ComponentID | dict = ComponentID()
    F_OWNER: ComponentID | dict = ComponentID()
    F_KIND: ComponentID | dict = ComponentID()
    F_WAITS: ComponentID | dict = ComponentID()
    F_SCHEDULE: ComponentID | dict = ComponentID()
    F_DESCRIPTION: ComponentID | dict = ComponentID()
    F_CRON: ComponentID | dict = ComponentID()

    def _workflow_ids_(self) -> None:
        self.F_UID = self.register(type="field", name="uid")
        self.F_NAME = self.register(type="field", name="name")
        self.F_OWNER = self.register(type="field", name="owner")
        self.F_KIND = self.register(type="field", name="kind")
        self.F_WAITS = self.register(type="field", name="waits")
        self.F_SCHEDULE = self.register(type="field", name="schedule")
        self.F_DESCRIPTION = self.register(type="field", name="description")
        self.F_CRON = self.register(type="link", name="cron")

    def _fetch_(self, uid):
        return self._manager_.workflow(uid)

    def _modal_(self) -> ModalAPI:
        return ModalAPI(id=self.MODAL_ID, size="lg", centered=True, scrollable=True, open=False,
            header=[html.Span("Insert Workflow", id=self.MODAL_TITLE_ID, className="modal-title")],
            body=[
                self._field_("UID", InputAPI(id=self.F_UID, type="text", placeholder="unique-workflow-id").build(), help="Unique identifier of the workflow · immutable once created"),
                self._field_("Name", InputAPI(id=self.F_NAME, type="text").build(), help="Human-readable display name shown across the app"),
                self._field_("Owner", InputAPI(id=self.F_OWNER, type="text").build(), help="Account responsible for the workflow · used for auditing"),
                self._field_("Kind", SelectAPI(id=self.F_KIND, options=[{"label": "(derive from Schedule)", "value": ""}] + [{"label": member.name, "value": member.name} for member in Kind]).build(), help="Lifecycle · Manual opens a cycle only on demand · Scheduled opens a cycle at each cron occurrence · Service keeps one resident always-on cycle and only accepts Service tasks · empty derives from Schedule"),
                self._field_("Schedule (cron)", html.Div([*InputAPI(id=self.F_SCHEDULE, type="text", placeholder="0 22 * * 1-5").build(), self._cron_(self.F_CRON)], className="scheduler-cron-row"), help="Cron that opens a new cycle at each occurrence · required for Scheduled and forbidden otherwise"),
                self._field_("Description", TextareaAPI(id=self.F_DESCRIPTION).build(), help="Free text shown on the workflow detail page"),
                self._switch_(self.F_WAITS, "Waits", WorkflowAPI.DEFAULTS["Waits"], "On: an overrunning cycle makes the next occurrence wait for it · Off: the next occurrence kills the open cycle and starts fresh"),
            ],
            footer=self._footer_())

    @clientside_callback(
        Output(F_CRON, "href"),
        Input(F_SCHEDULE, "value"),
    )
    def _cron_link_(self):
        return self.app.asset("Callbacks/Cron.js", url=False)

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        Output(SchedulerEntityAPI.MODAL_TITLE_ID, "children"),
        Output(F_UID, "value"),
        Output(F_UID, "disabled"),
        Output(F_NAME, "value"),
        Output(F_OWNER, "value"),
        Output(F_KIND, "value"),
        Output(F_WAITS, "value"),
        Output(F_SCHEDULE, "value"),
        Output(F_DESCRIPTION, "value"),
        Input(SchedulerEntityAPI.INSERT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _new_(self, clicks):
        return (True, {"mode": "create", "uid": None}, "Insert Workflow",
                "", False, "", self._current_owner_(), "", WorkflowAPI.DEFAULTS["Waits"], "", "")

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        Output(SchedulerEntityAPI.MODAL_TITLE_ID, "children"),
        Output(F_UID, "value"),
        Output(F_UID, "disabled"),
        Output(F_NAME, "value"),
        Output(F_OWNER, "value"),
        Output(F_KIND, "value"),
        Output(F_WAITS, "value"),
        Output(F_SCHEDULE, "value"),
        Output(F_DESCRIPTION, "value"),
        Input(SchedulerEntityAPI.EDIT_BTN, "n_clicks"),
        State(SchedulerEntityAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _edit_(self, clicks, target):
        uid = target[0] if target and len(target) == 1 else None
        row = self._fetch_(uid) if uid else None
        if row is None:
            self.app.notify.warning("Select a single workflow to edit", header="Selection")
            return (dash.no_update,) * 11
        return (True, {"mode": "update", "uid": row.get("UID")}, "Edit Workflow",
                row.get("UID"), True, row.get("Name"), row.get("Owner"),
                row.get("Kind") or "", row.get("Waits") is not False, row.get("Schedule"), row.get("Description"))

    @serverside_callback(
        Output(SchedulerEntityAPI.MODAL_ID, "is_open"),
        Output("RELOAD_STORE_ID", "data"),
        Input(SchedulerEntityAPI.SAVE_BTN, "n_clicks"),
        State(SchedulerEntityAPI.MODE_STORE_ID, "data"),
        State(F_UID, "value"),
        State(F_NAME, "value"),
        State(F_OWNER, "value"),
        State(F_KIND, "value"),
        State(F_WAITS, "value"),
        State(F_SCHEDULE, "value"),
        State(F_DESCRIPTION, "value"),
        on_click=InjectionType.Hidden,
    )
    def _save_(self, clicks, mode, uid, name, owner, kind, waits, schedule, description):
        if not name or not owner:
            self.app.notify.error("Name and Owner are required", header="Invalid Workflow")
            return dash.no_update, dash.no_update
        fields = dict(Name=name, Owner=owner, Kind=kind or None, Waits=bool(waits), Schedule=schedule or None, Description=description or None)
        try:
            if mode and mode.get("mode") == "update":
                self._manager_.update_workflow(mode["uid"], **fields)
                self.app.notify.success(f"Workflow '{mode['uid']}' updated", header="Saved")
            else:
                if not uid:
                    self.app.notify.error("UID is required", header="Invalid Workflow")
                    return dash.no_update, dash.no_update
                self._manager_.create_workflow(UID=uid, Enabled=True, **fields)
                self.app.notify.success(f"Workflow '{uid}' created", header="Saved")
        except Exception as error:
            self.app.notify.error(str(error), header="Save Failed")
            return dash.no_update, dash.no_update
        return False, uuid.uuid4().hex

class SchedulerRunAPI(SchedulerBaseAPI):

    TARGET_STORE_ID: ComponentID | dict = ComponentID()
    APPROVE_BTN: ComponentID | dict = ComponentID()
    REJECT_BTN: ComponentID | dict = ComponentID()
    CANCEL_BTN: ComponentID | dict = ComponentID()
    F_FAILURE: ComponentID | dict = ComponentID()

    def _run_ids_(self) -> None:
        self.TARGET_STORE_ID = self.register(type="store", name="target")
        self.APPROVE_BTN = self.register(type="button", name="approve")
        self.REJECT_BTN = self.register(type="button", name="reject")
        self.CANCEL_BTN = self.register(type="button", name="cancel")
        self.F_FAILURE = self.register(type="field", name="failure")

    def _resolve_buttons_(self) -> list:
        return [
            ButtonAPI(id=self.APPROVE_BTN, label=self._icon_("bi bi-check-lg", "Approve", tint="success"), background="secondary", tooltip="Accept the selected gated runs · requires the Moderator role"),
            ButtonAPI(id=self.REJECT_BTN, label=self._icon_("bi bi-x-lg", "Reject", tint="danger"), background="secondary", tooltip="Reject the selected gated runs · requires the Moderator role"),
            ButtonAPI(id=self.CANCEL_BTN, label=self._icon_("bi bi-stop-circle", "Cancel", tint="danger"), background="secondary", tooltip="Terminate the selected live runs · records the As Failure outcome"),
            SwitchAPI(id=self.F_FAILURE, label="As Failure", value=False, classname="scheduler-switch", tooltip="Outcome recorded by Cancel · off records Success · on records Failure", placement="top"),
        ]

    def _resolve_(self, verb: str, uids):
        from flask_login import current_user
        if not current_user.grants(RoleAPI.Moderator):
            self.app.notify.error("Moderator role required to resolve runs", header="Forbidden")
            return dash.no_update
        uids = [uids] if isinstance(uids, str) else list(uids or [])
        if not uids:
            self.app.notify.warning("Select a run first", header="No Selection")
            return dash.no_update
        by = self._current_owner_() or "UI"
        resolved = 0
        for uid in uids:
            if (self._manager_.approve(uid, by) if verb == "approve" else self._manager_.reject(uid, by)): resolved += 1
        if resolved: self.app.notify.success(f"Run '{uids[0]}' {verb}d" if resolved == 1 else f"{resolved} runs {verb}d", header="Done")
        else: self.app.notify.warning("No selected run is awaiting approval or review", header="No Action")
        return uuid.uuid4().hex if resolved else dash.no_update

    @clientside_callback(
        Output(APPROVE_BTN, "disabled"),
        Output(REJECT_BTN, "disabled"),
        Output(CANCEL_BTN, "disabled"),
        Input("TABLE_ID", "selected_rows"),
        State("TABLE_ID", "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_(self):
        return self.app.asset("Callbacks/GateRuns.js", url=False)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(APPROVE_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _approve_(self, clicks, target):
        return self._resolve_("approve", target)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(REJECT_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _reject_(self, clicks, target):
        return self._resolve_("reject", target)

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(CANCEL_BTN, "n_clicks"),
        State("TARGET_STORE_ID", "data"),
        State(F_FAILURE, "value"),
        on_click=InjectionType.Hidden,
    )
    def _cancel_(self, clicks, target, failure):
        uids = [target] if isinstance(target, str) else list(target or [])
        if not uids:
            self.app.notify.warning("Select a run first", header="No Selection")
            return dash.no_update
        by = self._current_owner_() or "UI"
        cancelled = sum(1 for uid in uids if self._manager_.cancel(uid, failure=bool(failure), by=by))
        if not cancelled:
            self.app.notify.warning("No selected run is live", header="No Action")
            return dash.no_update
        outcome = "Failure" if failure else "Success"
        self.app.notify.success(f"{cancelled} run(s) cancelled as {outcome}", header="Done")
        return uuid.uuid4().hex

class SchedulerPageAPI(SchedulerBaseAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler", redirect="/scheduler/workflows", button="Scheduler", icon="bi bi-calendar2-week", description="Create, schedule and monitor workflows, tasks and their runs")

    def content(self) -> list:
        return []

class SchedulerWorkflowsPageAPI(SchedulerWorkflowAPI, SchedulerSelectionAPI, TableAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/workflows", button="Workflows", icon="bi bi-calendar2-week", description="Group tasks into scheduled dependency workflows")

    def ids(self) -> None:
        super().ids()
        self._entity_ids_()
        self._workflow_ids_()

    def _columns_(self) -> list:
        return self._WORKFLOW_COLUMNS_

    def _detail_base_(self):
        return self.anchor

    def _rows_(self) -> list:
        return [self._workflow_row_(workflow) for workflow in self._manager_.workflows()]

    def _fingerprint_(self):
        return self._manager_.fingerprint("Scheduler", "Workflow")

    def _actions_(self) -> list:
        return self._lifecycle_buttons_()

    def _extras_(self) -> list:
        return [self._modal_(), StorageAPI(id=self.MODE_STORE_ID, data={}), StorageAPI(id=self.TARGET_STORE_ID, data=None)]

class SchedulerWorkflowDetailPageAPI(SchedulerWorkflowAPI, SchedulerDetailAPI):

    DAG_GRAPH_ID: ComponentID | dict = ComponentID()
    SUB_TABLE_ID: ComponentID | dict = ComponentID()
    SUB_CONFIG_STORE_ID: ComponentID | dict = ComponentID()
    SUB_OPEN_BTN: ComponentID | dict = ComponentID()
    CYCLE_TABLE_ID: ComponentID | dict = ComponentID()
    LINK_PRED: ComponentID | dict = ComponentID()
    LINK_SUCC: ComponentID | dict = ComponentID()
    LINK_BTN: ComponentID | dict = ComponentID()
    UNLINK_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/workflows/:uid", button="Workflow", icon="bi bi-calendar2-week", parametric=True)

    def ids(self) -> None:
        self._entity_ids_()
        self._workflow_ids_()
        self._detail_ids_()
        self.DAG_GRAPH_ID = self.register(type="graph", name="dag")
        self.SUB_TABLE_ID = self.register(type="table", name="tasks")
        self.SUB_CONFIG_STORE_ID = self.register(type="store", name="sub-config")
        self.SUB_OPEN_BTN = self.register(type="button", name="task-open")
        self.CYCLE_TABLE_ID = self.register(type="table", name="cycles")
        self.LINK_PRED = self.register(type="field", name="link-predecessor")
        self.LINK_SUCC = self.register(type="field", name="link-successor")
        self.LINK_BTN = self.register(type="button", name="link")
        self.UNLINK_BTN = self.register(type="button", name="unlink")

    def _fingerprint_(self) -> str:
        return self._manager_.fingerprint("Scheduler", "Task", "Run")

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            html.H1("Workflow", id=self.TITLE_ID, className="page-title"),
            self._toolbar_([self._refresh_button_()] + self._lifecycle_buttons_(insert=False)),
            html.Div(id=self.FIELDS_ID),
            html.Div("Dependencies", className="scheduler-subtitle"),
            html.Div([
                *SelectAPI(id=self.LINK_PRED, options=[], placeholder="Predecessor", style={"maxWidth": "200px"}).build(),
                html.Span("→", className="scheduler-arrow"),
                *SelectAPI(id=self.LINK_SUCC, options=[], placeholder="Successor", style={"maxWidth": "200px"}).build(),
                *ButtonAPI(id=self.LINK_BTN, label=self._icon_("bi bi-link-45deg", "Link", tint="primary"), background="secondary", tooltip="Make the successor wait for the predecessor").build(),
                *ButtonAPI(id=self.UNLINK_BTN, label=self._icon_("bi bi-scissors", "Unlink", tint="danger"), background="secondary", tooltip="Remove the dependency between the two tasks").build(),
            ], className="table-toolbar"),
            PlotlyAPI(id=self.DAG_GRAPH_ID, figure=self._empty_figure_("Loading dependency graph"), config={"displayModeBar": False, "displaylogo": False}, style={"height": "42vh", "minHeight": "280px"}),
            self._legend_(),
            html.Div("Tasks", className="scheduler-subtitle"),
            TableAPI.navigable(self._table_(self.SUB_TABLE_ID, self._MEMBER_COLUMNS_, self._MARKDOWN_COLUMNS_), "/scheduler/tasks"),
            self._toolbar_([ButtonAPI(id=self.SUB_OPEN_BTN, label=self._icon_("bi bi-box-arrow-up-right", "Open Task"), background="secondary", tooltip="Open the selected tasks · one opens here · several open in new tabs")], "table-bar"),
            html.Div("Cycles", className="scheduler-subtitle"),
            self._table_(self.CYCLE_TABLE_ID, self._CYCLE_COLUMNS_, self._MARKDOWN_COLUMNS_, row_selectable=False),
            self._modal_(),
            StorageAPI(id=self.SUB_CONFIG_STORE_ID, data=self._config_("/scheduler/tasks")),
            StorageAPI(id=self.MODE_STORE_ID, data={}),
            *self._hidden_(),
        ]

    @serverside_callback(
        Output("BREADCRUMB_ID", "children"),
        Output("TITLE_ID", "children"),
        Output("TARGET_STORE_ID", "data"),
        Output("FIELDS_ID", "children"),
        Output(DAG_GRAPH_ID, "figure"),
        Output(SUB_TABLE_ID, "data"),
        Output(CYCLE_TABLE_ID, "data"),
        Output(LINK_PRED, "options"),
        Output(LINK_SUCC, "options"),
        Input("RELOAD_STORE_ID", "data"),
        State("GLOBAL_LOCATION_ID", "pathname"),
    )
    def _populate_(self, token, pathname):
        from dash.exceptions import PreventUpdate
        uid = self.capture(pathname)
        if uid is None: raise PreventUpdate
        workflow = self._manager_.workflow(uid)
        if workflow is None:
            return self._breadcrumb_(uid), uid, [uid], self._details_([("Status", "Workflow not found")]), self._empty_figure_("Workflow not found"), [], [], [], []
        members = self._manager_.tasks(workflow=uid)
        latest = self._manager_.latest()
        cycles = [self._cycle_row_(cycle) for cycle in self._manager_.cycles(workflow=uid, limit=10)]
        pairs = [("Owner", workflow.get("Owner")), ("Kind", workflow.get("Kind")), ("Schedule", workflow.get("Schedule")), ("Enabled", workflow.get("Enabled")), ("Waits", workflow.get("Waits") is not False), ("Description", workflow.get("Description")), ("Tasks", len(members)), ("Updated", self._stamp_(workflow.get("UpdatedAt")))]
        rows = [self._task_row_(member, latest.get(member["UID"])) for member in members]
        options = [{"label": member["UID"], "value": member["UID"]} for member in members]
        return self._breadcrumb_(uid), workflow.get("Name") or uid, [uid], self._details_(pairs), self._figure_(uid, members, latest), rows, cycles, options, options

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(LINK_BTN, "n_clicks"),
        State(LINK_PRED, "value"),
        State(LINK_SUCC, "value"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _link_(self, clicks, predecessor, successor, target):
        uid = target[0] if target else None
        if uid is None: return dash.no_update
        if not predecessor or not successor or predecessor == successor:
            self.app.notify.warning("Pick two distinct tasks", header="Invalid Dependency")
            return dash.no_update
        if self._manager_.link(uid, predecessor, successor) is None:
            self.app.notify.error("Link rejected — it would create a cycle", header="Invalid Dependency")
            return dash.no_update
        self.app.notify.success(f"Linked {predecessor} → {successor}", header="Done")
        return uuid.uuid4().hex

    @serverside_callback(
        Output("RELOAD_STORE_ID", "data"),
        Input(UNLINK_BTN, "n_clicks"),
        State(LINK_PRED, "value"),
        State(LINK_SUCC, "value"),
        State("TARGET_STORE_ID", "data"),
        on_click=InjectionType.Hidden,
    )
    def _unlink_(self, clicks, predecessor, successor, target):
        uid = target[0] if target else None
        if uid is None: return dash.no_update
        if not predecessor or not successor or predecessor == successor:
            self.app.notify.warning("Pick two distinct tasks", header="Invalid Dependency")
            return dash.no_update
        self._manager_.unlink(uid, predecessor, successor)
        self.app.notify.success(f"Unlinked {predecessor} → {successor}", header="Done")
        return uuid.uuid4().hex

    @clientside_callback(
        Output("GLOBAL_LOCATION_ID", "pathname"),
        Input(SUB_OPEN_BTN, "n_clicks"),
        State(SUB_CONFIG_STORE_ID, "data"),
        State(SUB_TABLE_ID, "selected_rows"),
        State(SUB_TABLE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _subopen_(self):
        return self.app.asset("Callbacks/TableOpen.js", url=False)

class SchedulerTasksPageAPI(SchedulerTaskAPI, SchedulerSelectionAPI, TableAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/tasks", button="Tasks", icon="bi bi-list-check", description="Create, schedule and monitor tasks")

    def ids(self) -> None:
        super().ids()
        self._entity_ids_()
        self._task_ids_()

    def _columns_(self) -> list:
        return self._TASK_COLUMNS_

    def _markdown_columns_(self) -> set:
        return self._MARKDOWN_COLUMNS_

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
        return [self._modal_(), StorageAPI(id=self.MODE_STORE_ID, data={}), StorageAPI(id=self.TARGET_STORE_ID, data=None)]

class SchedulerTaskDetailPageAPI(SchedulerTaskAPI, SchedulerDetailAPI):

    SUB_TABLE_ID: ComponentID | dict = ComponentID()
    SUB_CONFIG_STORE_ID: ComponentID | dict = ComponentID()
    SUB_OPEN_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/tasks/:uid", button="Task", icon="bi bi-list-check", parametric=True)

    def ids(self) -> None:
        self._entity_ids_()
        self._task_ids_()
        self._detail_ids_()
        self.SUB_TABLE_ID = self.register(type="table", name="runs")
        self.SUB_CONFIG_STORE_ID = self.register(type="store", name="sub-config")
        self.SUB_OPEN_BTN = self.register(type="button", name="run-open")

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            html.H1("Task", id=self.TITLE_ID, className="page-title"),
            self._toolbar_([self._refresh_button_()] + self._lifecycle_buttons_(insert=False) + self._intervention_buttons_()),
            html.Div(id=self.FIELDS_ID),
            html.Div("Runs", className="scheduler-subtitle"),
            TableAPI.navigable(self._table_(self.SUB_TABLE_ID, self._TASK_RUN_COLUMNS_, self._MARKDOWN_COLUMNS_), "/scheduler/runs"),
            self._toolbar_([ButtonAPI(id=self.SUB_OPEN_BTN, label=self._icon_("bi bi-box-arrow-up-right", "Open Run"), background="secondary", tooltip="Open the selected runs · one opens here · several open in new tabs")], "table-bar"),
            self._modal_(),
            StorageAPI(id=self.SUB_CONFIG_STORE_ID, data=self._config_("/scheduler/runs")),
            StorageAPI(id=self.MODE_STORE_ID, data={}),
            *self._hidden_(),
        ]

    @serverside_callback(
        Output("BREADCRUMB_ID", "children"),
        Output("TITLE_ID", "children"),
        Output("TARGET_STORE_ID", "data"),
        Output("FIELDS_ID", "children"),
        Output(SUB_TABLE_ID, "data"),
        Input("RELOAD_STORE_ID", "data"),
        State("GLOBAL_LOCATION_ID", "pathname"),
    )
    def _populate_(self, token, pathname):
        from dash.exceptions import PreventUpdate
        uid = self.capture(pathname)
        if uid is None: raise PreventUpdate
        task = self._manager_.task(uid)
        if task is None:
            return self._breadcrumb_(uid), uid, [uid], self._details_([("Status", "Task not found")]), []
        pairs = [("Owner", task.get("Owner")), ("Type", task.get("Type")), ("Kind", task.get("Kind")), ("Path", task.get("Path")), ("Schedule", task.get("Schedule")), ("Workflow", task.get("WID")), ("Enabled", task.get("Enabled")), ("Waits", task.get("Waits") is not False), ("Tolerates", task.get("Tolerates") is not False), ("Requires Approval", task.get("RequiresApproval")), ("Requires Review", task.get("RequiresReview")), ("Max Retry", task.get("MaxRetry")), ("Retry Delay", task.get("RetryDelay")), ("Description", task.get("Description")), ("Updated", self._stamp_(task.get("UpdatedAt")))]
        runs = [self._run_row_(run) for run in self._manager_.runs(task=uid, limit=50)]
        return self._breadcrumb_(uid), task.get("Name") or uid, [uid], self._details_(pairs), runs

    @clientside_callback(
        Output("GLOBAL_LOCATION_ID", "pathname"),
        Input(SUB_OPEN_BTN, "n_clicks"),
        State(SUB_CONFIG_STORE_ID, "data"),
        State(SUB_TABLE_ID, "selected_rows"),
        State(SUB_TABLE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _subopen_(self):
        return self.app.asset("Callbacks/TableOpen.js", url=False)

class SchedulerRunsPageAPI(SchedulerRunAPI, SchedulerSelectionAPI, TableAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/runs", button="Runs", icon="bi bi-clock-history", description="Audit run history and resolve approval and review gates")

    def ids(self) -> None:
        super().ids()
        self._run_ids_()

    def _columns_(self) -> list:
        return self._RUN_COLUMNS_

    def _markdown_columns_(self) -> set:
        return self._MARKDOWN_COLUMNS_

    def _detail_base_(self):
        return self.anchor

    def _rows_(self) -> list:
        return [self._run_row_(run) for run in self._manager_.runs(limit=50)]

    def _fingerprint_(self):
        return self._manager_.fingerprint("Scheduler", "Run")

    def _actions_(self) -> list:
        return self._resolve_buttons_()

    def _extras_(self) -> list:
        return [StorageAPI(id=self.TARGET_STORE_ID, data=None)]

class SchedulerRunDetailPageAPI(SchedulerRunAPI, SchedulerDetailAPI):

    LOG_ID: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/runs/:uid", button="Run", icon="bi bi-clock-history", parametric=True)

    def ids(self) -> None:
        self._run_ids_()
        self._detail_ids_()
        self.LOG_ID = self.register(type="div", name="log")

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            html.H1("Run", id=self.TITLE_ID, className="page-title"),
            self._toolbar_([self._refresh_button_()] + self._resolve_buttons_()),
            html.Div(id=self.FIELDS_ID),
            html.Div("Log", className="scheduler-subtitle"),
            html.Div(id=self.LOG_ID),
            *self._hidden_(),
        ]

    _ANSI_ = re.compile(r"\x1b\[([0-9;]*)m")
    _BASICS_ = ("#000000", "#cd3131", "#0dbc79", "#e5e510", "#2472c8", "#bc3fbc", "#11a8cd", "#e5e5e5", "#666666", "#f14c4c", "#23d18b", "#f5f543", "#3b8eea", "#d670d6", "#29b8db", "#ffffff")

    @staticmethod
    def _tail_(path):
        if not path: return "(no log)"
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
        except OSError:
            return "(log unavailable)"
        try:
            data = raw.decode("utf-8")
        except UnicodeDecodeError:
            data = raw.decode("windows-1252", "replace")
        return data[-8000:] if data.strip() else "(empty log)"

    @classmethod
    def _shade_(cls, code: int) -> str:
        if code < 16: return cls._BASICS_[code]
        if code < 232:
            code -= 16
            levels = (0, 95, 135, 175, 215, 255)
            return f"#{levels[code // 36]:02x}{levels[code % 36 // 6]:02x}{levels[code % 6]:02x}"
        gray = 8 + 10 * (code - 232)
        return f"#{gray:02x}{gray:02x}{gray:02x}"

    @classmethod
    def _paint_(cls, text: str) -> list:
        spans, color, cursor = [], None, 0
        for match in cls._ANSI_.finditer(text):
            if match.start() > cursor:
                chunk = text[cursor:match.start()]
                spans.append(html.Span(chunk, style={"color": color}) if color else chunk)
            cursor = match.end()
            codes = [int(part) for part in match.group(1).split(";") if part] or [0]
            if codes[0] == 0: color = None
            elif len(codes) == 3 and codes[0] == 38 and codes[1] == 5: color = cls._shade_(codes[2])
        if cursor < len(text):
            spans.append(html.Span(text[cursor:], style={"color": color}) if color else text[cursor:])
        return spans

    @serverside_callback(
        Output("BREADCRUMB_ID", "children"),
        Output("TITLE_ID", "children"),
        Output("TARGET_STORE_ID", "data"),
        Output("FIELDS_ID", "children"),
        Output(LOG_ID, "children"),
        Input("RELOAD_STORE_ID", "data"),
        State("GLOBAL_LOCATION_ID", "pathname"),
    )
    def _populate_(self, token, pathname):
        from dash.exceptions import PreventUpdate
        uid = self.capture(pathname)
        if uid is None: raise PreventUpdate
        run = self._manager_.run(uid)
        if run is None:
            return self._breadcrumb_(uid), uid, [uid], self._details_([("Status", "Run not found")]), "(no log)"
        task = dcc.Link(run.get("TID"), href=f"/scheduler/tasks/{run.get('TID')}", className="scheduler-crumb") if run.get("TID") else None
        memory = f"{run.get('Memory') / 1048576:.1f} MB" if isinstance(run.get("Memory"), (int, float)) else None
        duration = f"{run.get('Duration'):.2f} s" if isinstance(run.get("Duration"), (int, float)) else None
        pairs = [("Status", self._led_dot_(run.get("Status"))), ("Task", task), ("Kind", run.get("Kind")), ("Retry", run.get("Retry")), ("Exit Code", run.get("ExitCode")), ("Duration", duration), ("Memory", memory), ("PID", run.get("PID")), ("Started", self._stamp_(run.get("StartedAt"))), ("Stopped", self._stamp_(run.get("StoppedAt"))), ("Auditor", run.get("Auditor")), ("Cycle", run.get("CID"))]
        return self._breadcrumb_(uid), f"Run {uid[:12]}", [uid], self._details_(pairs), html.Pre(self._paint_(self._tail_(run.get("Log"))), className="scheduler-log")