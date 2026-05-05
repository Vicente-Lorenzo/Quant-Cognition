from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Security import SecurityAPI
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Category import CategoryAPI
from Library.Database.Datapoint import DatapointAPI
def test_security_initialization(db):
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    try:
        sec = SecurityAPI(Ticker="oanda:eurusd.m", Provider="Pepperstone-Europe", Contract=ContractType.Spot, db=db)
        assert sec.Ticker.UID == "EURUSD"
        assert sec.Provider.UID == "Pepperstone Europe"
        assert sec.Contract.Type == ContractType.Spot
    except ValueError:
        pass