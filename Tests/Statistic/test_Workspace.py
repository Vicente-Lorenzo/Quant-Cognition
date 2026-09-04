from datetime import datetime

from Library.Statistic import (
    BENCHMARK_BETA,
    BENCHMARK_CORRELATION,
    BENCHMARK_LABEL,
    NET_TOTAL_AGGREGATED,
    NET_TOTAL_INDIVIDUAL,
    PROFITFACTOR,
    SHARPERATIO,
    STATISTICS_METRICS_LABEL,
    TOTALTRADESVALUE,
    compare,
    covariant,
    distribution,
    diurnal,
    excursion,
    headline,
    overwater,
    periodic,
    rolling,
    stitch,
    tabulate,
    trace,
    transpose,
    underwater,
    walkforward
)
from Library.Statistic.Workspace import (
    SeriesType,
    AxisType,
    FormatType,
    AlignType,
    PointAPI,
    MarkerAPI,
    LineAPI,
    SpanAPI,
    DealAPI,
    SeriesAPI,
    PaneAPI,
    ColumnAPI,
    SheetAPI,
    WorkspaceAPI
)

BARS = [(datetime(2024, 1, 1, hour), 1.0 + hour / 100, 1.02 + hour / 100, 0.99 + hour / 100, 1.01 + hour / 100) for hour in range(12)]
SERIES = [(datetime(2024, 1, 1, hour), float(hour)) for hour in range(12)]
_EPOCHS_ = [1704067200, 1704070800, 1704074400, 1704078000, 1704081600, 1704085200, 1704088800, 1704092400, 1704096000, 1704099600, 1704103200, 1704106800]
_COMPACT_ = {'a': 1.123457, 'b': [2.987654, {'c': 3.141593}], 'd': 'text', 'e': True, 'f': 7}
_ROWS_ = [{"UID": "a", "Name": "Alpha", "Score": 1}, {"UID": "b", "Name": BENCHMARK_BETA, "Score": 2}]
_UNIQUE_ = [{'time': 1, 'value': 2.0}, {'time': 2, 'value': 3.0}, {'time': 3, 'value': 9.0}]
_CANDLES_ = [{'time': 1704067200, 'open': 1.0, 'high': 1.02, 'low': 0.99, 'close': 1.01}, {'time': 1704070800, 'open': 1.01, 'high': 1.03, 'low': 1.0, 'close': 1.02}, {'time': 1704074400, 'open': 1.02, 'high': 1.04, 'low': 1.01, 'close': 1.03}, {'time': 1704078000, 'open': 1.03, 'high': 1.05, 'low': 1.02, 'close': 1.04}, {'time': 1704081600, 'open': 1.04, 'high': 1.06, 'low': 1.03, 'close': 1.05}, {'time': 1704085200, 'open': 1.05, 'high': 1.07, 'low': 1.04, 'close': 1.06}, {'time': 1704088800, 'open': 1.06, 'high': 1.08, 'low': 1.05, 'close': 1.07}, {'time': 1704092400, 'open': 1.07, 'high': 1.09, 'low': 1.06, 'close': 1.08}, {'time': 1704096000, 'open': 1.08, 'high': 1.1, 'low': 1.07, 'close': 1.09}, {'time': 1704099600, 'open': 1.09, 'high': 1.11, 'low': 1.08, 'close': 1.1}, {'time': 1704103200, 'open': 1.1, 'high': 1.12, 'low': 1.09, 'close': 1.11}, {'time': 1704106800, 'open': 1.11, 'high': 1.1300000000000001, 'low': 1.1, 'close': 1.12}]
_LINE_ = [{'time': 1704067200, 'value': 0.0}, {'time': 1704070800, 'value': 1.0}, {'time': 1704074400, 'value': 2.0}, {'time': 1704078000, 'value': 3.0}, {'time': 1704081600, 'value': 4.0}, {'time': 1704085200, 'value': 5.0}, {'time': 1704088800, 'value': 6.0}, {'time': 1704092400, 'value': 7.0}, {'time': 1704096000, 'value': 8.0}, {'time': 1704099600, 'value': 9.0}, {'time': 1704103200, 'value': 10.0}, {'time': 1704106800, 'value': 11.0}]
_CONFORM_ = [(datetime(2024, 1, 1, 0, 0), 0.0), (datetime(2024, 1, 1, 1, 0), 0.0), (datetime(2024, 1, 1, 2, 0), 0.0), (datetime(2024, 1, 1, 3, 0), 0.0), (datetime(2024, 1, 1, 4, 0), 0.0), (datetime(2024, 1, 1, 5, 0), 5.0), (datetime(2024, 1, 1, 6, 0), 5.0), (datetime(2024, 1, 1, 7, 0), 5.0), (datetime(2024, 1, 1, 8, 0), 5.0), (datetime(2024, 1, 1, 9, 0), 9.0), (datetime(2024, 1, 1, 10, 0), 9.0), (datetime(2024, 1, 1, 11, 0), 9.0)]
_REBASE_ = [(datetime(2024, 1, 1, 0, 0), None), (datetime(2024, 1, 1, 1, 0), 100.0), (datetime(2024, 1, 1, 2, 0), 200.0), (datetime(2024, 1, 1, 3, 0), 300.0), (datetime(2024, 1, 1, 4, 0), 400.0), (datetime(2024, 1, 1, 5, 0), 500.0), (datetime(2024, 1, 1, 6, 0), 600.0), (datetime(2024, 1, 1, 7, 0), 700.0), (datetime(2024, 1, 1, 8, 0), 800.0), (datetime(2024, 1, 1, 9, 0), 900.0), (datetime(2024, 1, 1, 10, 0), 1000.0), (datetime(2024, 1, 1, 11, 0), 1100.0)]
_BOUND_ = 20.0
_CELLS_ = ['', 'Yes', 'No', '12.5', '1,200', 'text', '1 · 2 · 3']

