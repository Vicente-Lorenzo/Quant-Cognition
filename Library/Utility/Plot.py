from __future__ import annotations

import json
import webbrowser

from datetime import datetime, timezone
from pathlib import Path
from typing import Union

class PlotAPI:

    _LIBRARY_: Path = Path(__file__).parent / "Assets" / "lightweight-charts.js"

    _PLANE_: str = "#0b0e14"
    _SURFACE_: str = "#131722"
    _INK_: str = "#ffffff"
    _SECONDARY_: str = "#b8c0cc"
    _MUTED_: str = "#7b8798"
    _GRID_: str = "#1e2431"
    _BORDER_: str = "#2a3242"
    _EQUITY_: str = "#3d9bff"
    _BALANCE_: str = "#00e07a"
    _BENCHMARKS_: tuple = ("#a77bff", "#ff8a3d", "#22d3ee", "#ffd23d")
    _UP_: str = "#00e07a"
    _DOWN_: str = "#ff3b5c"
    _LONG_: str = "#3d9bff"
    _SHORT_: str = "#ff3b5c"
    _DATUM_: str = "#8a94a6"
    _BAND_: str = "#ffd23d"
    _FONT_: str = "system-ui, -apple-system, 'Segoe UI', sans-serif"
    _DIGITS_: int = 7
    _ROWS_: int = 500

    def __init__(self,
                 title: str,
                 currency: str = "EUR",
                 bars: Union[list, None] = None,
                 equity: Union[list, None] = None,
                 balance: Union[list, None] = None,
                 signals: Union[list, None] = None,
                 trades: Union[list, None] = None,
                 benchmarks: Union[dict, None] = None,
                 thresholds: Union[tuple, None] = None,
                 tables: Union[dict, None] = None) -> None:
        self._title_ = title
        self._currency_ = currency
        self._bars_ = bars or []
        self._equity_ = equity or []
        self._balance_ = balance or []
        self._signals_ = signals or []
        self._trades_ = trades or []
        self._benchmarks_ = benchmarks or {}
        self._thresholds_ = thresholds
        self._sheets_ = tables or {}

    @staticmethod
    def _epoch_(stamp: datetime) -> int:
        return int(stamp.replace(tzinfo=timezone.utc).timestamp())

    @classmethod
    def _compact_(cls, value):
        if isinstance(value, float): return float(f"{value:.{cls._DIGITS_}g}")
        if isinstance(value, dict): return {key: cls._compact_(entry) for key, entry in value.items()}
        if isinstance(value, list): return [cls._compact_(entry) for entry in value]
        return value

    @classmethod
    def _unique_(cls, points: list) -> list:
        ordered, seen = [], None
        for point in sorted(points, key=lambda entry: entry["time"]):
            if point["time"] == seen: ordered[-1] = point
            else: ordered.append(point); seen = point["time"]
        return ordered

    @classmethod
    def _candles_(cls, bars: list) -> list:
        return cls._unique_([{"time": cls._epoch_(bar[0]), "open": bar[1], "high": bar[2], "low": bar[3], "close": bar[4]} for bar in bars])

    @classmethod
    def _line_(cls, series: list) -> list:
        return cls._unique_([{"time": cls._epoch_(stamp), "value": value} for stamp, value in series if value is not None])

    @staticmethod
    def _conform_(series: list, spine: list) -> list:
        if not series or not spine: return []
        conformed, index, current = [], 0, None
        for stamp in spine:
            while index < len(series) and series[index][0] <= stamp:
                current = series[index][1]
                index += 1
            conformed.append((stamp, current))
        return conformed

    @staticmethod
    def _anchor_(series: list) -> Union[datetime, None]:
        starts = [entry[0][0] for entry in series if entry]
        return max(starts) if starts else None

    @staticmethod
    def _rebase_(series: list, anchor: Union[datetime, None]) -> list:
        base = None
        for stamp, value in series:
            if value and (anchor is None or stamp <= anchor): base = value
            elif base is None and value: base = value
        return [(stamp, 100.0 * value / base if base and value else None) for stamp, value in series]

    def _markers_(self) -> list:
        markers = []
        for uid, direction, entry, exit, entry_price, exit_price, net in self._trades_:
            long = direction == "Buy"
            if entry is not None:
                markers.append({"time": self._epoch_(entry), "position": "belowBar" if long else "aboveBar", "uid": uid,
                                "color": self._UP_ if long else self._DOWN_, "shape": "arrowUp" if long else "arrowDown", "size": 1.4})
            if exit is not None:
                markers.append({"time": self._epoch_(exit), "position": "aboveBar" if long else "belowBar", "uid": uid,
                                "color": self._UP_ if long else self._DOWN_, "shape": "square", "size": 0.9})
        return sorted(markers, key=lambda marker: marker["time"])

    def _spans_(self) -> dict:
        spans = {}
        for uid, direction, entry, exit, entry_price, exit_price, net in self._trades_:
            if uid is None or entry is None: continue
            spans[str(uid)] = {"direction": direction, "entry": self._epoch_(entry), "exit": self._epoch_(exit) if exit is not None else None,
                               "entryPrice": entry_price, "exitPrice": exit_price, "net": net}
        return spans

    @staticmethod
    def _bound_(series: list) -> Union[float, None]:
        extremes = [abs(point["value"]) for point in series if point.get("value") is not None]
        return max(extremes) or None if extremes else None

    @classmethod
    def _cell_(cls, value):
        if value is None: return ""
        if isinstance(value, bool): return "Yes" if value else "No"
        if isinstance(value, float): return f"{value:,.{cls._DIGITS_}g}"
        if isinstance(value, int): return f"{value:,}"
        if isinstance(value, (list, tuple)): return " · ".join(cls._cell_(entry) for entry in value)
        return str(value)

    @staticmethod
    def _keys_(value) -> list:
        if value is None: return []
        if isinstance(value, (list, tuple)): return [str(entry) for entry in value if entry is not None]
        return [str(value)]

    def _sheets_payload_(self) -> list:
        sheets, spans = [], self._spans_()
        for name, table in self._sheets_.items():
            if table is None or not hasattr(table, "columns") or table.is_empty(): continue
            columns = [str(column) for column in table.columns]
            rows = table.head(self._ROWS_).rows()
            index = columns.index("UID") if "UID" in columns else None
            keys = [[key for key in self._keys_(row[index]) if key in spans] for row in rows] if index is not None else []
            sheets.append({"name": name, "columns": columns,
                           "rows": [[self._cell_(cell) for cell in row] for row in rows],
                           "keys": keys, "height": table.height, "shown": len(rows)})
        return sheets

    def _panes_(self) -> list:
        spine = [bar[0] for bar in self._bars_]
        glyphs = [{"name": "Buy Opened", "color": self._UP_, "symbol": "▲"}, {"name": "Buy Closed", "color": self._UP_, "symbol": "■"},
                  {"name": "Sell Opened", "color": self._DOWN_, "symbol": "▼"}, {"name": "Sell Closed", "color": self._DOWN_, "symbol": "■"}] if self._trades_ else []
        panes = [{"id": "price", "title": "Price", "flex": 38, "format": "price", "margins": {"top": 0.12, "bottom": 0.10}, "glyphs": glyphs, "series": [
            {"key": "candles", "name": "Candles", "type": "candlestick", "color": self._UP_, "data": self._candles_(self._bars_), "markers": self._markers_()},
            {"key": "close", "name": "Close", "type": "line", "color": self._SECONDARY_, "width": 1, "visible": False, "markers": self._markers_(), "data": self._line_([(bar[0], bar[4]) for bar in self._bars_])}]}]
        accounts = [series for series in (
            {"key": "balance", "name": "Balance", "type": "line", "color": self._BALANCE_, "width": 2, "data": self._line_(self._conform_(self._balance_, spine))},
            {"key": "equity", "name": "Equity", "type": "line", "color": self._EQUITY_, "width": 2, "data": self._line_(self._conform_(self._equity_, spine))}) if series["data"]]
        if self._signals_:
            raw = self._line_(self._conform_([(stamp, value) for stamp, value, _ in self._signals_], spine))
            panes.append({"id": "signal", "title": "Signal", "flex": 13, "format": "signal", "bound": self._bound_(raw), "margins": {"top": 0.10, "bottom": 0.10}, "lines": list(self._thresholds_ or ()), "datum": 0.0, "series": [
                {"key": "signal", "name": "Raw Signal", "type": "line", "color": self._EQUITY_, "width": 2, "data": raw}]})
            volumes = self._unique_([{"time": self._epoch_(stamp), "value": volume, "color": self._LONG_ if volume > 0 else self._SHORT_} for stamp, _, volume in self._signals_ if volume])
            panes.append({"id": "volume", "title": "Signal Volume", "flex": 12, "format": "volume", "bound": self._bound_(volumes), "margins": {"top": 0.10, "bottom": 0.10}, "datum": 0.0, "series": [
                {"key": "volume", "name": "Signal Volume", "type": "histogram", "color": self._LONG_, "data": volumes}]})
        opening = self._balance_[0][1] if self._balance_ else (self._equity_[0][1] if self._equity_ else None)
        if accounts: panes.append({"id": "accounts", "title": f"Balance & Equity ({self._currency_})", "flex": 17, "format": "value", "datum": opening, "series": accounts})
        curves = [self._equity_] + [series for series in self._benchmarks_.values() if series]
        anchor = self._anchor_(curves)
        growth = []
        if self._equity_: growth.append({"key": "strategy", "name": "Strategy", "type": "line", "color": self._EQUITY_, "width": 2, "data": self._line_(self._conform_(self._rebase_(self._equity_, anchor), spine))})
        for index, (name, series) in enumerate(self._benchmarks_.items()):
            if not series: continue
            growth.append({"key": f"benchmark{index}", "name": name, "type": "line", "color": self._BENCHMARKS_[index % len(self._BENCHMARKS_)], "width": 2, "data": self._line_(self._conform_(self._rebase_(series, anchor), spine))})
        if growth: panes.append({"id": "growth", "title": "Growth vs Benchmarks (rebased 100)", "flex": 20, "format": "value", "datum": 100.0, "series": growth})
        return panes

    def _document_(self) -> str:
        panes = self._panes_()
        for index, pane in enumerate(panes): pane["last"] = index == len(panes) - 1
        timeline = sorted({point["time"] for pane in panes for series in pane["series"] for point in series["data"]})
        payload = {"title": self._title_, "currency": self._currency_, "panes": panes, "sheets": self._sheets_payload_(), "spans": self._spans_(), "timeline": [{"time": stamp} for stamp in timeline],
                   "theme": {"plane": self._PLANE_, "surface": self._SURFACE_, "ink": self._INK_, "secondary": self._SECONDARY_,
                             "muted": self._MUTED_, "grid": self._GRID_, "border": self._BORDER_, "up": self._UP_, "down": self._DOWN_, "datum": self._DATUM_, "band": self._BAND_}}
        return _TEMPLATE_.replace("__LIBRARY__", self._LIBRARY_.read_text(encoding="utf-8")).replace("__PAYLOAD__", json.dumps(self._compact_(payload), default=str, separators=(",", ":"))).replace("__FONT__", self._FONT_)

    def render(self, directory: Path, name: str = "Plot", show: bool = True) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.html"
        path.write_text(self._document_(), encoding="utf-8")
        if show: webbrowser.open(path.as_uri())
        return path

