import uuid

import dash
from dash import html

from Library.App.V2 import CrumbAPI, BreadcrumbAPI, PageAPI, RefreshAPI, TableAPI, LightweightTableAPI, WorkspaceAPI, ComponentID, Output, Input, clientside_callback, StorageAPI, NetworkAPI
from Library.Web.Core.Status import StatusAPI
from Library.Scheduler import ManagerAPI
from Library.Utility.Typing import MISSING

class SchedulerBaseAPI(StatusAPI, PageAPI):

    TARGET_STORE_ID: ComponentID | dict = ComponentID()
    BREADCRUMB_ID: ComponentID | dict = ComponentID()
    FIELDS_ID: ComponentID | dict = ComponentID()

    _WORKFLOW_COLUMNS_ = ["Status", "UID", "Name", "Owner", "Enabled", "Kind", "Waits", "Schedule"]
    _TASK_COLUMNS_ = ["Status", "UID", "Name", "Type", "Kind", "Enabled", "Waits", "Tolerates", "Schedule", "WID", "MaxRetry"]
    _MEMBER_COLUMNS_ = ["Status", "UID", "Name", "Type", "Kind", "Enabled"]
    _RUN_COLUMNS_ = ["Status", "UID", "CID", "TID", "Kind", "Retry", "StartedAt", "StoppedAt", "Duration", "ExitCode", "PID", "Auditor"]
    _TASK_RUN_COLUMNS_ = ["Status", "UID", "Kind", "Retry", "StartedAt", "StoppedAt", "Duration", "ExitCode", "PID", "Auditor"]
    _CYCLE_COLUMNS_ = ["Status", "UID", "Kind", "StartedAt", "StoppedAt"]
    _MARKDOWN_COLUMNS_ = {"Status"}
    _IDENTIFIER_COLUMNS_ = {"PID", "ExitCode", "Retry"}
    _DAG_FLOOR_ = 200
    _DAG_LANE_ = 78
    _VERBS_ = {"run": "dispatched", "enable": "enabled", "disable": "disabled", "delete": "deleted", "skip": "skipped", "cancel": "canceled"}

    def __init__(self, *, app, **kwargs) -> None:
        super().__init__(app=app, **kwargs)
        self._manager_ = ManagerAPI(database="Quant")

    @staticmethod
    def _icon_(icon: str, label: str = None, tint: str = None) -> list:
        return TableAPI._icon_(icon, label, tint)

    @staticmethod
    def _toolbar_(buttons: list, classname: str = "table-toolbar") -> html.Div:
        return TableAPI.toolbar(buttons, classname)

    @classmethod
    def _payload_(cls, name: str, columns: list, rows: list, base: str = None, outbound: dict = None) -> WorkspaceAPI:
        sheet = TableAPI.sheet(name, columns, rows, "UID", markdown=cls._MARKDOWN_COLUMNS_)
        return WorkspaceAPI(title=name, sheets=[sheet], outbound=outbound, navigation={"base": base, "key": "UID"} if base else None)

    @classmethod
    def _grid_(cls, id: dict, carrier: dict, name: str, columns: list, base: str = None, outbound: dict = None, height: str = MISSING) -> list:
        grid = LightweightTableAPI(id=id, carrier=carrier, selection=outbound if outbound else MISSING, workspace=name.lower(), payload=cls._payload_(name, columns, [], base, outbound), height=height)
        return grid.build()

    def _markdown_columns_(self) -> set:
        return self._MARKDOWN_COLUMNS_

    @staticmethod
    def _fired_(cid: dict) -> bool:
        return dash.ctx.triggered_id == cid

    @staticmethod
    def _current_owner_():
        from flask_login import current_user
        return getattr(current_user, "Username", None) or getattr(current_user, "Name", None)

    def _intervene_(self, entity: str, verb: str, uids, failure, blocked: str):
        uids = [uids] if isinstance(uids, str) else list(uids or [])
        if not uids:
            self.app.notify.warning(f"Select a {entity} first", header="No Selection")
            return dash.no_update
        by = self._current_owner_()
        action = getattr(self._manager_, verb)
        done = sum(1 for uid in uids if action(uid, failure=bool(failure), by=by))
        if not done:
            self.app.notify.warning(blocked, header="No Action")
            return dash.no_update
        self.app.notify.success(f"{done} {entity}(s) {self._VERBS_[verb]} as {'Failure' if failure else 'Success'}", header="Done")
        return uuid.uuid4().hex

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
            if column == "Duration" and isinstance(value, (int, float)): value = round(value, 2)
            elif column in self._IDENTIFIER_COLUMNS_ and value is not None: value = str(value)
            row[column] = value
        row["Status"] = self._led_(run.get("Status"))
        return row

    def _workflow_row_(self, workflow: dict, status=None) -> dict:
        row = {column: self._stamp_(workflow.get(column)) for column in self._WORKFLOW_COLUMNS_}
        row["Status"] = self._led_(status)
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

    def _pairs_(self, row: dict, fields, extra: list = None) -> list:
        pairs = [(entry.label, entry.read(row, self)) for entry in fields if not entry.identity and entry.stored]
        return pairs + (extra or []) + [("Updated", self._stamp_(row.get("UpdatedAt")))]

    def _label_(self, row: dict, uid: str) -> str:
        return (row or {}).get("Name") or uid

    def _lineage_(self, uid: str) -> list:
        return [CrumbAPI(label="Workflow", href="/scheduler/workflow")]

    def _breadcrumb_(self, uid: str) -> list:
        return BreadcrumbAPI(trail=self._lineage_(uid) + [CrumbAPI(label=self._crumb_(uid))]).build()

    def _crumb_(self, uid: str) -> str:
        return uid

    @classmethod
    def _empty_figure_(cls, text: str):
        return NetworkAPI.blank(text, cls._NEUTRAL_)

    def _nodes_(self, members: list, latest: dict) -> list:
        return [{"uid": task["UID"], "color": self._STATUS_COLOR_.get(latest.get(task["UID"]))} for task in members]

    def _edges_(self, wid: str) -> list:
        return [(row["Predecessor"], row["Successor"]) for row in self._manager_.dependencies(wid)]

    def _sequenced_(self, wid: str, members: list, latest: dict) -> list:
        order = NetworkAPI.order(self._nodes_(members, latest), self._edges_(wid))
        rank = {uid: index for index, uid in enumerate(order)}
        return sorted(members, key=lambda task: rank.get(task["UID"], len(rank)))

    def _figure_(self, wid: str, members: list, latest: dict):
        return NetworkAPI.render(self._nodes_(members, latest), self._edges_(wid), self._NEUTRAL_, self._UNRUN_COLOR_, "Workflow has no tasks")

    def _canvas_(self, wid: str, members: list, latest: dict) -> dict:
        widest = NetworkAPI.span(self._nodes_(members, latest), self._edges_(wid))
        return {"height": f"{max(self._DAG_FLOOR_, 80 + widest * self._DAG_LANE_)}px"}

class SchedulerSelectionAPI:

    @clientside_callback(
        Output(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _target_sync_(self):
        return self.app.asset("Callbacks/Select.js", url=False)

class SchedulerDetailAPI(RefreshAPI, SchedulerBaseAPI):

    def _detail_ids_(self) -> None:
        self._refresh_ids_()
        self.BREADCRUMB_ID = self.register(type="div", name="breadcrumb")
        self.FIELDS_ID = self.register(type="div", name="fields")

    def _fingerprint_(self) -> str:
        return self._manager_.fingerprint("Scheduler", "Run")

    def _hidden_(self) -> list:
        return [StorageAPI(id=self.TARGET_STORE_ID, data=None), *self._polling_()]