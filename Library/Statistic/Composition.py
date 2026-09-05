import bisect
from statistics import fmean

from Library.Statistic.Label import (
    BENCHMARK_ALPHA,
    BENCHMARK_LABEL,
    BENCHMARK_ALPHASIGNIFICANCE,
    BENCHMARK_BETA,
    BENCHMARK_CORRELATION,
    BENCHMARK_INFORMATIONRATIO,
    CALMARRATIO,
    MAXEQUITYDRAWDOWNPERC,
    NETRETURNANNPERC,
    NETRETURNPERC,
    NETVOLATILITYANNPERC,
    NET_TOTAL_INDIVIDUAL,
    PROFITFACTOR,
    SHARPERATIO,
    SORTINORATIO,
    TOTALTRADESVALUE,
    WINNINGRATEPERC
)
from Library.Statistic.Payload import (
    diurnal,
    grouped,
    ordinal,
    searched,
    stitch,
    tabulate,
    tick,
    trace,
    transpose,
    winners
)
from Library.Statistic.Series import (covariant, distribution, overwater, periodic, rolling, underwater)
from Library.Statistic.Workspace import (
    AxisType,
    DealAPI,
    FormatType,
    LineAPI,
    MarkerAPI,
    PaneAPI,
    PointAPI,
    SeriesAPI,
    SeriesType,
    SheetAPI,
    SpanAPI,
    WorkspaceAPI
)

def excursion(bars: list, trades: list) -> list:
    if not bars or not trades: return []
    spine = [PointAPI.epoch(bar[0]) for bar in bars]
    rows = []
    for uid, direction, entry, exit, entry_price, exit_price, net in trades:
        if uid is None or entry is None or not entry_price: continue
        opened = bisect.bisect_left(spine, PointAPI.epoch(entry))
        closed = bisect.bisect_right(spine, PointAPI.epoch(exit)) if exit is not None else len(spine)
        window = bars[opened:closed]
        if not window: continue
        long = direction == "Buy"
        peak, trough = max(bar[2] for bar in window), min(bar[3] for bar in window)
        favorable = max((peak - entry_price) if long else (entry_price - trough), 0.0) / entry_price * 100.0
        adverse = max((entry_price - trough) if long else (peak - entry_price), 0.0) / entry_price * 100.0
        result = ((exit_price - entry_price) if long else (entry_price - exit_price)) / entry_price * 100.0 if exit_price else None
        rows.append({"UID": uid, "Direction": direction, "Entry": entry, "Exit": exit,
                     "MFE (%)": round(favorable, 4), "MAE (%)": round(adverse, 4),
                     "Result (%)": round(result, 4) if result is not None else None,
                     "Efficiency (%)": round(result / favorable * 100.0, 2) if result is not None and favorable else None,
                     "Net": net})
    return rows

_COMPARED_ = (
    NETRETURNPERC,
    NETRETURNANNPERC,
    NETVOLATILITYANNPERC,
    SHARPERATIO,
    SORTINORATIO,
    CALMARRATIO,
    MAXEQUITYDRAWDOWNPERC,
    PROFITFACTOR,
    TOTALTRADESVALUE,
    WINNINGRATEPERC,
)

_BENCHMARKED_ = (
    BENCHMARK_ALPHA,
    BENCHMARK_BETA,
    BENCHMARK_ALPHASIGNIFICANCE,
    BENCHMARK_INFORMATIONRATIO,
    BENCHMARK_CORRELATION,
)

_TINTS_ = ("equity", "benchmark0", "benchmark1", "benchmark2", "benchmark3", "balance", "long", "short")

