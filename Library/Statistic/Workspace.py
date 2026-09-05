import json
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any
from typing_extensions import Self

from Library.Utility.Enumeration import EnumerationAPI

class SeriesType(EnumerationAPI):

    Candlestick = "candlestick"
    Line = "line"
    Area = "area"
    Histogram = "histogram"
    Bar = "bar"
    Baseline = "baseline"

class AxisType(EnumerationAPI):

    Right = "right"
    Left = "left"

class FormatType(EnumerationAPI):

    Price = "price"
    Signal = "signal"
    Volume = "volume"
    Value = "value"
    Percent = "percent"
    Integer = "integer"
    Text = "text"

class AlignType(EnumerationAPI):

    Left = "left"
    Right = "right"
    Center = "center"

class PointAPI:

    _DIGITS_: int = 7

    @staticmethod
    def epoch(stamp) -> int:
        if isinstance(stamp, (int, float)): return int(stamp)
        if isinstance(stamp, datetime): return int(stamp.replace(tzinfo=timezone.utc).timestamp())
        if isinstance(stamp, date): return int(datetime(stamp.year, stamp.month, stamp.day, tzinfo=timezone.utc).timestamp())
        return int(stamp)

    @classmethod
    def compact(cls, value):
        if isinstance(value, bool): return value
        if isinstance(value, float): return float(f"{value:.{cls._DIGITS_}g}")
        if isinstance(value, dict): return {key: cls.compact(entry) for key, entry in value.items()}
        if isinstance(value, (list, tuple)): return [cls.compact(entry) for entry in value]
        return value

    @staticmethod
    def unique(points: list) -> list:
        ordered, seen = [], None
        for point in sorted(points, key=lambda entry: entry["time"]):
            if point["time"] == seen: ordered[-1] = point
            else: ordered.append(point); seen = point["time"]
        return ordered

    @classmethod
    def candles(cls, bars: list) -> list:
        return cls.unique([{"time": cls.epoch(bar[0]), "open": bar[1], "high": bar[2], "low": bar[3], "close": bar[4]} for bar in bars])

    @classmethod
    def volumes(cls, bars: list, index: int = 6) -> list:
        if not bars or len(bars[0]) <= index: return []
        points = [{"time": cls.epoch(bar[0]), "value": bar[index], "color": "traded"}
                  for bar in bars if bar[index] is not None]
        return cls.unique(points) if any(point["value"] for point in points) else []

    @classmethod
    def line(cls, series: list) -> list:
        return cls.unique([{"time": cls.epoch(stamp), "value": value} for stamp, value in series if value is not None])

    @staticmethod
    def conform(series: list, spine: list) -> list:
        if not series or not spine: return []
        conformed, index, current = [], 0, None
        for stamp in spine:
            while index < len(series) and series[index][0] <= stamp:
                current = series[index][1]
                index += 1
            conformed.append((stamp, current))
        return conformed

    @staticmethod
    def rebase(series: list, anchor=None, base: float = 100.0) -> list:
        def before(stamp) -> bool:
            if anchor is None: return False
            return stamp < anchor if isinstance(anchor, datetime) else stamp.date() < anchor
        origin = next((value for stamp, value in series if value and not before(stamp)), None)
        return [(stamp, base * value / origin if origin and value and not before(stamp) else None) for stamp, value in series]

    @staticmethod
    def bound(points: list, lines: list = None):
        extremes = [abs(point["value"]) for point in points if point.get("value") is not None]
        extremes += [abs(line.price if isinstance(line, LineAPI) else line["price"]) for line in lines or ()]
        return max(extremes) or None if extremes else None

    @staticmethod
    def merge(bucket: list, stamp: int) -> dict:
        if "close" in bucket[0]:
            return {"time": stamp, "open": bucket[0]["open"], "high": max(entry["high"] for entry in bucket),
                    "low": min(entry["low"] for entry in bucket), "close": bucket[-1]["close"]}
        values = [entry["value"] for entry in bucket if entry.get("value") is not None]
        return {"time": stamp, "value": max(values, key=abs) if values else None}

    @classmethod
    def regrid(cls, points: list, grid: list) -> list:
        if not points or not grid: return points
        reduced, index, total = [], 0, len(points)
        for position, stamp in enumerate(grid):
            stop = grid[position + 1] if position + 1 < len(grid) else float("inf")
            bucket = []
            while index < total and points[index]["time"] < stop:
                if points[index]["time"] >= stamp: bucket.append(points[index])
                index += 1
            if bucket: reduced.append(cls.merge(bucket, stamp))
        return reduced

    @classmethod
    def decimate(cls, points: list, budget: int) -> list:
        if budget <= 0 or len(points) <= budget: return points
        stride = len(points) / float(budget)
        return cls.regrid(points, [points[int(position * stride)]["time"] for position in range(budget)])

    @classmethod
    def thin(cls, payload: dict, budget: int) -> dict:
        panes = payload.get("panes", [])
        stamps = sorted({point["time"] for pane in panes for series in pane.get("series", []) for point in series.get("data", [])})
        if budget <= 0 or len(stamps) <= budget: return payload
        stride = len(stamps) / float(budget)
        grid = [stamps[int(position * stride)] for position in range(budget)]
        for pane in panes:
            for series in pane.get("series", []): series["data"] = cls.regrid(series.get("data", []), grid)
        if "timeline" in payload: payload["timeline"] = [{"time": stamp} for stamp in grid]
        return payload

    @classmethod
    def decimal(cls, value: float) -> str:
        if not math.isfinite(value): return str(value)
        magnitude = abs(value)
        if not magnitude: return "0"
        if not 1e-4 <= magnitude < 10.0 ** 15: return f"{value:.{cls._DIGITS_}g}"
        if magnitude >= 1.0: decimals = max(0, cls._DIGITS_ - len(str(int(magnitude))))
        else: decimals = cls._DIGITS_ - 1 - math.floor(math.log10(magnitude))
        text = f"{value:,.{decimals}f}"
        return text.rstrip("0").rstrip(".") if "." in text else text

    @classmethod
    def cell(cls, value) -> str:
        if value is None: return ""
        if isinstance(value, bool): return "Yes" if value else "No"
        if isinstance(value, float): return cls.decimal(value)
        if isinstance(value, int): return f"{value:,}"
        if isinstance(value, datetime): return value.isoformat(sep=" ", timespec="seconds")
        if isinstance(value, date): return value.isoformat()
        if isinstance(value, (list, tuple)): return " · ".join(cls.cell(entry) for entry in value)
        return str(value)

