import dash
import pytest
from datetime import datetime, timedelta

from Library.Auth import RoleAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Market.Download import DownloadAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Security import SecurityAPI
from Library.Universe.Ticker import TickerAPI, ContractType

PROVIDER = "PageProbe(cTrader)"

@pytest.fixture(scope="module")
def pages(application):
    return {name: application._pages_[f"/database/{name}/"] for name in ("universe", "market", "portfolio")}

@pytest.fixture
def listed():
    with PostgresDatabaseAPI(database="Tests") as db:
        for kind in (CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI, DownloadAPI): kind(db=db, migrate=True, autoload=False)
        CategoryAPI.store(db, "Forex", "Major", "Currency", "Tester")
        ProviderAPI(UID=PROVIDER, Platform=Platform.cTrader, Name="Page Probe", Abbreviation="PageProbe", db=db).save()
        TickerAPI(UID="PRBUSD", Category="Forex(Major)", BaseAsset="PRB", QuoteAsset="USD", Description="Probe vs US Dollar", db=db).save()
        security = SecurityAPI(Provider=PROVIDER, Ticker="PRBUSD", Type=ContractType.Spot, Symbol=424242, Status="Enabled", Tracked=True, db=db)
        security.save()
        ContractAPI(Security=security.UID, Timestamp=datetime(2026, 9, 1), Digits=5, PipSize=0.0001, LotSize=100000, db=db).save()
        try: yield db, security.UID
        finally:
            db.remove(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition='"Provider" = :provider:', parameters={"provider": PROVIDER})
            db.remove(schema=TickerAPI.Schema, table=TickerAPI.Table, condition='"UID" = :uid:', parameters={"uid": "PRBUSD"})
            db.remove(schema=ProviderAPI.Schema, table=ProviderAPI.Table, condition='"UID" = :uid:', parameters={"uid": PROVIDER})

@pytest.fixture
def notes(pages, monkeypatch):
    notes = []
    for page in pages.values():
        for level in ("error", "warning", "success"): monkeypatch.setattr(page.app.notify, level, lambda message, level=level, **kwargs: notes.append((level, message)))
    return notes

def test_the_section_replaces_the_framework_placeholder_and_each_page_has_its_audience(application, pages):
    assert "/framework/database/" not in application._pages_
    assert application._pages_["/database/"].access is RoleAPI.Viewer
    assert pages["universe"].access is RoleAPI.Viewer and pages["market"].access is RoleAPI.Viewer
    assert pages["portfolio"].access is RoleAPI.Editor

def test_the_universe_filters_by_provider_class_status_tracking_and_text(pages):
    row = {"Provider": "Pepperstone(cTrader)", "Category": "Forex(Major)", "Status": "Enabled", "Tracked": True, "Ticker": "EURUSD", "Description": "Euro vs US Dollar"}
    matches = pages["universe"]._matches_
    assert matches(row, None, None, None, None, None)
    assert matches(row, "Pepperstone(cTrader)", "Forex", "Enabled", "Tracked", "euro")
    assert not matches(row, "Other(cTrader)", None, None, None, None)
    assert not matches(row, None, "Metal", None, None, None)
    assert not matches(row, None, None, "Archived", None, None)
    assert not matches(row, None, None, None, "Untracked", None)
    assert not matches(row, None, None, None, None, "yen")

def test_the_universe_lists_a_providers_securities_with_their_latest_terms(pages, listed):
    rows = pages["universe"]._rows_(provider=PROVIDER)
    assert [(row["Ticker"], row["Tracked"], row["Pip"], row["Symbol"], row["Category"]) for row in rows] == [("PRBUSD", True, 0.0001, "424242", "Forex(Major)")]

def test_a_viewer_cannot_track_and_an_editor_can(pages, listed, notes, monkeypatch):
    (db, uid), page = listed, pages["universe"]
    tracked = lambda: db.first(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition='"UID" = :uid:', parameters={"uid": uid})["Tracked"]
    monkeypatch.setattr(page, "_permitted_", lambda role=RoleAPI.Editor: False)
    assert page._mark_({"selected": [str(uid)]}, False) is dash.no_update and tracked() is True
    monkeypatch.setattr(page, "_permitted_", lambda role=RoleAPI.Editor: True)
    monkeypatch.setattr(page.app, "actor", lambda: "editor@test.com")
    assert page._mark_({"selected": [str(uid)]}, False) is not dash.no_update and tracked() is False
    assert notes[-1][0] == "success"

