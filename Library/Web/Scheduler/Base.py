import dash

from Library.App.V2 import GlobalAPI, CrumbAPI, BreadcrumbAPI, RefreshAPI, TableAPI, WorkspaceAPI, ComponentID, Output, Input, State, InjectionType, clientside_callback, StorageAPI, NetworkAPI, ControlType
from Library.Auth import AccessAPI
from Library.Web.Core.Managed import ManagedPageAPI
from Library.Utility.Typing import MISSING

class SchedulerBaseAPI(ManagedPageAPI):

    TARGET_STORE_ID: ComponentID | dict = ComponentID()
    BREADCRUMB_ID: ComponentID | dict = ComponentID()
    FIELDS_ID: ComponentID | dict = ComponentID()

    _WORKFLOW_COLUMNS_ = ["Status", "UID", "Name", "Owner", "Run", "Edit", "Access", "Enabled", "Kind", "Waits", "Schedule", "Zone"]
    _TASK_COLUMNS_ = ["Status", "UID", "Name", "Owner", "Run", "Edit", "Access", "Type", "Kind", "Enabled", "Waits", "Tolerates", "Schedule", "WID", "MaxRetry"]
    _MEMBER_COLUMNS_ = ["Status", "UID", "Name", "Type", "Kind", "Enabled"]
    _RUN_COLUMNS_ = ["Status", "UID", "CID", "TID", "Kind", "Retry", "StartedAt", "StoppedAt", "Duration", "ExitCode", "PID", "Auditor"]
    _TASK_RUN_COLUMNS_ = ["Status", "UID", "Kind", "Retry", "StartedAt", "StoppedAt", "Duration", "ExitCode", "PID", "Auditor"]
    _CYCLE_COLUMNS_ = ["Status", "UID", "Kind", "StartedAt", "StoppedAt"]
    _IDENTIFIER_COLUMNS_ = {"PID", "ExitCode", "Retry"}
    _DAG_FLOOR_ = 200
    _DAG_LANE_ = 78
    _VERBS_ = {"run": "dispatched", "enable": "enabled", "disable": "disabled", "delete": "deleted", "skip": "skipped", "cancel": "canceled"}

    @classmethod
    def _payload_(cls, name: str, columns: list, rows: list, base: str = None, outbound: dict = None) -> WorkspaceAPI:
        return TableAPI.workspace(name, columns, rows, markdown=cls._MARKDOWN_COLUMNS_, base=base, selection=outbound)

    @classmethod
    def _grid_(cls, id: dict, carrier: dict, name: str, columns: list, base: str = None, outbound: dict = None, height: str = MISSING) -> list:
        return TableAPI.table(id, name, columns, [], markdown=cls._MARKDOWN_COLUMNS_, base=base, carrier=carrier, selection=outbound if outbound else MISSING, height=height).build()

    def _intervene_(self, entity: str, verb: str, uids, failure, blocked: str):
        uids = self._selection_(uids, f"Select a {entity} first")
        if not uids: return dash.no_update
        by, action = self.app.actor(), getattr(self._manager_, verb)
        return self._tally_(uids, lambda uid: action(uid, failure=bool(failure), by=by), f"{entity}(s) {self._VERBS_[verb]} as {'Failure' if failure else 'Success'}", blocked)

    def _apply_(self, entity: str, verb: str, uids):
        uids = self._selection_(uids, f"Select a {entity} first")
        if not uids: return dash.no_update
        done, error = [], None
        for uid in uids:
            try:
                getattr(self._manager_, f"{verb}_{entity}")(uid, by=self.app.actor())
                done.append(uid)
            except Exception as reason:
                error = str(reason)
        if error: self.app.notify.error(error, header="Action Failed")
        if not done: return dash.no_update
        detail = f"{entity.capitalize()} '{done[0]}'" if len(done) == 1 else f"{len(done)} {entity}s"
        self.app.notify.success(f"{detail} {self._VERBS_[verb]}", header="Done")
        return RefreshAPI.token()

    def _guarded_(self, row: dict, entity: dict, principal) -> dict:
        row["Run"], row["Edit"] = AccessAPI.label(entity.get("RunRole")), AccessAPI.label(entity.get("EditRole"))
        row["Access"] = self._manager_.access(entity, principal).name
        return row

    def _task_row_(self, task: dict, status, principal=None) -> dict:
        row = {column: task.get(column) for column in self._TASK_COLUMNS_}
        row["Status"] = self._led_(status)
        row["Waits"] = task.get("Waits") is not False
        row["Tolerates"] = task.get("Tolerates") is not False
        return self._guarded_(row, task, principal)

    def _run_row_(self, run: dict) -> dict:
        row = {}
        for column in self._RUN_COLUMNS_:
            value = run.get(column)
            if column == "Duration" and isinstance(value, (int, float)): value = round(value, 2)
            elif column in self._IDENTIFIER_COLUMNS_ and value is not None: value = str(value)
            row[column] = value
        row["Status"] = self._led_(run.get("Status"))
        return row

    def _workflow_row_(self, workflow: dict, status=None, principal=None) -> dict:
        row = {column: workflow.get(column) for column in self._WORKFLOW_COLUMNS_}
        row["Status"] = self._led_(status)
        row["Waits"] = workflow.get("Waits") is not False
        return self._guarded_(row, workflow, principal)

    def _cycle_row_(self, cycle: dict) -> dict:
        row = {column: cycle.get(column) for column in self._CYCLE_COLUMNS_}
        row["Status"] = self._led_(cycle.get("Status"))
        return row

    def capture(self, pathname: str):
        parts = self.segments(pathname)
        return parts[0] if parts else None

    def _shown_(self, entry, row: dict):
        value = entry.read(row, self)
        if entry.control is not ControlType.Select: return value
        return next((option["label"] for option in entry.options if option["value"] == value), value)

    def _pairs_(self, row: dict, fields, extra: list = None) -> list:
        pairs = [(entry.label, self._shown_(entry, row)) for entry in fields if not entry.identity and entry.stored]
        return pairs + (extra or []) + [("Updated", self._stamp_(row.get("UpdatedAt")))]

    def _label_(self, row: dict, uid: str) -> str:
        return (row or {}).get("Name") or uid

    def _task_trail_(self, task: dict | None) -> list:
        workflow = self._manager_.workflow(task["WID"]) if task and task.get("WID") else None
        trail = [CrumbAPI(label="Workflow", href="/scheduler/workflow")]
        if workflow: trail.append(CrumbAPI(label=self._label_(workflow, task["WID"]), href=f"/scheduler/workflow/{task['WID']}"))
        return trail + [CrumbAPI(label="Task", href="/scheduler/task")]

    def _lineage_(self, row: dict | None) -> list:
        return [CrumbAPI(label="Workflow", href="/scheduler/workflow")]

    def _breadcrumb_(self, uid: str, row: dict | None) -> list:
        return BreadcrumbAPI(trail=self._lineage_(row) + [CrumbAPI(label=self._crumb_(uid, row))]).build()

    def _crumb_(self, uid: str, row: dict | None) -> str:
        return uid

    @staticmethod
    def _empty_figure_(text: str):
        return NetworkAPI.blank(text)

    def _nodes_(self, members: list, latest: dict) -> list:
        return [{"uid": task["UID"], "color": self._STATUS_COLOR_.get(latest.get(task["UID"]))} for task in members]

    def _edges_(self, wid: str) -> list:
        return [(row["Predecessor"], row["Successor"]) for row in self._manager_.dependencies(wid)]

    def _sequenced_(self, members: list, latest: dict, edges: list) -> list:
        order = NetworkAPI.order(self._nodes_(members, latest), edges)
        rank = {uid: index for index, uid in enumerate(order)}
        return sorted(members, key=lambda task: rank.get(task["UID"], len(rank)))

    @staticmethod
    def _figure_(nodes: list, edges: list, graph):
        return NetworkAPI.render(nodes, edges, placeholder="Workflow has no tasks", graph=graph)

    def _canvas_(self, nodes: list, edges: list, graph) -> dict:
        widest = NetworkAPI.span(nodes, edges, graph=graph)
        return {"height": f"{max(self._DAG_FLOOR_, 80 + widest * self._DAG_LANE_)}px"}

