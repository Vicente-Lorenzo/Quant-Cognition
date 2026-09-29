import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Cashflow import CashflowAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Logging import LoggingAPI
from Script.Task import migrate, provision

def populate_portfolio(db):
    migrate(db, AccountAPI, OrderAPI, PositionAPI, TradeAPI, CashflowAPI)

def main(database="Quant"):
    with LoggingAPI() as log:
        return provision(log, "Portfolio", populate_portfolio, database=database, detail="Schema + 5 Tables · Account · Order · Position · Trade · Cashflow")

if __name__ == "__main__":
    raise SystemExit(main())