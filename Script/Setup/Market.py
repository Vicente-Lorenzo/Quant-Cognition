import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Logging import LoggingAPI
from Library.Market.Tape import TapeAPI
from Script.Task import provision

def populate_market(db):
    TapeAPI.create(db)

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Market", populate_market, database=database, detail="Schema + Tick Hypertable")

if __name__ == "__main__":
    raise SystemExit(main())