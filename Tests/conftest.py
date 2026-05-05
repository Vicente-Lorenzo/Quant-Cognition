import pytest
import Library.Universe
import Library.Market
import Library.Portfolio
from Library.Database.Datapoint import DatapointAPI
def override_databases(cls, db_name):
    cls.Database = db_name
    for sub in cls.__subclasses__():
        override_databases(sub, db_name)
override_databases(DatapointAPI, "Tests")
from Library.Database.Query import QueryAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Universe.Universe import UniverseAPI
from Library.Market.Market import MarketAPI
from Library.Portfolio.Portfolio import PortfolioAPI
@pytest.fixture(scope="session")
def db():
    admin = PostgresDatabaseAPI(admin=True)
    try:
        admin.connect()
        if not admin.exists(database=DatapointAPI.Database):
            admin.create(database=DatapointAPI.Database)
    finally:
        admin.disconnect()
    conn = PostgresDatabaseAPI(database=DatapointAPI.Database)
    try:
        conn.connect()
        conn.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{UniverseAPI.Schema}" CASCADE'))
        conn.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{MarketAPI.Schema}" CASCADE'))
        conn.executeone(QueryAPI(f'DROP SCHEMA IF EXISTS "{PortfolioAPI.Schema}" CASCADE'))
        conn.commit()
        conn.executeone(QueryAPI(f'CREATE SCHEMA "{UniverseAPI.Schema}"'))
        conn.executeone(QueryAPI(f'CREATE SCHEMA "{MarketAPI.Schema}"'))
        conn.executeone(QueryAPI(f'CREATE SCHEMA "{PortfolioAPI.Schema}"'))
        conn.commit()
        yield conn
    finally:
        conn.disconnect()
@pytest.fixture(scope="session")
def universe(db):
    from Library.Universe.Category import CategoryAPI
    from Library.Universe.Provider import ProviderAPI, Platform
    from Library.Universe.Ticker import TickerAPI, ContractType
    from Library.Universe.Contract import ContractAPI
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Timeframe import TimeframeAPI
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ContractAPI.Table, structure=ContractAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=SecurityAPI.Table, structure=SecurityAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TimeframeAPI.Table, structure=TimeframeAPI(db=None).Structure)
    cat = CategoryAPI(UID="Forex (Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db)
    cat.save(by="fixture")
    prov = ProviderAPI(UID="Pepperstone (cTrader)", Platform=Platform.cTrader, Name="Pepperstone Europe", Abbreviation="Pepperstone", db=db)
    prov.save(by="fixture")
    ticker = TickerAPI(UID="EURUSD", Category="Forex (Major)", BaseAsset="EUR", BaseName="Euro", QuoteAsset="USD", QuoteName="US Dollar", Description="Euro vs US Dollar", db=db)
    ticker.save(by="fixture")
    contract = ContractAPI(Ticker="EURUSD", Provider="Pepperstone (cTrader)", Type=ContractType.Spot, PipSize=0.0001, PointSize=0.00001, Digits=5, LotSize=100000, db=db)
    contract.save(by="fixture")
    sec = SecurityAPI(Ticker="EURUSD", Provider="Pepperstone (cTrader)", Contract=ContractType.Spot, db=db)
    sec.save(by="fixture")
    tf = TimeframeAPI(UID="M1", db=db)
    tf.save(by="fixture")
    return {"category": cat, "provider": prov, "ticker": ticker, "contract": contract, "security": sec, "timeframe": tf}
@pytest.fixture(scope="session")
def market(db, universe):
    from Library.Market.Tick import TickAPI
    from Library.Market.Bar import BarAPI
    db.migrate(schema=MarketAPI.Schema, table=TickAPI.Table, structure=TickAPI(db=None).Structure)
    db.migrate(schema=MarketAPI.Schema, table=BarAPI.Table, structure=BarAPI(db=None).Structure)
    return {"tick_table": f'"{TickAPI.Schema}"."{TickAPI.Table}"', "bar_table": f'"{BarAPI.Schema}"."{BarAPI.Table}"'}