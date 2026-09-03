import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Logging import LoggingAPI
from Setup.Task import migrate, provision

def populate_portfolio(db):
    migrate(db, SessionAPI, AccountAPI, OrderAPI, PositionAPI, TradeAPI)

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Portfolio", populate_portfolio, database=database, detail="Schema + 5 Tables")

if __name__ == "__main__":
    raise SystemExit(main())