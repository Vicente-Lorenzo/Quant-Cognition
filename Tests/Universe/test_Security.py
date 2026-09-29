from datetime import datetime

import pytest

from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Security import SecurityAPI, SecurityStatus
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI

@pytest.fixture
def stored(db):
    for kind in (CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI): db.migrate(schema=UniverseAPI.Schema, table=kind.Table, structure=kind(db=db).Structure)
    CategoryAPI(UID="Forex(Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save()
    ProviderAPI(UID="ProbeMarketsEU", Platform=Platform.cTrader, Name="Probe Markets EU", Abbreviation="ProbeMarkets", db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex(Major)", BaseAsset="EUR", QuoteAsset="USD", db=db).save()
    security = SecurityAPI(Ticker="EURUSD", Provider="ProbeMarketsEU", Type=ContractType.Spot, Symbol=7, Status=SecurityStatus.Enabled, Tracked=False, db=db)
    security.save()
    return db, security

def test_a_security_normalizes_what_names_it(stored):
    db, _ = stored
    security = SecurityAPI(Ticker="oanda:eurusd.m", Provider="Probe-Markets-EU", db=db, autoload=True)
    assert security.Ticker.UID == "EURUSD" and security.Provider.UID == "ProbeMarketsEU"
    assert security.Type is ContractType.Spot and security.Symbol == 7 and security.Status is SecurityStatus.Enabled and security.Tracked is False

def test_a_security_reads_its_category_through_its_ticker(stored):
    db, security = stored
    assert SecurityAPI(UID=security.UID, db=db, autoload=True).Category.UID == "Forex(Major)"

def test_a_lookup_that_misses_is_refused_and_named(stored):
    db, _ = stored
    TickerAPI(UID="GBPUSD", Category="Forex(Major)", BaseAsset="GBP", QuoteAsset="USD", db=db).save()
    with pytest.raises(LookupError, match="ProbeMarketsEU GBPUSD is not in the Universe"):
        SecurityAPI(Ticker="GBPUSD", Provider="ProbeMarketsEU", db=db, autoload=True)

def test_a_security_without_stored_terms_has_no_contract(stored):
    db, security = stored
    db.remove(schema=UniverseAPI.Schema, table=ContractAPI.Table, condition='"Security" = :security:', parameters={"security": security.UID})
    assert SecurityAPI(UID=security.UID, db=db, autoload=True).Contract is None

def test_an_attached_contract_answers_for_its_security():
    contract = ContractAPI(Timestamp=datetime(2026, 9, 1), PipSize=0.0001)
    security = SecurityAPI(UID=5, Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Contract=contract)
    assert security.Contract is contract and contract.Security == 5 and contract.Type is ContractType.Spot