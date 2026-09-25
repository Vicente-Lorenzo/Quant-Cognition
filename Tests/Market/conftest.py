import pytest

from datetime import datetime

from Library.Database.Query import QueryAPI
from Library.Market.Tape import TapeAPI
from Library.Market.Tick import TickAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Security import SecurityAPI
from Library.Universe.Ticker import TickerAPI
from Library.Universe.Timeframe import TimeframeAPI

@pytest.fixture
def stored(db):
    for kind in (CategoryAPI, ProviderAPI, TickerAPI, ContractAPI, TimeframeAPI, SecurityAPI): db.migrate(schema="Universe", table=kind.Table, structure=kind(db=db).Structure)
    CategoryAPI(UID="Forex", db=db).save()
    ProviderAPI(UID="TestProv", Platform=Platform.cTrader, db=db).save()
    TickerAPI(UID="EURUSD", Category="Forex", db=db).save()
    security = SecurityAPI(Ticker="EURUSD", Provider="TestProv", Category="Forex", db=db)
    security.save()
    try: TapeAPI.create(db)
    except Exception as error: pytest.skip(f"TimescaleDB unavailable in the Tests database · {error}")
    db.executeone(QueryAPI('TRUNCATE "Market"."Tick"'))
    def add(stamp: datetime, ask: float, bid: float, volume: float = None) -> None:
        db.executeone(QueryAPI('INSERT INTO "Market"."Tick" ("UID", "Security", "Ask", "Bid", "Volume") VALUES (:uid:, :security:, :ask:, :bid:, :volume:)'), uid=TickAPI.encode(security.UID, stamp), security=security.UID, ask=round(ask * 100000), bid=round(bid * 100000), volume=volume)
    yield db, security.UID, add
    db.executeone(QueryAPI('TRUNCATE "Market"."Tick"'))