def test_epoch_matches_baseline():
    assert [PointAPI.epoch(stamp) for stamp, *_ in BARS] == _EPOCHS_

def test_compact_matches_baseline():
    payload = {"a": 1.123456789, "b": [2.987654321, {"c": 3.14159265358979}], "d": "text", "e": True, "f": 7}
    assert PointAPI.compact(payload) == _COMPACT_

def test_unique_matches_baseline():
    points = [{"time": 3, "value": 1.0}, {"time": 1, "value": 2.0}, {"time": 3, "value": 9.0}, {"time": 2, "value": 3.0}]
    assert PointAPI.unique(points) == _UNIQUE_

def test_candles_and_line_match_baseline():
    assert PointAPI.candles(BARS) == _CANDLES_
    assert PointAPI.line(SERIES) == _LINE_

def test_conform_matches_baseline():
    spine = [bar[0] for bar in BARS]
    sparse = [SERIES[0], SERIES[5], SERIES[9]]
    assert PointAPI.conform(sparse, spine) == _CONFORM_

def test_rebase_matches_baseline():
    assert PointAPI.rebase(SERIES) == _REBASE_

def test_bound_matches_baseline():
    points = PointAPI.line(SERIES)
    assert PointAPI.bound(points, [{"price": 20.0}]) == _BOUND_
    assert PointAPI.bound(points, [LineAPI(price=20.0)]) == _BOUND_

def test_cell_matches_baseline():
    assert [PointAPI.cell(value) for value in (None, True, False, 12.5, 1200, "text", [1, 2, 3])] == _CELLS_

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

def test_sheet_marks_editable_columns_and_spares_the_key():
    sheet = SheetAPI.frame("Rows", ["UID", "Name", "Score"], _ROWS_, editable=("UID", "Name", "Score"))
    assert [column.editable for column in sheet.columns] == [False, True, True]

def test_sheet_without_editable_marks_nothing():
    sheet = SheetAPI.frame("Rows", ["UID", "Name", "Score"], _ROWS_)
    assert not any(column.editable for column in sheet.columns)

def test_column_payload_carries_editable_only_when_set():
    assert "editable" not in ColumnAPI(name="Name").payload()
    assert ColumnAPI(name="Name", editable=True).payload()["editable"] is True

