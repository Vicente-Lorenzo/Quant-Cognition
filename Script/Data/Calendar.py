import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Data.Calendar import CalendarServiceAPI
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Indicator.Fundamental.Calendar import CalendarAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Utility.Datetime import parse_datetime
from Script.Data.Horizon import HORIZON

def main() -> int:
    parser = argparse.ArgumentParser(prog="Calendar")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--start", default=None)
    parser.add_argument("--stop", default=None)
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Info)
    with log:
        if args.start is None: return CalendarServiceAPI(horizon=HORIZON, database=args.database, delay=args.delay).serve()
        try:
            start, stop = parse_datetime(args.start), parse_datetime(args.stop) if args.stop else parse_datetime(args.start)
            with PostgresDatabaseAPI(database=args.database) as db: total = CalendarAPI.download(db, start, stop, by="Backfill", delay=args.delay)
            log.info(lambda: f"Calendar Download: Completed ({total} Events · {start:%Y-%m-%d} · {stop:%Y-%m-%d})")
            return 0
        except Exception as error:
            log.exception(lambda error=error: f"Calendar Download: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())