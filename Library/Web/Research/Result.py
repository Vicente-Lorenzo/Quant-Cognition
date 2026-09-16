import re
import json
import yaml
from datetime import datetime

import dash
from dash import dcc, html
from dash.exceptions import PreventUpdate

from Library.Statistic import (
    AVERAGEHOLDINGTIME,
    AVERAGELOSINGTRADE,
    AVERAGEWINNINGTRADE,
    BENCHMARK_ALPHA,
    BENCHMARK_ALPHASIGNIFICANCE,
    BENCHMARK_BETA,
    BENCHMARK_CORRELATION,
    BENCHMARK_DOWNSIDECAPTURE,
    BENCHMARK_INFORMATIONRATIO,
    BENCHMARK_LABEL,
    BENCHMARK_TRACKINGERROR,
    BENCHMARK_UPSIDECAPTURE,
    CALMARRATIO,
    COMMISSIONSPNLVALUE,
    DOWNSIDEVOLATILITYANNPERC,
    EXPECTEDTRADE,
    GROSSPNLVALUE,
    LOSINGRATEPERC,
    MAXBALANCEDRAWDOWNPERC,
    MAXBALANCERUNUPPERC,
    MAXEQUITYDRAWDOWNPERC,
    MAXEQUITYRUNUPPERC,
    MAXLOSINGSTREAK,
    MAXWINNINGSTREAK,
    MEANEQUITYDRAWDOWNPERC,
    MEANEQUITYRUNUPPERC,
    NETPNLVALUE,
    NETRETURNANNPERC,
    NETRETURNPERC,
    NETVOLATILITYANNPERC,
    NET_BUY_INDIVIDUAL,
    NET_SELL_INDIVIDUAL,
    NET_TOTAL_INDIVIDUAL,
    PROFITFACTOR,
    RISKTOREWARDRATIO,
    SHARPERATIO,
    SORTINORATIO,
    STERLINGRATIO,
    SWAPSPNLVALUE,
    TOTALTRADESVALUE,
    UPSIDEVOLATILITYANNPERC,
    WINNINGRATEPERC,
    compare,
    tabulate,
    transpose
)
from Library.App.V2 import (
    AppAPI,
    RefreshAPI,
    TableAPI,
    FieldAPI,
    ChoiceAPI,
    SegmentAPI,
    ComponentID,
    Output,
    Input,
    State,
    InjectionType,
    serverside_callback,
    clientside_callback,
    modal_callbacks,
    ButtonAPI,
    TextAPI,
    CrumbAPI,
    BreadcrumbAPI,
    StorageAPI,
    ModalAPI,
    WorkspaceAPI,
    LightweightAPI,
    LightweightChartAPI,
    LightweightTableAPI
)

from Library.Scheduler import RetentionLevel
from Library.Strategy.Ladder import LadderAPI
from Library.Utility.IO import read_json, read_text
from Library.Utility.Typing import MISSING
from Library.System.System import SystemAPI
from Library.Web.Research.Launch import LaunchAPI, LaunchFieldsAPI
from Library.Strategy.Catalog import CatalogAPI
from Library.Web.Core.Artifact import ArtifactAPI
from Library.Web.Core.Managed import ManagedPageAPI

