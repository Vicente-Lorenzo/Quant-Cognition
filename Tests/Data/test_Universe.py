import pytest
from datetime import datetime

from Library.Database.Dataframe import pl
from Library.Data.Universe import UniverseServiceAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Ticker import TickerAPI

BROKER = "Sync Probe Markets"
PROVIDER = "SyncProbeMarkets(cTrader)"

def symbol(uid: int, ticker: str, primary: str, base: str, quote: str, status: str = "Enabled", swap: float = -2.5) -> dict:
    return {"Symbol": uid, "Ticker": ticker, "Description": f"{base} vs {quote}", "Primary": primary, "Type": "Spot" if primary == "Forex" else "CFD", "Country": None,
            "BaseAsset": base, "BaseName": base, "QuoteAsset": quote, "QuoteName": quote, "Status": status, "Digits": 5, "PointSize": 1e-05, "PipSize": 0.0001, "LotSize": 100000,
            "VolumeMin": 1000.0, "VolumeMax": 1e7, "VolumeStep": 1000.0, "CommissionMode": "BaseAssetPerMillionVolume", "Commission": 45.0, "SwapMode": "Pips", "SwapLong": swap,
            "SwapShort": -0.1, "SwapPeriod": 24, "SwapTime": 1259, "SwapExtraDay": "Wednesday", "SwapWeekends": False, "TradingMode": "Enabled"}

def catalog(*rows: dict) -> pl.DataFrame:
    return pl.DataFrame(list(rows), infer_schema_length=None)

@pytest.fixture(scope="module")
def synced(universe, db):
    first = UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD"), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR"), symbol(9003, "OLDXYZ", "Forex", "OLD", "XYZ", status="Archived")), at=datetime(2026, 9, 1))
    return db, first

def securities(db) -> dict:
    return {row["Ticker"]: row for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition='"Provider" = :provider:', parameters={"provider": PROVIDER})}

def test_a_first_sync_registers_the_provider_its_current_symbols_and_their_terms(synced):
    db, outcome = synced
    assert outcome == {"Provider": PROVIDER, "Symbols": 2, "Created": 1, "Revised": 2, "Archived": 0}
    rows = securities(db)
    assert sorted(rows) == ["EURUSD", "XAUEUR"]
    assert not any(row["Tracked"] for row in rows.values())
    assert ContractAPI.current(db, rows["EURUSD"]["UID"]).SwapLong == -2.5

def test_a_new_ticker_is_classified_and_an_existing_one_keeps_its_category(synced):
    db, _ = synced
    tickers = {row["UID"]: row["Category"] for row in db.records(schema=TickerAPI.Schema, table=TickerAPI.Table)}
    assert tickers["XAUEUR"] == "Metal(Major)"
    assert tickers["EURUSD"] == "Forex(Major)"
    assert db.first(schema=CategoryAPI.Schema, table=CategoryAPI.Table, condition='"UID" = :uid:', parameters={"uid": "Metal(Major)"})["Alternative"] == "Commodity"

def test_an_unchanged_catalog_revises_nothing_and_keeps_every_uid(synced):
    db, _ = synced
    before = {ticker: row["UID"] for ticker, row in securities(db).items()}
    again = UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD"), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR")), at=datetime(2026, 9, 2))
    assert again["Revised"] == 0 and again["Created"] == 0
    assert {ticker: row["UID"] for ticker, row in securities(db).items()} == before

def test_a_changed_term_adds_one_dated_row_and_the_old_terms_stay_readable(synced):
    db, _ = synced
    uid = securities(db)["EURUSD"]["UID"]
    changed = UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD", swap=-3.1), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR")), at=datetime(2026, 9, 3))
    assert changed["Revised"] == 1
    history = ContractAPI.history(db, uid)
    assert [revision.SwapLong for revision in history] == [-2.5, -3.1]
    assert ContractAPI.current(db, uid, at=datetime(2026, 9, 2)).SwapLong == -2.5

def test_a_category_chosen_by_hand_survives_the_next_sync(synced):
    db, _ = synced
    CategoryAPI.store(db, "Probe", "Hand", None, "Tester")
    assert TickerAPI.categorize(db, ["XAUEUR"], "Probe(Hand)", "Tester") == 1
    UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD", swap=-3.1), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR")), at=datetime(2026, 9, 4))
    assert db.first(schema=TickerAPI.Schema, table=TickerAPI.Table, condition='"UID" = :uid:', parameters={"uid": "XAUEUR"})["Category"] == "Probe(Hand)"

def test_an_unknown_category_is_refused(synced):
    db, _ = synced
    with pytest.raises(ValueError, match="Unknown category"): TickerAPI.categorize(db, ["XAUEUR"], "Nowhere(Nothing)", "Tester")

def test_tracking_is_the_users_column_and_a_sync_never_resets_it(synced):
    db, _ = synced
    uid = securities(db)["XAUEUR"]["UID"]
    assert SecurityAPI.track(db, [uid], True, "Tester") == 1
    UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD", swap=-3.1), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR")), at=datetime(2026, 9, 5))
    assert securities(db)["XAUEUR"]["Tracked"] is True
    SecurityAPI.track(db, [uid], False, "Tester")
    assert securities(db)["XAUEUR"]["Tracked"] is False

def test_an_archived_symbol_is_marked_archived_and_leaves_the_current_set(synced):
    db, _ = synced
    outcome = UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD", swap=-3.1, status="Archived"), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR")), at=datetime(2026, 9, 6))
    assert outcome["Archived"] == 1 and outcome["Symbols"] == 1
    assert securities(db)["EURUSD"]["Status"] == "Archived"

def test_the_overview_joins_each_security_to_its_latest_terms(synced):
    db, _ = synced
    frame = SecurityAPI.overview(db).filter(pl.col("Provider") == PROVIDER)
    rows = {row["Ticker"]: row for row in frame.to_dicts()}
    assert rows["EURUSD"]["SwapLong"] == -3.1 and rows["EURUSD"]["Terms"] == datetime(2026, 9, 3)
    assert rows["XAUEUR"]["Category"] == "Probe(Hand)"

def test_a_new_category_needs_a_primary_class(db, universe):
    with pytest.raises(ValueError, match="primary class"): CategoryAPI.store(db, "  ", "Minor", None, "Tester")
    assert CategoryAPI.store(db, "Commodity", None, None, "Tester") == "Commodity"
def test_an_existing_ticker_without_a_category_gets_the_default_one(synced):
    db, _ = synced
    db.upsert(schema=TickerAPI.Schema, table=TickerAPI.Table, data=[{"UID": "USDZZZ", "Category": None, "UpdatedBy": "Tester"}], key=["UID"])
    UniverseServiceAPI.sync(db, BROKER, catalog(symbol(9001, "EURUSD", "Forex", "EUR", "USD", swap=-3.1, status="Archived"), symbol(9002, "XAUEUR", "Metal", "XAU", "EUR"), symbol(9004, "USDZZZ", "Forex", "USD", "ZZZ")), at=datetime(2026, 9, 7))
    assert db.first(schema=TickerAPI.Schema, table=TickerAPI.Table, condition='"UID" = :uid:', parameters={"uid": "USDZZZ"})["Category"] == "Forex(Exotic)"