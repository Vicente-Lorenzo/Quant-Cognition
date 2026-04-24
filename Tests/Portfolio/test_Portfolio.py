import pytest
from datetime import datetime
from Library.Portfolio.Account import AccountAPI, AccountType, MarginMode, Environment
from Library.Portfolio.Position import PositionAPI, PositionType, TradeType
from Library.Portfolio.Trade import TradeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Universe import UniverseAPI

def test_portfolio_initialization(db):
    db.migrate(schema=UniverseAPI.Schema, table=CategoryAPI.Table, structure=CategoryAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=ProviderAPI.Table, structure=ProviderAPI(db=db).Structure)
    db.migrate(schema=UniverseAPI.Schema, table=TickerAPI.Table, structure=TickerAPI(db=db).Structure)
    from Library.Universe.Contract import ContractAPI
    db.migrate(schema=UniverseAPI.Schema, table=ContractAPI.Table, structure=ContractAPI(db=db).Structure)
    db.migrate(schema=SecurityAPI.Schema, table=SecurityAPI.Table, structure=SecurityAPI(db=db).Structure)
    db.migrate(schema=AccountAPI.Schema, table=AccountAPI.Table, structure=AccountAPI(db=db).Structure)
    db.migrate(schema=PositionAPI.Schema, table=PositionAPI.Table, structure=PositionAPI(db=db).Structure)
    db.migrate(schema=TradeAPI.Schema, table=TradeAPI.Table, structure=TradeAPI(db=db).Structure)

    CategoryAPI(UID="Forex (Major)", Primary="Forex", Secondary="Major", Alternative="Currency", db=db).save(by="test")
    provider = ProviderAPI(UID="Pepperstone (cTrader)", Platform=Platform.cTrader, Name="Pepperstone Europe", Abbreviation="Pepperstone", db=db)
    provider.save(by="test")
    TickerAPI(UID="EURUSD", Category="Forex (Major)", BaseAsset="EUR", BaseName="Euro", QuoteAsset="USD", QuoteName="US Dollar", Description="Euro vs US Dollar", db=db).save(by="test")
    ContractAPI(Ticker="EURUSD", Provider="Pepperstone (cTrader)", Type=ContractType.Spot, db=db).save(by="test")

    acc = AccountAPI(
        UID="123456",
        Provider=provider.UID,
        Environment=Environment.Live,
        AccountType=AccountType.Hedged,
        MarginMode=MarginMode.Net,
        Asset="USD",
        Balance=10000.0,
        Equity=10050.0,
        Credit=0.0,
        Leverage=30.0,
        MarginUsed=500.0,
        MarginFree=9550.0,
        MarginLevel=2010.0,
        MarginStopLevel=50.0,
        db=db
    )
    assert acc.UID == "123456"
    assert acc.Provider.UID == "Pepperstone (cTrader)"
    assert acc.Environment == Environment.Live
    assert acc.AccountType == AccountType.Hedged

    sec = SecurityAPI(Ticker="EURUSD", Provider="Pepperstone (cTrader)", Contract=ContractType.Spot, db=db, autoload=True)
    sec.save(by="test")
    dt = datetime(2023, 1, 1, 12, 0, 0)
    
    pos = PositionAPI(
        UID=1001,
        Security=sec.UID,
        PositionType=PositionType.Normal,
        TradeType=TradeType.Buy,
        Volume=100000,
        Quantity=1.0,
        EntryTimestamp=dt,
        EntryPrice=1.0500,
        StopLossPrice=1.0450,
        TakeProfitPrice=1.0600,
        UsedMargin=500.0,
        EntryBalance=10000.0,
        Contract=sec.Contract,
        db=db
    )
    assert pos.UID == 1001
    assert pos.Security.UID == sec.UID
    assert pos.TradeType == TradeType.Buy
    assert pos.EntryPrice.Price == pytest.approx(1.0500)

    exit_dt = datetime(2023, 1, 1, 14, 0, 0)
    trade = TradeAPI(
        UID=2001,
        Security=sec.UID,
        PositionType=PositionType.Normal,
        TradeType=TradeType.Buy,
        Volume=100000,
        Quantity=1.0,
        EntryTimestamp=dt,
        EntryPrice=1.0500,
        ExitTimestamp=exit_dt,
        ExitPrice=1.0550,
        GrossPnL=500.0,
        NetPnL=495.0,
        CommissionPnL=-5.0,
        EntryBalance=10000.0,
        ExitBalance=10495.0,
        Contract=sec.Contract,
        db=db
    )
    assert trade.UID == 2001
    assert trade.ExitPrice.Price == pytest.approx(1.0550)
    assert trade.NetPnL.PnL == pytest.approx(495.0)

    from Library.Database.Query import QueryAPI
    db.executeone(QueryAPI(f'DELETE FROM "{TradeAPI.Schema}"."{TradeAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{PositionAPI.Schema}"."{PositionAPI.Table}"')).commit()
    db.executeone(QueryAPI(f'DELETE FROM "{AccountAPI.Schema}"."{AccountAPI.Table}"')).commit()