def walkforward(folds: list, elected: list = None) -> tuple[list, list]:
    curve, marks = stitch(folds)
    if not curve: return [], []
    series = [SeriesAPI(key="rolling", name="Rolling Refit", color="equity", width=2, data=PointAPI.line(curve))]
    opening, closing = PointAPI.epoch(curve[0][0]), PointAPI.epoch(curve[-1][0])
    held = [(stamp, value) for stamp, value in (elected or []) if opening <= PointAPI.epoch(stamp) <= closing]
    if held: series.append(SeriesAPI(key="elected", name="Elected Model", color="band", width=2, data=PointAPI.line(PointAPI.rebase(held))))
    pane = PaneAPI(id="walkforward", title="Walk-Forward · Each Fold Out of Sample (rebased 100)", flex=20, format=FormatType.Value, datum=100.0, series=series)
    sheet = SheetAPI.frame(name="Folds", columns=list(marks[0].keys()), rows=marks, key="Fold")
    return [pane], [sheet]

_SEARCH_ = ("accent", "band", "up", "exit", "benchmark2", "benchmark1", "long", "short")

def convergence(journal: list) -> list:
    scored = [record for record in journal if record.get("Fitness") is not None]
    if len(scored) < 2: return []
    running, summit = [], None
    for record in scored:
        summit = record["Fitness"] if summit is None else max(summit, record["Fitness"])
        running.append(summit)
    trace = [SeriesAPI(key="best", name="Best So Far", color="up", width=2, data=ordinal(running)),
             SeriesAPI(
                 key="trial",
                 name="Trial Fitness",
                 kind=SeriesType.Histogram,
                 color="accent",
                 axis=AxisType.Left,
                 toggle=True,
                 visible=True,
                 data=ordinal([record["Fitness"] for record in scored])
             )]
    return [PaneAPI(id="convergence", scale="index", title=f"Search Convergence · {len(scored)} Scored Trials", flex=18, format=FormatType.Value, series=trace)]

def sensitivity(journal: list, budget: int = 6) -> list:
    scored = [record for record in journal if record.get("Fitness") is not None]
    panes = []
    for name in searched(scored)[:budget]:
        marks = {}
        for record in scored:
            value = record.get(name)
            if value is None: continue
            marks.setdefault(str(value), []).append(record["Fitness"])
        if len(marks) < 2: continue
        ordered = sorted(marks, key=lambda label: (_numeric_(label) is None, _numeric_(label), label))
        panes.append(PaneAPI(id=f"sensitivity-{name.lower()}", scale="index", flex=16, format=FormatType.Value,
                             title=f"Sensitivity · {name} · best and mean fitness per value",
                             series=[SeriesAPI(
                                 key=f"{name}-best",
                                 name="Best",
                                 color="up",
                                 width=2,
                                 data=[{"time": tick(index), "value": max(marks[label])} for index, label in enumerate(ordered, start=1)]
                             ),
                                     SeriesAPI(
                                         key=f"{name}-mean",
                                         name="Mean",
                                         color="band",
                                         width=2,
                                         data=[{"time": tick(index), "value": fmean(marks[label])} for index, label in enumerate(ordered, start=1)]
                                     ),
                                     SeriesAPI(
                                         key=f"{name}-axis",
                                         name=name,
                                         kind=SeriesType.Histogram,
                                         color="muted",
                                         axis=AxisType.Left,
                                         toggle=True,
                                         visible=False,
                                         data=[{"time": tick(index), "value": float(len(marks[label]))} for index, label in enumerate(ordered, start=1)]
                                     )],
                             labels=ordered))
    return panes

def _numeric_(label: str):
    try: return float(label)
    except (TypeError, ValueError): return None

def generalization(folds: list) -> list:
    marks = [record for record in folds if record.get("Training") is not None or record.get("Validation") is not None]
    if len(marks) < 2: return []
    return [PaneAPI(id="generalization", scale="index", flex=16, format=FormatType.Value, datum=0.0,
                    title="Generalization · Training against Validation fitness per fold",
                    series=[SeriesAPI(key="fittrain", name="Training", color="band", width=2, data=ordinal([record.get("Training") for record in marks])),
                            SeriesAPI(key="fitvalidation", name="Validation", color="accent", width=2, data=ordinal([record.get("Validation") for record in marks]))],
                    labels=[f"Fold {record.get('Fold')}" for record in marks])]

