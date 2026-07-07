import math
from datetime import datetime, timezone

from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode, parse_technical
from Library.Indicator.Technical.Momentum.ROC import RateOfChangeAPI
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

def test_batch_is_log_return_over_window():
    closes = [1.10, 1.11, 1.09, 1.12, 1.15, 1.13]
    market, _ = _market_(closes)
    roc = RateOfChangeAPI(name="MOM3", window=3, mode=IndicatorMode.Off)
    roc.init_data(market)
    assert abs(roc.Result.last() - math.log(1.13 / 1.09)) < 1e-12
    assert abs(roc.Result.last(shift=1) - math.log(1.15 / 1.11)) < 1e-12

def test_batch_warmup_is_null():
    closes = [1.10, 1.11, 1.09]
    market, _ = _market_(closes)
    roc = RateOfChangeAPI(name="MOM3", window=3, mode=IndicatorMode.Off)
    roc.init_data(market)
    assert roc.Result.last() is None

def test_stream_matches_batch():
    closes = [1.10, 1.11, 1.09, 1.12, 1.15]
    market, df = _market_(closes)
    roc = RateOfChangeAPI(name="MOM3", window=3, mode=IndicatorMode.Off)
    roc.init_data(market)
    _append_(market, df, 1.13, 6, 6)
    roc.update_data(market)
    assert abs(roc.Result.last() - math.log(1.13 / 1.09)) < 1e-12

def test_parse_technical_builds_roc():
    technical = parse_technical({"MOM24": ["ROC", 24]})
    indicator = getattr(technical, "MOM24", None)
    assert isinstance(indicator, RateOfChangeAPI) and indicator.Window == 24
