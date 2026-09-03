import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from Library.Logging import LoggingAPI
from Library.Logging import VerboseLevel
from Library.Logging.Log import LogAPI
from Setup.Enum import enum_block
from Setup.Task import migrate, provision

def logging_block() -> str:
    return enum_block("VerboseLevel", VerboseLevel)

def setup_logging(db):
    db.create(schema=LogAPI.Schema)
    migrate(db, LogAPI)

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Logging", setup_logging, database=database, detail=f"{LogAPI.Schema}.{LogAPI.Table}")

if __name__ == "__main__":
    raise SystemExit(main())