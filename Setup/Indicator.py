import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Library.Logging import LoggingAPI
from Library.Database import PostgresDatabaseAPI, QueryAPI
from Library.Indicator.Fundamental.Calendar import CalendarAPI
from Library.Utility.Datetime import HORIZON
from Setup.Task import migrate

def moment(value, fallback=None):
    if value is None: return fallback
    if isinstance(value, datetime): return value
    return datetime.strptime(value, "%Y-%m-%d")

def setup_indicator(db, start=HORIZON, stop=None, delay: float = 3.0):
    log = LoggingAPI()
    db.create(schema=CalendarAPI.Schema)
    migrate(db, CalendarAPI)
    if start is None: return 0
    since, until = moment(start), moment(stop, datetime.now())
    stored = db.executeone(QueryAPI(f'SELECT COUNT(*) AS n FROM {db._target_(CalendarAPI.Schema, CalendarAPI.Table)}'), admin=False).fetchall(legacy=False)
    if int(next(iter(stored.to_dicts()[0].values()))) > 0:
        log.info(lambda: "Indicator Setup: Skipped Backfill · Calendar already holds events")
        return 0
    log.info(lambda: f"Indicator Setup: Backfilling Calendar ({since:%Y-%m-%d} · {until:%Y-%m-%d})")
    total = CalendarAPI.download(db, since, until, by="Backfill", delay=delay)
    log.info(lambda: f"Indicator Setup: Backfilled Calendar ({total} Events)")
    return total

def main(database="Quant", start=HORIZON, stop=None):
    with LoggingAPI() as log:
        try:
            with PostgresDatabaseAPI(database=database) as db:
                setup_indicator(db, start=start, stop=stop)
            log.info(lambda: "Indicator Setup: Completed · Schema + 1 Table")
            return 0
        except Exception as error:
            log.exception(lambda: f"Indicator Setup: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(prog="Indicator")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--start", default=HORIZON.strftime("%Y-%m-%d"))
    parser.add_argument("--stop", default=None)
    arguments = parser.parse_args()
    raise SystemExit(main(database=arguments.database, start=arguments.start, stop=arguments.stop))