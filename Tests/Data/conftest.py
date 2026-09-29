import pytest

from Library.Database.Query import QueryAPI
from Library.Market.Download import DownloadAPI
from Library.Market.Tape import TapeAPI
from Library.Market.Tick import TickAPI

@pytest.fixture
def tape(db, universe):
    try: TapeAPI.create(db)
    except Exception as error: pytest.skip(f"TimescaleDB unavailable in the Tests database · {error}")
    DownloadAPI(db=db, migrate=True, autoload=False)
    security = universe["security"].UID
    def clear() -> None:
        db.executeone(QueryAPI('DELETE FROM "Market"."Tick" WHERE "UID" BETWEEN :low: AND :high:'), low=security << TickAPI.bits(), high=((security + 1) << TickAPI.bits()) - 1)
        db.remove(schema=DownloadAPI.Schema, table=DownloadAPI.Table, condition='"Security" = :security:', parameters={"security": security})
    clear()
    yield db, security
    clear()