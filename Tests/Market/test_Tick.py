import pytest
from datetime import datetime
from Library.Market.Tick import TickAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI

def test_tick_initialization():
    now = datetime.now()
    tick = TickAPI(1, now, Ask=1.1005, Bid=1.1000)
    
    assert tick.Security is not None
    assert tick.Security.UID == 1
    
    assert tick.Timestamp is not None
    assert tick.Timestamp.DateTime == now
    
    assert tick.Ask is not None
    assert tick.Ask.Price == 1.1005
    
    assert tick.Bid is not None
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
    
    cat = CategoryAPI(UID="Forex", db=db, migrate=True)
    cat.save(by="Tester")
    
    prov = ProviderAPI(UID="TestProv", Platform=Platform.cTrader, db=db, migrate=True)
    prov.save(by="Tester")
    
    tick_def = TickerAPI(UID="EURUSD", Category="Forex", BaseAsset="EUR", QuoteAsset="USD", db=db, migrate=True)
    tick_def.save(by="Tester")
    
    contract = ContractAPI(Ticker="EURUSD", Provider="TestProv", Type=ContractType.Spot, db=db, migrate=True)
    contract.save(by="Tester")
    
    sec = SecurityAPI(UID=1, Provider="TestProv", Category="Forex", Ticker="EURUSD", Contract=ContractType.Spot, db=db, migrate=True)
    sec.save(by="Tester")
    
    now = datetime(2023, 1, 1, 12, 0, 0)
    tick = TickAPI(1, now, Ask=1.1005, Bid=1.1000, db=db, migrate=True)
    tick.save(by="Tester")
    
    loaded_tick = TickAPI(1, now, db=db)
    loaded_tick.load()
    
    assert loaded_tick.Ask is not None
    import pytest
    assert loaded_tick.Ask.Price == pytest.approx(1.1005)
    assert loaded_tick.Bid.Price == pytest.approx(1.1000)
    assert loaded_tick.CreatedBy == "Tester"
    
    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{TickAPI.Schema}"."{TickAPI.Table}" CASCADE'))
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{SecurityAPI.Schema}"."{SecurityAPI.Table}" CASCADE'))
    db.commit()
