import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Indicator.Fundamental.Calendar import CalendarAPI
from Library.Database import PostgresDatabaseAPI
from Library.Logging import LoggingAPI

def setup_indicator(db):
    db.create(schema=CalendarAPI.Schema)
    CalendarAPI(db=db, migrate=True, autosave=False, autoload=False)

def main(database="Quant"):
    with LoggingAPI() as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                setup_indicator(db)
            log.info(lambda: "Indicator Setup: Completed · Schema + 1 Table")
            return 0
        except Exception as error:
            log.exception(lambda: f"Indicator Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())