import pytest
from datetime import datetime, timezone
import Library.Market
import Library.Portfolio
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAGetTrendbarsRes,
    ProtoOAGetTickDataRes
)
def test_period_resolves_wire_and_framework_timeframes(spotware):
    assert spotware.market._period_("M1") == 1
    assert spotware.market._period_("m5") == 5
    assert spotware.market._period_("H1") == 9
    assert spotware.market._period_("Hour") == 9
    assert spotware.market._period_("Daily") == 12
    assert spotware.market._period_("W1") == 13
    assert spotware.market._period_("MN1") == 14
    assert spotware.market._period_(7) == 7
def test_bars_decodes_ohlc_from_deltas(spotware):
    res = ProtoOAGetTrendbarsRes()
    res.period = 1
    res.symbolId = 1
    b = res.trendbar.add()
    b.low = 100000
    b.deltaOpen = 500
    b.deltaHigh = 1000
    b.deltaClose = 700
    b.volume = 50
    b.utcTimestampInMinutes = 26500000
    b.period = 1
    b2 = res.trendbar.add()
    b2.low = 200000
    b2.deltaOpen = 0
    b2.deltaHigh = 500
    b2.deltaClose = 250
    b2.volume = 25
    b2.utcTimestampInMinutes = 26500001
    b2.period = 1
    spotware._responses_.append(res)
    df = spotware.market.bars(symbol=1, start=datetime(2020, 5, 1, tzinfo=timezone.utc), timeframe="M1")
    assert len(df) == 2
    assert df["Timeframe"][0] == "M1"
    assert df["Symbol"][0] == 1
    assert df["Low"][0] == pytest.approx(1.0)
    assert df["Open"][0] == pytest.approx(1.005)
    assert df["High"][0] == pytest.approx(1.01)
    assert df["Close"][0] == pytest.approx(1.007)
    assert df["Volume"][0] == 50
    assert df["Low"][1] == pytest.approx(2.0)
    assert df["High"][1] == pytest.approx(2.005)
    sent = spotware._sent_[0]
    assert type(sent).__name__ == "ProtoOAGetTrendbarsReq"
    assert sent.period == 1
    assert sent.symbolId == 1
def test_bars_timestamp_decodes_minutes(spotware):
    res = ProtoOAGetTrendbarsRes()
    res.period = 9
    res.symbolId = 1
    b = res.trendbar.add()
    b.low = 100000; b.deltaOpen = 0; b.deltaHigh = 0; b.deltaClose = 0; b.volume = 1
    b.utcTimestampInMinutes = 27000000
    b.period = 9
    spotware._responses_.append(res)
    df = spotware.market.bars(symbol=1, start=datetime(2021, 1, 1, tzinfo=timezone.utc), timeframe="H1")
    expected = datetime.fromtimestamp(27000000 * 60, tz=timezone.utc)
    assert df["Timestamp"][0].replace(tzinfo=timezone.utc) == expected
    assert df["Timeframe"][0] == "H1"
def test_bars_passes_count(spotware):
    res = ProtoOAGetTrendbarsRes()
    res.period = 1
    res.symbolId = 1
    spotware._responses_.append(res)
    spotware.market.bars(symbol=1, start=datetime(2020, 1, 1, tzinfo=timezone.utc), timeframe="M1", count=100)
    sent = spotware._sent_[0]
    assert sent.count == 100
def test_ticks_accumulates_deltas(spotware):
    res = ProtoOAGetTickDataRes()
    base_ms = 1577836800000
    t = res.tickData.add(); t.timestamp = base_ms; t.tick = 105000
    t = res.tickData.add(); t.timestamp = 1000; t.tick = 5
    t = res.tickData.add(); t.timestamp = 500; t.tick = -2
    res.hasMore = False
    spotware._responses_.append(res)
    df = spotware.market.ticks(
        symbol=1,
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 2, tzinfo=timezone.utc),
        quote="BID"
    )
    assert len(df) == 3
    assert df.columns == ["Timestamp", "Bid"]
    prices = df.sort("Timestamp")["Bid"].to_list()
    assert prices[0] == pytest.approx(1.05)
    assert prices[1] == pytest.approx(1.05005)
    assert prices[2] == pytest.approx(1.05003)
def test_ticks_quote_type_request(spotware):
    res = ProtoOAGetTickDataRes()
    res.hasMore = False
    spotware._responses_.append(res)
    spotware.market.ticks(
        symbol=7,
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 2, tzinfo=timezone.utc),
        quote="ASK"
    )
    sent = spotware._sent_[0]
    assert sent.type == 2
    assert sent.symbolId == 7
def test_ticks_empty_response(spotware):
    res = ProtoOAGetTickDataRes()
    res.hasMore = False
    spotware._responses_.append(res)
    df = spotware.market.ticks(
        symbol=1,
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stop=datetime(2020, 1, 2, tzinfo=timezone.utc)
    )
    assert len(df) == 0