_TEMPLATE_ = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quant Plot</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; height: 100%; width: 100%; background: #0b0e14; }
  body { font-family: __FONT__; color: #b8c0cc; display: flex; flex-direction: column; overflow-x: hidden; }
  header { flex: 0 0 auto; padding: 9px 14px; border-bottom: 1px solid #1e2431; background: #0b0e14; position: sticky; top: 0; z-index: 5; }
  h1 { margin: 0; font-size: 14px; font-weight: 600; color: #ffffff; letter-spacing: .01em; }
  .bar { flex: 0 0 auto; display: flex; align-items: center; gap: 10px; padding: 5px 12px;
         background: #0b0e14; border-bottom: 1px solid #1e2431; overflow-x: auto; scrollbar-width: thin; }
  .chips { display: flex; gap: 5px; flex-wrap: nowrap; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 9px; border: 1px solid #2a3242; border-radius: 999px;
          font-size: 11px; line-height: 1.4; cursor: pointer; user-select: none; background: #171b26; color: #b8c0cc; white-space: nowrap; }
  .chip:hover { border-color: #4a5568; }
  .chip.off { opacity: .4; }
  .glyph { display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; font-size: 11px;
           color: #7b8798; white-space: nowrap; cursor: default; }
  .glyph i { font-style: normal; font-size: 12px; line-height: 1; }
  .swatch { width: 9px; height: 9px; border-radius: 2px; flex: 0 0 auto; }
  .chip b { font-weight: 600; color: #ffffff; font-variant-numeric: tabular-nums; }
  main { flex: 1 0 auto; display: flex; flex-direction: column; min-height: 0; }
  .pane { display: flex; flex-direction: column; min-height: 0; }
  .pane-title { font-size: 10px; color: #7b8798; letter-spacing: .04em; text-transform: uppercase; white-space: nowrap; flex: 0 0 auto; }
  .chart { flex: 1 1 auto; min-height: 0; position: relative; }
  .sheets { flex: 0 0 auto; border-top: 1px solid #2a3242; background: #0b0e14; }
  .grid { overflow: auto; max-height: 78vh; }
  table { border-collapse: collapse; width: 100%; font-size: 11px; font-variant-numeric: tabular-nums; }
  thead th { position: sticky; top: 0; background: #171b26; color: #ffffff; font-weight: 600; text-align: right;
             padding: 6px 10px; border-bottom: 1px solid #2a3242; white-space: nowrap; z-index: 1; }
  thead th:first-child, tbody td:first-child { text-align: left; }
  tbody td { padding: 4px 10px; border-bottom: 1px solid #161b26; text-align: right; white-space: nowrap; color: #b8c0cc; }
  tbody tr:nth-child(even) { background: #10141d; }
  tbody tr:hover { background: #1a2130; }
  tbody tr.link { cursor: pointer; }
  tbody tr.on, tbody tr.on:nth-child(even) { background: #223049; box-shadow: inset 2px 0 0 #3d9bff; }
  tbody tr.on td { color: #ffffff; }
  .count { font-size: 10px; color: #7b8798; padding: 6px 12px; }
</style></head>
<body>
<header><h1 id="title"></h1></header>
<main id="panes"></main>
<section class="sheets" id="sheets" hidden><div class="bar"><span class="pane-title">Report</span><span class="chips" id="tabs"></span><span class="count" id="count"></span></div><div class="grid" id="grid"></div></section>
<script>__LIBRARY__</script>
<script>
const DATA = __PAYLOAD__;
const T = DATA.theme;
document.getElementById("title").textContent = DATA.title;
document.title = DATA.title;
const panesRoot = document.getElementById("panes");
const charts = [], registry = [], priced = [];
const fmt = (kind, value) => {
  if (value === undefined || value === null) return "–";
  if (kind === "signal") return value.toFixed(4);
  if (kind === "volume") return Math.round(value).toLocaleString();
  if (kind === "price") return value.toFixed(5);
  return value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
};
DATA.panes.forEach((pane) => {
  const host = document.createElement("section");
  host.className = "pane";
  host.style.flex = pane.flex + " 1 0";
  const bar = document.createElement("div"); bar.className = "bar";
  const label = document.createElement("span"); label.className = "pane-title"; label.textContent = pane.title;
  const chips = document.createElement("span"); chips.className = "chips";
  bar.append(label, chips);
  const holder = document.createElement("div"); holder.className = "chart";
  host.append(bar, holder); panesRoot.append(host);
  const chart = LightweightCharts.createChart(holder, {
    autoSize: true,
    layout: { background: { type: "solid", color: T.surface }, textColor: T.secondary, fontFamily: getComputedStyle(document.body).fontFamily, fontSize: 11, attributionLogo: false },
    grid: { vertLines: { color: T.grid }, horzLines: { color: T.grid } },
    rightPriceScale: { borderColor: T.border, scaleMargins: pane.margins || { top: 0.10, bottom: 0.08 } },
    timeScale: { borderColor: T.border, timeVisible: true, secondsVisible: false, rightOffset: 4, visible: pane.last, minBarSpacing: 0.02 },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal,
                 vertLine: { color: T.muted, width: 1, style: 3, labelBackgroundColor: T.border },
                 horzLine: { color: T.muted, width: 1, style: 3, labelBackgroundColor: T.border } },
    handleScale: { axisPressedMouseMove: { time: true, price: false } },
    localization: { priceFormatter: (value) => fmt(pane.format, value) }
  });
  charts.push(chart);
  if (DATA.timeline && DATA.timeline.length) {
    const backbone = chart.addLineSeries({ lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false });
    backbone.setData(DATA.timeline);
  }
  pane.series.forEach((spec) => {
    let series;
    const base = { priceLineVisible: false, lastValueVisible: false };
    if (pane.bound) base.autoscaleInfoProvider = () => ({ priceRange: { minValue: -pane.bound, maxValue: pane.bound } });
    if (spec.type === "candlestick") {
      series = chart.addCandlestickSeries({ ...base, upColor: T.up, downColor: T.down, borderUpColor: T.up, borderDownColor: T.down, wickUpColor: T.up, wickDownColor: T.down });
    } else if (spec.type === "histogram") {
      series = chart.addHistogramSeries({ ...base, color: spec.color, priceFormat: { type: "volume" } });
    } else {
      series = chart.addLineSeries({ ...base, color: spec.color, lineWidth: spec.width || 2, lineType: 0 });
    }
    series.setData(spec.data);
    if (spec.markers && spec.markers.length) { series.__markers__ = spec.markers; series.setMarkers(spec.markers); priced.push(series); }
    if (spec.visible === false) series.applyOptions({ visible: false });
    if (!chart.__bands__) {
      chart.__bands__ = true;
      (pane.lines || []).forEach((level) => series.createPriceLine({ price: level, color: T.band, lineWidth: 1, lineStyle: 2, axisLabelVisible: true, axisLabelColor: T.band, axisLabelTextColor: "#0b0e14", title: "entry" }));
    }
    if (pane.datum !== undefined && pane.datum !== null && !chart.__datum__) {
      chart.__datum__ = true;
      series.createPriceLine({ price: pane.datum, color: T.datum, lineWidth: 1, lineStyle: 0, axisLabelVisible: true, axisLabelColor: T.border, axisLabelTextColor: T.ink });
    }
    const chip = document.createElement("span");
    chip.className = "chip" + (spec.visible === false ? " off" : "");
    chip.innerHTML = '<span class="swatch" style="background:' + (spec.type === "candlestick" ? T.up : spec.color) + '"></span><span>' + spec.name + "</span> <b></b>";
    chip.onclick = () => { const on = !(series.options().visible === false); series.applyOptions({ visible: !on }); chip.classList.toggle("off", on); };
    chips.append(chip);
    const lookup = new Map();
    spec.data.forEach((point) => lookup.set(point.time, point.close !== undefined ? point.close : point.value));
    if (!chart.__primary__) { chart.__primary__ = series; chart.__lookup__ = lookup; }
    registry.push({ series, chip, chart, lookup, format: pane.format, type: spec.type });
  });
  (pane.glyphs || []).forEach((glyph) => {
    const badge = document.createElement("span");
    badge.className = "glyph";
    badge.innerHTML = '<i style="color:' + glyph.color + '">' + glyph.symbol + "</i>" + glyph.name;
    chips.append(badge);
  });
});
let syncing = false;
charts.forEach((chart) => {
  chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (syncing || !range) return; syncing = true;
    charts.forEach((other) => { if (other !== chart) other.timeScale().setVisibleLogicalRange(range); });
    syncing = false;
  });
  chart.subscribeCrosshairMove((param) => {
    const stamp = param.time;
    registry.forEach((entry) => {
      const value = stamp === undefined ? undefined : entry.lookup.get(stamp);
      entry.chip.querySelector("b").textContent = value === undefined || value === null ? "" : fmt(entry.format, value);
    });
    charts.forEach((other) => {
      if (other === chart) return;
      if (param.point && stamp !== undefined && other.__primary__) {
        const value = other.__lookup__ ? other.__lookup__.get(stamp) : undefined;
        other.setCrosshairPosition(value === undefined || value === null ? 0 : value, stamp, other.__primary__);
      } else other.clearCrosshairPosition();
    });
  });
});
const sheets = DATA.sheets || [];
if (sheets.length) {
  const host = document.getElementById("sheets"), tabs = document.getElementById("tabs");
  const grid = document.getElementById("grid"), count = document.getElementById("count");
  host.hidden = false;
  panesRoot.style.height = "calc(100vh - " + document.querySelector("header").offsetHeight + "px)";
  const spans = DATA.spans || {};
  let lines = [];
  const clear = () => {
    lines.forEach((entry) => entry.series.removePriceLine(entry.line));
    lines = [];
    priced.forEach((series) => series.setMarkers(series.__markers__));
  };
  const select = (keys, row) => {
    clear();
    const chosen = keys.map((key) => spans[key]).filter(Boolean);
    if (!chosen.length) return;
    grid.querySelectorAll("tr.on").forEach((other) => other.classList.remove("on"));
    row.classList.add("on");
    const picked = new Set(keys);
    priced.forEach((series) => series.setMarkers(series.__markers__.map((marker) =>
      picked.has(String(marker.uid)) ? { ...marker, size: 2.4, text: marker.shape === "square" ? "EXIT" : "ENTRY" } : { ...marker, color: T.border })));
    const first = chosen[0], colour = first.direction === "Buy" ? T.up : T.down;
    chosen.forEach((span) => priced.forEach((series) => {
      [["entryPrice", 0], ["exitPrice", 2]].forEach(([field, style]) => {
        if (span[field] === null || span[field] === undefined) return;
        lines.push({ series, line: series.createPriceLine({ price: span[field], color: colour, lineWidth: 1, lineStyle: style, axisLabelVisible: true, axisLabelColor: colour, axisLabelTextColor: "#0b0e14" }) });
      });
    }));
    const starts = chosen.map((span) => span.entry), ends = chosen.map((span) => span.exit || span.entry);
    const from = Math.min(...starts), to = Math.max(...ends), pad = Math.max((to - from) * 1.5, 86400);
    charts.forEach((chart) => chart.timeScale().setVisibleRange({ from: from - pad, to: to + pad }));
  };
  const draw = (sheet) => {
    const head = "<tr>" + sheet.columns.map((column) => "<th>" + column + "</th>").join("") + "</tr>";
    const body = sheet.rows.map((row) => "<tr>" + row.map((cell) => "<td>" + cell + "</td>").join("") + "</tr>").join("");
    grid.innerHTML = "<table><thead>" + head + "</thead><tbody>" + body + "</tbody></table>";
    grid.scrollTop = 0;
    clear();
    const keys = sheet.keys || [];
    [...grid.querySelectorAll("tbody tr")].forEach((row, index) => {
      const linked = keys[index] || [];
      if (!linked.length) return;
      row.classList.add("link");
      row.onclick = () => { if (row.classList.contains("on")) { row.classList.remove("on"); clear(); } else select(linked, row); };
    });
    count.textContent = (sheet.shown < sheet.height ? "Showing " + sheet.shown + " of " + sheet.height + " rows" : sheet.height + " rows") + (keys.some((entry) => entry.length) ? " · click a row to highlight it on the charts" : "");
  };
  sheets.forEach((sheet, index) => {
    const tab = document.createElement("span");
    tab.className = "chip" + (index ? " off" : "");
    tab.textContent = sheet.name;
    tab.onclick = () => { tabs.querySelectorAll(".chip").forEach((other) => other.classList.add("off")); tab.classList.remove("off"); draw(sheet); };
    tabs.append(tab);
  });
  draw(sheets[0]);
}
requestAnimationFrame(() => charts.forEach((chart) => chart.timeScale().fitContent()));
</script></body></html>
"""

__all__ = ["PlotAPI"]