def test_workspace_payload_carries_the_edit_channel():
    import json
    payload = json.loads(WorkspaceAPI(title="T", sheets=[], edition={"name": "edit"}).encode())
    assert payload["edition"] == {"name": "edit"}

def test_workspace_without_edition_omits_the_channel():
    import json
    assert "edition" not in json.loads(WorkspaceAPI(title="T", sheets=[]).encode())

def test_underwater_measures_depth_from_the_running_peak():
    series = underwater([(1, 100.0), (2, 110.0), (3, 88.0), (4, 120.0)])
    assert [round(value, 6) for _, value in series] == [0.0, 0.0, -20.0, 0.0]

def test_underwater_skips_missing_values():
    assert [stamp for stamp, _ in underwater([(1, 100.0), (2, None), (3, 90.0)])] == [1, 3]

def test_periodic_compounds_months_into_a_year_total():
    rows = periodic([(datetime(2024, 1, 31), 100.0), (datetime(2024, 2, 29), 110.0), (datetime(2024, 3, 31), 99.0)])
    assert len(rows) == 1
    assert rows[0]["Year"] == "2024"
    assert (rows[0]["Jan"], rows[0]["Feb"], rows[0]["Mar"]) == (0.0, 10.0, -10.0)
    assert rows[0]["Apr"] is None
    assert rows[0]["Year Total"] == -1.0

def test_periodic_returns_nothing_without_timestamps():
    assert periodic([(1, 100.0), (2, 110.0)]) == []

def test_rolling_reports_annualized_sharpe_and_volatility():
    sharpes, volatilities = rolling([(1, 100.0), (2, 110.0), (3, 99.0), (4, 108.9)], window=2, periods=4.0)
    assert [stamp for stamp, _ in sharpes] == [3, 4]
    assert [round(value, 6) for _, value in sharpes] == [0.0, 0.0]
    assert [round(value, 4) for _, value in volatilities] == [28.2843, 28.2843]

def test_rolling_needs_more_samples_than_the_window():
    assert rolling([(1, 100.0), (2, 110.0)], window=2) == ([], [])

def test_covariant_recovers_unit_beta_from_a_proportional_benchmark():
    betas = covariant([(1, 100.0), (2, 110.0), (3, 99.0), (4, 108.9)], [(1, 50.0), (2, 55.0), (3, 49.5), (4, 54.45)], window=2)
    assert [stamp for stamp, _ in betas] == [3, 4]
    assert [round(value, 6) for _, value in betas] == [1.0, 1.0]

def test_covariant_pairs_only_shared_timestamps():
    assert covariant([(1, 100.0), (2, 110.0)], [(3, 50.0), (4, 55.0)], window=1) == []

def test_distribution_buckets_returns():
    assert [(round(edge, 6), count) for edge, count in distribution([(1, 100.0), (2, 110.0), (3, 99.0), (4, 108.9)], buckets=2)] == [(-5.0, 1), (5.0, 2)]

def test_distribution_needs_one_return_per_bucket():
    assert distribution([(1, 100.0), (2, 110.0)], buckets=41) == []

def test_excursion_measures_both_extremes_within_the_holding_window():
    bars = [(datetime(2024, 1, day), 100.0, 102.0 + day, 98.0 - day, 100.0 + day) for day in range(1, 6)]
    rows = excursion(bars, [(1, "Buy", datetime(2024, 1, 1), datetime(2024, 1, 5), 100.0, 104.0, 40.0)])
    assert rows[0]["MFE (%)"] == 7.0 and rows[0]["MAE (%)"] == 7.0
    assert rows[0]["Result (%)"] == 4.0 and rows[0]["Efficiency (%)"] == 57.14

def test_excursion_mirrors_the_extremes_for_a_short():
    bars = [(datetime(2024, 1, day), 100.0, 102.0 + day, 98.0 - day, 100.0 + day) for day in range(1, 6)]
    rows = excursion(bars, [(2, "Sell", datetime(2024, 1, 2), datetime(2024, 1, 4), 100.0, 97.0, 30.0)])
    assert rows[0]["MFE (%)"] == 6.0 and rows[0]["MAE (%)"] == 6.0
    assert rows[0]["Result (%)"] == 3.0 and rows[0]["Efficiency (%)"] == 50.0