def drift(folds: list) -> list:
    names, marks = [], []
    for record in folds:
        settings = record.get("Settings") or {}
        marks.append(settings)
        for name in settings:
            if name not in names and _numeric_(str(settings[name]).split("/")[-1]) is not None: names.append(name)
    if len(marks) < 2 or not names: return []
    series = []
    for index, name in enumerate(names[:6]):
        values = [_numeric_(str(settings.get(name, "")).split("/")[-1]) for settings in marks]
        if all(value is None for value in values): continue
        series.append(SeriesAPI(key=f"drift-{name.lower()}", name=name, color=_SEARCH_[index % len(_SEARCH_)], width=2, data=ordinal(values)))
    if not series: return []
    return [PaneAPI(
        id="drift",
        scale="index",
        flex=16,
        format=FormatType.Value,
        title="Parameter Drift · what each fold elected",
        series=series,
        labels=[f"Fold {record.get('Fold')}" for record in folds]
    )]

def episodes(journal: list) -> list:
    passes = [record for record in journal if record.get("Episode") is not None]
    if len(passes) < 2: return []
    series = []
    for index, (key, records) in enumerate(sorted(grouped(passes, "Seed", "Fold").items(), key=lambda entry: (entry[0][0] or 0, entry[0][1] or 0))[:8]):
        seed, fold = key
        label = f"Fold {fold}" if seed is None else f"Seed {seed} · Fold {fold}"
        series.append(SeriesAPI(key=f"episode-{seed}-{fold}", name=label, color=_SEARCH_[index % len(_SEARCH_)], width=2, data=ordinal([record.get("Validation") for record in records])))
    return [PaneAPI(id="episodes", scale="index", flex=18, format=FormatType.Value,
                    title="Learning Curves · validation fitness per episode", series=series)]

def leaderboard(journal: list) -> list:
    scored = [record for record in journal if record.get("Fitness") is not None]
    if not scored: return []
    names = searched(scored)
    axes = [name for name in ("Fold", "Stage", "Round", "Candidate") if any(record.get(name) is not None for record in scored)]
    rows = [{"UID": str(index), **{name: record.get(name) for name in axes},
             "Fitness": round(record["Fitness"], 6), **{name: record.get(name) for name in names}}
            for index, record in enumerate(sorted(scored, key=lambda record: record["Fitness"], reverse=True), start=1)]
    sheet = SheetAPI.frame(name="Candidates", columns=[*axes, "Fitness", *names], rows=rows)
    sheet.height = len(rows)
    return [sheet]

def analysis(journal: list, folds: list) -> tuple[list, list]:
    panes, sheets = [], []
    if not journal: return panes, sheets
    staged = any(record.get("Stage") is not None for record in journal)
    rounded = any((record.get("Round") or 1) > 1 for record in journal)
    panes.extend(generalization(folds))
    panes.extend(drift(folds))
    panes.extend(convergence(journal))
    panes.extend(episodes(journal))
    panes.extend(sensitivity(journal))
    if staged:
        marks = winners(journal, "Fold", "Stage")
        if marks:
            sheet = SheetAPI.frame(name="Stages", columns=list(marks[0].keys()), rows=marks)
            sheet.height = len(marks)
            sheets.append(sheet)
    if rounded:
        marks = winners(journal, "Fold", "Stage", "Round")
        if marks:
            sheet = SheetAPI.frame(name="Rounds", columns=list(marks[0].keys()), rows=marks)
            sheet.height = len(marks)
            sheets.append(sheet)
    if any(record.get("Episode") is not None for record in journal):
        seeded = any(record.get("Seed") is not None for record in journal)
        marks = [{**({"Seed": record.get("Seed")} if seeded else {}),
                  "Fold": record.get("Fold"), "Episode": record.get("Episode"),
                  "Train": record.get("Train"), "Validation": record.get("Validation"),
                  "Return (%)": record.get("Return"), "Eligible": record.get("Eligible")} for record in journal]
        sheet = SheetAPI.frame(name="Episodes", columns=list(marks[0].keys()), rows=marks)
        sheet.height = len(marks)
        sheets.append(sheet)
    sheets.extend(leaderboard(journal))
    return panes, sheets

