import re
import dash
from dash import html
from dash.exceptions import PreventUpdate

from Library.App.V2 import ButtonAPI, ComponentID, ContainerAPI, FieldAPI, InjectionType, InputAPI, ModalAPI, Output, Input, State, RefreshAPI, SelectAPI, TableAPI, TextAPI, serverside_callback, modal_callbacks
from Library.Database import PostgresDatabaseAPI
from Library.Market.Download import DownloadAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Security import SecurityAPI, SecurityStatus
from Library.Universe.Ticker import TickerAPI
from Library.Web.Database.Database import DatabaseTableAPI

class UniverseDatabasePageAPI(DatabaseTableAPI):

    _COLUMNS_ = ["Ticker", "Description", "Category", "Type", "Status", "Tracked", "Digits", "Pip", "Lot", "Minimum", "Commission", "Swap Long", "Swap Short", "Trading", "Last Tick", "Provider", "Symbol"]
    _ROW_KEY_ = "UID"
    _SHEET_ = "Securities"
    _POLL_ = 0

    PROVIDER_ID: ComponentID | dict = ComponentID()
    CLASS_ID: ComponentID | dict = ComponentID()
    STATUS_ID: ComponentID | dict = ComponentID()
    TRACKED_ID: ComponentID | dict = ComponentID()
    SEARCH_ID: ComponentID | dict = ComponentID()
    TRACK_BTN: ComponentID | dict = ComponentID()
    UNTRACK_BTN: ComponentID | dict = ComponentID()
    CATEGORY_BTN: ComponentID | dict = ComponentID()
    TERMS_ID: ComponentID | dict = ComponentID()
    HISTORY_TABLE_ID: ComponentID | dict = ComponentID()
    HISTORY_CARRIER_ID: ComponentID | dict = ComponentID()
    HISTORY_WRAP_ID: ComponentID | dict = ComponentID()
    MODAL_ID: ComponentID | dict = ComponentID()
    CATEGORY_ID: ComponentID | dict = ComponentID()
    PRIMARY_ID: ComponentID | dict = ComponentID()
    SECONDARY_ID: ComponentID | dict = ComponentID()
    ALTERNATIVE_ID: ComponentID | dict = ComponentID()
    DISCARD_BTN: ComponentID | dict = ComponentID()
    APPLY_BTN: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/database/universe", button="Universe", icon="bi bi-globe2", description="Every security the provider lists, its category, its contract terms as they changed, and which ones are tracked")

    def ids(self) -> None:
        super().ids()
        self.PROVIDER_ID = self.register(type="field", name="provider")
        self.CLASS_ID = self.register(type="field", name="class")
        self.STATUS_ID = self.register(type="field", name="status")
        self.TRACKED_ID = self.register(type="field", name="tracked")
        self.SEARCH_ID = self.register(type="field", name="search")
        self.TRACK_BTN = self.register(type="button", name="track")
        self.UNTRACK_BTN = self.register(type="button", name="untrack")
        self.CATEGORY_BTN = self.register(type="button", name="category")
        self.TERMS_ID = self.register(type="div", name="terms")
        self.HISTORY_TABLE_ID = self.register(type="grid", name="history")
        self.HISTORY_CARRIER_ID = self.register(type="script", name="history-payload")
        self.HISTORY_WRAP_ID = self.register(type="div", name="history-wrap")
        self.MODAL_ID = self.register(type="modal", name="categorize")
        self.CATEGORY_ID = self.register(type="field", name="category")
        self.PRIMARY_ID = self.register(type="field", name="primary")
        self.SECONDARY_ID = self.register(type="field", name="secondary")
        self.ALTERNATIVE_ID = self.register(type="field", name="alternative")
        self.DISCARD_BTN = self.register(type="button", name="discard")
        self.APPLY_BTN = self.register(type="button", name="apply")

    @staticmethod
    def _groups_() -> tuple:
        return (("Price", ("Digits", "PointSize", "PipSize")),
                ("Volume", ("LotSize", "VolumeMin", "VolumeMax", "VolumeStep")),
                ("Commission", ("CommissionMode", "Commission")),
                ("Swap", ("SwapMode", "SwapLong", "SwapShort", "SwapPeriod", "SwapTime", "SwapExtraDay", "SwapWeekends")),
                ("Trading", ("TradingMode", "Variant", "Payoff", "Strike", "Maturity", "Exercise")))

    def _columns_(self) -> list:
        return self._COLUMNS_

    @staticmethod
    def _spaced_(text: str) -> str:
        return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)

    @classmethod
    def _shown_(cls, name: str, value):
        if name == "SwapTime" and isinstance(value, int): return f"{value // 60:02d}:{value % 60:02d} UTC"
        return cls._spaced_(value) if isinstance(value, str) else value

    @classmethod
    def _row_(cls, row: dict, through) -> dict:
        return {"UID": row["UID"], "Ticker": row["Ticker"], "Description": row["Description"], "Category": row["Category"], "Type": row["Type"], "Status": row["Status"], "Tracked": bool(row["Tracked"]),
                "Digits": row["Digits"], "Pip": row["PipSize"], "Lot": row["LotSize"], "Minimum": row["VolumeMin"], "Commission": row["Commission"], "Swap Long": row["SwapLong"], "Swap Short": row["SwapShort"],
                "Trading": row["TradingMode"], "Last Tick": through, "Provider": row["Provider"], "Symbol": cls._key_(row["Symbol"])}

    @staticmethod
    def _matches_(row: dict, provider, primary, status, tracked, search) -> bool:
        if provider and row["Provider"] != provider: return False
        if primary and (row["Category"] or "").split("(")[0] != primary: return False
        if status and row["Status"] != status: return False
        if tracked and bool(row["Tracked"]) != (tracked == "Tracked"): return False
        if search:
            text = search.strip().lower()
            if text and text not in (row["Ticker"] or "").lower() and text not in (row["Description"] or "").lower(): return False
        return True

    def _rows_(self, provider=None, primary=None, status=None, tracked=None, search=None) -> list:
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
            frame, summary = SecurityAPI.overview(db), DownloadAPI.summary(db)
        through = dict(zip(summary["Security"].to_list(), summary["Through"].to_list())) if summary.height else {}
        rows = [row for row in frame.to_dicts() if self._matches_(row, provider, primary, status, tracked, search)]
        return [self._row_(row, through.get(row["UID"])) for row in sorted(rows, key=lambda row: (not row["Tracked"], row["Category"] or "~", row["Ticker"]))]

    def _selects_(self) -> list:
        statuses = [{"label": "Any Status", "value": ""}] + FieldAPI.choices(SecurityStatus.names())
        tracking = [{"label": "Tracked Or Not", "value": ""}, {"label": "Tracked", "value": "Tracked"}, {"label": "Untracked", "value": "Untracked"}]
        return [
            *SelectAPI(id=self.PROVIDER_ID, options=[{"label": "Any Provider", "value": ""}], value="").build(),
            *SelectAPI(id=self.CLASS_ID, options=[{"label": "Any Class", "value": ""}], value="").build(),
            *SelectAPI(id=self.STATUS_ID, options=statuses, value="").build(),
            *SelectAPI(id=self.TRACKED_ID, options=tracking, value="").build(),
            *InputAPI(id=self.SEARCH_ID, type="search", placeholder="Search ticker or description", debounce=True).build(),
        ]

    def _actions_(self) -> list:
        return [
            ButtonAPI(id=self.TRACK_BTN, label=self._icon_("bi bi-broadcast", "Track", tint="primary"), background="secondary", tooltip="Download the selected securities' ticks from the horizon and keep them current · requires the Editor role"),
            ButtonAPI(id=self.UNTRACK_BTN, label=self._icon_("bi bi-slash-circle", "Untrack", tint="danger"), background="secondary", tooltip="Stop downloading the selected securities · the stored ticks stay · requires the Editor role"),
            ButtonAPI(id=self.CATEGORY_BTN, label=self._icon_("bi bi-tags", "Category"), background="secondary", tooltip="Assign a category to the selected tickers · requires the Editor role"),
        ]

    def _preface_(self) -> list:
        return [html.Div(self._selects_(), className="table-toolbar database-filters"), self._terms_panel_()]

    def _terms_panel_(self) -> ContainerAPI:
        return ContainerAPI(fluid=True, classname="panel", elements=[
            TextAPI(text="Contract Terms", classname="panel-title", builder=html.H5),
            html.Div(self._hint_("Select one security to see its terms and how they changed"), id=self.TERMS_ID),
            html.Div(TableAPI.table(self.HISTORY_TABLE_ID, "Changes", self._history_columns_(), [], carrier=self.HISTORY_CARRIER_ID, height="240px").build(), id=self.HISTORY_WRAP_ID, style={"display": "none"}),
        ])

    @staticmethod
    def _history_columns_() -> list:
        return ["Timestamp", "Term", "Before", "After", "By"]

    def _form_(self) -> list:
        field = lambda label, control, help: html.Div([html.Label(label, className="app-field-label"), *control, html.Small(help, className="app-field-help")], className="app-field")
        return [
            field("Category", SelectAPI(id=self.CATEGORY_ID, options=[], value=None).build(), "An existing category · or leave it and name a new one below"),
            field("New Primary", InputAPI(id=self.PRIMARY_ID, placeholder="Forex").build(), "Optional · the class of a new category · Forex · Metal · Index · Crypto · Energy · Stock"),
            field("New Secondary", InputAPI(id=self.SECONDARY_ID, placeholder="Minor").build(), "Optional · its subclass · the category is named Primary(Secondary)"),
            field("New Alternative", InputAPI(id=self.ALTERNATIVE_ID, placeholder="Currency").build(), "Optional · the family it also belongs to"),
        ]

    def _modal_(self) -> ModalAPI:
        return ModalAPI(id=self.MODAL_ID, size="md", centered=True, scrollable=True, open=False,
                        header=[html.Span("Assign Category", className="modal-title")],
                        body=self._form_(),
                        footer=[*ButtonAPI(id=self.DISCARD_BTN, label=self._icon_("bi bi-x-lg", "Cancel", tint="danger"), background="secondary", tooltip="Close without changing anything").build(),
                                *ButtonAPI(id=self.APPLY_BTN, label=self._icon_("bi bi-check-lg", "Apply", tint="success"), background="secondary", tooltip="Assign the category to every selected ticker").build()])

    def _extras_(self) -> list:
        return [self._modal_()]

    @serverside_callback(
        Output(TableAPI.CARRIER_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(PROVIDER_ID, "value"),
        Input(CLASS_ID, "value"),
        Input(STATUS_ID, "value"),
        Input(TRACKED_ID, "value"),
        Input(SEARCH_ID, "value"),
    )
    def _reload_(self, token, provider, primary, status, tracked, search):
        if token is None: raise PreventUpdate
        return self._workspace_(rows=self._rows_(provider, primary, status, tracked, search)).encode()

    @serverside_callback(
        Output(PROVIDER_ID, "options"),
        Output(CLASS_ID, "options"),
        on_enter=InjectionType.Hidden,
    )
    def _options_(self):
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
            providers = [row["UID"] for row in db.records(schema=ProviderAPI.Schema, table=ProviderAPI.Table, columns=["UID"], order='"UID"')]
            classes = sorted({row["Primary"] for row in db.records(schema=CategoryAPI.Schema, table=CategoryAPI.Table, columns=["Primary"]) if row["Primary"]})
        return [{"label": "Any Provider", "value": ""}] + FieldAPI.choices(providers), [{"label": "Any Class", "value": ""}] + FieldAPI.choices(classes)

    def _changes_(self, history: list) -> list:
        rows, previous = [], None
        for revision in history:
            terms = revision.plain()
            if previous is None: rows = [{"Timestamp": revision.Timestamp, "Term": "Recorded", "Before": "", "After": f"{sum(value is not None for value in terms.values())} Terms", "By": revision.UpdatedBy}] + rows
            else: rows = [{"Timestamp": revision.Timestamp, "Term": self._spaced_(name), "Before": self._shown_(name, previous[name]), "After": self._shown_(name, value), "By": revision.UpdatedBy} for name, value in terms.items() if value != previous[name]] + rows
            previous = terms
        return rows

    @serverside_callback(
        Output(TERMS_ID, "children"),
        Output(HISTORY_CARRIER_ID, "children"),
        Output(HISTORY_WRAP_ID, "style"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _terms_(self, state):
        keys, hidden = self.selected(state), {"display": "none"}
        if len(keys) != 1: return self._hint_("Select one security to see its terms and how they changed"), dash.no_update, hidden
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: history = ContractAPI.history(db, int(keys[0]))
        if not history: return self._hint_("No terms recorded for this security yet"), dash.no_update, hidden
        terms = history[-1].plain()
        groups = [self._group_(title, [(self._spaced_(name), self._shown_(name, terms.get(name))) for name in names if terms.get(name) is not None]) for title, names in self._groups_()]
        stamp = html.Span(["In force since ", html.Span(f"{history[-1].Timestamp:%Y-%m-%d %H:%M:%S}", **{"data-utc": f"{history[-1].Timestamp:%Y-%m-%d %H:%M:%S}"}), f" · {len(history)} dated revision(s)"], className="app-hint")
        return [html.Div([group for group in groups if group is not None], className="result-metrics database-terms"), stamp], TableAPI.workspace("Changes", self._history_columns_(), self._changes_(history)).encode(), {"display": "block", "marginTop": "0.75rem"}

    def _mark_(self, state, tracked: bool):
        if not self._permitted_(): return dash.no_update
        keys = self._selection_(state, "Select the securities first")
        if not keys: return dash.no_update
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: count = SecurityAPI.track(db, [int(key) for key in keys], tracked, self.app.actor() or "Web")
        self.app.notify.success(f"{count} securities {'tracked' if tracked else 'untracked'} · the Market service follows within a minute", header="Saved")
        return RefreshAPI.token()

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(TRACK_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _track_(self, clicks, state):
        return self._mark_(state, True)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(UNTRACK_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _untrack_(self, clicks, state):
        return self._mark_(state, False)

    _discard_, = modal_callbacks(MODAL_ID, closer=DISCARD_BTN)

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Output(CATEGORY_ID, "options"),
        Output(CATEGORY_ID, "value"),
        Output(PRIMARY_ID, "value"),
        Output(SECONDARY_ID, "value"),
        Output(ALTERNATIVE_ID, "value"),
        Input(CATEGORY_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _categorize_(self, clicks, state):
        if not self._permitted_() or not self._selection_(state, "Select the securities first"): return (dash.no_update,) * 6
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: categories = [row["UID"] for row in db.records(schema=CategoryAPI.Schema, table=CategoryAPI.Table, columns=["UID"], order='"UID"')]
        current = {row.get("Category") for row in (state or {}).get("rows") or []}
        return True, [{"label": "(choose)", "value": ""}] + FieldAPI.choices(categories), next(iter(current)) if len(current) == 1 else "", "", "", ""

    @serverside_callback(
        Output(MODAL_ID, "is_open"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(APPLY_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        State(CATEGORY_ID, "value"),
        State(PRIMARY_ID, "value"),
        State(SECONDARY_ID, "value"),
        State(ALTERNATIVE_ID, "value"),
        on_click=InjectionType.Hidden,
    )
    def _apply_(self, clicks, state, category, primary, secondary, alternative):
        if not self._permitted_(): return dash.no_update, dash.no_update
        tickers = sorted({row.get("Ticker") for row in (state or {}).get("rows") or [] if row.get("Ticker")})
        if not tickers:
            self.app.notify.warning("Select the securities first", header="No Selection")
            return dash.no_update, dash.no_update
        by = self.app.actor() or "Web"
        try:
            with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
                if primary and primary.strip(): category = CategoryAPI.store(db, primary, secondary, alternative, by)
                if not category: raise ValueError("Choose a category or name a new one")
                count = TickerAPI.categorize(db, tickers, category, by)
        except ValueError as error:
            self.app.notify.error(str(error), header="Refused")
            return dash.no_update, dash.no_update
        self.app.notify.success(f"{count} ticker(s) now in {category}", header="Saved")
        return False, RefreshAPI.token()