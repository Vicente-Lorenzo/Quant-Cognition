import re

import dash
from dash import html, dcc
from dash.exceptions import PreventUpdate

from Library.App.V2 import GlobalAPI, CrumbAPI, RefreshAPI, TableAPI, ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback, SwitchAPI, ButtonAPI, StorageAPI
from Library.Auth import RoleAPI
from Library.Utility.Memory import memory_to_string
from Library.Web.Scheduler.Base import SchedulerBaseAPI, SchedulerSelectionAPI, SchedulerDetailAPI

class SchedulerRunAPI(SchedulerBaseAPI):

    def _lineage_(self, row: dict | None) -> list:
        task = self._manager_.task(row["TID"]) if row and row.get("TID") else None
        trail = self._task_trail_(task)
        if task: trail.append(CrumbAPI(label=self._label_(task, row["TID"]), href=f"/scheduler/task/{row['TID']}"))
        return trail + [CrumbAPI(label="Run", href="/scheduler/run")]

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
            SwitchAPI(id=self.F_FAILURE, label="As Failure", value=False, classname="app-switch", tooltip="Outcome recorded by Cancel · off records Success · on records Failure", placement="top"),
        ]

    def _resolve_(self, verb: str, uids):
        from flask_login import current_user
        if not current_user.grants(RoleAPI.Moderator):
            self.app.notify.error("Moderator role required to resolve runs", header="Forbidden")
            return dash.no_update
        uids = self._selection_(uids, "Select a run first")
        if not uids: return dash.no_update
        by, action = self.app.actor(), self._manager_.approve if verb == "approve" else self._manager_.reject
        return self._tally_(uids, lambda uid: action(uid, by=by), f"run(s) {verb}d", "No selected run is awaiting approval or review")

    @clientside_callback(
        Output(APPROVE_BTN, "disabled"),
        Output(REJECT_BTN, "disabled"),
        Output(CANCEL_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_(self):
        return self.app.asset("Callbacks/GateRuns.js", url=False)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(APPROVE_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _approve_(self, clicks, target):
        return self._resolve_("approve", target)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(REJECT_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _reject_(self, clicks, target):
        return self._resolve_("reject", target)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(CANCEL_BTN, "n_clicks"),
        State(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        State(F_FAILURE, "value"),
        on_click=InjectionType.Hidden,
    )
    def _cancel_(self, clicks, target, failure):
        return self._intervene_("run", "cancel", target, failure, "No selected run is live")

class SchedulerRunPageAPI(SchedulerRunAPI, SchedulerSelectionAPI, TableAPI):

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/run", button="Run", icon="bi bi-clock-history", description="Audit run history and resolve approval and review gates")

    def ids(self) -> None:
        super().ids()
        self._run_ids_()

    def _columns_(self) -> list:
        return self._RUN_COLUMNS_

    def _rows_(self) -> list:
        return [self._run_row_(run) for run in self._manager_.runs(limit=50)]

    def _actions_(self) -> list:
        return self._resolve_buttons_()

    def _extras_(self) -> list:
        return [self._legend_(), StorageAPI(id=self.TARGET_STORE_ID, data=None)]

class SchedulerRunDetailPageAPI(SchedulerRunAPI, SchedulerDetailAPI):

    LOG_ID: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/scheduler/run/:uid", button="Run", icon="bi bi-clock-history", parametric=True)

    def ids(self) -> None:
        self._run_ids_()
        self._detail_ids_()
        self.LOG_ID = self.register(type="div", name="log")

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            self.toolbar([self._refresh_button_()] + self._resolve_buttons_()),
            html.Div(id=self.FIELDS_ID),
            html.Div("Log", className="scheduler-subtitle"),
            html.Div(id=self.LOG_ID),
            *self._hidden_(),
        ]

    _ANSI_ = re.compile(r"\x1b\[([0-9;]*)m")
    _BASICS_ = ("#000000", "#cd3131", "#0dbc79", "#e5e510", "#2472c8", "#bc3fbc", "#11a8cd", "#e5e5e5", "#666666", "#f14c4c", "#23d18b", "#f5f543", "#3b8eea", "#d670d6", "#29b8db", "#ffffff")

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
        Output(SchedulerBaseAPI.BREADCRUMB_ID, "children"),
        Output(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        Output(SchedulerBaseAPI.FIELDS_ID, "children"),
        Output(LOG_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        State(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
    )
    def _populate_(self, token, pathname):
        uid = self.capture(pathname)
        if uid is None: raise PreventUpdate
        run = self._manager_.run(uid)
        if run is None:
            return self._breadcrumb_(uid, None), [uid], self._details_([("Status", "Run not found")]), "(no log)"
        task = dcc.Link(run.get("TID"), href=f"/scheduler/task/{run.get('TID')}", className="scheduler-crumb") if run.get("TID") else None
        memory = memory_to_string(run.get("Memory")) if isinstance(run.get("Memory"), (int, float)) else None
        duration = f"{run.get('Duration'):.2f} s" if isinstance(run.get("Duration"), (int, float)) else None
        pairs = [("Status", self._led_dot_(run.get("Status"))), ("Task", task), ("Kind", run.get("Kind")), ("Retry", run.get("Retry")), ("Exit Code", run.get("ExitCode")), ("Duration", duration), ("Memory", memory), ("PID", run.get("PID")), ("Started", self._stamp_(run.get("StartedAt"))), ("Stopped", self._stamp_(run.get("StoppedAt"))), ("Auditor", run.get("Auditor")), ("Cycle", run.get("CID"))]
        return self._breadcrumb_(uid, run), [uid], self._details_(pairs), html.Pre(self._paint_(self._manager_.log(uid) or "(no log)"), className="scheduler-log")