import sys
import types
from unittest.mock import MagicMock, patch

class _Backend:
    PANDAS = "pandas"
    POLARS = "polars"

try:
    import xbbg  # noqa: F401
except ImportError:
    _stub = types.ModuleType("xbbg")
    _stub.blp = MagicMock()
    _stub.Backend = _Backend
    _stub.ovr = lambda **kwargs: kwargs
    sys.modules["xbbg"] = _stub

from Library.Database.Dataframe import pl
from Library.Bloomberg import BloombergAPI, ReferenceAPI, HistoricalAPI, IntradayAPI, QueryAPI, StreamingAPI
import Library.Bloomberg.Bloomberg as Bloomberg
import Library.Bloomberg.Reference as Reference
import Library.Bloomberg.Historical as Historical
import Library.Bloomberg.Intraday as Intraday
import Library.Bloomberg.Query as Query

def test_wiring():
    bbg = BloombergAPI()
    assert isinstance(bbg.reference, ReferenceAPI)
    assert isinstance(bbg.historical, HistoricalAPI)
    assert isinstance(bbg.intraday, IntradayAPI)
    assert isinstance(bbg.query, QueryAPI)
    assert isinstance(bbg.streaming, StreamingAPI)

def test_reference_fetch_single_args_and_polars_backend():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["AAPL US Equity"], "field": ["PX_LAST"], "value": [100.0]})
    with patch.object(Reference, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        df = BloombergAPI(legacy=False).reference.fetch("AAPL US Equity", "PX_LAST")
    args, kwargs = engine.bdp.call_args
    assert args == ("AAPL US Equity", "PX_LAST")
    assert kwargs["backend"] == _Backend.POLARS
    assert len(df) == 1

def test_reference_fetch_list_args_and_legacy_pandas_backend():
    engine = MagicMock()
    engine.bdp.return_value = pl.DataFrame({"ticker": ["A", "B"], "field": ["PX_LAST", "PX_LAST"], "value": [1.0, 2.0]})
    with patch.object(Reference, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        BloombergAPI(legacy=True).reference.fetch(["A", "B"], ["PX_LAST", "NAME"])
    args, kwargs = engine.bdp.call_args
    assert args == (["A", "B"], ["PX_LAST", "NAME"])
    assert kwargs["backend"] == _Backend.PANDAS

def test_reference_bulk_calls_bds():
    engine = MagicMock()
    engine.bds.return_value = pl.DataFrame({"ticker": ["SPX Index"], "field": ["INDX_MEMBERS"], "member": ["AAPL"]})
    with patch.object(Reference, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        BloombergAPI().reference.bulk("SPX Index", "INDX_MEMBERS")
    assert engine.bds.called

def test_historical_fetch_calls_bdh():
    engine = MagicMock()
    engine.bdh.return_value = pl.DataFrame({"ticker": ["SPX Index"], "date": ["2024-01-02"], "field": ["PX_LAST"], "value": [1.1]})
    with patch.object(Historical, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        BloombergAPI().historical.fetch("SPX Index", "PX_LAST", start="2024-01-01", stop="2024-01-31")
    assert engine.bdh.called

def test_intraday_bars_calls_bdib():
    engine = MagicMock()
    engine.bdib.return_value = pl.DataFrame({"time": ["2024-01-15T10:00"], "close": [1.0]})
    with patch.object(Intraday, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        BloombergAPI().intraday.bars("TSLA US Equity", dt="2024-01-15", interval=5)
    args, kwargs = engine.bdib.call_args
    assert kwargs["dt"] == "2024-01-15" and kwargs["interval"] == 5

def test_intraday_ticks_calls_bdtick_over_range():
    engine = MagicMock()
    engine.bdtick.return_value = pl.DataFrame({"time": ["2024-01-15T10:00:00"], "value": [1.0]})
    with patch.object(Intraday, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        BloombergAPI().intraday.ticks("TSLA US Equity", "2024-01-15 09:30", "2024-01-15 16:00")
    args, kwargs = engine.bdtick.call_args
    assert args == ("TSLA US Equity", "2024-01-15 09:30", "2024-01-15 16:00")
    assert kwargs["event_types"] == "TRADE"

def test_query_execute_calls_bql():
    engine = MagicMock()
    engine.bql.return_value = pl.DataFrame({"ID": ["AAPL US Equity"], "px_last": [100.0]})
    with patch.object(Query, "blp", engine), patch.object(Bloomberg, "Backend", _Backend):
        BloombergAPI().query.execute("get(px_last) for(['AAPL US Equity'])")
    assert engine.bql.called