def test_excursion_runs_an_open_trade_to_the_last_bar():
    bars = [(datetime(2024, 1, day), 100.0, 102.0 + day, 98.0 - day, 100.0 + day) for day in range(1, 6)]
    rows = excursion(bars, [(3, "Buy", datetime(2024, 1, 1), None, 100.0, None, None)])
    assert rows[0]["MFE (%)"] == 7.0 and rows[0]["Result (%)"] is None and rows[0]["Efficiency (%)"] is None

def test_excursion_ignores_trades_without_an_entry_price():
    bars = [(datetime(2024, 1, 1), 100.0, 101.0, 99.0, 100.0)]
    assert excursion(bars, [(1, "Buy", datetime(2024, 1, 1), None, None, None, None)]) == []

def _payload_(name, points, metrics):
    return {"panes": [{"id": "growth", "series": [{"key": "strategy", "name": name, "data": points}]}],
            "sheets": [{"name": "Net", "columns": [{"name": STATISTICS_METRICS_LABEL}, {"name": NET_TOTAL_INDIVIDUAL}, {"name": NET_TOTAL_AGGREGATED}],
                        "rows": [[label, individual, aggregated] for label, individual, aggregated in metrics]}]}

def test_diurnal_keeps_the_last_value_of_each_day():
    points = [{"time": 86400 + 3600, "value": 1.0}, {"time": 86400 + 7200, "value": 2.0}, {"time": 172800, "value": 3.0}]
    assert diurnal(points) == [{"time": 86400, "value": 2.0}, {"time": 172800, "value": 3.0}]

def test_diurnal_drops_empty_values():
    assert diurnal([{"time": 0, "value": None}, {"time": 0, "value": 5.0}]) == [{"time": 0, "value": 5.0}]

def test_tabulate_reads_the_named_column_not_the_last():
    payload = _payload_("A", [], [(TOTALTRADESVALUE, "37", "25")])
    assert tabulate(payload, "Net", NET_TOTAL_INDIVIDUAL) == {TOTALTRADESVALUE: "37"}
    assert tabulate(payload, "Net") == {TOTALTRADESVALUE: "25"}

def test_tabulate_falls_back_to_the_last_column_when_the_name_is_absent():
    payload = _payload_("A", [], [(PROFITFACTOR, "1.1", "1.2")])
    assert tabulate(payload, "Net", "Missing Column") == {PROFITFACTOR: "1.2"}

def test_trace_finds_a_series_and_tolerates_absence():
    payload = _payload_("A", [{"time": 0, "value": 100.0}], [])
    assert trace(payload, "growth", "strategy") == [{"time": 0, "value": 100.0}]
    assert trace(payload, "growth", "missing") == []
    assert trace(payload, "missing", "strategy") == []

def test_compare_builds_one_series_per_run_and_a_metric_row():
    first = _payload_("A", [{"time": 0, "value": 100.0}, {"time": 86400, "value": 110.0}], [(PROFITFACTOR, "1.1", "9.9")])
    second = _payload_("B", [{"time": 0, "value": 100.0}, {"time": 86400, "value": 90.0}], [(PROFITFACTOR, "0.8", "9.9")])
    space = compare([("Run A", first), ("Run B", second)])
    assert [series.name for series in space.panes[0].series] == ["Run A", "Run B"]
    sheet = space.sheets[0]
    assert [column.name for column in sheet.columns] == ["Metric", "Run A", "Run B"]
    assert sheet.rows == [[PROFITFACTOR, "1.1", "0.8"]]

def test_compare_skips_runs_without_a_curve():
    payload = _payload_("A", [{"time": 0, "value": 100.0}], [])
    space = compare([("Run A", payload), ("Run B", {"panes": [], "sheets": []})])
    assert [series.name for series in space.panes[0].series] == ["Run A"]

