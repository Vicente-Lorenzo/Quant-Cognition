import sys
import types
import threading
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

try:
    import xbbg
except ImportError:
    xbbg = types.ModuleType("xbbg")
    xbbg.blp = MagicMock()
    sys.modules["xbbg"] = xbbg

from Library.Database.Dataframe import pd, pl
from Library.Bloomberg import BloombergAPI, ReferenceAPI, HistoricalAPI, IntradayAPI, QueryAPI, StreamingAPI

def test_wiring():
    bbg = BloombergAPI()
    assert isinstance(bbg.reference, ReferenceAPI)
    assert isinstance(bbg.historical, HistoricalAPI)
    assert isinstance(bbg.intraday, IntradayAPI)
    assert isinstance(bbg.query, QueryAPI)
    assert isinstance(bbg.streaming, StreamingAPI)
    assert not bbg.remote()

def test_reference_fetch_single_args_and_polars_backend():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["AAPL US Equity"], "field": ["PX_LAST"], "value": [100.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        df = BloombergAPI(legacy=False).reference.fetch("AAPL US Equity", "PX_LAST")
    args, kwargs = engine.bdp.call_args
    assert args == ("AAPL US Equity", "PX_LAST")
    assert kwargs["backend"] == "polars"
    assert len(df) == 1

def test_reference_fetch_list_args_and_legacy_pandas_backend():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["A", "B"], "field": ["PX_LAST", "PX_LAST"], "value": [1.0, 2.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI(legacy=True).reference.fetch(["A", "B"], ["PX_LAST", "NAME"])
    args, kwargs = engine.bdp.call_args
    assert args == (["A", "B"], ["PX_LAST", "NAME"])
    assert kwargs["backend"] == "pandas"

def test_reference_bulk_calls_bds():
    engine = MagicMock()
    engine.bds.return_value = pl.DataFrame({"ticker": ["SPX Index"], "field": ["INDX_MEMBERS"], "member": ["AAPL"]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().reference.bulk("SPX Index", "INDX_MEMBERS")
    args, kwargs = engine.bds.call_args
    assert args == ("SPX Index", "INDX_MEMBERS")

def test_historical_fetch_calls_bdh():
    engine = MagicMock()
    engine.bdh.return_value = pl.DataFrame({"ticker": ["SPX Index"], "date": ["2024-01-02"], "field": ["PX_LAST"], "value": [1.1]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().historical.fetch("SPX Index", "PX_LAST", start="2024-01-01", stop="2024-01-31")
    args, kwargs = engine.bdh.call_args
    assert args == ("SPX Index", "PX_LAST", "2024-01-01", "2024-01-31")
    assert kwargs["Per"] == "D"

def test_historical_fetch_defaults_stop_to_today_and_maps_timeframe():
    engine = MagicMock()
    engine.bdh.return_value = pl.DataFrame({"ticker": ["SPX Index"], "date": ["2024-01-05"], "field": ["PX_LAST"], "value": [1.1]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().historical.fetch("SPX Index", "PX_LAST", start="2024-01-01", timeframe="WEEKLY")
    args, kwargs = engine.bdh.call_args
    assert args == ("SPX Index", "PX_LAST", "2024-01-01", "today")
    assert kwargs["Per"] == "W"

def test_intraday_bars_calls_bdib():
    engine = MagicMock()
    engine.bdib.return_value = pl.DataFrame({"time": ["2024-01-15T10:00"], "close": [1.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().intraday.bars("TSLA US Equity", dt="2024-01-15", interval=5)
    args, kwargs = engine.bdib.call_args
    assert kwargs["dt"] == "2024-01-15" and kwargs["interval"] == 5

def test_intraday_ticks_calls_bdtick_over_range():
    engine = MagicMock()
    engine.bdtick.return_value = pl.DataFrame({"time": ["2024-01-15T10:00:00"], "value": [1.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().intraday.ticks("TSLA US Equity", "2024-01-15 09:30", "2024-01-15 16:00")
    args, kwargs = engine.bdtick.call_args
    assert args == ("TSLA US Equity", "2024-01-15 09:30", "2024-01-15 16:00")
    assert kwargs["event_types"] == ["TRADE"]

def test_intraday_ticks_wraps_string_event_types_in_list():
    engine = MagicMock()
    engine.bdtick.return_value = pl.DataFrame({"time": ["2024-01-15T10:00:00"], "value": [1.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().intraday.ticks("TSLA US Equity", "2024-01-15 09:30", "2024-01-15 16:00", event_types="BID")
        BloombergAPI().intraday.ticks("TSLA US Equity", "2024-01-15 09:30", "2024-01-15 16:00", event_types=["BID", "ASK"])
    first, second = engine.bdtick.call_args_list
    assert first.kwargs["event_types"] == ["BID"]
    assert second.kwargs["event_types"] == ["BID", "ASK"]

def test_streaming_subscribe_backend_and_limit():
    engine = MagicMock()
    engine.stream.return_value = iter([pl.DataFrame({"value": [1.0]}), pl.DataFrame({"value": [2.0]}), pl.DataFrame({"value": [3.0]})])
    received = []
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().streaming.subscribe("AAPL US Equity", "LAST_PRICE", callback=received.append, limit=2)
    args, kwargs = engine.stream.call_args
    assert args == ("AAPL US Equity", "LAST_PRICE")
    assert kwargs["backend"] == "polars"
    assert len(received) == 2

def test_query_execute_calls_bql():
    engine = MagicMock()
    engine.bql.return_value = pl.DataFrame({"ID": ["AAPL US Equity"], "px_last": [100.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        BloombergAPI().query.execute("get(px_last) for(['AAPL US Equity'])")
    args, kwargs = engine.bql.call_args
    assert args == ("get(px_last) for(['AAPL US Equity'])",)

def _serve_(engine, port, token):
    server = BloombergAPI()
    with patch.object(xbbg, "blp", engine, create=True):
        threading.Thread(target=lambda: server.serve(port=port, token=token), daemon=True).start()
    return server

def test_remote_roundtrip_over_loopback():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["AAPL US Equity"], "field": ["PX_LAST"], "value": [100.0]})
    engine.bdh.return_value = pl.DataFrame({"ticker": ["SPX Index"], "date": ["2024-01-02"], "field": ["PX_LAST"], "value": [1.1]})
    with patch.object(xbbg, "blp", engine, create=True):
        _serve_(engine, port=55565, token="secret")
        client = BloombergAPI(host="127.0.0.1", port=55565, token="secret", timeout=10)
        try:
            df = client.reference.fetch("AAPL US Equity", "PX_LAST")
            legacy = client.reference.fetch("AAPL US Equity", "PX_LAST", legacy=True)
            client.historical.fetch("SPX Index", "PX_LAST", start=date(2024, 1, 1), stop=date(2024, 1, 31))
        finally:
            client.disconnect()
    assert isinstance(df, pl.DataFrame) and df["value"][0] == 100.0
    assert isinstance(legacy, pd.DataFrame) and len(legacy) == 1
    assert engine.bdp.call_args.kwargs["backend"] == "polars"
    args, kwargs = engine.bdh.call_args
    assert args == ("SPX Index", "PX_LAST", "2024-01-01", "2024-01-31")
    assert kwargs["Per"] == "D"

def test_remote_rejects_invalid_token_and_relays_errors():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["AAPL US Equity"], "field": ["PX_LAST"], "value": [100.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        _serve_(engine, port=55566, token="secret")
        client = BloombergAPI(host="127.0.0.1", port=55566, token="wrong", timeout=10)
        try:
            with pytest.raises(RuntimeError, match="Invalid Token"):
                client.reference.fetch("AAPL US Equity", "PX_LAST")
        finally:
            client.disconnect()
    assert not engine.bdp.called

def test_remote_whitelist_allows_and_blacklist_rejects():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["AAPL US Equity"], "field": ["PX_LAST"], "value": [100.0]})
    with patch.object(xbbg, "blp", engine, create=True):
        threading.Thread(target=lambda: BloombergAPI().serve(port=55568, whitelist=["127.0.0.1"]), daemon=True).start()
        threading.Thread(target=lambda: BloombergAPI().serve(port=55569, blacklist=["127.0.0.1"]), daemon=True).start()
        threading.Thread(target=lambda: BloombergAPI().serve(port=55570, whitelist=["10.0.0.9"]), daemon=True).start()
        allowed = BloombergAPI(host="127.0.0.1", port=55568, timeout=10)
        blacklisted = BloombergAPI(host="127.0.0.1", port=55569, timeout=10)
        unlisted = BloombergAPI(host="127.0.0.1", port=55570, timeout=10)
        try:
            df = allowed.reference.fetch("AAPL US Equity", "PX_LAST")
            with pytest.raises(RuntimeError, match="Blacklisted"):
                blacklisted.reference.fetch("AAPL US Equity", "PX_LAST")
            with pytest.raises(RuntimeError, match="Whitelisted"):
                unlisted.reference.fetch("AAPL US Equity", "PX_LAST")
        finally:
            allowed.disconnect()
            blacklisted.disconnect()
            unlisted.disconnect()
    assert isinstance(df, pl.DataFrame) and len(df) == 1

def test_remote_streaming_roundtrip_over_pub_sub():
    engine = MagicMock()
    engine.stream.return_value = iter([pl.DataFrame({"value": [1.0]}), pl.DataFrame({"value": [2.0]}), pl.DataFrame({"value": [3.0]})])
    received = []
    with patch.object(xbbg, "blp", engine, create=True):
        _serve_(engine, port=55571, token="secret")
        client = BloombergAPI(host="127.0.0.1", port=55571, token="secret", timeout=10)
        try:
            client.streaming.subscribe("AAPL US Equity", "LAST_PRICE", callback=received.append, limit=2)
        finally:
            client.disconnect()
    args, kwargs = engine.stream.call_args
    assert args == (["AAPL US Equity"], ["LAST_PRICE"]) or args == ("AAPL US Equity", "LAST_PRICE")
    assert kwargs["backend"] == "polars"
    assert len(received) == 2
    assert all(isinstance(update, pl.DataFrame) for update in received)

def test_remote_endless_streaming_stops_on_unsubscribe():
    engine = MagicMock()
    engine.stream.return_value = iter([pl.DataFrame({"value": [float(i)]}) for i in range(100)])
    received = []
    with patch.object(xbbg, "blp", engine, create=True):
        _serve_(engine, port=55572, token="secret")
        client = BloombergAPI(host="127.0.0.1", port=55572, token="secret", timeout=10)
        try:
            client.streaming.subscribe("AAPL US Equity", "LAST_PRICE", callback=received.append, limit=3)
        finally:
            client.disconnect()
    assert len(received) == 3

def test_remote_connect_raises_when_server_is_down():
    with patch.object(BloombergAPI, "_PING_", 1):
        client = BloombergAPI(host="127.0.0.1", port=55599)
        try:
            with pytest.raises(ConnectionError, match="Server Unreachable"):
                client.reference.fetch("AAPL US Equity", "PX_LAST")
        finally:
            client.disconnect()