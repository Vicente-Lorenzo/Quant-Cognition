import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import LoggingAPI
from Library.Logging import VerboseLevel
from Library.Logging.Log import LogAPI
from Library.Database import PostgresDatabaseAPI
from Setup.Enum import enum_block

def logging_block() -> str:
    return enum_block("VerboseLevel", [(v.name, v.value) for v in VerboseLevel])

def setup_logging(db):
    db.create(schema=LogAPI.Schema)
    LogAPI(db=db, migrate=True, autosave=False, autoload=False)

def main(database="Quant"):
    with LoggingAPI() as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                setup_logging(db)
            log.info(lambda: f"Logging Setup: Completed · {LogAPI.Schema}.{LogAPI.Table}")
            return 0
        except Exception as error:
            log.exception(lambda: f"Logging Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())