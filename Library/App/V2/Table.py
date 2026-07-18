import uuid

import dash
from dash import html, dash_table
from dash.exceptions import PreventUpdate

from Library.App.V2.Page import PageAPI
from Library.App.V2.Component import ComponentAPI, IconAPI, TextAPI, ButtonAPI, StorageAPI, IntervalAPI
from Library.App.V2.Callback import ComponentID, Output, Input, State, InjectionType, serverside_callback, clientside_callback

class TableAPI(PageAPI):

    TABLE_ID: ComponentID | dict = ComponentID()
    RELOAD_STORE_ID: ComponentID | dict = ComponentID()
    FINGERPRINT_STORE_ID: ComponentID | dict = ComponentID()
    CONFIG_STORE_ID: ComponentID | dict = ComponentID()
    INTERVAL_ID: ComponentID | dict = ComponentID()
    OPEN_BTN: ComponentID | dict = ComponentID()
    REFRESH_BTN: ComponentID | dict = ComponentID()
    ROW_INSERT_BTN: ComponentID | dict = ComponentID()
    ROW_DELETE_BTN: ComponentID | dict = ComponentID()
    COUNTER_ID: ComponentID | dict = ComponentID()

    _POLL_ = 10000
    _ROW_KEY_ = "UID"
    _EDITABLE_ = False
    _NAVIGABLE_ = True

    _KWARGS_ = dict(
        markdown_options={"html": True},
        style_as_list_view=True,
        page_size=25,
        sort_action="native",
        row_selectable="multi",
        selected_rows=[],
        cell_selectable=False,
        style_table={"width": "100%", "minWidth": "100%", "overflowX": "auto"},
        style_header={"backgroundColor": "transparent", "color": "var(--bs-secondary-color)", "fontWeight": "600", "textTransform": "uppercase", "fontSize": "0.68rem", "letterSpacing": "0.05em", "border": "none", "borderBottom": "1px solid var(--bs-border-color)", "padding": "0.5rem 0.75rem"},
        style_cell={"backgroundColor": "transparent", "color": "var(--bs-body-color)", "border": "none", "borderBottom": "1px solid var(--bs-border-color)", "fontSize": "0.83rem", "padding": "0.55rem 0.75rem", "textAlign": "left", "fontFamily": "inherit", "maxWidth": "240px", "overflow": "hidden", "textOverflow": "ellipsis"},
        style_data_conditional=[
            {"if": {"state": "selected"}, "backgroundColor": "rgba(var(--bs-primary-rgb), 0.18)", "color": "var(--bs-emphasis-color)", "border": "none", "borderBottom": "1px solid var(--bs-border-color)"},
            {"if": {"state": "active"}, "backgroundColor": "rgba(var(--bs-primary-rgb), 0.12)", "color": "var(--bs-emphasis-color)", "border": "none", "borderBottom": "1px solid var(--bs-border-color)"},
        ],
    )

    def ids(self) -> None:
        self.TABLE_ID = self.register(type="table", name="table")
        self.RELOAD_STORE_ID = self.register(type="store", name="reload")
        self.FINGERPRINT_STORE_ID = self.register(type="store", name="fingerprint")
        self.CONFIG_STORE_ID = self.register(type="store", name="config")
        self.INTERVAL_ID = self.register(type="interval", name="poll")
        self.OPEN_BTN = self.register(type="button", name="open")
        self.REFRESH_BTN = self.register(type="button", name="refresh")
        self.ROW_INSERT_BTN = self.register(type="button", name="row-insert")
        self.ROW_DELETE_BTN = self.register(type="button", name="row-delete")
        self.COUNTER_ID = self.register(type="text", name="counter")

    @staticmethod
    def _icon_(name: str, label: str = None, tint: str = None) -> list:
        parts = [IconAPI(icon=name, classname=f"icon icon-{tint}") if tint else IconAPI(icon=name)]
        if label is not None: parts.append(TextAPI(text=label))
        return parts

    @staticmethod
    def toolbar(buttons: list, classname: str = "table-toolbar") -> html.Div:
        built = []
        for button in buttons: built.extend(button.build() if isinstance(button, ComponentAPI) else [button])
        return html.Div(built, className=classname)

    @classmethod
    def kwargs(cls, editable: bool) -> dict:
        return {**cls._KWARGS_, "editable": editable, "cell_selectable": editable}

    @classmethod
    def definitions(cls, columns: list, markdown, editable: bool, key: str) -> list:
        marks = set(markdown or ())
        rows = []
        for column in columns:
            definition = {"name": column, "id": column}
            if column in marks: definition["presentation"] = "markdown"
            if editable: definition["editable"] = column != key
            rows.append(definition)
        return rows

    @classmethod
    def table(cls, id: dict, columns: list, markdown=(), editable: bool = False, key: str = "UID", **over) -> dash_table.DataTable:
        return dash_table.DataTable(id=id, columns=cls.definitions(columns, markdown, editable, key), data=[], **{**cls.kwargs(editable), **over})

    @staticmethod
    def navigable(table, base: str = None, key: str = "UID", fill: bool = False) -> html.Div:
        attributes = {"data-base": base, "data-key": key} if base else {}
        return html.Div(table, className="table-nav table-fill" if fill else "table-nav", **attributes)

    @staticmethod
    def selected_row(rows: list, data: list):
        if not rows or not data: return None
        index = rows[0]
        return data[index] if 0 <= index < len(data) else None

    @classmethod
    def selected_uid(cls, rows: list, data: list, key: str = "UID"):
        row = cls.selected_row(rows, data)
        return row.get(key) if row else None

    @classmethod
    def selected_uids(cls, rows: list, data: list, key: str = "UID") -> list:
        if not rows or not data: return []
        uids = []
        for index in rows:
            if 0 <= index < len(data):
                value = data[index].get(key)
                if value is not None: uids.append(value)
        return uids

    def _columns_(self) -> list:
        return []

    def _markdown_columns_(self) -> set:
        return set()

    def _rows_(self) -> list:
        return []

    def _detail_base_(self):
        return None

    def _fingerprint_(self):
        return None

    def _actions_(self) -> list:
        return []

    def _extras_(self) -> list:
        return []

    def _write_(self, key, column: str, value) -> None:
        raise NotImplementedError

    def _append_(self) -> None:
        raise NotImplementedError

    def _remove_(self, keys: list) -> None:
        raise NotImplementedError

    def _refresh_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.REFRESH_BTN, label=self._icon_("bi bi-arrow-clockwise", "Refresh"), background="secondary", tooltip="Reload the table from the database")

    def _open_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.OPEN_BTN, label=self._icon_("bi bi-box-arrow-up-right", "Open"), background="secondary", tooltip="Open the selected rows · one opens here · several open in new tabs")

    def _insert_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.ROW_INSERT_BTN, label=self._icon_("bi bi-plus-lg", "Insert", tint="primary"), background="secondary", tooltip="Insert a new row")

    def _delete_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.ROW_DELETE_BTN, label=self._icon_("bi bi-trash3", "Delete", tint="danger"), background="secondary", tooltip="Delete the selected rows")

    def content(self) -> list:
        buttons = [self._refresh_button_()]
        if self._EDITABLE_: buttons += [self._insert_button_(), self._delete_button_()]
        table = self.table(self.TABLE_ID, self._columns_(), self._markdown_columns_(), self._EDITABLE_, self._ROW_KEY_)
        counter = html.Span(id=self.COUNTER_ID, className="table-count")
        elements = [
            self.toolbar(buttons + self._actions_(), "table-toolbar"),
            self.navigable(table, self._detail_base_() if self._NAVIGABLE_ else None, self._ROW_KEY_, fill=True),
            self.toolbar([self._open_button_(), counter] if self._NAVIGABLE_ else [counter], "table-bar"),
        ]
        elements.append(StorageAPI(id=self.RELOAD_STORE_ID, data=None))
        elements.append(StorageAPI(id=self.FINGERPRINT_STORE_ID, data=None))
        elements.append(StorageAPI(id=self.CONFIG_STORE_ID, data={"base": self._detail_base_(), "key": self._ROW_KEY_, "navigable": self._NAVIGABLE_}))
        if self._POLL_ and not self._EDITABLE_: elements.append(IntervalAPI(id=self.INTERVAL_ID, interval=self._POLL_, intervals=0))
        elements.extend(self._extras_())
        return elements

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Output(FINGERPRINT_STORE_ID, "data"),
        on_enter=InjectionType.Hidden,
    )
    def _enter_(self):
        return uuid.uuid4().hex, (self._fingerprint_() or dash.no_update)

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Output(FINGERPRINT_STORE_ID, "data"),
        Input(INTERVAL_ID, "n_intervals"),
        State(FINGERPRINT_STORE_ID, "data"),
    )
    def _tick_(self, intervals, previous):
        if not intervals: raise PreventUpdate
        token = self._fingerprint_()
        if token is not None and token == previous: raise PreventUpdate
        return uuid.uuid4().hex, (dash.no_update if token is None else token)

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
        Input(REFRESH_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _refresh_(self, clicks):
        return uuid.uuid4().hex

    @serverside_callback(
        Output(TABLE_ID, "data"),
        Input(RELOAD_STORE_ID, "data"),
    )
    def _reload_(self, token):
        if token is None: raise PreventUpdate
        return self._rows_()

    @clientside_callback(
        Output("GLOBAL_LOCATION_ID", "pathname"),
        Input(OPEN_BTN, "n_clicks"),
        State(CONFIG_STORE_ID, "data"),
        State(TABLE_ID, "selected_rows"),
        State(TABLE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _open_(self):
        return self.app.asset("Callbacks/TableOpen.js", url=False)

    @clientside_callback(
        Output(COUNTER_ID, "children"),
        Input(TABLE_ID, "data"),
        Input(TABLE_ID, "derived_viewport_data"),
        Input(TABLE_ID, "selected_rows"),
    )
    def _count_(self):
        return self.app.asset("Callbacks/Count.js", url=False)

    @clientside_callback(
        Output(OPEN_BTN, "disabled"),
        Input(TABLE_ID, "selected_rows"),
        on_init=InjectionType.Hidden,
    )
    def _gate_open_(self):
        return self.app.asset("Callbacks/GateAny.js", url=False)

    @clientside_callback(
        Output(ROW_DELETE_BTN, "disabled"),
        Input(TABLE_ID, "selected_rows"),
        on_init=InjectionType.Hidden,
    )
    def _gate_delete_(self):
        return self.app.asset("Callbacks/GateAny.js", url=False)

    @serverside_callback(
        Output(FINGERPRINT_STORE_ID, "data"),
        Output(RELOAD_STORE_ID, "data"),
        Input(TABLE_ID, "data"),
        State(TABLE_ID, "data_previous"),
    )
    def _edit_(self, data, previous):
        if not self._EDITABLE_ or not previous or data == previous: raise PreventUpdate
        for new, old in zip(data, previous):
            if new == old: continue
            for column, value in new.items():
                if value == old.get(column): continue
                try:
                    self._write_(new.get(self._ROW_KEY_), column, value)
                except Exception as error:
                    self.app.notify.error(str(error), header="Update Failed")
                    return dash.no_update, uuid.uuid4().hex
                self.app.notify.success(f"Updated {column}", header="Saved")
        return self._fingerprint_() or dash.no_update, dash.no_update

    @serverside_callback(
        Output(RELOAD_STORE_ID, "data"),
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
        Output(RELOAD_STORE_ID, "data"),
        Input(ROW_DELETE_BTN, "n_clicks"),
        State(TABLE_ID, "selected_rows"),
        State(TABLE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _delete_(self, clicks, rows, data):
        keys = self.selected_uids(rows, data, self._ROW_KEY_)
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