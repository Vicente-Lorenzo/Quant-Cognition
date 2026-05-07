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
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Database.Query import QueryAPI

@pytest.fixture(autouse=True)
def setup_market_test(db):
    db.migrate(schema="Universe", table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema="Universe", table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema="Universe", table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    db.migrate(schema="Universe", table=ContractAPI.Table, structure=ContractAPI(db=db).Structure)
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
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{ContractAPI.Schema}"."{ContractAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{TickerAPI.Schema}"."{TickerAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{ProviderAPI.Schema}"."{ProviderAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{CategoryAPI.Schema}"."{CategoryAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{TimeframeAPI.Schema}"."{TimeframeAPI.Table}" CASCADE')).commit()

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

def test_series_tick_initialization():
    market = MarketAPI()
    data = pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        "Security": [1, 1],
        "Ask": [1.1, 1.2],
        "Bid": [1.0, 1.1],
        "Volume": [100.0, 200.0]
    })
    market.init_data(data)
    
    assert market.Ticks.Bid.last() == 1.1
    assert market.Ticks.Ask.last() == 1.2
    
    tick = market.Ticks.last(dataframe=False)
    assert isinstance(tick, TickAPI)
    assert tick.Bid.Price == 1.1
    assert tick.Ask.Price == 1.2
    
    # test offset
    market.update_offset(2)
    assert market.Ticks.Bid.last() == 1.0

def test_series_bar_initialization():
    market = MarketAPI()
    data = pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1)],
        "Security": [1],
        "Timeframe": ["M1"],
        "CloseTick.Ask": [1.2],
        "CloseTick.Bid": [1.1],
        "OpenTick.Ask": [1.1],
        "OpenTick.Bid": [1.0],
        "Volume": [1000.0]
    })
    market.init_data(data)
    
    assert market.CloseTicks.Bid.last() == 1.1
    assert market.OpenTicks.Ask.last() == 1.1
    
    # over test
    assert market.CloseTicks.Bid.over(market.OpenTicks.Bid) == True

def test_series_group_crossover():
    market = MarketAPI()
    data = pl.DataFrame({
        "Timestamp": [datetime(2020, 1, 1), datetime(2020, 1, 2)],
        "Security": [1, 1],
        "Timeframe": ["M1", "M1"],
        "CloseTick.Ask": [1.0, 1.3],
        "CloseTick.Bid": [0.9, 1.2],
        "OpenTick.Ask": [1.1, 1.1],
        "OpenTick.Bid": [1.0, 1.0],
        "Volume": [1000.0, 1000.0]
    })
    market.init_data(data)
    
    # Close Ask (1.0 -> 1.3) crosses Open Ask (1.1 -> 1.1)
    res = market.CloseTicks.crossover(market.OpenTicks, dataframe=False)
    df_res = market.CloseTicks.crossover(market.OpenTicks, dataframe=True)
    assert df_res["CloseTick.Ask"][0] == True
    assert df_res["CloseTick.Bid"][0] == True

def test_market_update_data():
    market = MarketAPI()
    t1 = TickAPI(Timestamp=datetime(2020, 1, 1), Security=1, Ask=1.1, Bid=1.0, Volume=100.0)
    data = pl.DataFrame([t1.dict()], strict=False)
    market.init_data(data)
    
    tick = TickAPI(Timestamp=datetime(2020, 1, 2), Security=1, Ask=1.2, Bid=1.1, Volume=200.0)
    market.update_data(tick)
    
    assert market.Ticks.Ask.last() == 1.2
