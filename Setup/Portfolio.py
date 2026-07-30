import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI

def _migrate_(db):
    SessionAPI(db=db, migrate=True, autosave=False, autoload=False)
    AccountAPI(db=db, migrate=True, autosave=False, autoload=False)
    OrderAPI(db=db, migrate=True, autosave=False, autoload=False)
    PositionAPI(db=db, migrate=True, autosave=False, autoload=False)
    TradeAPI(db=db, migrate=True, autosave=False, autoload=False)

def populate_portfolio(db):
    _migrate_(db)

def main(database="Quant"):
    with LoggingAPI() as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                populate_portfolio(db)
            log.info(lambda: "Portfolio Setup: Completed · Schema + 5 Tables")
            return 0
        except Exception as error:
            log.exception(lambda: f"Portfolio Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())