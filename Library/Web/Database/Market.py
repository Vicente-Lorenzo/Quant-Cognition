import calendar
from dash import html
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate

from Library.App.V2 import ComponentID, ContainerAPI, Output, Input, RefreshAPI, TextAPI, serverside_callback
from Library.Database import PostgresDatabaseAPI
from Library.Market.Download import DownloadAPI
from Library.Universe.Security import SecurityAPI
from Library.Utility.Datetime import utc_now
from Library.Web.Database.Database import DatabaseTableAPI

class MarketDatabasePageAPI(DatabaseTableAPI):

    _COLUMNS_ = ["Ticker", "State", "Through", "Lag", "First Day", "Last Day", "Complete", "Empty", "Failed", "Ticks", "Tracked"]
    _ROW_KEY_ = "UID"
    _SHEET_ = "Feeds"
    _POLL_ = 30000

    COVERAGE_ID: ComponentID | dict = ComponentID()

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/database/market", button="Market", icon="bi bi-activity", description="The tick feed of every tracked security · live state, lag and the days each month holds")

    def ids(self) -> None:
        super().ids()
        self.COVERAGE_ID = self.register(type="div", name="coverage")

    def _columns_(self) -> list:
        return self._COLUMNS_

    @staticmethod
    def _state_(summary: dict, now: datetime) -> str:
        if summary.get("UpdatedAt") is None: return "Waiting"
        idle = (now - summary["UpdatedAt"]).total_seconds()
        if summary.get("Through") is not None and summary.get("Last") is not None and summary["Last"] >= now.replace(hour=0, minute=0, second=0, microsecond=0) and idle < 120: return "Live"
        if idle < 300: return "Backfilling"
        return "Stopped"

    @staticmethod
    def _date_(moment):
        return moment.date() if moment is not None else None

    @staticmethod
    def _lag_(through, now: datetime) -> str:
        if through is None: return ""
        seconds = max(0.0, (now - through).total_seconds())
        if seconds < 120: return f"{seconds:.0f}s"
        if seconds < 7200: return f"{seconds / 60:.0f}m"
        if seconds < 172800: return f"{seconds / 3600:.1f}h"
        return f"{seconds / 86400:.0f}d"

    def _fetch_(self) -> tuple[list, dict, dict]:
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db:
            securities = db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Ticker", "Tracked"])
            summary, months = DownloadAPI.summary(db), DownloadAPI.months(db)
        summaries = {row["Security"]: row for row in summary.to_dicts()} if summary.height else {}
        coverage = {}
        for row in months.to_dicts() if months.height else []: coverage.setdefault(row["Security"], {})[row["Month"]] = row
        return [row for row in securities if row["Tracked"] or row["UID"] in summaries], summaries, coverage

    def _rows_(self) -> list:
        securities, summaries, _ = self._fetch_()
        now, rows = utc_now(), []
        for security in sorted(securities, key=lambda row: row["Ticker"]):
            summary = summaries.get(security["UID"], {})
            state = self._state_(summary, now)
            rows.append({"UID": security["UID"], "Ticker": security["Ticker"], "State": state, "Through": summary.get("Through"), "Lag": self._lag_(summary.get("Through"), now) if state == "Live" else "",
                         "First Day": self._date_(summary.get("First")), "Last Day": self._date_(summary.get("Last")), "Complete": summary.get("Complete"), "Empty": summary.get("Empty"), "Failed": summary.get("Failed"),
                         "Ticks": summary.get("Ticks"), "Tracked": bool(security["Tracked"])})
        return rows

    @staticmethod
    def _cell_(ticker: str, month: datetime, row: dict | None, today: datetime) -> html.Span:
        if row is None: return html.Span(className="app-strip-cell is-none", title=f"{ticker} {month:%Y-%m} · Nothing yet")
        days = calendar.monthrange(month.year, month.month)[1] if (month.year, month.month) != (today.year, today.month) else today.day - 1
        settled = row["Complete"] + row["Empty"]
        if row["Failed"]: state = "is-failed"
        elif row["Live"]: state = "is-live"
        elif settled >= days and not row["Complete"]: state = "is-empty"
        elif settled >= days: state = "is-complete"
        else: state = "is-partial"
        detail = f"{row['Complete']} Complete · {row['Empty']} Empty · {row['Failed']} Failed · {row['Ticks'] or 0:,} Ticks"
        return html.Span(className=f"app-strip-cell {state}", title=f"{ticker} {month:%Y-%m} · {detail}")

    def _coverage_(self) -> list:
        securities, _, coverage = self._fetch_()
        tracked = sorted((row for row in securities if row["UID"] in coverage), key=lambda row: row["Ticker"])
        if not tracked: return [self._hint_("No day has been downloaded yet")]
        first = min(min(coverage[row["UID"]]) for row in tracked)
        today = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        months, month = [], first
        while month <= today:
            months.append(month)
            month = (month + timedelta(days=32)).replace(day=1)
        strips = [html.Div([html.Span(row["Ticker"], className="app-strip-label"), html.Div([self._cell_(row["Ticker"], month, coverage[row["UID"]].get(month), today) for month in months], className="app-strip-cells")],
                           className="app-strip-row") for row in tracked]
        years = html.Div([html.Span(className="app-strip-label"), html.Div([html.Span(f"{month:%Y}" if month.month == 1 or not index else "", className="app-strip-year") for index, month in enumerate(months)], className="app-strip-cells")], className="app-strip-row app-strip-axis")
        legend = html.Div([html.Span([html.Span(className=f"app-strip-cell {state}"), label], className="app-strip-key") for state, label in
                           (("is-complete", "Every day settled"), ("is-partial", "Some days missing"), ("is-empty", "No ticks that month"), ("is-live", "Live"), ("is-failed", "A day failed"), ("is-none", "Not downloaded"))], className="app-strip-legend")
        return [html.Div([*strips, years], className="app-strip"), legend]

    def _preface_(self) -> list:
        return [ContainerAPI(fluid=True, classname="panel", elements=[TextAPI(text="Coverage by Month", classname="panel-title", builder=html.H5), html.Div(id=self.COVERAGE_ID)])]

    @serverside_callback(
        Output(COVERAGE_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
    )
    def _covered_(self, token):
        if token is None: raise PreventUpdate
        return self._coverage_()

    def _fingerprint_(self):
        with PostgresDatabaseAPI.attach(database=self.app.Database) as db: summary = DownloadAPI.summary(db)
        now = utc_now()
        return "|".join(f"{row['Security']}:{row['Complete']}:{row['Empty']}:{row['Failed']}:{self._state_(row, now)}" for row in sorted(summary.to_dicts(), key=lambda row: row["Security"])) if summary.height else ""