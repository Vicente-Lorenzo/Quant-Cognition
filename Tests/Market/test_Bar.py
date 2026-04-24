import pytest
from datetime import datetime
from Library.Market.Bar import BarAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Universe import UniverseAPI

def test_bar_initialization(db):
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TimeframeAPI.Table, structure=TimeframeAPI(db=db).Structure)
    from Library.Universe.Contract import ContractAPI
    db.migrate(schema=UniverseAPI.Schema, table=ContractAPI.Table, structure=ContractAPI(db=db).Structure)

    CategoryAPI(UID="Forex (Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save(by="test")
    ProviderAPI(UID="Pepperstone (cTrader)", Platform=Platform.cTrader, Name="Pepperstone Europe", Abbreviation="Pepperstone", db=db).save(by="test")
    TickerAPI(UID="EURUSD", Category="Forex (Major)", BaseAsset="EUR", BaseName="Euro", QuoteAsset="USD", QuoteName="US Dollar", Description="Euro vs US Dollar", db=db).save(by="test")
    ContractAPI(Ticker="EURUSD", Provider="Pepperstone (cTrader)", Type=ContractType.Spot, db=db).save(by="test")
    tf = TimeframeAPI(UID="M1", db=db)
    tf.save(by="test")

    sec = SecurityAPI(Ticker="EURUSD", Provider="Pepperstone (cTrader)", Contract=ContractType.Spot, db=db, migrate=True)
    sec.save(by="test")
    dt = datetime(2023, 1, 1, 12, 0, 0)
    
    from Library.Market.Tick import TickAPI
    db.migrate(schema=TickAPI.Schema, table=TickAPI.Table, structure=TickAPI(db=db).Structure)

    bar = BarAPI(
        Security=sec.UID, 
        Timeframe=tf.UID,
        Timestamp=dt, 
        OpenTick=TickAPI(Ask=1.0500, Bid=1.0498),
        HighTick=TickAPI(Ask=1.0510, Bid=1.0508),
        LowTick=TickAPI(Ask=1.0490, Bid=1.0488),
        CloseTick=TickAPI(Ask=1.0505, Bid=1.0503),
        db=db,
        migrate=True
    )
    
    assert bar.Security.UID == sec.UID
    assert bar.Timeframe.UID == tf.UID
    assert bar.Timestamp.DateTime == dt
    assert bar.OpenTick.Ask.Price == pytest.approx(1.0500)
    assert bar.HighTick.Ask.Price == pytest.approx(1.0510)
    assert bar.LowTick.Ask.Price == pytest.approx(1.0490)
    assert bar.CloseTick.Ask.Price == pytest.approx(1.0505)
    
    assert bar.OpenTick.Mid == pytest.approx(1.0499)
    assert bar.HighTick.Mid == pytest.approx(1.0509)
    assert bar.LowTick.Mid == pytest.approx(1.0489)
    assert bar.CloseTick.Mid == pytest.approx(1.0504)
    
    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'DELETE FROM "{BarAPI.Schema}"."{BarAPI.Table}"')).commit()