@dataclass(kw_only=True)
class SpecAPI:

    @staticmethod
    def resolve(value):
        if isinstance(value, SpecAPI): return value.payload()
        if isinstance(value, (list, tuple)): return [SpecAPI.resolve(entry) for entry in value]
        if isinstance(value, EnumerationAPI): return value.value
        return value

    @staticmethod
    def prune(payload: dict) -> dict:
        return {key: value for key, value in payload.items() if value is not None}

    def payload(self) -> dict:
        raise NotImplementedError

@dataclass(kw_only=True)
class MarkerAPI(SpecAPI):

    time: int
    position: str = "aboveBar"
    shape: str = "circle"
    color: str = "up"
    size: float = 1.0
    text: str = None
    uid: Any = None

    def payload(self) -> dict:
        return self.prune({"time": PointAPI.epoch(self.time), "position": self.position, "shape": self.shape,
                           "color": self.color, "size": self.size, "text": self.text, "uid": self.uid})

@dataclass(kw_only=True)
class LineAPI(SpecAPI):

    price: float
    title: str = None
    color: str = "band"
    style: int = 2

    def payload(self) -> dict:
        return self.prune({"price": float(self.price), "title": self.title, "color": self.color, "style": self.style})

@dataclass(kw_only=True)
class SpanAPI(SpecAPI):

    entry: Any
    exit: Any = None
    direction: str = None
    entryPrice: float = None
    exitPrice: float = None
    net: float = None

    def payload(self) -> dict:
        return {"direction": self.direction, "entry": PointAPI.epoch(self.entry), "exit": None if self.exit is None else PointAPI.epoch(self.exit),
                "entryPrice": self.entryPrice, "exitPrice": self.exitPrice, "net": self.net}

@dataclass(kw_only=True)
class DealAPI(SpecAPI):

    uid: Any
    points: list
    color: str = "up"
    side: str = None

    def payload(self) -> dict:
        return self.prune({"uid": str(self.uid), "color": self.color, "side": self.side, "points": self.points})

@dataclass(kw_only=True)
class SeriesAPI(SpecAPI):

    key: str
    name: str
    data: list = field(default_factory=list)
    kind: SeriesType | str = SeriesType.Line
    color: str = "accent"
    width: int = 2
    axis: AxisType | str = AxisType.Right
    toggle: bool = False
    visible: bool = True
    markers: list = field(default_factory=list)

    def decimate(self, budget: int) -> Self:
        self.data = PointAPI.decimate(self.data, budget)
        return self

    def payload(self) -> dict:
        return self.prune({"key": self.key, "name": self.name, "type": SeriesType.parse(self.kind).value, "color": self.color,
                           "width": self.width, "axis": AxisType.parse(self.axis).value, "toggle": self.toggle or None,
                           "visible": self.visible, "data": self.data, "markers": self.resolve(self.markers) or None})

@dataclass(kw_only=True)
class PaneAPI(SpecAPI):

    id: str
    title: str = None
    scale: str = "time"
    series: list = field(default_factory=list)
    flex: int = 20
    format: FormatType | str = FormatType.Value
    margins: dict = None
    underlay: dict = None
    bound: float = None
    datum: float = None
    lines: list = field(default_factory=list)
    labels: list = field(default_factory=list)
    last: bool = False

    def payload(self) -> dict:
        return self.prune({"id": self.id, "title": self.title, "scale": self.scale, "flex": self.flex, "format": FormatType.parse(self.format).value,
                           "margins": self.margins, "underlay": self.underlay, "bound": self.bound, "datum": self.datum,
                           "lines": self.resolve(self.lines), "labels": self.labels,
                           "series": self.resolve(self.series), "last": self.last})

