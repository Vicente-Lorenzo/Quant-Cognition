import pytest
import polars as pl
from datetime import datetime, timedelta
from Library.Market.Market import MarketAPI
from Library.Market.Tick import TickAPI
from Library.Market.Bar import BarAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Ticker import TickerAPI
from Library.Database.Query import QueryAPI
@pytest.fixture(autouse=True)
def setup_market_test(db):
    db.migrate(schema="Universe", table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema="Universe", table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema="Universe", table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    db.migrate(schema="Universe", table=TimeframeAPI.Table, structure=TimeframeAPI(db=db).Structure)
    db.migrate(schema="Universe", table=SecurityAPI.Table, structure=SecurityAPI(db=db).Structure)
    db.migrate(schema=MarketAPI.Schema, table=TickAPI.Table, structure=TickAPI(db=db).Structure)
    db.migrate(schema=MarketAPI.Schema, table=BarAPI.Table, structure=BarAPI(db=db).Structure)
    CategoryAPI(UID="Forex", db=db).save()
    ProviderAPI(UID="TestProv", Platform=Platform.cTrader, db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex", db=db).save()
    TimeframeAPI(UID="M1", db=db).save()
    sec = SecurityAPI(Ticker="EURUSD", Provider="TestProv", Category="Forex", db=db)
    sec.save()
    yield sec.UID
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{MarketAPI.Schema}"."{BarAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{MarketAPI.Schema}"."{TickAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{SecurityAPI.Schema}"."{SecurityAPI.Table}" CASCADE')).commit()
def test_market_bulk_ticks(db, setup_market_test):
    sec_uid = setup_market_test
    base_time = datetime(2023, 1, 1, 10, 0, 0)
    tick_data = []
    for i in range(100):
        tick_data.append({
            "Security": sec_uid,
            "Timestamp": base_time + timedelta(seconds=i),
            "Ask": 1.1000 + (i * 0.0001),
            "Bid": 1.0999 + (i * 0.0001),
            "Volume": 100000.0
        })
    df = pl.DataFrame(tick_data)
    MarketAPI.push_ticks(db, df)
    pulled_df = MarketAPI.pull_ticks(db, security=sec_uid, start=base_time, stop=base_time + timedelta(seconds=99))
    assert len(pulled_df) == 100
    assert pulled_df["Ask"].max() == pytest.approx(1.1000 + (99 * 0.0001))
def test_market_bulk_bars(db, setup_market_test):
    sec_uid = setup_market_test
    base_time = datetime(2023, 1, 1, 10, 0, 0)
    bar_data = []
    for i in range(50):
        bar_data.append({
            "Security": sec_uid,
            "Timeframe": "M1",
            "Timestamp": base_time + timedelta(minutes=i),
            "Volume": 5000.0
        })
    df = pl.DataFrame(bar_data)
    MarketAPI.push_bars(db, df)
    pulled_df = MarketAPI.pull_bars(db, security=sec_uid, timeframe="M1", start=base_time, stop=base_time + timedelta(minutes=49))
    assert len(pulled_df) == 50
    assert pulled_df["Volume"].sum() == 5000.0 * 50
def test_market_empty_pulls(db, setup_market_test):
    sec_uid = setup_market_test
    start = datetime(1990, 1, 1)
    stop = datetime(1990, 1, 2)
    ticks = MarketAPI.pull_ticks(db, sec_uid, start, stop)
    assert len(ticks) == 0
    bars = MarketAPI.pull_bars(db, sec_uid, "M1", start, stop)
    assert len(bars) == 0