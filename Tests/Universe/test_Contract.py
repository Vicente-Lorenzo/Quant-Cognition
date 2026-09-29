from datetime import datetime

import pytest

from Library.Universe.Universe import UniverseAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import CommissionMode, ContractAPI, SwapMode, TradingMode
from Library.Utility.Datetime import Weekday
from Library.Utility.IO import read_yaml, write_yaml

def _stored_(db):
    for kind in (CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI): db.migrate(schema=UniverseAPI.Schema, table=kind.Table, structure=kind(db=db).Structure)
    db.remove(schema=UniverseAPI.Schema, table=ContractAPI.Table)
    CategoryAPI(UID="Forex(Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save()
    ProviderAPI(UID="Spotware(cTrader)", Platform=Platform.cTrader, Name="Spotware", Abbreviation="Spotware", db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex(Major)", BaseAsset="EUR", QuoteAsset="USD", db=db).save()
    security = SecurityAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Symbol=1, db=db)
    security.save()
    return security

def _terms_(swap_long=-2.445) -> dict:
    return {"Digits": 5, "PointSize": 0.00001, "PipSize": 0.0001, "LotSize": 100000, "VolumeMin": 1000.0, "VolumeMax": 10000000.0, "VolumeStep": 1000.0,
            "CommissionMode": "BaseAssetPerMillionVolume", "Commission": 45.0, "SwapMode": "Pips", "SwapLong": swap_long, "SwapShort": -0.105, "SwapPeriod": 24,
            "SwapTime": 1259, "SwapExtraDay": "Wednesday", "SwapWeekends": False, "TradingMode": "Enabled"}

def _spot_(ticker="EURUSD", swap_long=-2.445):
    contract = ContractAPI(Timestamp=datetime(2026, 9, 10, 18, 30), **_terms_(swap_long), UpdatedAt=datetime(2026, 9, 10, 18, 30), UpdatedBy="Autosave")
    SecurityAPI(Ticker=ticker, Provider="Spotware(cTrader)", Type=ContractType.Spot, Contract=contract)
    return contract

def test_a_contract_takes_its_identity_from_its_security():
    contract = _spot_()
    assert contract.Type == ContractType.Spot and contract.IsSpot and contract.IsLinear and not contract.IsDerivative
    assert contract.CommissionMode is CommissionMode.BaseAssetPerMillionVolume and contract.SwapMode is SwapMode.Pips
    assert contract.SwapExtraDay is Weekday.Wednesday and contract.TradingMode is TradingMode.Enabled

def test_a_snapshot_lists_identity_then_every_term_then_provenance():
    snapshot = _spot_().snapshot()
    assert list(snapshot)[:4] == ["Provider", "Ticker", "Type", "Digits"]
    assert list(snapshot)[-3:] == ["Timestamp", "UpdatedAt", "UpdatedBy"]
    assert snapshot["Type"] == "Spot" and snapshot["CommissionMode"] == "BaseAssetPerMillionVolume" and snapshot["SwapExtraDay"] == "Wednesday"
    assert snapshot["SwapLong"] == -2.445 and snapshot["SwapTime"] == 1259 and snapshot["UpdatedBy"] == "Autosave"
    assert "SwapSummerTime" not in snapshot and "SwapWinterTime" not in snapshot

def test_a_pin_restores_every_term_through_a_yaml_file(tmp_path):
    write_yaml(tmp_path / "Contract.yml", _spot_(swap_long=-9.0).snapshot(), safe=False)
    contract = _spot_().pin(read_yaml(tmp_path / "Contract.yml", safe=False))
    assert contract.snapshot() == _spot_(swap_long=-9.0).snapshot()
    assert contract.SwapExtraDay is Weekday.Wednesday and contract.CommissionMode is CommissionMode.BaseAssetPerMillionVolume

def test_a_pin_refuses_missing_and_unknown_terms():
    snapshot = _spot_().snapshot()
    del snapshot["SwapLong"]
    snapshot["SwapSummerTime"] = 22
    with pytest.raises(ValueError, match="Missing SwapLong · Unknown SwapSummerTime"):
        _spot_().pin(snapshot)

def test_a_pin_refuses_the_terms_of_another_contract():
    with pytest.raises(ValueError, match="Due to another contract · Ticker USDJPY Against EURUSD"):
        _spot_().pin(_spot_(ticker="USDJPY").snapshot())

def test_a_pin_refuses_an_enum_name_it_cannot_parse():
    snapshot = _spot_().snapshot()
    snapshot["CommissionMode"] = "BaseAssetPerMillion"
    with pytest.raises(ValueError, match="Unknown CommissionMode BaseAssetPerMillion · Expected one of BaseAssetPerMillionVolume"):
        _spot_().pin(snapshot)

def test_a_revision_is_written_only_when_a_term_changes(db):
    security = _stored_(db)
    first = ContractAPI.revise(db, security.UID, _terms_(), datetime(2026, 9, 1), "Universe")
    assert first is not None
    assert ContractAPI.revise(db, security.UID, _terms_(), datetime(2026, 9, 2), "Universe") is None
    assert ContractAPI.revise(db, security.UID, _terms_(swap_long=-2.5), datetime(2026, 9, 3), "Universe") is not None
    assert [row.SwapLong for row in ContractAPI.history(db, security.UID)] == [-2.445, -2.5]

def test_the_terms_on_a_date_are_the_newest_row_at_or_before_it(db):
    security = _stored_(db)
    ContractAPI.revise(db, security.UID, _terms_(), datetime(2026, 9, 1), "Universe")
    ContractAPI.revise(db, security.UID, _terms_(swap_long=-2.5), datetime(2026, 9, 3), "Universe")
    assert ContractAPI.current(db, security.UID).SwapLong == -2.5
    assert ContractAPI.current(db, security.UID, datetime(2026, 9, 2)).SwapLong == -2.445
    assert ContractAPI.current(db, security.UID, datetime(2026, 8, 31)) is None

def test_a_loaded_security_carries_its_newest_contract(db):
    security = _stored_(db)
    ContractAPI.revise(db, security.UID, _terms_(), datetime(2026, 9, 1), "Universe")
    ContractAPI.revise(db, security.UID, _terms_(swap_long=-2.5), datetime(2026, 9, 3), "Universe")
    loaded = SecurityAPI(Provider="Spotware", Ticker="EURUSD", db=db, autoload=True)
    assert loaded.Contract.SwapLong == -2.5 and loaded.Contract.Type == ContractType.Spot
    assert loaded.Contract.snapshot()["Ticker"] == "EURUSD" and loaded.Category.UID == "Forex(Major)"