def test_compare_names_the_basis_only_when_the_runs_disagree():
    backtested = _payload_("A", [{"time": 0, "value": 100.0}, {"time": 86400, "value": 110.0}], [])
    searched = _payload_("A", [{"time": 0, "value": 100.0}, {"time": 86400, "value": 105.0}], [])
    searched["headline"] = "walkforward"
    searched["panes"].append({"id": "walkforward", "series": [{"key": "rolling", "data": [{"time": 0, "value": 100.0}, {"time": 86400, "value": 104.0}]}]})
    space = compare([("Run A", backtested), ("Run B", searched)])
    assert [series.name for series in space.panes[0].series] == ["Run A · Growth", "Run B · Walk-Forward"]
    assert space.sheets[0].rows[0] == ["Curve", "Growth", "Walk-Forward"]

def test_compare_prefers_the_walk_forward_curve_of_a_searched_run():
    searched = _payload_("A", [{"time": 0, "value": 100.0}, {"time": 86400, "value": 110.0}], [])
    searched["headline"] = "walkforward"
    searched["panes"].append({"id": "walkforward", "series": [{"key": "rolling", "data": [{"time": 0, "value": 100.0}, {"time": 86400, "value": 104.0}]}]})
    other = dict(searched)
    space = compare([("Run A", searched), ("Run B", other)])
    assert space.panes[0].series[0].data[-1]["value"] == 104.0
    assert [series.name for series in space.panes[0].series] == ["Run A", "Run B"]

def test_compare_without_any_curve_yields_an_empty_workspace():
    space = compare([("Run A", {"panes": [], "sheets": []})])
    assert space.panes == [] and space.sheets == []
def test_cell_keeps_large_values_out_of_scientific_notation():
    assert PointAPI.cell(10000000.0) == "10,000,000"
    assert PointAPI.cell(12345678.9) == "12,345,679"
    assert PointAPI.cell(9863.456) == "9,863.456"

def test_cell_keeps_seven_significant_digits_below_one():
    assert PointAPI.cell(-0.0008794785) == "-0.0008794785"
    assert PointAPI.cell(0.5) == "0.5"
    assert PointAPI.cell(0.0) == "0"

def test_cell_falls_back_to_exponent_at_the_extremes():
    assert PointAPI.cell(1e-05) == "1e-05"
    assert PointAPI.cell(1e16) == "1e+16"

def test_transpose_reads_a_row_per_entity_sheet():
    payload = {"sheets": [{"name": BENCHMARK_LABEL,
                           "columns": [{"name": BENCHMARK_LABEL}, {"name": BENCHMARK_BETA}, {"name": BENCHMARK_CORRELATION}],
                           "rows": [["Strategy", "", ""], ["Buy & Hold", "0.13", "0.55"]]}]}
    assert transpose(payload, BENCHMARK_LABEL) == {BENCHMARK_BETA: "0.13", BENCHMARK_CORRELATION: "0.55"}

def test_transpose_returns_nothing_when_only_the_skipped_row_exists():
    payload = {"sheets": [{"name": BENCHMARK_LABEL, "columns": [{"name": BENCHMARK_LABEL}, {"name": BENCHMARK_BETA}],
                           "rows": [["Strategy", ""]]}]}
    assert transpose(payload, BENCHMARK_LABEL) == {}
    assert transpose(payload, "Missing") == {}

def test_overwater_measures_recovery_since_the_last_peak():
    series = overwater([(1, 100.0), (2, 110.0), (3, 88.0), (4, 99.0), (5, 120.0), (6, 114.0)])
    assert [round(value, 4) for _, value in series] == [0.0, 0.0, 0.0, 12.5, 0.0, 0.0]

def test_overwater_and_underwater_both_reset_at_every_new_peak():
    equity = [(1, 100.0), (2, 110.0), (3, 88.0), (4, 99.0), (5, 120.0), (6, 114.0)]
    depths = dict(underwater(equity))
    rises = dict(overwater(equity))
    for stamp in (2, 5):
        assert depths[stamp] == 0.0 and rises[stamp] == 0.0

def test_overwater_skips_missing_values():
    assert [stamp for stamp, _ in overwater([(1, 100.0), (2, None), (3, 90.0)])] == [1, 3]