_HEADLINES_ = {"walkforward": ("rolling", "Walk-Forward"), "growth": ("strategy", "Growth")}

def headline(payload: dict) -> tuple:
    wanted = payload.get("headline") or "growth"
    for pane in (wanted, "growth"):
        key, label = _HEADLINES_.get(pane, ("strategy", "Growth"))
        points = trace(payload, pane, key)
        if points: return points, label
    equity = [(point["time"], point["value"]) for point in trace(payload, "accounts", "equity")]
    return PointAPI.line(PointAPI.rebase(equity)), "Growth"

def compare(entries: list, title: str = "Run Comparison") -> WorkspaceAPI:
    lifted = []
    for name, payload in entries:
        points, kind = headline(payload)
        points = diurnal(points)
        if not points: continue
        record = tabulate(payload, "Net", NET_TOTAL_INDIVIDUAL)
        for label, value in transpose(payload, BENCHMARK_LABEL).items(): record.setdefault(label, value)
        lifted.append((name, kind, points, record))
    if not lifted: return WorkspaceAPI(title=title, panes=[], sheets=[])
    labels = [name for name, _, _, _ in lifted]
    kinds = [kind for _, kind, _, _ in lifted]
    records = [record for _, _, _, record in lifted]
    mixed = len(set(kinds)) > 1
    curves = [SeriesAPI(key=f"run{index}", name=f"{name} · {kind}" if mixed else name,
                        color=_TINTS_[index % len(_TINTS_)], width=2, data=points)
              for index, (name, kind, points, _) in enumerate(lifted)]
    caption = ("Headline Curve · mixed bases · rebased to 100 · Daily Resolution" if mixed
               else f"{kinds[0]} · Rebased to 100 at each run's first bar · Daily Resolution")
    panes = [PaneAPI(id="growth", title=caption, flex=60, format=FormatType.Value, datum=100.0, series=curves)]
    wanted = [metric for metric in (*_COMPARED_, *_BENCHMARKED_) if any(metric in record for record in records)]
    rows = [{"Metric": "Curve", **dict(zip(labels, kinds))}] if mixed else []
    rows += [{"Metric": metric, **{label: record.get(metric) for label, record in zip(labels, records)}} for metric in wanted]
    sheets = [SheetAPI.frame(name="Metrics", columns=["Metric", *labels], rows=rows, key="Metric")]
    return WorkspaceAPI(title=title, panes=panes, sheets=sheets)

def searchspace(*, workspace: WorkspaceAPI, journal: list, folds: list, elected: list = None) -> WorkspaceAPI:
    walked, folded = walkforward(folds or [], elected)
    panes, sheets = analysis(journal or [], folds or [])
    timed = [pane for pane in (*walked, *panes, *workspace.panes) if pane.scale == "time"]
    indexed = [pane for pane in (*walked, *panes, *workspace.panes) if pane.scale != "time"]
    workspace.panes = [*timed, *indexed]
    workspace.sheets = [*folded, *sheets, *workspace.sheets]
    if walked: workspace.headline = "walkforward"
    return workspace

