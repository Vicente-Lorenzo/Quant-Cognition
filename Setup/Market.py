import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI

def _migrate_(db):
    TickAPI(db=db, migrate=True, autosave=False, autoload=False)
    BarAPI(db=db, migrate=True, autosave=False, autoload=False)

def populate_market(db):
    _migrate_(db)

def main(database="Quant"):
    with LoggingAPI() as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                populate_market(db)
            log.info(lambda: "Market Setup: Completed · Schema + 2 Tables")
            return 0
        except Exception as error:
            log.exception(lambda: f"Market Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())