def test_compare_prefers_net_metrics_over_a_benchmark_of_the_same_name():
    payload = {"panes": [{"id": "growth", "series": [{"key": "strategy", "name": "A",
                                                      "data": [{"time": 0, "value": 100.0}]}]}],
               "sheets": [{"name": "Net",
                           "columns": [{"name": STATISTICS_METRICS_LABEL}, {"name": NET_TOTAL_INDIVIDUAL}],
                           "rows": [[SHARPERATIO, "0.9"]]},
                          {"name": BENCHMARK_LABEL,
                           "columns": [{"name": BENCHMARK_LABEL}, {"name": SHARPERATIO}, {"name": BENCHMARK_BETA}],
                           "rows": [["Strategy", "", ""], ["Buy & Hold", "-0.3", "0.13"]]}]}
    sheet = compare([("Run A", payload)]).sheets[0]
    values = {row[0]: row[1] for row in sheet.rows}
    assert values[SHARPERATIO] == "0.9"
    assert values[BENCHMARK_BETA] == "0.13"

def _fold_(index: int, opening: float, closing: float, month: int) -> dict:
    return {"Fold": index, "Parameters": f"Baseline=EMA/{index}", "Start": datetime(2020, month, 1),
            "Stop": datetime(2020, month + 3, 1), "Training": float(index), "Validation": float(index) / 2,
            "Settings": {"Baseline": f"EMA/{index}"},
            "Equity": [(datetime(2020, month, 1), opening), (datetime(2020, month + 3, 1), closing)]}

def test_stitch_compounds_each_fold_onto_the_previous_level():
    curve, marks = stitch([_fold_(1, 10000.0, 11000.0, 1), _fold_(2, 12000.0, 10800.0, 4)])
    assert [round(value, 4) for _, value in curve] == [100.0, 110.0, 110.0, 99.0]
    assert [mark["Return (%)"] for mark in marks] == [10.0, -10.0]
    assert [mark["Opening"] for mark in marks] == [100.0, 110.0]

def test_stitch_starts_every_run_at_one_hundred():
    curve, _ = stitch([_fold_(1, 47.5, 47.5, 1)])
    assert curve[0][1] == 100.0

def test_stitch_ignores_a_fold_that_never_traded():
    curve, marks = stitch([{"Fold": 1, "Equity": []}, _fold_(2, 100.0, 110.0, 1)])
    assert len(marks) == 1 and round(curve[-1][1], 4) == 110.0

def test_stitch_ignores_a_fold_opening_at_zero():
    assert stitch([{"Fold": 1, "Equity": [(datetime(2020, 1, 1), 0.0)]}]) == ([], [])

def test_stitch_of_nothing_is_empty():
    assert stitch([]) == ([], [])

def test_walkforward_builds_one_pane_and_one_sheet():
    panes, sheets = walkforward([_fold_(1, 10000.0, 11000.0, 1)])
    assert [pane.id for pane in panes] == ["walkforward"]
    assert [series.key for series in panes[0].series] == ["rolling"]
    assert [sheet.name for sheet in sheets] == ["Folds"]
    assert [column.name for column in sheets[0].columns] == ["Fold", "Parameters", "Start", "Stop", "Training", "Validation", "Opening", "Return (%)"]

def test_walkforward_overlays_an_elected_curve_that_covers_the_folds():
    folds = [_fold_(1, 10000.0, 11000.0, 1)]
    elected = [(datetime(2020, 1, 1), 10000.0), (datetime(2020, 4, 1), 10500.0)]
    panes, _ = walkforward(folds, elected)
    assert [series.key for series in panes[0].series] == ["rolling", "elected"]
    assert panes[0].series[1].data[0]["value"] == 100.0

def test_walkforward_drops_an_elected_curve_outside_the_folds():
    folds = [_fold_(1, 10000.0, 11000.0, 1)]
    elected = [(datetime(2024, 7, 1), 10000.0), (datetime(2024, 12, 1), 10500.0)]
    panes, _ = walkforward(folds, elected)
    assert [series.key for series in panes[0].series] == ["rolling"]

def test_walkforward_of_nothing_is_empty():
    assert walkforward([]) == ([], [])