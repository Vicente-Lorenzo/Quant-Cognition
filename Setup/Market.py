import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI
from Library.Logging import LoggingAPI
from Setup.Task import migrate, provision

def populate_market(db):
    migrate(db, TickAPI, BarAPI)

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Market", populate_market, database=database, detail="Schema + 2 Tables")

if __name__ == "__main__":
    raise SystemExit(main())