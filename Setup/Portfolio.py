from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Trade import TradeAPI

def _migrate_(db):
    SessionAPI(db=db, migrate=True, autosave=False, autoload=False)
    AccountAPI(db=db, migrate=True, autosave=False, autoload=False)
    OrderAPI(db=db, migrate=True, autosave=False, autoload=False)
    PositionAPI(db=db, migrate=True, autosave=False, autoload=False)
    TradeAPI(db=db, migrate=True, autosave=False, autoload=False)

def populate_portfolio(db):
    _migrate_(db)