class SchedulerSelectionAPI:

    def _detail_base_(self):
        return self.anchor

    @clientside_callback(
        Output(SchedulerBaseAPI.TARGET_STORE_ID, "data"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _target_sync_(self):
        return self.app.asset("Callbacks/Select.js", url=False)

class SchedulerDetailAPI(SchedulerBaseAPI, RefreshAPI):

    def _detail_ids_(self) -> None:
        self._refresh_ids_()
        self.BREADCRUMB_ID = self.register(type="div", name="breadcrumb")
        self.FIELDS_ID = self.register(type="div", name="fields")

    def _hidden_(self) -> list:
        return [StorageAPI(id=self.TARGET_STORE_ID, data=None), *self._polling_()]

class SchedulerGridDetailAPI(SchedulerDetailAPI):

    SUB_TABLE_ID: ComponentID | dict = ComponentID()
    SUB_CARRIER_ID: ComponentID | dict = ComponentID()
    SUB_STATE_STORE_ID: ComponentID | dict = ComponentID()
    SUB_OPEN_BTN: ComponentID | dict = ComponentID()

    def _grid_ids_(self, rows: str, row: str) -> None:
        self.SUB_TABLE_ID = self.register(type="grid", name=rows)
        self.SUB_CARRIER_ID = self.register(type="script", name=f"{rows}-payload")
        self.SUB_STATE_STORE_ID = self.register(type="store", name=f"{rows}-state")
        self.SUB_OPEN_BTN = self.register(type="button", name=f"{row}-open")

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        Input(SUB_OPEN_BTN, "n_clicks"),
        State(SUB_STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _subopen_(self):
        return self.app.asset("Callbacks/Open.js", url=False)