def test_the_term_history_lists_each_change_newest_first(pages):
    first = ContractAPI(Timestamp=datetime(2026, 9, 1), SwapLong=-2.5, SwapShort=-0.1, SwapTime=1259, UpdatedBy="Universe")
    second = ContractAPI(Timestamp=datetime(2026, 9, 3), SwapLong=-3.1, SwapShort=-0.1, SwapTime=1319, UpdatedBy="Universe")
    rows = pages["universe"]._changes_([first, second])
    assert [(row["Term"], row["Before"], row["After"]) for row in rows[:2]] == [("Swap Long", -2.5, -3.1), ("Swap Time", "20:59 UTC", "21:59 UTC")]
    assert rows[-1]["Term"] == "Recorded" and rows[-1]["After"] == "3 Terms"

def test_a_feed_is_live_only_while_it_writes_today_and_lag_reads_in_units(pages):
    page, now = pages["market"], datetime(2026, 9, 28, 12)
    today = now.replace(hour=0)
    assert page._state_({"UpdatedAt": now - timedelta(seconds=5), "Through": now - timedelta(seconds=15), "Last": today}, now) == "Live"
    assert page._state_({"UpdatedAt": now - timedelta(seconds=5), "Through": today, "Last": today - timedelta(days=900)}, now) == "Backfilling"
    assert page._state_({"UpdatedAt": now - timedelta(hours=2), "Through": today, "Last": today}, now) == "Stopped"
    assert page._state_({}, now) == "Waiting"
    assert [page._lag_(now - timedelta(seconds=seconds), now) for seconds in (15, 600, 18_000, 900_000)] == ["15s", "10m", "5.0h", "10d"]

def test_a_month_cell_names_its_state(pages):
    cell, today = pages["market"]._cell_, datetime(2026, 9, 28)
    state = lambda row, month=datetime(2026, 3, 1): cell("EURUSD", month, row, today).className.split()[-1]
    assert state(None) == "is-none"
    assert state({"Complete": 22, "Empty": 9, "Failed": 0, "Live": 0, "Ticks": 1}) == "is-complete"
    assert state({"Complete": 0, "Empty": 31, "Failed": 0, "Live": 0, "Ticks": 0}) == "is-empty"
    assert state({"Complete": 10, "Empty": 3, "Failed": 0, "Live": 0, "Ticks": 1}) == "is-partial"
    assert state({"Complete": 20, "Empty": 3, "Failed": 1, "Live": 0, "Ticks": 1}) == "is-failed"
    assert state({"Complete": 20, "Empty": 6, "Failed": 0, "Live": 1, "Ticks": 1}, datetime(2026, 9, 1)) == "is-live"

def test_portfolio_filters_bind_their_values_and_leave_the_account_first(pages):
    condition, parameters = pages["portfolio"]._condition_(7, "3", "Run", datetime(2026, 9, 1), datetime(2026, 9, 2), "ExitTimestamp")
    assert condition == '"Account" = :account: AND "Security" = :security: AND "Label" = :label: AND "ExitTimestamp" >= :since: AND "ExitTimestamp" < :until:'
    assert parameters == {"account": 7, "security": 3, "label": "Run", "since": datetime(2026, 9, 1), "until": datetime(2026, 9, 2)}
    assert pages["portfolio"]._condition_(7, None, None, datetime(2026, 9, 1), None, None) == ('"Account" = :account:', {"account": 7})
    assert pages["portfolio"]._day_("2026-09-01", end=True) == datetime(2026, 9, 2)

def test_accounts_are_tracked_only_from_the_accounts_sheet(pages, notes, monkeypatch):
    page = pages["portfolio"]
    monkeypatch.setattr(page, "_permitted_", lambda role=RoleAPI.Editor: True)
    assert page._mark_({"sheet": "Trades", "selected": ["1"]}, True) is dash.no_update
    assert notes[-1] == ("warning", "Select accounts on the Accounts sheet first")

def test_drawing_needs_an_account(pages, notes):
    assert pages["portfolio"]._draw_(1, None, "", "H1") == (dash.no_update,) * 3
    assert notes[-1] == ("warning", "Choose an account first")

def test_identifiers_render_without_thousands_separators(pages):
    row = pages["portfolio"]._trade_({"UID": 335671634, "Position": 292866407, "Security": 1, "Direction": "Buy", "Volume": 0.01, "EntryTimestamp": None, "EntryPrice": None, "ExitTimestamp": None,
                                       "ExitPrice": None, "GrossPnL": None, "CommissionPnL": None, "SwapPnL": None, "NetPnL": None, "ExitBalance": None, "MaxEquityDrawdownPnL": None, "MaxEquityRunupPnL": None, "Label": None}, {1: "BTCUSD"})
    assert (row["UID"], row["Position"], row["Security"]) == ("335671634", "292866407", "BTCUSD")