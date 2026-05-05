import pytest
from datetime import datetime
from Library.Market.Tick import TickAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI
def test_tick_initialization():
    now = datetime.now()
    tick_args = (100, now, 1.1005, 1.1000, 1.0, 1.0, 1.0, 1.0)
    tick = TickAPI(*tick_args)
    assert tick.Security is not None
    assert tick.Security.UID == 100
    assert tick.Timestamp.DateTime == now
    assert tick.Ask.Price == 1.1005
    assert tick.Bid.Price == 1.1000
def test_tick_properties():
    now = datetime.now()
    tick = TickAPI(1, now, Ask=1.1005, Bid=1.1000)
    assert tick.Mid == 1.10025
    assert tick.Spread is not None
    assert round(tick.Spread.Price, 4) == 0.0005
    assert tick.InvertedAsk == 1.0 / 1.1005
    assert tick.InvertedBid == 1.0 / 1.1000
def test_tick_db_operations(db):
    from Library.Universe.Category import CategoryAPI
    from Library.Universe.Provider import ProviderAPI, Platform
    from Library.Universe.Ticker import TickerAPI, ContractType
    from Library.Universe.Contract import ContractAPI
    CategoryAPI(UID="Forex", db=db, migrate=True).save(by="Tester")
    ProviderAPI(UID="TestProv", Platform=Platform.cTrader, db=db, migrate=True).save(by="Tester")
    TickerAPI(UID="EURUSD", Category="Forex", db=db, migrate=True).save(by="Tester")
    ContractAPI(Ticker="EURUSD", Provider="TestProv", Type=ContractType.Spot, db=db, migrate=True).save(by="Tester")
    sec = SecurityAPI(Provider="TestProv", Category="Forex", Ticker="EURUSD", Contract=ContractType.Spot, db=db, migrate=True, autoload=True)
    sec.save(by="Tester")
    now = datetime(2023, 1, 1, 12, 0, 0)
    tick_data = (sec.UID, now, 1.1005, 1.1000, 1.0, 1.0, 1.0, 1.0)
    tick = TickAPI(*tick_data, db=db, migrate=True)
    tick.save(by="Tester")
    loaded_tick = TickAPI(sec.UID, now, db=db, autoload=True)
    assert loaded_tick.Ask.Price == pytest.approx(1.1005)
    assert loaded_tick.Bid.Price == pytest.approx(1.1000)
    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{TickAPI.Schema}"."{TickAPI.Table}" CASCADE'))
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{SecurityAPI.Schema}"."{SecurityAPI.Table}" CASCADE'))
    db.commit()