import pytest
from Library.Database.Dataframe import pl
from Library.Indicator.Indicator import IndicatorMode, parse_technical
from Library.Indicator.Technical.Technical import TechnicalAPI
from Library.Indicator.Technical.Baseline.MA import MovingAverageType
from Library.Indicator.Technical.Baseline.SMA import SimpleMovingAverageAPI
from Library.Indicator.Technical.Momentum.MACD import MovingAverageConvergenceDivergenceAPI
from Library.Market.Market import MarketAPI
from datetime import datetime, timezone

def test_technical_container_assignment():
    sma = SimpleMovingAverageAPI(name="SMA", window=2, mode=IndicatorMode.Off)
    tech = TechnicalAPI(name="Technical", window=None, mode=IndicatorMode.Off, SMA=sma)
    assert hasattr(tech, "SMA")
    assert tech.SMA is sma

def test_parse_technical():
    config = {
        "ShortDMA": ["DMA", 5, "Exponential", 1],
        "LongTMA": ["TMA", 20, "Simple", 0]
    }
    tech = parse_technical(config)
    assert hasattr(tech, "ShortDMA")
    assert hasattr(tech, "LongTMA")
    assert tech.ShortDMA.Window == 5
    assert tech.ShortDMA.TypeMA == MovingAverageType.Exponential
    assert tech.LongTMA.Window == 20
    assert tech.LongTMA.TypeMA == MovingAverageType.Simple

def test_sma_calculation():
    market = MarketAPI(db=None, migrate=False, autosave=False, autoload=False, autooverload=False)
    
    df = pl.DataFrame({
        "UID": [1, 2, 3, 4],
        "Timestamp": [datetime(2020, 1, 1, tzinfo=timezone.utc), datetime(2020, 1, 2, tzinfo=timezone.utc), 
                      datetime(2020, 1, 3, tzinfo=timezone.utc), datetime(2020, 1, 4, tzinfo=timezone.utc)],
        "Security": [1, 1, 1, 1],
        "Timeframe": ["M1", "M1", "M1", "M1"],
        "CloseTick.Bid": [1.0, 2.0, 3.0, 4.0],
        "Volume": [100.0, 200.0, 300.0, 400.0]
    })
    market.init_data(df)
    
    sma = SimpleMovingAverageAPI(name="ShortSMA", window=2, mode=IndicatorMode.Off)
    tech = TechnicalAPI(name="Technical", window=None, mode=IndicatorMode.Off, ShortSMA=sma)
    tech.init_data(market)
    
    assert tech.ShortSMA.Result.last() == 3.5
    
    new_bar_data = {
        "UID": 5, "Timestamp": datetime(2020, 1, 5, tzinfo=timezone.utc), "Security": 1, "Timeframe": "M1",
        "CloseTick.Bid": 5.0, "Volume": 500.0
    }
    for col in df.columns:
        if col not in new_bar_data: new_bar_data[col] = None
    
    market._data_ = market._data_.vstack(pl.DataFrame([new_bar_data]).select(df.columns))
    market.CloseTicks.init_data(market._data_)
    
    tech.update_data(market)
    assert tech.ShortSMA.Result.last() == 4.5

def test_macd_calculation_and_padding():
    market = MarketAPI(db=None, migrate=False, autosave=False, autoload=False, autooverload=False)
    
    macd = MovingAverageConvergenceDivergenceAPI(name="MACD", fast_period=3, slow_period=5, signal_period=2, mode=IndicatorMode.Off)
    tech = TechnicalAPI(name="Technical", window=None, mode=IndicatorMode.Off, MACD=macd)
    
    df = pl.DataFrame({
        "UID": list(range(1, 10)),
        "Timestamp": [datetime(2020, 1, i, tzinfo=timezone.utc) for i in range(1, 10)],
        "Security": [1] * 9,
        "Timeframe": ["M1"] * 9,
        "CloseTick.Bid": [float(i) for i in range(1, 10)],
        "Volume": [100.0] * 9
    })
    market.init_data(df)
    tech.init_data(market)
    
    macd_data = tech.MACD._data_
    # padding check
    assert macd_data["MACD.MACD"][3] is None
    assert macd_data["MACD.MACD"][4] is not None
    assert macd_data["MACD.Signal"][4] is None
    assert macd_data["MACD.Signal"][5] is not None
    
    # Stream update check
    new_bar = {
        "UID": 10, "Timestamp": datetime(2020, 1, 10, tzinfo=timezone.utc), "Security": 1, "Timeframe": "M1",
        "CloseTick.Bid": 10.0, "Volume": 500.0
    }
    for col in df.columns:
        if col not in new_bar: new_bar[col] = None
    market._data_ = market._data_.vstack(pl.DataFrame([new_bar]).select(df.columns))
    market.CloseTicks.init_data(market._data_)
    
    tech.update_data(market)
    assert tech.MACD.Signal.last() is not None
    assert tech.MACD.Histogram.last() is not None