import uuid
import dash
from dash.exceptions import PreventUpdate

from Library.App.V2.Core.Callback import ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback
from Library.App.V2.Core.Identity import GlobalAPI
from Library.App.V2.Component.Component import ButtonAPI
from Library.Statistic.Workspace import SheetAPI, WorkspaceAPI
from Library.App.V2.Lightweight.Lightweight import LightweightTableAPI
from Library.App.V2.Page.Page import PageAPI, RefreshAPI
from Library.Utility.Typing import MISSING

class TableAPI(RefreshAPI, PageAPI):

    TABLE_ID: ComponentID | dict = ComponentID()
    CARRIER_ID: ComponentID | dict = ComponentID()
    STATE_STORE_ID: ComponentID | dict = ComponentID()
    EDIT_STORE_ID: ComponentID | dict = ComponentID()
    ROW_INSERT_BTN: ComponentID | dict = ComponentID()
    ROW_DELETE_BTN: ComponentID | dict = ComponentID()
    OPEN_BTN: ComponentID | dict = ComponentID()

    _ROW_KEY_ = "UID"
    _SHEET_ = "Rows"
    _EDITABLE_ = False
    _EXTENDABLE_ = True
    _NAVIGABLE_ = True

    def ids(self) -> None:
        self.TABLE_ID = self.register(type="grid", name="grid")
        self.CARRIER_ID = self.register(type="script", name="payload")
        self._refresh_ids_()
        self.STATE_STORE_ID = self.register(type="store", name="state")
        self.EDIT_STORE_ID = self.register(type="store", name="edit")
        self.ROW_INSERT_BTN = self.register(type="button", name="row-insert")
        self.ROW_DELETE_BTN = self.register(type="button", name="row-delete")
        self.OPEN_BTN = self.register(type="button", name="open")

    @staticmethod
    def sheet(name: str, columns: list, rows: list, key: str = "UID", markdown=(), editable=()) -> SheetAPI:
        return SheetAPI.frame(name, columns, rows, key, markdown=markdown, editable=editable)

    @classmethod
    def workspace(cls, name: str, columns: list, rows: list, *, key: str = "UID", markdown=(), base: str = None,
                  selection: dict = None, edition: dict = None) -> WorkspaceAPI:
        return WorkspaceAPI(
            title=name,
            sheets=[cls.sheet(name, columns, rows, key, markdown=markdown, editable=() if edition is None else columns)],
            outbound=selection,
            edition=edition,
            navigation={"base": base, "key": key} if base else None
        )

    @classmethod
    def table(cls, id: dict, name: str, columns: list, rows: list, *, key: str = "UID", markdown=(), base: str = None,
              carrier=MISSING, selection=MISSING, height: str = MISSING, **over) -> LightweightTableAPI:
        payload = cls.workspace(name, columns, rows, key=key, markdown=markdown, base=base, selection=None if selection is MISSING else selection)
        return LightweightTableAPI(id=id, carrier=carrier, selection=selection, workspace=name.lower(), payload=payload, height=height, **over)

    def _columns_(self) -> list:
        return []

    def _markdown_columns_(self) -> set:
        return set()

    def _rows_(self) -> list:
        return []

    def _detail_base_(self):
        return None

    def _actions_(self) -> list:
        return []

    def _extras_(self) -> list:
        return []

    def _editable_columns_(self) -> set:
        return set(self._columns_()) - {self._ROW_KEY_} if self._EDITABLE_ else set()

    def _write_(self, key, column: str, value) -> None:
        raise NotImplementedError

    def _append_(self) -> None:
        raise NotImplementedError

    def _remove_(self, keys: list) -> None:
        raise NotImplementedError

    def _workspace_(self) -> WorkspaceAPI:
        sheet = self.sheet(self._SHEET_, self._columns_(), self._rows_(), self._ROW_KEY_, markdown=self._markdown_columns_(), editable=self._editable_columns_())
        base = self._detail_base_() if self._NAVIGABLE_ else None
        return WorkspaceAPI(
            title=self.button or self._SHEET_,
            sheets=[sheet],
            outbound=self.STATE_STORE_ID,
            edition=self.EDIT_STORE_ID if self._EDITABLE_ else None,
            navigation={"base": base, "key": self._ROW_KEY_} if base else None
        )

    def _insert_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.ROW_INSERT_BTN, label=self._icon_("bi bi-plus-lg", "Insert", tint="primary"), background="secondary", tooltip="Insert a new row")

    def _delete_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.ROW_DELETE_BTN, label=self._icon_("bi bi-trash3", "Delete", tint="danger"), background="secondary", tooltip="Delete the selected rows")

    def _open_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.OPEN_BTN, label=self._icon_("bi bi-box-arrow-up-right", "Open"), background="secondary", tooltip="Open the selected rows · one opens here · several open in new tabs")

    def content(self) -> list:
        buttons = [self._refresh_button_()]
        if self._NAVIGABLE_: buttons.append(self._open_button_())
        if self._EDITABLE_ and self._EXTENDABLE_: buttons += [self._insert_button_(), self._delete_button_()]
        grid = LightweightTableAPI(
            id=self.TABLE_ID,
            carrier=self.CARRIER_ID,
            selection=self.STATE_STORE_ID,
            edition=self.EDIT_STORE_ID if self._EDITABLE_ else MISSING,
            workspace=self.endpoint,
            payload=self._workspace_(),
            stylename="lightweight-fill"
        )
        elements = [
            self.toolbar(buttons + self._actions_(), "table-toolbar"),
            *grid.build(),
            *self._polling_(poll=not self._EDITABLE_),
        ]
        elements.extend(self._extras_())
        return elements

    @serverside_callback(
        Output(CARRIER_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
    )
    def _reload_(self, token):
        if token is None: raise PreventUpdate
        return self._workspace_().encode()

    @clientside_callback(
        Output(OPEN_BTN, "disabled"),
        Input(STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_open_(self):
        return self.app.asset("Callbacks/GateAny.js", url=False)

    @clientside_callback(
        Output(ROW_DELETE_BTN, "disabled"),
        Input(STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_delete_(self):
        return self.app.asset("Callbacks/GateAny.js", url=False)

    @clientside_callback(
        Output(GlobalAPI.GLOBAL_LOCATION_ID, "pathname"),
        Input(OPEN_BTN, "n_clicks"),
        State(STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _open_(self):
        return self.app.asset("Callbacks/Open.js", url=False)

    @serverside_callback(
        Output(RefreshAPI.FINGERPRINT_STORE_ID, "data"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(EDIT_STORE_ID, "data"),
    )
    def _edit_(self, edit):
        if not self._EDITABLE_ or not edit or edit.get("uid") is None: raise PreventUpdate
        try:
            self._write_(edit["uid"], edit["column"], edit["value"])
        except Exception as error:
            self.app.notify.error(str(error), header="Update Failed")
            return dash.no_update, uuid.uuid4().hex
        self.app.notify.success(f"Updated {edit['column']}", header="Saved")
        return self._fingerprint_() or dash.no_update, dash.no_update

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(ROW_INSERT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _insert_(self, clicks):
        try:
            self._append_()
        except Exception as error:
            self.app.notify.error(str(error), header="Insert Failed")
            return dash.no_update
        self.app.notify.success("Row inserted", header="Saved")
        return uuid.uuid4().hex

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(ROW_DELETE_BTN, "n_clicks"),
        State(STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _delete_(self, clicks, state):
        keys = list((state or {}).get("selected") or [])
        if not keys:
            self.app.notify.warning("Select rows to delete", header="No Selection")
            return dash.no_update
        try:
            self._remove_(keys)
        except Exception as error:
            self.app.notify.error(str(error), header="Delete Failed")
            return dash.no_update
        self.app.notify.success(f"Deleted {len(keys)} row(s)", header="Done")
        return uuid.uuid4().hex