def backtest(*, title: str, description: str = None, currency: str = "", anchor=None,
             bars: list, equity: list, balance: list, signals=(), trades=(),
             benchmarks: dict = None, directional=None, volumetric=None, sheets: dict = None,
             markers: bool = False, dealmap: bool = True, deals: int = 400, rows: int = 500) -> WorkspaceAPI:
    spine = [bar[0] for bar in bars]
    spans = {str(uid): SpanAPI(direction=direction, entry=entry, exit=exit, entryPrice=entry_price, exitPrice=exit_price, net=net)
             for uid, direction, entry, exit, entry_price, exit_price, net in trades if uid is not None and entry is not None}
    stamps = []
    for uid, direction, entry, exit, entry_price, exit_price, net in trades:
        long = direction == "Buy"
        if entry is not None:
            stamps.append(MarkerAPI(time=entry, position="belowBar" if long else "aboveBar", uid=uid,
                                    color="up" if long else "down", shape="arrowUp" if long else "arrowDown", size=1.4))
        if exit is not None:
            stamps.append(MarkerAPI(time=exit, position="aboveBar" if long else "belowBar", uid=uid,
                                    color="up" if long else "down", shape="square", size=0.9))
    stamps.sort(key=lambda marker: PointAPI.epoch(marker.time))
    map = [DealAPI(uid=uid, color="up" if (net or 0.0) > 0.0 else "down", side=direction,
                   points=[{"time": PointAPI.epoch(entry), "value": entry_price}, {"time": PointAPI.epoch(exit), "value": exit_price}])
           for uid, direction, entry, exit, entry_price, exit_price, net in list(trades)[:deals]
           if None not in (entry, exit, entry_price, exit_price)]

    def thresholds(bounds) -> list:
        if not bounds: return []
        lines = []
        for pair, kind, color in ((bounds[0], "Entry", "entry"), (bounds[1], "Exit", "exit")):
            if not pair: continue
            lower, upper = pair
            if upper is not None: lines.append(LineAPI(price=float(upper), title=f"Buy {kind}", color=color))
            if lower is not None: lines.append(LineAPI(price=float(lower), title=f"Sell {kind}", color=color))
        return lines

    traded = PointAPI.volumes(bars)
    price = [SeriesAPI(key="candles", name="Candles", kind=SeriesType.Candlestick, color="up", data=PointAPI.candles(bars), markers=stamps),
             SeriesAPI(key="close", name="Close", kind=SeriesType.Line, color="secondary", width=2, visible=False,
                       data=PointAPI.line([(bar[0], bar[4]) for bar in bars]))]
    if traded:
        price.append(SeriesAPI(key="traded", name="Volume", kind=SeriesType.Histogram, color="traded", axis=AxisType.Left,
                               toggle=True, visible=True, data=traded))
    panes = [PaneAPI(id="price", title="Price", flex=38, format=FormatType.Price, margins={"top": 0.12, "bottom": 0.10},
                     underlay={"top": 0.78, "bottom": 0.0} if traded else None, series=price)]

    if signals:
        direction = PointAPI.line(PointAPI.conform([(stamp, signal) for stamp, signal, _, _, _ in signals], spine))
        delta = PointAPI.line(PointAPI.conform([(stamp, value) for stamp, _, value, _, _ in signals], spine))
        volume = PointAPI.line(PointAPI.conform([(stamp, value) for stamp, _, _, value, _ in signals], spine))
        shift = PointAPI.line(PointAPI.conform([(stamp, value) for stamp, _, _, _, value in signals], spine))
        entries = thresholds(directional)
        panes.append(PaneAPI(id="signal", title="Direction", flex=13, format=FormatType.Signal, bound=PointAPI.bound(direction, entries),
                             margins={"top": 0.16, "bottom": 0.16}, lines=entries, datum=0.0, series=[
            SeriesAPI(key="dsignal", name="Direction Signal", color="equity", width=2, toggle=True, data=direction),
            SeriesAPI(key="ddelta", name="Direction Delta", kind=SeriesType.Histogram, color="band", axis=AxisType.Left, toggle=True, visible=True, data=delta)]))
        exits = thresholds(volumetric)
        panes.append(PaneAPI(id="volume", title="Volume", flex=12, format=FormatType.Volume, bound=PointAPI.bound(volume, exits),
                             margins={"top": 0.16, "bottom": 0.16}, lines=exits, datum=0.0, series=[
            SeriesAPI(key="vsignal", name="Volume Signal", color="long", width=2, toggle=True, data=volume),
            SeriesAPI(key="vdelta", name="Volume Delta", kind=SeriesType.Histogram, color="short", axis=AxisType.Left, toggle=True, visible=True, data=shift)]))

    accounts = [series for series in (
        SeriesAPI(key="balance", name="Balance", color="balance", width=2, data=PointAPI.line(PointAPI.conform(balance, spine))),
        SeriesAPI(key="equity", name="Equity", color="equity", width=2, data=PointAPI.line(PointAPI.conform(equity, spine)))) if series.data]
    if accounts:
        opening = balance[0][1] if balance else (equity[0][1] if equity else None)
        panes.append(PaneAPI(id="accounts", title=f"Balance & Equity ({currency})", flex=17, format=FormatType.Value, datum=opening, series=accounts))

    depths, rises = underwater(equity), overwater(equity)
    if depths or rises:
        swings = [series for series in (
            SeriesAPI(key="underwater", name="Drawdown", color="short", width=2,
                      data=PointAPI.line(PointAPI.conform(depths, spine))),
            SeriesAPI(key="overwater", name="Runup", color="up", width=2,
                      data=PointAPI.line(PointAPI.conform(rises, spine)))) if series.data]
        panes.append(PaneAPI(id="underwater", title="Drawdown & Runup (%) · Bar Close", flex=16,
                             format=FormatType.Percent, datum=0.0, series=swings))

    growth = []
    if equity: growth.append(SeriesAPI(key="strategy", name="Strategy", color="equity", width=2,
                                       data=PointAPI.line(PointAPI.conform(PointAPI.rebase(equity, anchor), spine))))
    for index, (name, series) in enumerate((benchmarks or {}).items()):
        if not series: continue
        growth.append(SeriesAPI(key=f"benchmark{index}", name=name, color=f"benchmark{index % 4}", width=2,
                                data=PointAPI.line(PointAPI.conform(PointAPI.rebase(series, anchor), spine))))
    if growth: panes.append(PaneAPI(id="growth", title="Growth vs Benchmarks (rebased 100)", flex=20, format=FormatType.Value, datum=100.0, series=growth))

    tables = []
    for name, frame in (sheets or {}).items():
        if frame is None or not hasattr(frame, "columns") or frame.is_empty(): continue
        columns = [str(column) for column in frame.columns]
        body = frame.head(rows).rows(named=True)
        sheet = SheetAPI.frame(name=name, columns=columns, rows=body)
        sheet.keys = [[key for key in keys if key in spans] for keys in sheet.keys]
        sheet.height = frame.height
        tables.append(sheet)

    travel = excursion(bars, trades)
    if travel:
        sheet = SheetAPI.frame(name="Excursion", columns=list(travel[0].keys()), rows=travel[:rows])
        sheet.keys = [[key for key in keys if key in spans] for keys in sheet.keys]
        sheet.height = len(travel)
        tables.append(sheet)

    sharpes, volatilities = rolling(equity)
    if sharpes:
        trailing = [SeriesAPI(key="rsharpe", name="Rolling Sharpe", color="equity", width=2, data=PointAPI.line(PointAPI.conform(sharpes, spine))),
                    SeriesAPI(key="rvol", name="Rolling Volatility (%)", color="band", width=2, axis=AxisType.Left,
                              data=PointAPI.line(PointAPI.conform(volatilities, spine)))]
        for index, (name, series) in enumerate((benchmarks or {}).items()):
            betas = covariant(equity, series)
            if not betas: continue
            trailing.append(SeriesAPI(key=f"rbeta{index}", name=f"Rolling Beta vs {name}", color=f"benchmark{index % 4}", width=2,
                                      axis=AxisType.Left, data=PointAPI.line(PointAPI.conform(betas, spine))))
        panes.append(PaneAPI(id="rolling", title="Rolling Sharpe · Volatility · Beta (63 bar window)", flex=15, format=FormatType.Value, datum=0.0, series=trailing))

    spread = distribution(equity)
    if spread:
        tables.append(SheetAPI.frame(name="Distribution", columns=["Return (%)", "Periods"],
                                     rows=[{"Return (%)": round(edge, 3), "Periods": count} for edge, count in spread]))

    calendar = periodic(equity)
    if calendar:
        tables.append(SheetAPI.frame(name="Monthly", columns=list(calendar[0].keys()), rows=calendar))

    return WorkspaceAPI(title=title, description=description, currency=currency, panes=panes, sheets=tables,
                        spans=spans, deals=map, markers=markers, dealmap=dealmap)

__all__ = ["excursion", "walkforward", "convergence", "sensitivity", "generalization", "drift", "episodes", "leaderboard", "analysis", "headline", "compare", "searchspace", "backtest"]