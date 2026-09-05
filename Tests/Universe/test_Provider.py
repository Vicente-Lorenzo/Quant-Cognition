from Library.Universe.Provider import ProviderAPI, Platform

def test_provider_normalize():
    assert ProviderAPI.normalize("Pepperstone-Europe") == "PepperstoneEurope"
    assert ProviderAPI.normalize("IC Markets EU Ltd") == "ICMarketsEULtd"
    assert ProviderAPI.normalize("IC Markets-Demo") == "ICMarkets"
    assert ProviderAPI.normalize("IC-Markets-Demo") == "ICMarkets"
    assert ProviderAPI.normalize("Bloomberg") == "Bloomberg"

def test_provider_initialization(db):
    prov = ProviderAPI(Abbreviation="Pepperstone", Platform=Platform.cTrader, db=db)
    assert prov.UID == "Pepperstone(cTrader)"
    assert prov.Platform == Platform.cTrader