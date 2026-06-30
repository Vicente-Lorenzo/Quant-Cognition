import math
from datetime import datetime, timezone

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode, parse_technical
from Library.Indicator.Technical.Technical import TechnicalAPI
from Library.Indicator.Technical.Volatility.RV import RealizedVolatilityAPI
from Library.Market.Market import MarketAPI

def _market_(closes):
    market = MarketAPI(db=None, migrate=False, autosave=False, autoload=False, autooverload=False)
    n = len(closes)
    df = pl.DataFrame({
        "UID": list(range(1, n + 1)),
        "Timestamp": [datetime(2020, 1, i + 1, tzinfo=timezone.utc) for i in range(n)],
        "Security": [1] * n,
        "Timeframe": ["M1"] * n,
        "CloseTick.Bid": [float(c) for c in closes],
        "Volume": [100.0] * n
    })
    market.init_data(df)
    return market, df

def _append_(market, df, close, uid, day):
    bar = {"UID": uid, "Timestamp": datetime(2020, 1, day, tzinfo=timezone.utc), "Security": 1, "Timeframe": "M1", "CloseTick.Bid": float(close), "Volume": 100.0}
    for col in df.columns:
        if col not in bar: bar[col] = None
    market._data_ = market._data_.vstack(pl.DataFrame([bar]).select(df.columns))
    market.CloseTicks.init_data(market._data_)

def _ewma_(squares, alpha):
    m = squares[0]
    for x in squares[1:]:
        m = (1.0 - alpha) * m + alpha * x
    return m

def _indicator_(market, window=2):
    rv = RealizedVolatilityAPI(name="RV", window=window, mode=IndicatorMode.Off)
    tech = TechnicalAPI(name="Technical", window=None, mode=IndicatorMode.Off, RV=rv)
    tech.init_data(market)
    return tech

def test_parse_registers_rv():
    tech = parse_technical({"Vol": ["RV", 20]})
    assert hasattr(tech, "Vol")
    assert isinstance(tech.Vol, RealizedVolatilityAPI)
    assert tech.Vol.Window == 20

def test_rv_matches_ewma_of_squared_log_returns():
    market, _ = _market_([1.0, 2.0, 4.0, 8.0])
    tech = _indicator_(market)
    squares = [0.0] + [math.log(2.0) ** 2] * 3
    expected = math.sqrt(_ewma_(squares, 0.5))
    assert abs(tech.RV.Result.last() - expected) < 1e-12

def test_rv_pads_first_window_nulls():
    market, _ = _market_([1.0, 2.0, 4.0, 8.0])
    tech = _indicator_(market)
    series = tech.RV._data_["RV"]
    assert series[0] is None and series[1] is None
    assert series[2] is not None and series[3] is not None

def test_rv_zero_for_constant_prices():
    market, _ = _market_([5.0, 5.0, 5.0, 5.0, 5.0])
    tech = _indicator_(market)
    assert tech.RV.Result.last() == 0.0

def test_rv_stream_continues_ewma():
    market, df = _market_([1.0, 2.0, 4.0, 8.0])
    tech = _indicator_(market)
    prev = tech.RV.Result.last()
    _append_(market, df, 16.0, 5, 5)
    tech.update_data(market)
    expected = math.sqrt((prev * prev * (2 - 1) + math.log(2.0) ** 2) / 2)
    assert abs(tech.RV.Result.last() - expected) < 1e-12