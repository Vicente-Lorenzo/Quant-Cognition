import dash
from dash import html
from datetime import timedelta
from dash.exceptions import PreventUpdate

from Library.App.V2 import ButtonAPI, ComponentID, ContainerAPI, FieldAPI, InjectionType, InputAPI, IntervalAPI, LightweightChartAPI, Output, Input, State, PaneAPI, PointAPI, RefreshAPI, SelectAPI, SeriesAPI, SheetAPI, TableAPI, TextAPI, WorkspaceAPI, serverside_callback
from Library.Database import PostgresDatabaseAPI
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Cashflow import CashflowAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Replay import ReplayAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import parse_datetime
from Library.Utility.Typing import MISSING
from Library.Web.Database.Database import DatabaseTableAPI

class PortfolioDatabasePageAPI(DatabaseTableAPI):

    _ROW_KEY_ = "UID"
    _SHEET_ = "Positions"
    _POLL_ = 0
    _FILL_ = False

    ACCOUNT_ID: ComponentID | dict = ComponentID()
    SECURITY_ID: ComponentID | dict = ComponentID()
    LABEL_ID: ComponentID | dict = ComponentID()
    SINCE_ID: ComponentID | dict = ComponentID()
    UNTIL_ID: ComponentID | dict = ComponentID()
    TRACK_BTN: ComponentID | dict = ComponentID()
    UNTRACK_BTN: ComponentID | dict = ComponentID()
    CARDS_ID: ComponentID | dict = ComponentID()
    CARDS_POLL_ID: ComponentID | dict = ComponentID()
    SCOPE_ID: ComponentID | dict = ComponentID()
    TIMEFRAME_ID: ComponentID | dict = ComponentID()
    DRAW_BTN: ComponentID | dict = ComponentID()
    CHART_ID: ComponentID | dict = ComponentID()
    CHART_CARRIER_ID: ComponentID | dict = ComponentID()
    CHART_WRAP_ID: ComponentID | dict = ComponentID()
    METRICS_ID: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/database/portfolio", button="Portfolio", icon="bi bi-briefcase", description="The mirrored demo accounts · positions, orders, trades and cash flows with their derived fields, and their balance and equity curves")

    def ids(self) -> None:
        super().ids()
        self.ACCOUNT_ID = self.register(type="field", name="account")
        self.SECURITY_ID = self.register(type="field", name="security")
        self.LABEL_ID = self.register(type="field", name="label")
        self.SINCE_ID = self.register(type="field", name="since")
        self.UNTIL_ID = self.register(type="field", name="until")
        self.TRACK_BTN = self.register(type="button", name="track")
        self.UNTRACK_BTN = self.register(type="button", name="untrack")
        self.CARDS_ID = self.register(type="div", name="cards")
        self.CARDS_POLL_ID = self.register(type="interval", name="cards-poll")
        self.SCOPE_ID = self.register(type="field", name="scope")
        self.TIMEFRAME_ID = self.register(type="field", name="timeframe")
        self.DRAW_BTN = self.register(type="button", name="draw")
        self.CHART_ID = self.register(type="chart", name="curves")
        self.CHART_CARRIER_ID = self.register(type="script", name="curves-payload")
        self.CHART_WRAP_ID = self.register(type="div", name="curves-wrap")
        self.METRICS_ID = self.register(type="div", name="metrics")

    @staticmethod
    def _sheets_() -> dict:
        return {
            "Positions": ["UID", "Security", "Direction", "Volume", "Entry", "Entry Price", "Stop Loss", "Take Profit", "Gross", "Spread", "Commission", "Swap", "Net", "Margin", "Max Drawdown", "Max Runup", "Entry Balance", "Label", "Comment"],
            "Orders": ["UID", "Security", "Direction", "Type", "Status", "Volume", "Executed", "Execution Price", "Limit", "Stop", "Stop Loss", "Take Profit", "Placed", "Updated", "Position", "Label"],
            "Trades": ["UID", "Position", "Security", "Direction", "Volume", "Entry", "Entry Price", "Exit", "Exit Price", "Gross", "Spread", "Commission", "Swap", "Net", "Exit Balance", "Max Drawdown", "Max Runup", "Label"],
            "Cashflow": ["UID", "Timestamp", "Type", "Delta", "Balance", "Equity", "Note"],
            "Accounts": ["UID", "Number", "Provider", "Environment", "Type", "Margin Mode", "Currency", "Leverage", "Balance", "Equity", "Tracked", "Updated"],
        }

    def _columns_(self) -> list:
        return self._sheets_()[self._SHEET_]

    def _filters_(self) -> list:
        return [
            *SelectAPI(id=self.ACCOUNT_ID, options=[], value=None, placeholder="Account").build(),
            *SelectAPI(id=self.SECURITY_ID, options=[{"label": "Any Security", "value": ""}], value="").build(),
            *SelectAPI(id=self.LABEL_ID, options=[{"label": "Any Label", "value": ""}], value="").build(),
            *InputAPI(id=self.SINCE_ID, type="date").build(),
            *InputAPI(id=self.UNTIL_ID, type="date").build(),
        ]

    def _actions_(self) -> list:
        return [
            ButtonAPI(id=self.TRACK_BTN, label=self._icon_("bi bi-broadcast", "Track", tint="primary"), background="secondary", tooltip="Mirror the accounts selected on the Accounts sheet · requires the Editor role"),
            ButtonAPI(id=self.UNTRACK_BTN, label=self._icon_("bi bi-slash-circle", "Untrack", tint="danger"), background="secondary", tooltip="Stop mirroring the accounts selected on the Accounts sheet · the stored rows stay · requires the Editor role"),
        ]

    def _preface_(self) -> list:
        return [html.Div(self._filters_(), className="table-toolbar database-filters"),
                html.Div(id=self.CARDS_ID, className="result-metrics database-cards"),
                IntervalAPI(id=self.CARDS_POLL_ID, interval=10000, intervals=0)]

    def _curves_panel_(self) -> ContainerAPI:
        timeframes = FieldAPI.choices(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        return ContainerAPI(fluid=True, classname="panel", elements=[
            TextAPI(text="Balance and Equity", classname="panel-title", builder=html.H5),
            html.Div([
                *SelectAPI(id=self.SCOPE_ID, options=[{"label": "Whole Account", "value": ""}], value="").build(),
                *SelectAPI(id=self.TIMEFRAME_ID, options=timeframes, value="H1").build(),
                *ButtonAPI(id=self.DRAW_BTN, label=self._icon_("bi bi-graph-up", "Draw", tint="primary"), background="secondary", tooltip="Replay the account's positions over the tape and draw its curves · the page's timeframe marks each bar at its close").build(),
            ], className="table-toolbar"),
            html.Div(LightweightChartAPI(id=self.CHART_ID, carrier=self.CHART_CARRIER_ID, workspace="curves", payload={}, height="420px").build(), id=self.CHART_WRAP_ID, style={"display": "none"}),
            html.Div(self._hint_("Choose a scope and press Draw"), id=self.METRICS_ID, className="database-curve-metrics"),
        ])

    def _extras_(self) -> list:
        return [self._curves_panel_()]

    @staticmethod
    def _day_(value, end: bool = False):
        if not value: return None
        moment = parse_datetime(value)
        return moment + timedelta(days=1) if end else moment

    @staticmethod
    def _condition_(account: int, security, label, since, until, stamp: str | None) -> tuple[str, dict]:
        clauses, parameters = ['"Account" = :account:'], {"account": account}
        if security: clauses, parameters = clauses + ['"Security" = :security:'], {**parameters, "security": int(security)}
        if label: clauses, parameters = clauses + ['"Label" = :label:'], {**parameters, "label": label}
        if stamp and since: clauses, parameters = clauses + [f'"{stamp}" >= :since:'], {**parameters, "since": since}
        if stamp and until: clauses, parameters = clauses + [f'"{stamp}" < :until:'], {**parameters, "until": until}
        return " AND ".join(clauses), parameters

    @classmethod
    def _position_(cls, row: dict, tickers: dict) -> dict:
        return {"UID": cls._key_(row["UID"]), "Security": tickers.get(row["Security"]), "Direction": row["Direction"], "Volume": row["Volume"], "Entry": row["EntryTimestamp"], "Entry Price": row["EntryPrice"],
                "Stop Loss": row["StopLossPrice"], "Take Profit": row["TakeProfitPrice"], "Gross": row["GrossPnL"], "Spread": row.get("SpreadPnL"), "Commission": row["CommissionPnL"], "Swap": row["SwapPnL"], "Net": row["NetPnL"],
                "Margin": row["UsedMargin"], "Max Drawdown": row["MaxEquityDrawdownPnL"], "Max Runup": row["MaxEquityRunupPnL"], "Entry Balance": row["EntryBalance"], "Label": row["Label"], "Comment": row["Comment"]}

    @classmethod
    def _order_(cls, row: dict, tickers: dict) -> dict:
        return {"UID": cls._key_(row["UID"]), "Security": tickers.get(row["Security"]), "Direction": row["Direction"], "Type": row["OrderType"], "Status": row["OrderStatus"], "Volume": row["Volume"],
                "Executed": row["ExecutedVolume"], "Execution Price": row["ExecutionPrice"], "Limit": row["LimitPrice"], "Stop": row["StopPrice"], "Stop Loss": row["StopLossPrice"],
                "Take Profit": row["TakeProfitPrice"], "Placed": row["EntryTimestamp"], "Updated": row["LastUpdateTimestamp"], "Position": cls._key_(row["Position"]), "Label": row["Label"]}

    @classmethod
    def _trade_(cls, row: dict, tickers: dict) -> dict:
        return {"UID": cls._key_(row["UID"]), "Position": cls._key_(row["Position"]), "Security": tickers.get(row["Security"]), "Direction": row["Direction"], "Volume": row["Volume"], "Entry": row["EntryTimestamp"],
                "Entry Price": row["EntryPrice"], "Exit": row["ExitTimestamp"], "Exit Price": row["ExitPrice"], "Gross": row["GrossPnL"], "Spread": row.get("SpreadPnL"), "Commission": row["CommissionPnL"], "Swap": row["SwapPnL"],
                "Net": row["NetPnL"], "Exit Balance": row["ExitBalance"], "Max Drawdown": row["MaxEquityDrawdownPnL"], "Max Runup": row["MaxEquityRunupPnL"], "Label": row["Label"]}

    @classmethod
    def _cashflow_(cls, row: dict) -> dict:
        return {"UID": cls._key_(row["UID"]), "Timestamp": row["Timestamp"], "Type": row["Type"], "Delta": row["Delta"], "Balance": row["Balance"], "Equity": row["Equity"], "Note": row["Note"]}

    @classmethod
    def _account_(cls, row: dict) -> dict:
        return {"UID": cls._key_(row["UID"]), "Number": cls._key_(row["Number"]), "Provider": row["Provider"], "Environment": row["Environment"], "Type": row["AccountType"], "Margin Mode": row["MarginMode"],
                "Currency": row["Asset"], "Leverage": row["Leverage"], "Balance": row["Balance"], "Equity": row["Equity"], "Tracked": bool(row["Tracked"]), "Updated": row["Timestamp"]}

    def _records_(self, account, security=None, label=None, since=None, until=None) -> dict:
        since, until = self._day_(since), self._day_(until, end=True)
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
            accounts = db.records(schema=AccountAPI.Schema, table=AccountAPI.Table, order='"UID"')
            if account is None: return {"Accounts": [self._account_(row) for row in accounts]}
            tickers = {row["UID"]: row["Ticker"] for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Ticker"])}
            condition, parameters = self._condition_(account, security, label, None, None, None)
            positions = db.records(schema=PositionAPI.Schema, table=PositionAPI.Table, condition=condition, order='"EntryTimestamp" DESC', parameters=parameters)
            condition, parameters = self._condition_(account, security, label, since, until, "EntryTimestamp")
            orders = db.records(schema=OrderAPI.Schema, table=OrderAPI.Table, condition=condition, order='"EntryTimestamp" DESC', limit=5000, parameters=parameters)
            condition, parameters = self._condition_(account, security, label, since, until, "ExitTimestamp")
            trades = db.records(schema=TradeAPI.Schema, table=TradeAPI.Table, condition=condition, order='"ExitTimestamp" DESC', limit=5000, parameters=parameters)
            condition, parameters = self._condition_(account, None, None, since, until, "Timestamp")
            flows = db.records(schema=CashflowAPI.Schema, table=CashflowAPI.Table, condition=condition, order='"Timestamp" DESC', parameters=parameters)
        return {"Positions": [self._position_(row, tickers) for row in positions], "Orders": [self._order_(row, tickers) for row in orders], "Trades": [self._trade_(row, tickers) for row in trades],
                "Cashflow": [self._cashflow_(row) for row in flows], "Accounts": [self._account_(row) for row in accounts]}

    def _payload_(self, records: dict) -> WorkspaceAPI:
        sheets = [SheetAPI.frame(name, columns, records.get(name, []), "UID") for name, columns in self._sheets_().items()]
        return WorkspaceAPI(title=self.button, sheets=sheets, outbound=self.STATE_STORE_ID)

    def _workspace_(self, columns: list = MISSING, rows: list = MISSING) -> WorkspaceAPI:
        return self._payload_({})

    @serverside_callback(
        Output(TableAPI.CARRIER_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(ACCOUNT_ID, "value"),
        Input(SECURITY_ID, "value"),
        Input(LABEL_ID, "value"),
        Input(SINCE_ID, "value"),
        Input(UNTIL_ID, "value"),
    )
    def _reload_(self, token, account, security, label, since, until):
        if token is None: raise PreventUpdate
        try: records = self._records_(int(account) if account else None, security, label, since, until)
        except ValueError as error:
            self.app.notify.error(str(error), header="Invalid Filter")
            return dash.no_update
        return self._payload_(records).encode()

    @serverside_callback(
        Output(ACCOUNT_ID, "options"),
        Output(ACCOUNT_ID, "value"),
        on_enter=InjectionType.Hidden,
    )
    def _accounts_(self):
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: accounts = db.records(schema=AccountAPI.Schema, table=AccountAPI.Table, order='"Tracked" DESC, "UID"')
        options = [{"label": f"{row['UID']} · {row['Number'] or ''} · {row['Asset'] or ''} · {row['Environment'] or ''}{'' if row['Tracked'] else ' · Untracked'}", "value": str(row["UID"])} for row in accounts]
        return options, options[0]["value"] if options else None

    @serverside_callback(
        Output(SECURITY_ID, "options"),
        Output(LABEL_ID, "options"),
        Output(SCOPE_ID, "options"),
        Input(ACCOUNT_ID, "value"),
    )
    def _choices_(self, account):
        securities, labels = [{"label": "Any Security", "value": ""}], [{"label": "Any Label", "value": ""}]
        scopes = [{"label": "Whole Account", "value": ""}]
        if not account: return securities, labels, scopes
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
            tickers = {row["UID"]: row["Ticker"] for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Ticker"])}
            rows = [row for model in (PositionAPI, TradeAPI, OrderAPI) for row in db.records(schema=model.Schema, table=model.Table, columns=["Security", "Label"], condition='"Account" = :account:', parameters={"account": int(account)})]
        found = sorted({row["Label"] for row in rows if row["Label"]})
        securities += [{"label": tickers.get(uid, str(uid)), "value": str(uid)} for uid in sorted({row["Security"] for row in rows if row["Security"] is not None}, key=lambda uid: tickers.get(uid, ""))]
        return securities, labels + FieldAPI.choices(found), scopes + [{"label": f"Label · {label}", "value": label} for label in found]

    @serverside_callback(
        Output(CARDS_ID, "children"),
        Input(ACCOUNT_ID, "value"),
        Input(CARDS_POLL_ID, "n_intervals"),
    )
    def _cards_(self, account, intervals):
        if not account: return self._hint_("No mirrored account yet · the Portfolio service discovers the demo accounts the stored token reaches")
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: row = db.first(schema=AccountAPI.Schema, table=AccountAPI.Table, condition='"UID" = :uid:', parameters={"uid": int(account)})
        if row is None: return self._hint_("Account not found")
        unrealized = row["Equity"] - row["Balance"] if row["Equity"] is not None and row["Balance"] is not None else None
        level = f"{row['MarginLevel']:,.1f}%" if row["MarginLevel"] is not None else None
        return [self._group_(f"Account {row['UID']} · {row['Asset'] or ''}", [("Balance", row["Balance"]), ("Equity", row["Equity"]), ("Unrealized P&L", unrealized), ("Margin Used", row["MarginUsed"]),
                                                                            ("Free Margin", row["MarginFree"]), ("Margin Level", level), ("Leverage", row["Leverage"]), ("Updated", row["Timestamp"])])]

    def _mark_(self, state, tracked: bool):
        if not self._permitted_(): return dash.no_update
        if not isinstance(state, dict) or state.get("sheet") != "Accounts" or not state.get("selected"):
            self.app.notify.warning("Select accounts on the Accounts sheet first", header="No Selection")
            return dash.no_update
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: count = AccountAPI.track(db, [int(key) for key in state["selected"]], tracked, self.app.actor() or "Web")
        self.app.notify.success(f"{count} account(s) {'tracked' if tracked else 'untracked'} · the Portfolio service follows within a minute", header="Saved")
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

    @staticmethod
    def _figure_(grid: list, balances: list, equities: list, currency: str) -> WorkspaceAPI:
        series = [SeriesAPI(key="equity", name="Equity", color="equity", width=2, data=PointAPI.line(list(zip(grid, equities)))),
                  SeriesAPI(key="balance", name="Balance", color="band", width=2, data=PointAPI.line(list(zip(grid, balances))))]
        return WorkspaceAPI(title="Balance and Equity", currency=currency, panes=[PaneAPI(id="equity", title="Balance and Equity", flex=20, series=series)])

    def _statistics_(self, curve, skipped: list) -> list:
        metrics = curve.metrics()
        groups = [self._group_("Equity Curve", [(label, value) for label, value in metrics.items() if isinstance(value, (int, float))], wide=True)]
        if skipped: groups.append(self._hint_(f"Left out · {' · '.join(skipped)}"))
        return groups

    @serverside_callback(
        Output(CHART_CARRIER_ID, "children"),
        Output(CHART_WRAP_ID, "style"),
        Output(METRICS_ID, "children"),
        Input(DRAW_BTN, "n_clicks"),
        State(ACCOUNT_ID, "value"),
        State(SCOPE_ID, "value"),
        State(TIMEFRAME_ID, "value"),
        on_click=InjectionType.Hidden,
    )
    def _draw_(self, clicks, account, scope, timeframe):
        if not account:
            self.app.notify.warning("Choose an account first", header="No Account")
            return dash.no_update, dash.no_update, dash.no_update
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
            row = db.first(schema=AccountAPI.Schema, table=AccountAPI.Table, condition='"UID" = :uid:', parameters={"uid": int(account)})
            if row is None:
                self.app.notify.error("The account is no longer mirrored", header="No Account")
                return dash.no_update, dash.no_update, dash.no_update
            grid, balances, equities, curve, skipped = ReplayAPI.curves(db, int(account), row["Asset"], TimeframeAPI(UID=timeframe or "H1"), label=scope or MISSING)
        if not grid: return "{}", {"display": "none"}, self._hint_("Nothing to draw · no position of this scope lies on a tracked security's tape")
        return self._figure_(grid, balances, equities, row["Asset"] or "").encode(), {"display": "block"}, self._statistics_(curve, skipped)