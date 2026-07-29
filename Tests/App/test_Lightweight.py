from datetime import datetime

from Library.App.V2.Lightweight import (
    AlignType,
    AxisType,
    ColumnAPI,
    DealAPI,
    FormatType,
    GlyphAPI,
    LightweightChartAPI,
    LightweightPageAPI,
    LightweightTableAPI,
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
from Library.App.V2.Table import TableAPI
from Library.Utility.Plot import PlotAPI

BARS = [(datetime(2024, 1, 1, hour), 1.0 + hour / 100, 1.02 + hour / 100, 0.99 + hour / 100, 1.01 + hour / 100) for hour in range(12)]
SERIES = [(datetime(2024, 1, 1, hour), float(hour)) for hour in range(12)]

def test_epoch_matches_plot():
    for stamp, *_ in BARS:
        assert PointAPI.epoch(stamp) == PlotAPI._epoch_(stamp)

def test_compact_matches_plot():
    payload = {"a": 1.123456789, "b": [2.987654321, {"c": 3.14159265358979}], "d": "text", "e": True, "f": 7}
    assert PointAPI.compact(payload) == PlotAPI._compact_(payload)

def test_unique_matches_plot():
    points = [{"time": 3, "value": 1.0}, {"time": 1, "value": 2.0}, {"time": 3, "value": 9.0}, {"time": 2, "value": 3.0}]
    assert PointAPI.unique(points) == PlotAPI._unique_(points)

def test_candles_and_line_match_plot():
    assert PointAPI.candles(BARS) == PlotAPI._candles_(BARS)
    assert PointAPI.line(SERIES) == PlotAPI._line_(SERIES)

def test_conform_matches_plot():
    spine = [bar[0] for bar in BARS]
    sparse = [SERIES[0], SERIES[5], SERIES[9]]
    assert PointAPI.conform(sparse, spine) == PlotAPI._conform_(sparse, spine)

def test_rebase_matches_plot():
    plot = PlotAPI(title="parity", start=None)
    assert PointAPI.rebase(SERIES) == plot._rebase_(SERIES)

def test_bound_matches_plot():
    points = PointAPI.line(SERIES)
    lines = [{"price": 20.0}]
    assert PointAPI.bound(points, lines) == PlotAPI._bound_(points, lines)
    assert PointAPI.bound(points, [LineAPI(price=20.0)]) == PlotAPI._bound_(points, lines)

def test_cell_matches_plot():
    for value in (None, True, False, 12.5, 1200, "text", [1, 2, 3]):
        assert PointAPI.cell(value) == PlotAPI._cell_(value)

def test_cell_formats_timestamps():
    assert PointAPI.cell(datetime(2024, 5, 4, 13, 30, 15)) == "2024-05-04 13:30:15"

def test_decimate_preserves_bounds():
    points = PointAPI.line(SERIES)
    reduced = PointAPI.decimate(points, 4)
    assert len(reduced) <= 4
    assert reduced[0]["time"] == points[0]["time"]
    assert PointAPI.decimate(points, 0) == points
    assert PointAPI.decimate(points, 99) == points

def test_decimate_keeps_candle_extremes():
    candles = PointAPI.candles(BARS)
    reduced = PointAPI.decimate(candles, 3)
    assert max(point["high"] for point in reduced) == max(point["high"] for point in candles)
    assert min(point["low"] for point in reduced) == min(point["low"] for point in candles)

def test_thin_rebuilds_timeline():
    workspace = WorkspaceAPI(panes=[PaneAPI(id="p", series=[SeriesAPI(key="s", name="S", data=PointAPI.line(SERIES))])])
    payload = PointAPI.thin(workspace.payload(), 4)
    assert len(payload["panes"][0]["series"][0]["data"]) <= 4
    assert len(payload["timeline"]) == len(payload["panes"][0]["series"][0]["data"])

def test_thin_aligns_series_on_one_grid():
    early = PointAPI.candles(BARS)
    late = PointAPI.line(SERIES[4:])
    workspace = WorkspaceAPI(panes=[PaneAPI(id="a", series=[SeriesAPI(key="c", name="C", kind="Candlestick", data=early)]),
                                    PaneAPI(id="b", series=[SeriesAPI(key="l", name="L", data=late)])])
    payload = PointAPI.thin(workspace.payload(), 5)
    grid = {point["time"] for point in payload["timeline"]}
    for pane in payload["panes"]:
        for series in pane["series"]:
            assert {point["time"] for point in series["data"]} <= grid

def test_regrid_stamps_bucket_start():
    points = PointAPI.line(SERIES)
    grid = [points[0]["time"], points[6]["time"]]
    reduced = PointAPI.regrid(points, grid)
    assert [point["time"] for point in reduced] == grid

def test_series_payload_resolves_enums():
    series = SeriesAPI(key="c", name="Candles", kind=SeriesType.Candlestick, axis=AxisType.Left, data=[], toggle=False)
    payload = series.payload()
    assert payload["type"] == "candlestick"
    assert payload["axis"] == "left"
    assert "toggle" not in payload

def test_series_accepts_string_enums():
    assert SeriesAPI(key="a", name="A", kind="Histogram", axis="Right").payload()["type"] == "histogram"

def test_pane_payload_prunes_optionals():
    payload = PaneAPI(id="price", title="Price", format=FormatType.Price).payload()
    assert payload["format"] == "price"
    assert "bound" not in payload and "datum" not in payload

def test_marker_line_glyph_deal_span_payloads():
    stamp = datetime(2024, 1, 1)
    assert MarkerAPI(time=stamp, uid=7).payload()["time"] == PointAPI.epoch(stamp)
    assert LineAPI(price=1.5, title="Cap").payload() == {"price": 1.5, "title": "Cap", "color": "band", "style": 2}
    assert GlyphAPI(name="Buy", symbol="A").payload()["symbol"] == "A"
    assert DealAPI(uid=3, points=[]).payload()["uid"] == "3"
    span = SpanAPI(entry=stamp, exit=None, direction="Buy").payload()
    assert span["entry"] == PointAPI.epoch(stamp) and span["exit"] is None

def test_column_payload_defaults_label():
    assert ColumnAPI(name="UID").payload() == {"name": "UID", "label": "UID"}
    assert ColumnAPI(name="Net", label="Net PnL", align=AlignType.Right).payload()["align"] == "right"

def test_sheet_frame_builds_rows_and_keys():
    rows = [{"UID": 1, "Net": 12.5}, {"UID": [2, 3], "Net": None}]
    sheet = SheetAPI.frame("Trades", ["UID", "Net"], rows).payload()
    assert sheet["rows"] == [["1", "12.5"], ["2 · 3", ""]]
    assert sheet["keys"] == [["1"], ["2", "3"]]
    assert sheet["height"] == 2 and sheet["shown"] == 2

def test_sheet_frame_marks_markdown_columns():
    sheet = SheetAPI.frame("T", ["UID", "Status"], [{"UID": 1, "Status": "<b>ok</b>"}], markdown={"Status"}).payload()
    assert sheet["columns"][1]["markdown"] is True
    assert "markdown" not in sheet["columns"][0]

def test_sheet_frame_without_key_column():
    assert SheetAPI.frame("T", ["Name"], [{"Name": "a"}]).payload()["keys"] == []

def test_workspace_payload_flags_last_pane():
    workspace = WorkspaceAPI(title="W", panes=[PaneAPI(id="a"), PaneAPI(id="b")])
    panes = workspace.payload()["panes"]
    assert panes[0]["last"] is False and panes[1]["last"] is True

def test_workspace_payload_defaults_and_prune():
    payload = WorkspaceAPI(title="W", markers=True, dealmap=False).payload()
    assert payload["defaults"] == {"markers": True, "deals": False}
    assert "theme" not in payload and "outbound" not in payload and "navigation" not in payload

def test_workspace_timeline_is_sorted_union():
    workspace = WorkspaceAPI(panes=[
        PaneAPI(id="a", series=[SeriesAPI(key="x", name="X", data=[{"time": 30, "value": 1.0}, {"time": 10, "value": 2.0}])]),
        PaneAPI(id="b", series=[SeriesAPI(key="y", name="Y", data=[{"time": 20, "value": 3.0}, {"time": 10, "value": 4.0}])])])
    assert workspace.payload()["timeline"] == [{"time": 10}, {"time": 20}, {"time": 30}]

def test_workspace_encode_is_json():
    import json
    workspace = WorkspaceAPI(title="W", panes=[PaneAPI(id="a")])
    assert json.loads(workspace.encode())["title"] == "W"

def test_workspace_document_embeds_assets():
    document = WorkspaceAPI(title="Doc", panes=[PaneAPI(id="a")]).document()
    assert "LightweightCharts" in document
    assert "lightweight-payload" in document
    assert '"title":"Doc"' in document
    assert "__PAYLOAD__" not in document and "__LIBRARY__" not in document and "__STYLES__" not in document and "__RUNTIME__" not in document

def test_chart_component_builds_host_and_carrier():
    built = LightweightChartAPI(id={"name": "chart"}, carrier={"name": "carrier"}, selection={"name": "state"},
                                workspace="demo", payload=WorkspaceAPI(title="W")).build()
    host = built[0]
    assert host.__dict__["data-workspace"] == "demo"
    assert host.__dict__["data-role"] == "chart"
    assert "lightweight" in host.className
    carrier, body = host.children
    assert carrier.type == "application/json" and "lightweight-payload" in carrier.className
    assert body.className == "lightweight-body"
    assert built[1].id == {"name": "state"}

def test_table_component_role_and_height():
    built = LightweightTableAPI(id={"name": "grid"}, workspace="demo", height="40vh").build()
    host = built[0]
    assert host.__dict__["data-role"] == "table"
    assert host.style["height"] == "40vh"
    assert len(built) == 1

def test_component_without_payload_encodes_empty():
    assert LightweightChartAPI(id={"name": "c"}, workspace="w").encode() == "{}"

def test_component_injects_outbound_into_dict_payload():
    import json
    component = LightweightChartAPI(id={"name": "c"}, workspace="w", selection={"name": "s"}, payload={"panes": []})
    assert json.loads(component.encode())["outbound"] == {"name": "s"}

def test_page_mirrors_table_contract():
    for hook in ("_columns_", "_markdown_columns_", "_rows_", "_detail_base_", "_fingerprint_", "_actions_", "_extras_", "content", "ids"):
        assert callable(getattr(LightweightPageAPI, hook))
    for knob in ("_POLL_", "_ROW_KEY_", "_NAVIGABLE_"):
        assert getattr(LightweightPageAPI, knob) == getattr(TableAPI, knob)

def test_page_defaults_match_table_defaults():
    assert LightweightPageAPI._columns_(LightweightPageAPI) == []
    assert LightweightPageAPI._rows_(LightweightPageAPI) == []
    assert LightweightPageAPI._markdown_columns_(LightweightPageAPI) == set()
    assert LightweightPageAPI._fingerprint_(LightweightPageAPI) is None
