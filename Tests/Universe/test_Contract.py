from Library.Universe.Universe import UniverseAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Universe.Contract import ContractAPI

def test_contract_initialization(db):
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    try:
        contract = ContractAPI(Ticker="oanda:eurusd.m", Provider="Pepperstone-Europe", Type=ContractType.Spot, db=db)
        assert contract.Ticker.UID == "EURUSD"
        assert contract.Provider.UID == "Pepperstone Europe"
        assert contract.Type == ContractType.Spot
    except ValueError:
        pass