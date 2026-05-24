from Library.Market.Bar import BarAPI
from Library.Market.Tick import TickAPI

def _migrate_(db):
    TickAPI(db=db, migrate=True, autosave=False, autoload=False)
    BarAPI(db=db, migrate=True, autosave=False, autoload=False)

def populate_market(db):
    _migrate_(db)