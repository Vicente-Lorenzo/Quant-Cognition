from datetime import datetime

import pytest

from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI

@pytest.fixture(autouse=True)
def setup_universe(db):
    for kind in (CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI): db.migrate(schema=UniverseAPI.Schema, table=kind.Table, structure=kind(db=db).Structure)
    yield db
    for kind in (ContractAPI, SecurityAPI, TickerAPI, ProviderAPI, CategoryAPI): db.executeone(QueryAPI(f'TRUNCATE TABLE "{UniverseAPI.Schema}"."{kind.Table}" CASCADE')).commit()

def test_universe_constants():
    assert UniverseAPI.Database == "Tests"
    assert UniverseAPI.Schema == "Universe"

def test_bulk_population_integrity(db):
    UniverseAPI.push_categories(db, pl.DataFrame([{"UID": "Cat1", "Primary": "P", "Secondary": "S", "Alternative": "A"}]))
    UniverseAPI.push_providers(db, pl.DataFrame([{"UID": "Prov1", "Platform": "cTrader", "Name": "N", "Abbreviation": "A"}]))
    UniverseAPI.push_tickers(db, pl.DataFrame([{"UID": "T1", "Category": "Cat1", "BaseAsset": "B", "QuoteAsset": "Q"}]))
    UniverseAPI.push_securities(db, pl.DataFrame([{"Provider": "Prov1", "Ticker": "T1", "Type": "Spot", "Symbol": 9, "Status": "Enabled", "Tracked": False}]))
    uid = UniverseAPI.pull_securities(db).row(0, named=True)["UID"]
    UniverseAPI.push_contracts(db, pl.DataFrame([{"Security": uid, "Timestamp": datetime(2026, 9, 1), "PipSize": 0.0001}]))
    assert len(UniverseAPI.pull_contracts(db)) == 1
    security = SecurityAPI(UID=uid, db=db, autoload=True)
    assert security.Ticker.UID == "T1" and security.Provider.UID == "Prov1" and security.Category.UID == "Cat1" and security.Contract.PipSize == 0.0001

def test_ticker_detection_logic():
    assert TickerAPI.detect("EURUSD") == ContractType.Spot
    assert TickerAPI.detect("AAPL.US") == ContractType.Spot
    assert TickerAPI.detect("ESH4") == ContractType.Future
    assert TickerAPI.detect("ESH24") == ContractType.Future
    assert TickerAPI.detect("CLF25") == ContractType.Future

def test_an_index_name_ending_like_a_month_code_is_not_a_future():
    assert TickerAPI.normalize("SPAIN 35") == "SPAIN35" and TickerAPI.detect("SPAIN35") == ContractType.Spot
    assert TickerAPI.normalize("HONG KONG 50") == "HONGKONG50"
    assert TickerAPI.normalize("ESZ4") == "ES" and TickerAPI.normalize("6EZ4") == "6E"

def test_referential_integrity_cascade(db):
    CategoryAPI(UID="Forex", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save()
    TickerAPI(UID="DELETEME", Category="Forex", BaseAsset="DEL", QuoteAsset="USD", db=db).save()
    ProviderAPI(UID="TestProv", Platform=Platform.API, Name="Test", Abbreviation="T", db=db).save()
    security = SecurityAPI(Ticker="DELETEME", Provider="TestProv", db=db)
    security.save()
    ContractAPI(Security=security.UID, Timestamp=datetime(2026, 9, 1), db=db).save()
    db.executeone(QueryAPI(f'DELETE FROM "{UniverseAPI.Schema}"."{TickerAPI.Table}" WHERE "UID" = \'DELETEME\'')).commit()
    assert db.executeone(QueryAPI(f'SELECT count(*) FROM "{UniverseAPI.Schema}"."{SecurityAPI.Table}" WHERE "Ticker" = \'DELETEME\'')).fetchall(legacy=False).item() == 0
    assert db.executeone(QueryAPI(f'SELECT count(*) FROM "{UniverseAPI.Schema}"."{ContractAPI.Table}" WHERE "Security" = :uid:'), uid=security.UID).fetchall(legacy=False).item() == 0

@pytest.mark.parametrize("primary, base, quote, country, expected", [
    ("Forex", "EUR", "USD", None, "Forex(Major)"),
    ("Forex", "USD", "JPY", None, "Forex(Major)"),
    ("Forex", "EUR", "GBP", None, "Forex(Minor)"),
    ("Forex", "NZD", "CAD", None, "Forex(Minor)"),
    ("Forex", "USD", "TRY", None, "Forex(Exotic)"),
    ("Forex", "SGD", "JPY", None, "Forex(Exotic)"),
    ("Metal", "XAU", "USD", None, "Metal(Major)"),
    ("Metal", "XAG", "EUR", None, "Metal(Major)"),
    ("Metal", "XAU", "JPY", None, "Metal(Minor)"),
    ("Crypto", "BTC", "EUR", None, "Crypto(Major)"),
    ("Crypto", "SOL", "USD", None, "Crypto(Minor)"),
    ("Energy", "WTI", "USD", None, "Energy(Major)"),
    ("Index", "US500", "USD", None, "Index(AMER)Equity"),
    ("Index", "GER40", "EUR", None, "Index(EMEA)Equity"),
    ("Index", "JP225", "JPY", None, "Index(APAC)Equity"),
    ("Index", "USD", "INDEX", None, "Index(AMER)Currency"),
    ("Stock", "SIEGn_DE", "EUR", "Germany", "Stock(Germany)"),
    ("ETF", "Stock1450", "USD", "United States", "ETF(United States)"),
    ("Bond", "X", "USD", None, "Bond")])
def test_a_new_ticker_is_classified_by_the_rules(primary, base, quote, country, expected):
    assert CategoryAPI.classify(primary, base=base, quote=quote, country=country).UID == expected

def test_a_classification_fills_every_column():
    category = CategoryAPI.classify("Forex", base="EUR", quote="USD")
    assert (category.Primary, category.Secondary, category.Alternative) == ("Forex", "Major", "Currency")