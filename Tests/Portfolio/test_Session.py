from datetime import datetime
from Library.Database import BufferAPI
from Library.Database.Query import QueryAPI
from Library.Portfolio.Account import AccountAPI, AccountType, MarginMode, Environment
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Market.Price import Direction
from Library.System.System import SystemType
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Security import SecurityAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Universe import UniverseAPI

def _setup_(db):
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ContractAPI.Table, structure=ContractAPI(db=None).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=SecurityAPI.Table, structure=SecurityAPI(db=None).Structure)
    db.migrate(schema=SessionAPI.Schema, table=SessionAPI.Table, structure=SessionAPI(db=None).Structure)
    db.migrate(schema=AccountAPI.Schema, table=AccountAPI.Table, structure=AccountAPI(db=None).Structure)
    db.migrate(schema=OrderAPI.Schema, table=OrderAPI.Table, structure=OrderAPI(db=None).Structure)
    db.migrate(schema=PositionAPI.Schema, table=PositionAPI.Table, structure=PositionAPI(db=None).Structure)
    db.migrate(schema=TradeAPI.Schema, table=TradeAPI.Table, structure=TradeAPI(db=None).Structure)
    db.executeone(QueryAPI(f'DELETE FROM "{TradeAPI.Schema}"."{TradeAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{PositionAPI.Schema}"."{PositionAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{OrderAPI.Schema}"."{OrderAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{AccountAPI.Schema}"."{AccountAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{SessionAPI.Schema}"."{SessionAPI.Table}"')).commit()
    CategoryAPI(UID="Forex(Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save()
    ProviderAPI(UID="Pepperstone(cTrader)", Platform=Platform.cTrader, Name="Pepperstone Europe", Abbreviation="Pepperstone", db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex(Major)", BaseAsset="EUR", BaseName="Euro", QuoteAsset="USD", QuoteName="US Dollar", Description="Euro vs US Dollar", db=db).save()
    ContractAPI(Ticker="EURUSD", Provider="Pepperstone(cTrader)", Type=ContractType.Spot, PipSize=0.0001, PointSize=0.00001, Digits=5, LotSize=100000, db=db).save()
    sec = SecurityAPI(Ticker="EURUSD", Provider="Pepperstone(cTrader)", Contract=ContractType.Spot, Category="Forex(Major)", db=db)
    sec.save()
    return sec

def test_session_auto_generates_iid(db):
    _setup_(db)
    s = SessionAPI(Type=SystemType.Backtesting, Strategy="NNFX", db=db)
    assert s.UID is not None
    assert s.UID.startswith("Backtesting-")
    s.save()
    assert s.UID is not None

def test_session_preserves_explicit_iid(db):
    _setup_(db)
    s = SessionAPI(UID="EXPLICIT-001", Type=SystemType.Live, Strategy="NNFX", db=db)
    assert s.UID == "EXPLICIT-001"
    s.save()
    assert s.UID is not None

def test_buffer_chain_session_account_position(db):
    sec = _setup_(db)
    session = SessionAPI(UID="CHAIN-001", Type=SystemType.Testing, Strategy="NNFX", Security=sec, StartTimestamp=datetime(2025, 1, 1, 12, 0, 0), db=db)
    session.save()
    account = AccountAPI(Timestamp=datetime(2025, 1, 1, 12, 0, 1), Session=session, Environment=Environment.Demo, AccountType=AccountType.Hedged, MarginMode=MarginMode.Net, Asset="USD", Balance=10000.0, Equity=10000.0, db=db)
    position = PositionAPI(UID=5001, Security=sec, Session=session, Account=account, Type=PositionType.Normal, Direction=Direction.Buy, Volume=100000, Quantity=1.0, EntryTimestamp=datetime(2025, 1, 1, 12, 0, 2), EntryPrice=1.10, EntryBalance=10000.0)
    buf = BufferAPI(types=[AccountAPI, OrderAPI, PositionAPI, TradeAPI], batch=10, interval=0.0, workers=1, db=lambda: db)
    buf.add(account)
    buf.add(position)
    buf.flush()
    buf._consume_(db)
    assert account.UID is not None
    assert position.UID is not None
    row = db.select(schema=PositionAPI.Schema, table=PositionAPI.Table, condition='"UID" = :uid:', parameters={"uid": position.UID}, limit=1, legacy=False)
    assert not row.is_empty()
    persisted = row.row(0, named=True)
    assert persisted["Session"] == session.UID
    assert persisted["Account"] == account.UID
