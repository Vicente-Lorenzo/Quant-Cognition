import pytest
import polars as pl
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
@pytest.fixture(autouse=True)
def setup_universe(db):
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ContractAPI.Table, structure=ContractAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=SecurityAPI.Table, structure=SecurityAPI(db=db).Structure)
    yield db
    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{UniverseAPI.Schema}"."{SecurityAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{UniverseAPI.Schema}"."{ContractAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{UniverseAPI.Schema}"."{TickerAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{UniverseAPI.Schema}"."{ProviderAPI.Table}" CASCADE')).commit()
    db.executeone(QueryAPI(f'TRUNCATE TABLE "{UniverseAPI.Schema}"."{CategoryAPI.Table}" CASCADE')).commit()
def test_universe_constants():
    assert UniverseAPI.Database == "Tests"
    assert UniverseAPI.Schema == "Universe"
def test_bulk_population_integrity(db):
    cats = pl.DataFrame([{"UID": "Cat1", "Primary": "P", "Secondary": "S", "Alternative": "A"}])
    UniverseAPI.push_categories(db, cats)
    provs = pl.DataFrame([{"UID": "Prov1", "Platform": "cTrader", "Name": "N", "Abbreviation": "A"}])
    UniverseAPI.push_providers(db, provs)
    tickers = pl.DataFrame([{"UID": "T1", "Category": "Cat1", "BaseAsset": "B", "QuoteAsset": "Q"}])
    UniverseAPI.push_tickers(db, tickers)
    contracts = pl.DataFrame([{"Ticker": "T1", "Provider": "Prov1", "Type": "Spot"}])
    UniverseAPI.push_contracts(db, contracts)
    contracts_df = UniverseAPI.pull_contracts(db)
    contract_uid = contracts_df.row(0, named=True)["UID"]
    securities = pl.DataFrame([{"Provider": "Prov1", "Category": "Cat1", "Ticker": "T1", "Contract": contract_uid}])
    UniverseAPI.push_securities(db, securities)
    assert len(UniverseAPI.pull_categories(db)) >= 1
    assert len(UniverseAPI.pull_providers(db)) >= 1
    assert len(UniverseAPI.pull_tickers(db)) >= 1
    assert len(UniverseAPI.pull_contracts(db)) >= 1
    sec_df = UniverseAPI.pull_securities(db)
    assert len(sec_df) == 1
    sec_id = sec_df.row(0, named=True)["UID"]
    sec = SecurityAPI(UID=sec_id, db=db, autoload=True)
    assert sec.Ticker.UID == "T1"
    assert sec.Provider.UID == "Prov1"
    assert sec.Category.UID == "Cat1"
def test_ticker_detection_logic():
    assert TickerAPI.detect("EURUSD") == ContractType.Spot
    assert TickerAPI.detect("AAPL.US") == ContractType.Spot
    assert TickerAPI.detect("ESH4") == ContractType.Future or TickerAPI.detect("ESH24") == ContractType.Future
def test_referential_integrity_cascade(db):
    cat = CategoryAPI(UID="Forex", Primary="Forex", Secondary="Major", Alternative="Currency", db=db)
    cat.save()
    ticker = TickerAPI(UID="DELETE_ME", Category="Forex", BaseAsset="DEL", QuoteAsset="USD", db=db)
    ticker.save()
    prov = ProviderAPI(UID="TestProv", Platform=Platform.API, Name="Test", Abbreviation="T", db=db)
    prov.save()
    contract = ContractAPI(Ticker="DELETE_ME", Provider="TestProv", Type=ContractType.Spot, db=db)
    contract.save()
    sec = SecurityAPI(Ticker="DELETE_ME", Provider="TestProv", Category="Forex", db=db)
    sec.save()
    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'DELETE FROM "{UniverseAPI.Schema}"."{TickerAPI.Table}" WHERE "UID" = \'DELETE_ME\'')).commit()
    res_sec = db.executeone(QueryAPI(f'SELECT count(*) FROM "{UniverseAPI.Schema}"."{SecurityAPI.Table}" WHERE "Ticker" = \'DELETE_ME\'')).fetchall(legacy=False).row(0)[0]
    res_con = db.executeone(QueryAPI(f'SELECT count(*) FROM "{UniverseAPI.Schema}"."{ContractAPI.Table}" WHERE "Ticker" = \'DELETE_ME\'')).fetchall(legacy=False).row(0)[0]
    assert res_sec == 0
    assert res_con == 0