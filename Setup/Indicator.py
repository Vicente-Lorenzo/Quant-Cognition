import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Indicator.Fundamental.Calendar import CalendarAPI
from Library.Market.Market import MarketAPI
from Library.Utility.Datetime import utc_now
from Setup.Task import migrate, provision

def moment(value, fallback=None):
    if value is None: return fallback
    if isinstance(value, datetime): return value
    return datetime.strptime(value, "%Y-%m-%d")

def setup_indicator(db, start=MarketAPI.HORIZON, stop=None, delay: float = 3.0):
    log = LoggingAPI()
    db.create(schema=CalendarAPI.Schema)
    migrate(db, CalendarAPI)
    if start is None: return 0
    since, until = moment(start), moment(stop, utc_now())
    if db.count(schema=CalendarAPI.Schema, table=CalendarAPI.Table) > 0:
        log.info(lambda: "Indicator Setup: Skipped Backfill · Calendar already holds events")
        return 0
    log.info(lambda: f"Indicator Setup: Backfilling Calendar ({since:%Y-%m-%d} · {until:%Y-%m-%d})")
    total = CalendarAPI.download(db, since, until, by="Backfill", delay=delay)
    log.info(lambda: f"Indicator Setup: Backfilled Calendar ({total} Events)")
    return total

def main(database="Quant", start=MarketAPI.HORIZON, stop=None):
    with LoggingAPI() as log:
        return provision(log, "Indicator", lambda db: setup_indicator(db, start=start, stop=stop), database=database, detail="Schema + 1 Table")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(prog="Indicator")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--start", default=MarketAPI.HORIZON.strftime("%Y-%m-%d"))
    parser.add_argument("--stop", default=None)
    arguments = parser.parse_args()
    raise SystemExit(main(database=arguments.database, start=arguments.start, stop=arguments.stop))