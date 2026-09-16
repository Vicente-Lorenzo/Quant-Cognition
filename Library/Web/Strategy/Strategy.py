import json
import re
from typing import Callable
from dataclasses import dataclass

from dash import dcc, html
from dash.exceptions import PreventUpdate

from Library.App.V2 import (
    ButtonAPI,
    ComponentID,
    InjectionType,
    Input,
    Output,
    ModalAPI,
    PageAPI,
    RefreshAPI,
    SectionPageAPI,
    State,
    StorageAPI,
    serverside_callback,
    modal_callbacks
)
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Database.Query import QueryAPI
from Library.Strategy.Ladder import LadderAPI
from Library.Strategy.Catalog import CatalogAPI
from Library.System.Space import SpaceAPI
from Library.Strategy.Strategy import StrategyAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Strategy.Range import RangeAPI
from Library.Strategy.Syntax import SyntaxAPI

@dataclass(frozen=True)
class GridColumnAPI:

    key: object
    scope: tuple
    strategy: str
    column: str
    label: str

class StrategyBaseAPI(RefreshAPI, PageAPI):

    KINDS = ("Realtime", "Backtesting", "Learning", "Optimization")
    SEARCHED = "Optimization"

    _DEFAULT_ = ("Spotware(cTrader)", "EURUSD", "H1")
    _POLL_ = 0
    _SCOPES_ = True
    _STRATEGIES_ = False
    _MARKERS_ = {"here": "cell-here", "parent": "cell-parent", "default": "cell-default"}
    _WORDS_ = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

    def __init__(self, *, app, **kwargs) -> None:
        super().__init__(app=app, **kwargs)

    STRATEGY_ID: ComponentID | dict = ComponentID()
    PROVIDER_ID: ComponentID | dict = ComponentID()
    TICKER_ID: ComponentID | dict = ComponentID()
    TIMEFRAME_ID: ComponentID | dict = ComponentID()
    GRID_ID: ComponentID | dict = ComponentID()
    STATUS_ID: ComponentID | dict = ComponentID()
    EDIT_STORE_ID: ComponentID | dict = ComponentID()
    APPLY_BTN: ComponentID | dict = ComponentID()
    REVERT_BTN: ComponentID | dict = ComponentID()
    DIFF_MODAL_ID: ComponentID | dict = ComponentID()
    DIFF_BODY_ID: ComponentID | dict = ComponentID()
    CONFIRM_BTN: ComponentID | dict = ComponentID()
    CANCEL_BTN: ComponentID | dict = ComponentID()
    APPLY_FOOT_BTN: ComponentID | dict = ComponentID()
    REVERT_FOOT_BTN: ComponentID | dict = ComponentID()

    def ids(self) -> None:
        super().ids()
        self._refresh_ids_()
        self.STRATEGY_ID = self.register(type="select", name="strategy")
        self.PROVIDER_ID = self.register(type="select", name="provider")
        self.TICKER_ID = self.register(type="select", name="ticker")
        self.TIMEFRAME_ID = self.register(type="select", name="timeframe")
        self.GRID_ID = self.register(type="grid", name="parameters")
        self.STATUS_ID = self.register(type="text", name="status")
        self.EDIT_STORE_ID = self.register(type="store", name="pending")
        self.APPLY_BTN = self.register(type="button", name="apply")
        self.REVERT_BTN = self.register(type="button", name="revert")
        self.DIFF_MODAL_ID = self.register(type="modal", name="diff")
        self.DIFF_BODY_ID = self.register(type="text", name="diff-body")
        self.CONFIRM_BTN = self.register(type="button", name="confirm")
        self.CANCEL_BTN = self.register(type="button", name="cancel")
        self.APPLY_FOOT_BTN = self.register(type="button", name="apply-foot")
        self.REVERT_FOOT_BTN = self.register(type="button", name="revert-foot")

    def _ladder_(self) -> LadderAPI:
        return LadderAPI()

    def _universe_(self) -> tuple:
        try:
            with PostgresDatabaseAPI(database=self.app.Database) as db:
                frame = db.executeone(QueryAPI('''
                    SELECT DISTINCT p."UID" AS provider, c."UID" AS category, t."UID" AS ticker
                    FROM "Universe"."Security" s
                    JOIN "Universe"."Provider" p ON p."UID" = s."Provider"
                    JOIN "Universe"."Ticker" t ON t."UID" = s."Ticker"
                    JOIN "Universe"."Category" c ON c."UID" = s."Category"
                    WHERE EXISTS (SELECT 1 FROM "Market"."Bar" b WHERE b."Security" = s."UID")
                    ORDER BY 1, 3
                ''')).fetchall()
                spans = db.executeone(QueryAPI('SELECT "UID" FROM "Universe"."Timeframe"')).fetchall()
        except Exception:
            return {}, []
        catalog = {(provider, ticker): category for provider, category, ticker
                   in zip(frame["provider"], frame["category"], frame["ticker"])}
        return catalog, [span.UID for span in sorted(TimeframeAPI(UID=uid) for uid in spans["UID"])]

    @staticmethod
    def _listed_(value) -> list:
        if value is None: return []
        return list(value) if isinstance(value, (list, tuple)) else [value]

    @staticmethod
    def _scopes_(catalog: dict, providers: list, tickers: list, timeframes: list) -> list:
        chosen = []
        for provider in providers:
            for ticker in tickers:
                category = catalog.get((provider, ticker))
                if category is None: continue
                for timeframe in timeframes:
                    chosen.append((provider, category, ticker, timeframe))
        return chosen

    @staticmethod
    def _painted_(text: str, searched: bool) -> list:
        if not text: return ["—"]
        if not searched: return [text]
        nodes = []
        for index, slot in enumerate(text.split(SyntaxAPI.SEPARATOR)):
            if index: nodes.append(html.Span("·", className="grid-slot-sep"))
            stripped = slot.strip()
            if stripped.casefold() == SpaceAPI.AUTOMATIC.casefold():
                nodes.append(html.Span(SpaceAPI.AUTOMATIC, className="grid-pill grid-pill-auto")); continue
            found = RangeAPI.PATTERN.match(stripped)
            if found:
                step = f" · {found.group(3)}" if found.group(3) else ""
                nodes.append(html.Span(f"{found.group(1)} → {found.group(2)}{step}", className="grid-pill grid-pill-range")); continue
            for option in (part for part in stripped.split(SyntaxAPI.ALTERNATIVE) if part):
                nodes.append(html.Span(option, className="grid-pill"))
        return nodes or ["—"]

    @classmethod
    def _worded_(cls, text: str) -> str:
        return cls._WORDS_.sub(" ", text) if text else text

    @staticmethod
    def _label_(scope: tuple) -> str:
        return f"{scope[2]} {scope[3]}"

    @staticmethod
    def _entries_(body, searched: bool) -> list:
        if not isinstance(body, dict): return [(None, None)]
        if searched and SyntaxAPI.numbered(body):
            return [(str(stage), name) for stage, parameters in body.items()
                    for name in (parameters if isinstance(parameters, dict) else {})]
        return [(None, name) for name in body]

    @staticmethod
    def _pick_(body, stage, name):
        if not isinstance(body, dict): return body
        if stage is not None:
            parameters = body.get(stage)
            return parameters.get(name) if isinstance(parameters, dict) else None
        return body.get(name)

    def _cell_(self, value, origin, scope: tuple, kind: str, searched: bool) -> dict:
        shown = SyntaxAPI.format_slots(value) if searched else SyntaxAPI.format_value(value)
        if origin is None: return {"value": shown, "origin": "default", "hint": "Strategy definition"}
        where, ancestor = origin
        if tuple(where) == tuple(scope) and ancestor == kind:
            return {"value": shown, "origin": "here", "hint": "Set at this scope"}
        via = "" if ancestor == kind else f" via {ancestor}"
        return {"value": shown, "origin": "parent",
                "hint": f"Inherited from {'/'.join(where) or 'Everywhere'}{via}"}

    @staticmethod
    def _origin_(sources: dict, section: str, name):
        return sources.get((section, name)) or sources.get((section, None))

    @staticmethod
    def _gather_(ladder: LadderAPI, keys: list, kind: str, locate: Callable) -> tuple[dict, dict]:
        resolved, sources = {}, {}
        for key in keys:
            strategy, scope = locate(key)
            resolved[key] = ladder.resolve(strategy, kind, *scope)[0]
            sources[key] = ladder.sources(strategy, kind, *scope)
        return resolved, sources

    def _collect_(self, ladder: LadderAPI, keys: list, locate: Callable) -> dict:
        model = {}
        for kind in self.KINDS:
            searched, sections = kind == self.SEARCHED, {}
            resolved, sources = self._gather_(ladder, keys, kind, locate)
            for key in keys:
                for section, body in (resolved[key] or {}).items():
                    for stage, name in self._entries_(body, searched):
                        sections.setdefault(section, {}).setdefault((stage, name), {})
            for section, entries in sections.items():
                for (stage, name), cells in entries.items():
                    for key in keys:
                        value = self._pick_((resolved[key] or {}).get(section), stage, name)
                        cells[key] = self._cell_(value, self._origin_(sources[key], section, name), locate(key)[1], kind, searched)
            if sections: model[kind] = sections
        return model

    def _model_(self, strategy: type[StrategyAPI], scopes: list) -> dict:
        ladder = self._ladder_()
        model = self._collect_(ladder, scopes, lambda scope: (strategy, scope))
        self._settable_(ladder, strategy, scopes, model)
        return model

    def _settable_(self, ladder: LadderAPI, strategy: type[StrategyAPI], scopes: list, model: dict) -> None:
        declared = {}
        for kind in self.KINDS:
            if kind == self.SEARCHED: continue
            for section, entries in model.get(kind, {}).items():
                for _, name in entries:
                    if name: declared.setdefault(section, set()).add(name)
        if not declared: return
        resolved, sources = self._gather_(ladder, scopes, self.SEARCHED, lambda scope: (strategy, scope))
        sections = model.setdefault(self.SEARCHED, {})
        for section, names in declared.items():
            entries = sections.setdefault(section, {})
            present = {name for _, name in entries if name}
            missing = sorted(names - present)
            if missing: entries.pop((None, None), None)
            for name in missing:
                cells = entries.setdefault((None, name), {})
                for scope in scopes:
                    value = self._pick_((resolved[scope] or {}).get(section), None, name)
                    cells[scope] = self._cell_(value, self._origin_(sources[scope], section, name), scope, self.SEARCHED, True)

    @staticmethod
    def _ordered_(sections) -> list:
        return sorted(sections, key=lambda name: (SpaceAPI.SECTIONS.index(name) if name in SpaceAPI.SECTIONS else len(SpaceAPI.SECTIONS), name))

    @staticmethod
    def _head_(columns: list, width: str) -> html.Div:
        head = [html.Div("Parameter", className="grid-corner")]
        for label, column in columns:
            head.append(html.Div(
                [html.Span(label, className="grid-scope-name"), html.Span("×", className="grid-scope-fold")],
                className="grid-scope",
                **{"data-fold": "column", "data-column": column}
            ))
        return html.Div(head, className="grid-head", style={"gridTemplateColumns": width})

    @staticmethod
    def _row_(cells: list, width: str) -> html.Div:
        return html.Div(cells, className="grid-row", style={"gridTemplateColumns": width})

    def _section_(self, section: str, unset: bool) -> html.Div:
        return html.Div(
            [html.Span("▾", className="grid-chevron"), html.Span(self._worded_(section)), html.Span("not set", className="grid-section-empty") if unset else None],
            className="grid-section" + (" grid-section-unset" if unset else ""),
            **{"data-fold": "section"}
        )

    def _name_(self, section: str, stage, name, differs: bool) -> html.Div:
        label = self._worded_(name) if name else self._worded_(section)
        if stage is not None: label = f"{stage} · {self._worded_(name)}"
        return html.Div([html.Span(label, className="grid-name"), html.Span("⚠", className="grid-differs") if differs else None], className="grid-label")

    @staticmethod
    def _control_(label: str, id: dict, options: list, value, multi: bool) -> html.Div:
        return html.Div([html.Label(label, className="grid-control-label"), dcc.Dropdown(id=id, options=options, value=value, multi=multi, clearable=multi)], className="grid-control")

    @staticmethod
    def _grouped_(pending: dict) -> dict:
        grouped = {}
        for token, value in pending.items():
            key, scope, kind, section, stage, name = token.split("|", 5)
            grouped.setdefault((key, tuple(scope.split("/")), kind), []).append((section, stage, name, value))
        return grouped

    def _slot_(self, cell: dict, scope: tuple, strategy: str, kind: str, section: str, stage, name,
               differs: bool, column: str) -> html.Div:
        return html.Div([html.Span(className=f"grid-dot {self._MARKERS_[cell['origin']]}"),
                         html.Span(self._painted_(cell["value"], kind == self.SEARCHED), className="grid-value")],
                        className="grid-cell" + (" grid-cell-differs" if differs else ""), title=cell["hint"],
                        **{"data-strategy": strategy, "data-scope": "/".join(scope), "data-kind": kind,
                           "data-section": section, "data-stage": stage or "", "data-name": name or "",
                           "data-value": cell["value"] or "", "data-column": column})

    def _band_(self, kind: str, sections: dict, columns: list, width: str) -> html.Div:
        rows, total, differing, searched = [], 0, 0, kind == self.SEARCHED
        for section in self._ordered_(sections):
            entries = sorted(sections[section].items(), key=lambda item: (item[0][0] or "", item[0][1] or ""))
            unset = len(entries) == 1 and entries[0][0] == (None, None)
            rows.append(self._section_(section, unset))
            if unset: continue
            for (stage, name), cells in entries:
                total += 1
                differs = len({cells[column.key]["value"] for column in columns}) > 1
                if differs: differing += 1
                cursor = [self._name_(section, stage, name, differs)]
                for column in columns:
                    cursor.append(self._slot_(cells[column.key], column.scope, column.strategy, kind, section, stage, name, differs, column.column))
                rows.append(self._row_(cursor, width))
        summary = f"{total} parameters" + (f" · {differing} differ" if differing else "") if total else "not set"
        header = html.Div([html.Span("▾", className="grid-chevron"),
                           html.Span(kind, className="grid-band-name"),
                           html.Span(summary, className="grid-band-summary")],
                          className="grid-band-head", **{"data-fold": "band"})
        return html.Div([header, html.Div(rows, className="grid-band-body")],
                        className="grid-band" + ("" if total else " grid-band-unset"))

    def _across_(self, keys: list, scope: tuple) -> dict:
        return self._collect_(self._ladder_(), keys, lambda key: (CatalogAPI.resolve(key), scope))

    def _pivot_(self, model: dict, scope: tuple) -> dict:
        sections = {}
        for kind in self.KINDS:
            for section, entries in model.get(kind, {}).items():
                for (stage, name), cells in entries.items():
                    if cells.get(scope) is None: continue
                    sections.setdefault(section, {}).setdefault((stage, name), {})[kind] = cells[scope]
        return sections

    def _single_(self, model: dict, scope: tuple, strategy: str) -> list:
        sections = self._pivot_(model, scope)
        width = f"minmax(240px, 1.3fr) repeat({len(self.KINDS)}, minmax(170px, 1fr))"
        rows = []
        for section in self._ordered_(sections):
            entries = sorted(sections[section].items(), key=lambda item: (item[0][0] or "", item[0][1] or ""))
            live = [(key, cells) for key, cells in entries if key != (None, None)]
            rows.append(self._section_(section, not live))
            for (stage, name), by_kind in live:
                shown = {cell["value"] for kind, cell in by_kind.items() if kind != self.SEARCHED and cell["value"]}
                differs = len(shown) > 1
                cursor = [self._name_(section, stage, name, differs)]
                for kind in self.KINDS:
                    cell = by_kind.get(kind)
                    if cell is None:
                        cursor.append(html.Div([html.Span("", className="grid-value")], className="grid-cell grid-cell-void", **{"data-column": kind}))
                        continue
                    cursor.append(self._slot_(cell, scope, strategy, kind, section, stage, name, differs and kind != self.SEARCHED, kind))
                rows.append(self._row_(cursor, width))
        blocks = [self._head_([(kind, kind) for kind in self.KINDS], width),
                  html.Div(rows, className="grid-band-body")]
        return [html.Div(blocks, className="grid")]

    def _columns_(self, model: dict, columns: list) -> list:
        width = f"minmax(220px, 1.3fr) repeat({len(columns)}, minmax(150px, 1fr))"
        blocks = [self._head_([(column.label, column.column) for column in columns], width)]
        for kind in self.KINDS:
            blocks.append(self._band_(kind, model.get(kind) or {}, columns, width))
        return [html.Div(blocks, className="grid")]

    def _grid_(self, keys: list, scopes: list) -> list:
        if not keys or not scopes:
            return [html.P("Select a strategy, provider, ticker and timeframe", className="status-line")]
        if self._STRATEGIES_:
            model = self._across_(keys, scopes[0])
            if not model: return [html.P("No strategy declares parameters here", className="status-line")]
            return self._columns_(model, [GridColumnAPI(key=key, scope=scopes[0], strategy=key, column=key, label=key)
                                          for key in keys])
        strategy, chosen = CatalogAPI.resolve(keys[0]), keys[0]
        model = self._model_(strategy, scopes)
        if not model:
            return [html.P(f"{strategy.key()} declares no parameters", className="status-line")]
        if not self._SCOPES_: return self._single_(model, scopes[0], chosen)
        return self._columns_(model, [GridColumnAPI(key=scope, scope=scope, strategy=chosen, column="/".join(scope), label=self._label_(scope))
                                      for scope in scopes])

    def _controls_(self, catalog: dict, timeframes: list) -> html.Div:
        providers = sorted({provider for provider, _ in catalog})
        tickers = sorted({ticker for _, ticker in catalog})
        def preset(options, wanted):
            chosen = wanted if wanted in options else (options[0] if options else None)
            if not self._SCOPES_: return chosen
            return [chosen] if chosen is not None else []
        return html.Div([
            self._control_("Strategy", self.STRATEGY_ID, [entry.key() for entry in CatalogAPI.STRATEGIES], [CatalogAPI.DEFAULT.key()] if self._STRATEGIES_ else CatalogAPI.DEFAULT.key(), self._STRATEGIES_),
            self._control_("Provider", self.PROVIDER_ID, providers, preset(providers, self._DEFAULT_[0]), self._SCOPES_),
            self._control_("Ticker", self.TICKER_ID, tickers, preset(tickers, self._DEFAULT_[1]), self._SCOPES_),
            self._control_("Timeframe", self.TIMEFRAME_ID, timeframes, preset(timeframes, self._DEFAULT_[2]), self._SCOPES_),
        ], className="grid-controls")

    def _buttons_(self, apply, revert, status: bool) -> html.Div:
        actions = [ButtonAPI(id=apply, label=self._icon_("bi bi-check2", "Apply"), background="success", tooltip="Write every pending edit to its own scope"),
                   ButtonAPI(id=revert, label=self._icon_("bi bi-x-lg", "Cancel"), background="secondary", tooltip="Throw away every pending edit")]
        if status: actions.append(html.Span(id=self.STATUS_ID, className="grid-status"))
        return self.toolbar(actions, classname="grid-toolbar" if status else "grid-toolbar grid-toolbar-foot")

    def content(self) -> list:
        catalog, timeframes = self._universe_()
        return [
            self._controls_(catalog, timeframes),
            self._buttons_(self.APPLY_BTN, self.REVERT_BTN, status=True),
            html.Div(id=self.GRID_ID, className="grid-host", **{"data-store": json.dumps(self.EDIT_STORE_ID)}),
            self._buttons_(self.APPLY_FOOT_BTN, self.REVERT_FOOT_BTN, status=False),
            StorageAPI(id=self.EDIT_STORE_ID, data={}),
            *self._polling_(poll=False),
            ModalAPI(id=self.DIFF_MODAL_ID, size="lg", centered=True, scrollable=True, open=False,
                     header=[html.Span("Review changes", className="modal-title")],
                     body=[html.Div(id=self.DIFF_BODY_ID, className="diff")],
                     footer=[*ButtonAPI(id=self.CANCEL_BTN, label=self._icon_("bi bi-x-lg", "Cancel", tint="danger"), background="secondary", tooltip="Close without writing anything").build(),
                             *ButtonAPI(
                                 id=self.CONFIRM_BTN,
                                 label=self._icon_("bi bi-check2", "Apply", tint="success"),
                                 background="secondary",
                                 tooltip="Write every change to its scope file"
                             ).build()]),
        ]

    def _write_(self, pending: dict) -> int:
        ladder, grouped = self._ladder_(), self._grouped_(pending)
        for (key, scope, kind), edits in grouped.items():
            strategy = CatalogAPI.resolve(key)
            sections = ladder.sparse(strategy, kind, *scope)
            for section, stage, name, value in edits:
                settled = SyntaxAPI.parse_slots(value) if kind == self.SEARCHED else SyntaxAPI.parse_value(value)
                if stage: sections.setdefault(section, {}).setdefault(stage, {})[name] = settled
                elif name: sections.setdefault(section, {})[name] = settled
                else: sections[section] = settled
            ladder.promote(strategy, kind, sections, *scope, origin="Manual")
        return len(grouped)

    @serverside_callback(
        Output(GRID_ID, "children"),
        Input(STRATEGY_ID, "value"),
        Input(PROVIDER_ID, "value"),
        Input(TICKER_ID, "value"),
        Input(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(TIMEFRAME_ID, "value"),
    )
    def _render_(self, strategy, providers, tickers, token, timeframes):
        catalog, _ = self._universe_()
        scopes = self._scopes_(catalog, self._listed_(providers), self._listed_(tickers), self._listed_(timeframes))
        return self._grid_(self._listed_(strategy), scopes)

    def _diff_(self, pending: dict) -> tuple:
        ladder, grouped, total = self._ladder_(), self._grouped_(pending), 0
        blocks = []
        for (key, scope, kind), edits in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])):
            strategy = CatalogAPI.resolve(key)
            resolved = ladder.resolve(strategy, kind, *scope)[0]
            own = ladder.sparse(strategy, kind, *scope)
            path = ladder.override(kind, *scope)
            lines = []
            for section, stage, name, value in sorted(edits):
                before = self._pick_(resolved.get(section), stage or None, name or None)
                shown = SyntaxAPI.format_slots(before) if kind == self.SEARCHED else SyntaxAPI.format_value(before)
                settled = (own.get(section) or {})
                fresh = name not in settled if not stage else name not in (settled.get(stage) or {})
                label = f"{section}.{name}" if name else section
                if stage: label = f"{section}[{stage}].{name}"
                if shown == value: continue
                total += 1
                lines.append(html.Div([
                    html.Span("NEW" if fresh else "SET", className="diff-tag diff-" + ("new" if fresh else "set")),
                    html.Span(label, className="diff-name"),
                    html.Span(shown or "—", className="diff-before"),
                    html.Span("→", className="diff-arrow"),
                    html.Span(value or "—", className="diff-after")], className="diff-line"))
            if not lines: continue
            blocks.append(html.Div([
                html.Div([html.Span(f"{key} {kind}", className="diff-kind"),
                          html.Span("/".join(scope) or "Everywhere", className="diff-scope"),
                          html.Span(path.name, className="diff-file")], className="diff-head"),
                html.Div(lines, className="diff-body")], className="diff-block"))
        if not blocks: blocks = [html.P("Nothing to write · every edit matches what already resolves", className="status-line")]
        return blocks, total

    @serverside_callback(
        Output(DIFF_MODAL_ID, "is_open"),
        Output(DIFF_BODY_ID, "children"),
        Input(APPLY_BTN, "n_clicks"),
        Input(APPLY_FOOT_BTN, "n_clicks"),
        State(EDIT_STORE_ID, "data"),
        State(STRATEGY_ID, "value"),
        on_click=InjectionType.Hidden,
    )
    def _review_(self, clicks, footer, pending, strategy):
        if not pending:
            self.app.notify.info("No pending edits", header="Nothing to apply")
            raise PreventUpdate
        blocks, _ = self._diff_(pending)
        return True, blocks

    @serverside_callback(
        Output(DIFF_MODAL_ID, "is_open"),
        Output(STATUS_ID, "children"),
        Output(EDIT_STORE_ID, "data"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(CONFIRM_BTN, "n_clicks"),
        State(EDIT_STORE_ID, "data"),
        State(STRATEGY_ID, "value"),
        on_click=InjectionType.Hidden,
    )
    def _commit_(self, clicks, pending, strategy):
        if not pending: raise PreventUpdate
        written = self._write_(pending)
        self.app.notify.success(f"{written} scope file(s) written", header="Applied")
        return False, f"Applied · {written} file(s)", {}, self.token()

    (_dismiss_,) = modal_callbacks(DIFF_MODAL_ID, closer=CANCEL_BTN)

    @serverside_callback(
        Output(EDIT_STORE_ID, "data"),
        Output(RefreshAPI.RELOAD_STORE_ID, "data"),
        Input(REVERT_BTN, "n_clicks"),
        Input(REVERT_FOOT_BTN, "n_clicks"),
        on_click=InjectionType.Hidden,
    )
    def _discard_(self, clicks, footer):
        if not (clicks or footer): raise PreventUpdate
        self.app.notify.info("Pending edits discarded", header="Discarded")
        return {}, self.token()

class StrategyPageAPI(SectionPageAPI):

    _FAMILY_ = "Strategy"

    def __init__(self, *, app) -> None:
        super().__init__(app=app, path="/strategy", button="Strategy", icon="bi bi-sliders", description="Inspect and edit what every strategy resolves to")

class StrategySystemPageAPI(StrategyBaseAPI):

    _FAMILY_ = "Strategy"
    _SCOPES_ = False
    _STRATEGIES_ = False

    def __init__(self, *, app) -> None:
        super().__init__(
            app=app,
            path="/strategy/system",
            button="System",
            icon="bi bi-layout-sidebar-inset",
            description="One strategy on one symbol — Realtime, Backtesting, Learning and Optimization side by side"
        )

class StrategyScopePageAPI(StrategyBaseAPI):

    _FAMILY_ = "Strategy"
    _SCOPES_ = True
    _STRATEGIES_ = False

    def __init__(self, *, app) -> None:
        super().__init__(
            app=app,
            path="/strategy/scope",
            button="Scope",
            icon="bi bi-columns-gap",
            description="One strategy across many symbols — compare how it is tuned per provider, ticker and timeframe"
        )

class StrategyStrategyPageAPI(StrategyBaseAPI):

    _FAMILY_ = "Strategy"
    _SCOPES_ = False
    _STRATEGIES_ = True

    def __init__(self, *, app) -> None:
        super().__init__(
            app=app,
            path="/strategy/strategy",
            button="Strategy",
            icon="bi bi-diagram-3",
            description="Many strategies on one symbol — compare how each is parameterized for the same market"
        )