@dataclass(kw_only=True)
class ColumnAPI(SpecAPI):

    name: str
    label: str = None
    align: AlignType | str = None
    format: FormatType | str = None
    width: str = None
    markdown: bool = False
    editable: bool = False

    def payload(self) -> dict:
        align = AlignType.parse(self.align).value if self.align is not None else None
        return self.prune({"name": self.name, "label": self.label or self.name, "align": align,
                           "format": FormatType.parse(self.format).value if self.format is not None else None,
                           "width": self.width, "markdown": self.markdown or None, "editable": self.editable or None})

@dataclass(kw_only=True)
class SheetAPI(SpecAPI):

    name: str
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    keys: list = field(default_factory=list)
    height: int = None
    shown: int = None

    @classmethod
    def frame(cls, name: str, columns: list, rows: list, key: str = "UID", markdown=(), editable=()) -> Self:
        marks, writable = set(markdown or ()), set(editable or ())
        definitions = [column if isinstance(column, ColumnAPI) else ColumnAPI(name=str(column), markdown=str(column) in marks, editable=str(column) in writable and str(column) != key) for column in columns]
        names = [definition.name for definition in definitions]
        body = [[PointAPI.cell(row.get(name)) for name in names] for row in rows]
        links = [cls.identify(row.get(key)) for row in rows] if any(key in row for row in rows) else []
        return cls(name=name, columns=definitions, rows=body, keys=links, height=len(rows), shown=len(body))

    @staticmethod
    def identify(value) -> list:
        if value is None: return []
        if isinstance(value, (list, tuple)): return [str(entry) for entry in value if entry is not None]
        return [str(value)]

    def payload(self) -> dict:
        return {"name": self.name, "columns": self.resolve(self.columns), "rows": self.rows, "keys": self.keys,
                "height": self.height if self.height is not None else len(self.rows), "shown": self.shown if self.shown is not None else len(self.rows)}

@dataclass(kw_only=True)
class WorkspaceAPI(SpecAPI):

    title: str = None
    description: str = None
    currency: str = None
    headline: str = "growth"
    panes: list = field(default_factory=list)
    sheets: list = field(default_factory=list)
    spans: dict = field(default_factory=dict)
    deals: list = field(default_factory=list)
    markers: bool = True
    dealmap: bool = False
    theme: dict = None
    outbound: dict = None
    edition: dict = None
    navigation: dict = None

    def timeline(self) -> list:
        stamps = set()
        for pane in self.panes:
            if (pane.scale if isinstance(pane, PaneAPI) else pane.get("scale", "time")) != "time": continue
            for series in (pane.series if isinstance(pane, PaneAPI) else pane.get("series", [])):
                data = series.data if isinstance(series, SeriesAPI) else series.get("data", [])
                for point in data: stamps.add(point["time"])
        return [{"time": stamp} for stamp in sorted(stamps)]

    def payload(self) -> dict:
        panes = self.resolve(self.panes)
        for scale in {pane.get("scale", "time") for pane in panes}:
            family = [pane for pane in panes if pane.get("scale", "time") == scale]
            for index, pane in enumerate(family): pane["last"] = index == len(family) - 1
        return PointAPI.compact(self.prune({
            "title": self.title, "description": self.description, "currency": self.currency, "headline": self.headline,
            "panes": panes, "sheets": self.resolve(self.sheets), "deals": self.resolve(self.deals),
            "spans": {key: self.resolve(span) for key, span in self.spans.items()},
            "defaults": {"markers": bool(self.markers), "deals": bool(self.dealmap)},
            "timeline": self.timeline(), "theme": self.theme, "outbound": self.outbound,
            "edition": self.edition, "navigation": self.navigation}))

    def encode(self) -> str:
        return json.dumps(self.payload(), default=str, separators=(",", ":"))

    def document(self) -> str:
        from Library.App.V2.App import AppAPI
        read = lambda *parts: AppAPI.Assets.joinpath(*parts).read_text(encoding="utf-8")
        return (read("lightweight.html")
                .replace("__STYLES__", read("Styles", "lightweight.css"))
                .replace("__ARCHIVE__", read("Scripts", "Archive.js"))
                .replace("__LIBRARY__", read("lightweight.js"))
                .replace("__RUNTIME__", read("Scripts", "Lightweight.js"))
                .replace("__PAYLOAD__", self.encode()))

    def render(self, directory, name: str = "Plot", show: bool = False):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.html"
        path.write_text(self.document(), encoding="utf-8")
        if show:
            from Library.Utility.Runtime import open_browser
            open_browser(path.as_uri())
        return path

__all__ = ["SeriesType", "AxisType", "FormatType", "AlignType", "PointAPI", "SpecAPI", "MarkerAPI", "LineAPI", "SpanAPI", "DealAPI", "SeriesAPI", "PaneAPI", "ColumnAPI", "SheetAPI", "WorkspaceAPI"]