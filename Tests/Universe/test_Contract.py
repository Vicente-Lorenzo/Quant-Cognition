from datetime import datetime

import pytest

from Library.Universe.Universe import UniverseAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Contract import CommissionMode, ContractAPI, SwapMode
from Library.Utility.Datetime import Weekday
from Library.Utility.IO import read_yaml, write_yaml

def test_contract_initialization(db):
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    CategoryAPI(UID="Forex(Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save()
    ProviderAPI(UID="PepperstoneEurope", Platform=Platform.cTrader, Name="Pepperstone Europe", Abbreviation="Pepperstone", db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex(Major)", BaseAsset="EUR", QuoteAsset="USD", db=db).save()
    contract = ContractAPI(Ticker="oanda:eurusd.m", Provider="Pepperstone-Europe", Type=ContractType.Spot, db=db)
    assert contract.Ticker.UID == "EURUSD"
    assert contract.Provider.UID == "PepperstoneEurope"
    assert contract.Type == ContractType.Spot

def _spot_(ticker="EURUSD", swap_long=-2.445):
    return ContractAPI(Ticker=ticker, Provider="Spotware(cTrader)", Type=ContractType.Spot, Digits=5, PointSize=0.00001, PipSize=0.0001, LotSize=100000,
                       VolumeMin=1000.0, VolumeMax=10000000.0, VolumeStep=1000.0, CommissionMode=CommissionMode.BaseAssetPerMillionVolume, Commission=45.0,
                       SwapMode=SwapMode.Pips, SwapLong=swap_long, SwapShort=-0.105, SwapExtraDay=Weekday.Wednesday, UpdatedAt=datetime(2026, 9, 10, 18, 30), UpdatedBy="Autosave")

def test_a_snapshot_lists_identity_then_every_term_then_provenance():
    snapshot = _spot_().snapshot()
    assert list(snapshot)[:4] == ["Provider", "Ticker", "Type", "Digits"]
    assert list(snapshot)[-2:] == ["UpdatedAt", "UpdatedBy"]
    assert snapshot["Type"] == "Spot" and snapshot["CommissionMode"] == "BaseAssetPerMillionVolume" and snapshot["SwapExtraDay"] == "Wednesday"
    assert snapshot["SwapLong"] == -2.445 and snapshot["UpdatedBy"] == "Autosave"

def test_a_pin_restores_every_term_through_a_yaml_file(tmp_path):
    write_yaml(tmp_path / "Contract.yml", _spot_(swap_long=-9.0).snapshot(), safe=False)
    contract = _spot_().pin(read_yaml(tmp_path / "Contract.yml", safe=False))
    assert contract.snapshot() == _spot_(swap_long=-9.0).snapshot()
    assert contract.SwapExtraDay is Weekday.Wednesday and contract.CommissionMode is CommissionMode.BaseAssetPerMillionVolume

def test_a_pin_refuses_missing_and_unknown_terms():
    snapshot = _spot_().snapshot()
    del snapshot["SwapLong"]
    snapshot["Spread"] = 0.5
    with pytest.raises(ValueError, match="Missing SwapLong · Unknown Spread"):
        _spot_().pin(snapshot)

def test_a_pin_refuses_the_terms_of_another_contract():
    with pytest.raises(ValueError, match="Due to another contract · Ticker USDJPY Against EURUSD"):
        _spot_().pin(_spot_(ticker="USDJPY").snapshot())

def test_a_pin_refuses_an_enum_name_it_cannot_parse():
    snapshot = _spot_().snapshot()
    snapshot["CommissionMode"] = "BaseAssetPerMillion"
    with pytest.raises(ValueError, match="Unknown CommissionMode BaseAssetPerMillion · Expected one of BaseAssetPerMillionVolume"):
        _spot_().pin(snapshot)