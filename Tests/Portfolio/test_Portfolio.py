import pytest
from datetime import datetime

from Library.Database.Query import QueryAPI
from Library.Market.Price import Direction
from Library.Portfolio.Account import AccountAPI, AccountType, MarginMode, Environment
from Library.Portfolio.Cashflow import CashflowAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Universe import UniverseAPI

@pytest.fixture
def mirror(db):
    for kind in (CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI): db.migrate(schema=UniverseAPI.Schema, table=kind.Table, structure=kind(db=db).Structure)
    for kind in (AccountAPI, OrderAPI, PositionAPI, TradeAPI, CashflowAPI): db.migrate(schema=kind.Schema, table=kind.Table, structure=kind(db=db).Structure)
    for kind in (CashflowAPI, TradeAPI, PositionAPI, OrderAPI, AccountAPI): db.executeone(QueryAPI(f'DELETE FROM "{kind.Schema}"."{kind.Table}"')).commit()
    CategoryAPI(UID="Forex(Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save()
    ProviderAPI(UID="Spotware(cTrader)", Platform=Platform.cTrader, Name="Spotware", Abbreviation="Spotware", db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex(Major)", BaseAsset="EUR", QuoteAsset="USD", db=db).save()
    security = SecurityAPI(Ticker="EURUSD", Provider="Spotware(cTrader)", Type=ContractType.Spot, Symbol=1, db=db)
    security.save()
    yield db, security
    for kind in (CashflowAPI, TradeAPI, PositionAPI, OrderAPI, AccountAPI): db.executeone(QueryAPI(f'DELETE FROM "{kind.Schema}"."{kind.Table}"')).commit()

def test_an_account_is_keyed_by_the_broker_and_carries_its_tracking(mirror):
    db, _ = mirror
    AccountAPI(UID=5804942, Provider="Spotware(cTrader)", Number=2024, Timestamp=datetime(2026, 9, 27), Environment=Environment.Demo, AccountType=AccountType.Hedged,
               MarginMode=MarginMode.Max, Asset="EUR", Balance=10000.0, Leverage=30.0, Tracked=True, db=db).save()
    account = AccountAPI(UID=5804942, db=db, autoload=True)
    assert account.Provider.UID == "Spotware(cTrader)" and account.Environment is Environment.Demo and account.IsHedged
    assert account.Balance == 10000.0 and account.Tracked is True and account.Asset == "EUR"

def test_positions_trades_and_cash_flows_round_trip_by_broker_id(mirror):
    db, security = mirror
    AccountAPI(UID=7, Provider="Spotware(cTrader)", Timestamp=datetime(2026, 9, 27), Balance=10000.0, Tracked=True, db=db).save()
    entry, exit = datetime(2026, 9, 25, 10), datetime(2026, 9, 25, 12)
    PositionAPI(UID=1001, Account=7, Security=security.UID, Type=PositionType.Normal, Direction=Direction.Buy, Volume=100000, EntryTimestamp=entry, EntryPrice=1.05, StopLossPrice=1.045, Label="Run-1", db=db).save()
    TradeAPI(UID=2001, Account=7, Position=1001, Security=security.UID, Type=PositionType.Normal, Direction=Direction.Buy, Volume=50000, EntryTimestamp=entry, EntryPrice=1.05,
             ExitTimestamp=exit, ExitPrice=1.055, GrossPnL=250.0, CommissionPnL=-2.5, SwapPnL=0.0, NetPnL=247.5, ExitBalance=10247.5, Label="Run-1", db=db).save()
    CashflowAPI(UID=31, Account=7, Timestamp=datetime(2026, 9, 1), Type="Deposit", Delta=10000.0, Balance=10000.0, db=db).save()
    position = PositionAPI(UID=1001, db=db, autoload=True)
    trade = TradeAPI(UID=2001, db=db, autoload=True)
    flow = CashflowAPI(UID=31, db=db, autoload=True)
    assert position.Account.UID == 7 and position.Security.UID == security.UID and position.EntryPrice.Price == pytest.approx(1.05) and position.Label == "Run-1"
    assert trade.Position.UID == 1001 and trade.NetPnL.PnL == pytest.approx(247.5) and trade.ExitBalance == pytest.approx(10247.5)
    assert flow.Delta == 10000.0 and flow.Account == 7

def test_a_trade_outlives_its_closed_position(mirror):
    db, security = mirror
    AccountAPI(UID=8, Provider="Spotware(cTrader)", Timestamp=datetime(2026, 9, 27), Tracked=True, db=db).save()
    PositionAPI(UID=1002, Account=8, Security=security.UID, Direction=Direction.Sell, Volume=1000, EntryTimestamp=datetime(2026, 9, 25), EntryPrice=1.1, db=db).save()
    TradeAPI(UID=2002, Account=8, Position=1002, Security=security.UID, Direction=Direction.Sell, Volume=1000, EntryTimestamp=datetime(2026, 9, 25), EntryPrice=1.1,
             ExitTimestamp=datetime(2026, 9, 26), ExitPrice=1.09, NetPnL=10.0, db=db).save()
    db.remove(schema=PositionAPI.Schema, table=PositionAPI.Table, condition='"UID" = :uid:', parameters={"uid": 1002})
    assert TradeAPI(UID=2002, db=db, autoload=True).NetPnL.PnL == pytest.approx(10.0)

def test_the_portfolio_tables_carry_no_session():
    for kind in (AccountAPI, OrderAPI, PositionAPI, TradeAPI):
        assert "Session" not in [str(name) for name in kind(db=None).Structure]