class ResultBaseAPI(ManagedPageAPI):

    _ARTIFACTS_: ArtifactAPI = ArtifactAPI.shared()
    _FAMILY_ = "Result"
    _TASK_ = None

    def _runs_(self, limit: int = 100) -> list:
        if not self._TASK_: return []
        tasks = self._TASK_ if isinstance(self._TASK_, tuple) else (self._TASK_,)
        if len(tasks) == 1: return self._manager_.runs(task=tasks[0], limit=limit)
        merged = [run for task in tasks for run in self._manager_.runs(task=task, limit=limit)]
        merged.sort(key=lambda run: run.get("StartedAt") or datetime.min, reverse=True)
        return merged[:limit]

    def _produced_(self, run: dict) -> list:
        return self._ARTIFACTS_.produced(run.get("UID"))

    @staticmethod
    def _weight_(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB": return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
            size /= 1024.0
        return f"{size:,.1f} GB"

class ResultsPageAPI(SegmentAPI, ResultBaseAPI, TableAPI):

    CANCEL_BTN: ComponentID | dict = ComponentID()
    COMPARE_BTN: ComponentID | dict = ComponentID()
    TEMPORARY_SEGMENT: ComponentID | dict = ComponentID()
    PERSISTENT_SEGMENT: ComponentID | dict = ComponentID()
    FAVORITE_SEGMENT: ComponentID | dict = ComponentID()

    _CHOICES_ = (
        ChoiceAPI(value=RetentionLevel.Temporary.name, label="Temporary", icon="bi bi-hourglass", state="", tooltip="Let retention prune these runs and their artifacts"),
        ChoiceAPI(value=RetentionLevel.Persistent.name, label="Persistent", icon="bi bi-bookmark-check", state="✔", tooltip="Keep these runs and their artifacts beyond the retention horizon"),
        ChoiceAPI(value=RetentionLevel.Favorite.name, label="Favorite", icon="bi bi-star-fill", state="★", tooltip="Keep these runs and mark them important"),
    )

    _MARKS_ = {choice.value: choice.state for choice in _CHOICES_ if choice.state}

    _COLUMNS_ = ["Status", "UID", "Retention", "StartedAt", "StoppedAt", "Duration", "Artifacts"]
    _ROW_KEY_ = "UID"
    _SHEET_ = "Runs"
    _POLL_ = 5000
    _LAUNCH_: tuple = ()
    _ANCHOR_: str = None

    def ids(self) -> None:
        super().ids()
        self.CANCEL_BTN = self.register(type="button", name="cancel")
        self.COMPARE_BTN = self.register(type="button", name="compare")
        self._segment_ids_()

    def _row_(self, run: dict, produced: list) -> dict | None:
        return {"Status": self._led_(run.get("Status")), "UID": run.get("UID"),
                "Retention": self._MARKS_.get(run.get("Retention"), ""), "StartedAt": run.get("StartedAt"),
                "StoppedAt": run.get("StoppedAt"), "Duration": self._elapsed_(run.get("Duration")),
                "Artifacts": len(produced), **FieldAPI.parse(self._LAUNCH_, run.get("Arguments"))}

    def _workspace_(self, columns: list = MISSING, rows: list = MISSING) -> WorkspaceAPI:
        runs = self._runs_() if columns is MISSING or rows is MISSING else []
        if columns is MISSING: columns = self._COLUMNS_ + list(dict.fromkeys(name for run in runs for name in FieldAPI.parse(self._LAUNCH_, run.get("Arguments"))))
        if rows is MISSING: rows = [row for row in (self._row_(run, self._produced_(run)) for run in runs) if row is not None]
        return super()._workspace_(columns, rows)

    def _detail_base_(self):
        return self._ANCHOR_ or self.anchor

    def _cancel_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.CANCEL_BTN, label=self._icon_("bi bi-stop-circle", "Cancel", tint="danger"), background="secondary", tooltip="Stop the selected live runs")

    def _compare_button_(self) -> ButtonAPI:
        return ButtonAPI(id=self.COMPARE_BTN, label=self._icon_("bi bi-bar-chart-steps", "Compare"), background="secondary", tooltip="Overlay the growth curves and metrics of the selected runs")

    def _actions_(self) -> list:
        return [self._compare_button_(), self._cancel_button_(), self._segment_()]

    def _extras_(self) -> list:
        return [self._legend_()]

    def _mark_(self, state, level: RetentionLevel):
        keys = self._selection_(state, "Select runs first")
        if not keys: return dash.no_update
        return self._tally_(keys, lambda uid: self._manager_.retain(uid, level=level), f"run(s) marked {level.name}")

    @clientside_callback(
        Output(CANCEL_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_cancel_(self):
        return self.app.asset("Callbacks/GateLive.js", url=False)

    @clientside_callback(
        Output(COMPARE_BTN, "disabled"),
        Input(TableAPI.STATE_STORE_ID, "data"),
        on_init=InjectionType.Hidden,
    )
    def _gate_compare_(self):
        return self.app.asset("Callbacks/GatePair.js", url=False)

    @clientside_callback(
        Output(AppAPI.GLOBAL_LOCATION_ID, "pathname"),
        Input(COMPARE_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _compare_(self):
        return self.app.asset("Callbacks/Compare.js", url=False)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(CANCEL_BTN, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _cancel_(self, clicks, state):
        keys = self._selection_(state, "Select a live run first")
        if not keys: return dash.no_update
        return self._tally_(keys, lambda uid: self._manager_.cancel(uid, by=self.app.actor()), "run(s) canceled", "No selected run is live")

    @serverside_callback(
        Output(TEMPORARY_SEGMENT, "disabled"),
        Output(PERSISTENT_SEGMENT, "disabled"),
        Output(FAVORITE_SEGMENT, "disabled"),
        Output(TEMPORARY_SEGMENT, "active"),
        Output(PERSISTENT_SEGMENT, "active"),
        Output(FAVORITE_SEGMENT, "active"),
        Input(TableAPI.STATE_STORE_ID, "data"),
    )
    def _gate_segment_(self, state):
        disabled, active = self._segment_state_(state, "Retention")
        return (*disabled, *active)

    @serverside_callback(
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(TEMPORARY_SEGMENT, "n_clicks"),
        Input(PERSISTENT_SEGMENT, "n_clicks"),
        Input(FAVORITE_SEGMENT, "n_clicks"),
        State(TableAPI.STATE_STORE_ID, "data"),
        on_click=InjectionType.Hidden,
    )
    def _retain_(self, temporary, persistent, favorite, state):
        choice = self._segment_choice_(dash.ctx.triggered_id)
        if choice is None: raise PreventUpdate
        return self._mark_(state, RetentionLevel.parse(choice))

class LaunchedResultsPageAPI(LaunchAPI, ResultsPageAPI):

    def ids(self) -> None:
        super().ids()
        self._launch_ids_()

    def _actions_(self) -> list:
        return [self._launch_button_()] + super()._actions_()

    def _extras_(self) -> list:
        return [self._launch_modal_(), *super()._extras_()]

class ResultPageAPI(ResultBaseAPI, RefreshAPI):

    BREADCRUMB_ID: ComponentID | dict = ComponentID()
    FRAME_ID: ComponentID | dict = ComponentID()
    FIELDS_ID: ComponentID | dict = ComponentID()
    VIEWS_ID: ComponentID | dict = ComponentID()
    SINK_STORE_ID: ComponentID | dict = ComponentID()
    DOWNLOAD_BTN: ComponentID | dict = ComponentID()
    EXPORT_BTN: ComponentID | dict = ComponentID()
    CHART_ID: ComponentID | dict = ComponentID()
    SHEET_ID: ComponentID | dict = ComponentID()
    PROMOTE_BTN: ComponentID | dict = ComponentID()
    PROMOTE_MODAL_ID: ComponentID | dict = ComponentID()
    PROMOTE_SCOPE_ID: ComponentID | dict = ComponentID()
    PROMOTE_KIND_ID: ComponentID | dict = ComponentID()
    PROMOTE_APPLY_BTN: ComponentID | dict = ComponentID()
    PROMOTE_DISCARD_BTN: ComponentID | dict = ComponentID()

    _POLL_ = 5000
    _JOINER_ = "+"
    _CANVAS_ = "fill"
    _LAUNCH_: tuple = ()
    _LABEL_ = (FieldAPI.index(LaunchFieldsAPI.MARKET)["ticker"], FieldAPI.index(LaunchFieldsAPI.MARKET)["timeframe"])
    _SUMMARY_ = (
        ("Activity", ((TOTALTRADESVALUE, "Trades"), ("Buy Trades", "Buy"), ("Sell Trades", "Sell"),
                      (WINNINGRATEPERC, "Win Rate (%)"), (LOSINGRATEPERC, "Loss Rate (%)"),
                      (MAXWINNINGSTREAK, "Win Streak"), (MAXLOSINGSTREAK, "Loss Streak"),
                      (AVERAGEHOLDINGTIME, "Avg Hold (Days)"))),
        ("Returns", ((NETRETURNPERC, NETRETURNPERC), (NETRETURNANNPERC, "Annualized (%)"),
                     (GROSSPNLVALUE, "Gross P/L"), (COMMISSIONSPNLVALUE, "Commissions"),
                     (SWAPSPNLVALUE, "Swaps"), (NETPNLVALUE, "Net P/L"),
                     (AVERAGEWINNINGTRADE, "Avg Win"), (AVERAGELOSINGTRADE, "Avg Loss"),
                     (EXPECTEDTRADE, "Expectancy"))),
        ("Volatility", ((NETVOLATILITYANNPERC, "Volatility (%)"),
                        (UPSIDEVOLATILITYANNPERC, "Upside (%)"),
                        (DOWNSIDEVOLATILITYANNPERC, "Downside (%)"))),
        ("Drawdown & Runup", ((MAXBALANCEDRAWDOWNPERC, "Balance DD (%)"), (MAXEQUITYDRAWDOWNPERC, "Equity DD (%)"),
                              (MEANEQUITYDRAWDOWNPERC, "Mean DD (%)"),
                              (MAXBALANCERUNUPPERC, "Balance Runup (%)"), (MAXEQUITYRUNUPPERC, "Equity Runup (%)"),
                              (MEANEQUITYRUNUPPERC, "Mean Runup (%)"))),
        ("Ratios", ((SHARPERATIO, "Sharpe"), (SORTINORATIO, "Sortino"),
                    (CALMARRATIO, "Calmar"), (STERLINGRATIO, "Sterling"),
                    (PROFITFACTOR, PROFITFACTOR), (RISKTOREWARDRATIO, "Risk / Reward"))),
        (BENCHMARK_LABEL, ((BENCHMARK_ALPHA, "Alpha (%)"), (BENCHMARK_BETA, BENCHMARK_BETA),
                       (BENCHMARK_ALPHASIGNIFICANCE, "Alpha t-Stat"), (BENCHMARK_INFORMATIONRATIO, BENCHMARK_INFORMATIONRATIO),
                       (BENCHMARK_CORRELATION, BENCHMARK_CORRELATION), (BENCHMARK_TRACKINGERROR, "Tracking Error (%)"),
                       (BENCHMARK_UPSIDECAPTURE, BENCHMARK_UPSIDECAPTURE), (BENCHMARK_DOWNSIDECAPTURE, BENCHMARK_DOWNSIDECAPTURE))),
    )
    _SIGNED_ = frozenset({
        NETRETURNPERC, "Annualized (%)", "Gross P/L", "Net P/L", "Expectancy",
        "Sharpe", "Sortino", "Calmar", "Sterling",
        "Alpha (%)", "Alpha t-Stat", BENCHMARK_INFORMATIONRATIO,
    })
    _NUMBER_ = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
    _VIEWS_ = (("overview", "Overview", "bi bi-clipboard-data"),
               ("charts", "Charts", "bi bi-graph-up"),
               ("tables", "Tables", "bi bi-table"))

    def ids(self) -> None:
        self._refresh_ids_()
        self.BREADCRUMB_ID = self.register(type="div", name="breadcrumb")
        self.FRAME_ID = self.register(type="div", name="frame")
        self.FIELDS_ID = self.register(type="div", name="fields")
        self.VIEWS_ID = self.register(type="div", name="views")
        self.SINK_STORE_ID = self.register(type="store", name="sink")
        self.DOWNLOAD_BTN = self.register(type="button", name="download")
        self.EXPORT_BTN = self.register(type="button", name="export")
        self.CHART_ID = self.register(type="chart", name="result-chart")
        self.SHEET_ID = self.register(type="table", name="result-sheet")
        self.PROMOTE_BTN = self.register(type="button", name="promote")
        self.PROMOTE_MODAL_ID = self.register(type="modal", name="promote")
        self.PROMOTE_SCOPE_ID = self.register(type="field", name="promote-scope")
        self.PROMOTE_KIND_ID = self.register(type="field", name="promote-kind")
        self.PROMOTE_APPLY_BTN = self.register(type="button", name="promote-apply")
        self.PROMOTE_DISCARD_BTN = self.register(type="button", name="promote-discard")

    def capture(self, pathname: str) -> tuple:
        parts = self.segments(pathname)
        if not parts: return [], "overview"
        view = parts[1] if len(parts) > 1 and parts[1] in {key for key, _, _ in self._VIEWS_} else "overview"
        return [uid for uid in parts[0].split(self._JOINER_) if uid], view

    def _views_(self, uid: str, current: str) -> html.Div:
        base = f"{self.parent.anchor}/{uid}"
        buttons = []
        for key, label, icon in self._VIEWS_:
            link = ButtonAPI(
                href=base if key == "overview" else f"{base}/{key}",
                background="secondary",
                active=key == current,
                classname="app-segment-choice",
                label=self._icon_(icon, label)
            )
            buttons.extend(link.build())
        return html.Div(buttons, className="app-segment")

    def _trail_(self, label: str, target: str, view: str) -> list:
        crumbs = [CrumbAPI(label=self.parent.button, href=self.parent.anchor), CrumbAPI(label=label, href=f"{self.parent.anchor}/{target}" if view != "overview" else None)]
        if view != "overview": crumbs.append(CrumbAPI(label=next(caption for key, caption, _ in self._VIEWS_ if key == view)))
        return BreadcrumbAPI(trail=crumbs).build()

    def _canvas_view_(self, view: str, payload) -> list:
        if view == "charts": return LightweightChartAPI(id=self.CHART_ID, workspace="result", payload=payload, height=self._CANVAS_).build()
        return LightweightTableAPI(id=self.SHEET_ID, workspace="result", payload=payload, height=self._CANVAS_).build()

    def _metrics_(self, document: dict) -> dict:
        metrics = tabulate(document, "Net", NET_TOTAL_INDIVIDUAL)
        for label, value in transpose(document, BENCHMARK_LABEL).items(): metrics.setdefault(label, value)
        metrics["Buy Trades"] = tabulate(document, "Net", NET_BUY_INDIVIDUAL).get(TOTALTRADESVALUE)
        metrics["Sell Trades"] = tabulate(document, "Net", NET_SELL_INDIVIDUAL).get(TOTALTRADESVALUE)
        return metrics

    @classmethod
    def _tone_(cls, label: str, value) -> str:
        if label not in cls._SIGNED_ or value in (None, ""): return ""
        text = str(value)
        found = cls._NUMBER_.search(text)
        if found is None: return ""
        try: number = float(found.group().replace(",", ""))
        except ValueError: return ""
        if "(" in text and ")" in text: number = -abs(number)
        if number > 0: return " result-value-good"
        return " result-value-bad" if number < 0 else ""

    @staticmethod
    def _accent_(heading: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")

    def _panel_(self, card, wide: bool = False) -> list:
        groups = []
        for heading, entries in self._SUMMARY_:
            cards = [built for built in (card(source, label) for source, label in entries) if built is not None]
            if not cards: continue
            groups.append(html.Div([html.Div(heading, className="result-group-title"),
                                    html.Div(cards, className="result-cards result-cards-wide" if wide else "result-cards")],
                                   className=f"result-group result-group-{self._accent_(heading)}"))
        return [html.Div(groups, className="result-metrics")] if groups else []

    def _summary_(self, produced: list) -> list:
        payload = self._payload_(produced)
        if payload is None: return []
        metrics = self._metrics_(json.loads(payload))
        def card(source, label):
            value = metrics.get(source)
            if value in (None, ""): return None
            return html.Div([html.Span(label, className="result-card-key"),
                             html.Span(value, className="result-card-val" + self._tone_(label, value))], className="result-card")
        return self._panel_(card)

    def _overview_(self, pairs: list, produced: list) -> html.Div:
        return html.Div([html.Div([self._details_(pairs), *self._artifacts_(produced)], className="result-side"),
                         html.Div(self._summary_(produced), className="result-main")], className="result-overview")

    def _payload_(self, produced: list):
        result = next((entry for entry in produced if entry["Path"].is_file() and entry["Path"].name == SystemAPI.RESULT), None)
        if result is not None: return read_text(result["Path"]) or None
        artifact = next((entry for entry in produced if entry["Path"].is_file() and entry["Path"].suffix == ".html"), None)
        if artifact is None: return None
        document = read_text(artifact["Path"])
        marker = f'class="{LightweightAPI.PAYLOAD}">'
        opening = document.find(marker)
        if opening == -1: return None
        opening += len(marker)
        closing = document.find("</script>", opening)
        return document[opening:closing] if closing != -1 else None

    _BREADTH_ = tuple((rung, depth) for depth, rung in reversed(tuple(enumerate(LadderAPI.RUNGS, 1)))) + (("Everywhere", 0),)

    def _manifest_(self, uid: str) -> dict:
        folder = self._ARTIFACTS_._folder_(uid)
        if folder is None: return {}
        return read_json(folder / SystemAPI.MANIFEST)

    def _promotable_(self, uid: str):
        folder = self._ARTIFACTS_._folder_(uid)
        if folder is None: return None
        candidate = folder / SystemAPI.OUTPUT / SystemAPI.PARAMETERS
        return candidate if candidate.is_file() else None

    def _promote_modal_(self) -> ModalAPI:
        kinds = FieldAPI.choices(("Realtime", "Backtesting", "Optimization", "Learning"))
        breadth = [{"label": label, "value": str(depth)} for label, depth in self._BREADTH_]
        body = [
            self._field_("Apply To", dcc.Dropdown(id=self.PROMOTE_SCOPE_ID, options=breadth, value=str(self._BREADTH_[0][1]), clearable=False)),
            self._field_("Applies As", dcc.Dropdown(id=self.PROMOTE_KIND_ID, options=kinds, value="Backtesting", clearable=False))
        ]
        footer = [
            *ButtonAPI(id=self.PROMOTE_DISCARD_BTN, label=self._icon_("bi bi-x-lg", "Cancel", tint="danger"), background="secondary", tooltip="Close without promoting").build(),
            *ButtonAPI(id=self.PROMOTE_APPLY_BTN, label=self._icon_("bi bi-arrow-up-circle", "Promote", tint="success"), background="secondary", tooltip="Write these parameters as the override").build()
        ]
        return ModalAPI(
            id=self.PROMOTE_MODAL_ID,
            size="md",
            centered=True,
            open=False,
            header=[html.Span("Promote Parameters", className="modal-title")],
            body=body,
            footer=footer
        )

    def _promote_(self, uid: str, depth: int, kind: str) -> str:
        source = self._promotable_(uid)
        if source is None: return "This run produced no parameters to promote"
        manifest = self._manifest_(uid)
        rungs = tuple(manifest.get("Scope") or ())
        strategy = CatalogAPI.CATALOG.get(manifest.get("Strategy"))
        if strategy is None: return f"Unknown strategy {manifest.get('Strategy')!r}"
        if depth and len(rungs) < depth: return "This run did not record a scope that deep"
        try: sections = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        except (OSError, ValueError) as error: return f"Could not read the parameters · {error}"
        ladder = LadderAPI()
        scope = rungs[:depth]
        resolved, _ = ladder.resolve(strategy, kind, *scope)
        delta = {name: body for name, body in sections.items() if body != resolved.get(name)}
        if not delta: return "These parameters already match what resolves there"
        ladder.promote(strategy, kind, delta, *scope, origin=f"{manifest.get('System', 'Run')} run {uid}")
        target = "/".join(scope) or "Everywhere"
        return f"Promoted {strategy.key()} {kind} to {target}"

    def content(self) -> list:
        return [
            html.Div(id=self.BREADCRUMB_ID),
            self.toolbar([self._refresh_button_(), html.Div(id=self.VIEWS_ID, className="result-views"),
                          ButtonAPI(id=self.DOWNLOAD_BTN, label=self._icon_("bi bi-file-earmark-image", "Download All PNG"), background="secondary", tooltip="Save every panel of this view as PNG images"),
                          ButtonAPI(id=self.EXPORT_BTN, label=self._icon_("bi bi-filetype-csv", "Export All CSV"), background="secondary", tooltip="Export every table of this run as CSV"),
                          ButtonAPI(id=self.PROMOTE_BTN, label=self._icon_("bi bi-arrow-up-circle", "Promote", tint="success"), background="secondary", tooltip="Use this run's parameters as the override for a strategy on a provider, ticker or timeframe")], "table-toolbar"),
            html.Div(id=self.FIELDS_ID),
            html.Div(id=self.FRAME_ID, className="result-frame"),
            StorageAPI(id=self.SINK_STORE_ID, data=None),
            self._promote_modal_(),
            self._legend_(),
            *self._polling_(poll=False),
        ]

    @serverside_callback(
        Output(BREADCRUMB_ID, "children"),
        Output(VIEWS_ID, "children"),
        Output(FIELDS_ID, "children"),
        Output(FRAME_ID, "children"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        State(AppAPI.GLOBAL_LOCATION_ID, "pathname"),
    )
    def _populate_(self, token, pathname):
        uids, view = self.capture(pathname)
        if not uids: raise PreventUpdate
        if len(uids) > 1: return self._contrast_(uids, view)
        uid = uids[0]
        run = self._manager_.run(uid)
        trail = self._trail_(uid, uid, view)
        if run is None:
            return trail, [], self._details_([("Status", "Run not found")]), []
        produced = self._produced_(run)
        tabs = self._views_(uid, view)
        if view == "overview":
            pairs = [("Status", self._led_dot_(run.get("Status"))), ("Retention", run.get("Retention") or RetentionLevel.Temporary.name),
                     ("Started", self._stamp_(run.get("StartedAt"))), ("Stopped", self._stamp_(run.get("StoppedAt"))),
                     ("Duration", self._elapsed_(run.get("Duration"))), ("Exit Code", run.get("ExitCode")),
                     ("Auditor", run.get("Auditor"))]
            pairs += list(FieldAPI.parse(self._LAUNCH_, run.get("Arguments")).items()) if self._LAUNCH_ else []
            return trail, tabs, self._overview_(pairs, produced), []
        payload = self._payload_(produced)
        if payload is None:
            return trail, tabs, [], [TextAPI(text="This run produced no plot artifact · re-run it with --plot", classname="status-line", builder=html.P)]
        return trail, tabs, [], self._canvas_view_(view, payload)

    @classmethod
    def _label_(cls, run: dict, uid: str) -> str:
        return " ".join([*FieldAPI.parse(cls._LABEL_, run.get("Arguments")).values(), uid[:6]])

    def _rivalry_(self, labels: list, records: list) -> list:
        def card(source, label):
            values = [(name, record.get(source)) for name, record in zip(labels, records)]
            if all(value in (None, "") for _, value in values): return None
            return html.Div([html.Span(label, className="result-card-key"),
                             *[html.Span([html.Span(name, className="result-rival-name"),
                                          html.Span(value if value not in (None, "") else "—", className="result-rival-val" + self._tone_(label, value))],
                                         className="result-rival") for name, value in values]], className="result-card")
        return self._panel_(card, wide=True)

    def _contrast_(self, uids: list, view: str) -> tuple:
        joined = self._JOINER_.join(uids)
        trail = self._trail_(f"Compare · {len(uids)} Runs", joined, view)
        tabs = self._views_(joined, view)
        entries, pairs = [], []
        for uid in uids:
            run = self._manager_.run(uid)
            if run is None: pairs.append((uid, "Run not found")); continue
            label = self._label_(run, uid)
            pairs.append((label, self._stamp_(run.get("StartedAt"))))
            payload = self._payload_(self._produced_(run))
            if payload is not None: entries.append((label, json.loads(payload)))
        details = self._details_(pairs)
        if len(entries) < 2:
            return trail, tabs, details, [TextAPI(text="Fewer than two of the selected runs produced a plot artifact · re-run them with --plot", classname="status-line", builder=html.P)]
        if view == "overview":
            labels = [name for name, _ in entries]
            records = [self._metrics_(document) for _, document in entries]
            return trail, tabs, html.Div([html.Div(details, className="result-side"),
                                          html.Div(self._rivalry_(labels, records), className="result-main")], className="result-overview"), []
        return trail, tabs, [], self._canvas_view_(view, compare(entries).encode())

    @clientside_callback(
        Output(SINK_STORE_ID, "data"),
        Input(DOWNLOAD_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _download_(self):
        return self.app.asset("Callbacks/Download.js", url=False)

    @clientside_callback(
        Output(SINK_STORE_ID, "data"),
        Input(EXPORT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _export_(self):
        return self.app.asset("Callbacks/Sheets.js", url=False)

    def _artifacts_(self, produced: list) -> list:
        if not produced: return [TextAPI(text="This run produced no artifacts yet", classname="status-line", builder=html.P)]
        return [self._details_([(f"{entry['Kind']} · {entry['Name']}", self._weight_(entry["Size"])) for entry in produced])]

    _open_promote_, _close_promote_ = modal_callbacks(PROMOTE_MODAL_ID, PROMOTE_BTN, PROMOTE_DISCARD_BTN)

    @serverside_callback(
        Output(PROMOTE_MODAL_ID, "is_open"),
        Input(PROMOTE_APPLY_BTN, "n_clicks"),
        State(PROMOTE_SCOPE_ID, "value"),
        State(PROMOTE_KIND_ID, "value"),
        State(AppAPI.GLOBAL_LOCATION_ID, "pathname"),
        on_click=InjectionType.Hidden,
    )
    def _apply_promote_(self, clicks, depth, kind, pathname):
        uids, _ = self.capture(pathname)
        if len(uids) != 1:
            self.app.notify.warning("Open a single run to promote it", header="No Run")
            return False
        outcome = self._promote_(uids[0], int(depth or 0), kind or "Backtesting")
        if outcome.startswith("Promoted"): self.app.notify.success(outcome, header="Promoted")
        else: self.app.notify.warning(outcome, header="Not Promoted")
        return False