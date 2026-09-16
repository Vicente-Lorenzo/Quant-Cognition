import sys
import argparse
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Indicator.Fundamental.Calendar import CalendarAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Utility.Datetime import parse_datetime, utc_now

def main() -> int:
    parser = argparse.ArgumentParser(prog="Calendar")
    parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
    parser.add_argument("--start", default=None)
    parser.add_argument("--stop", default=None)
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()
    with LoggingAPI() as log:
        log.console.set_level(VerboseLevel.Info)
        log.file.set_level(VerboseLevel.Debug)
        try:
            now = utc_now()
            start = parse_datetime(args.start) if args.start else now - timedelta(days=6)
            stop = parse_datetime(args.stop) if args.stop else now
            with PostgresDatabaseAPI(database=args.database) as db:
                total = CalendarAPI.download(db, start, stop, by="Backfill" if args.start or args.stop else "Daily", delay=args.delay)
            log.info(lambda: f"Calendar Download: Completed ({total} Events · {start:%Y-%m-%d} · {stop:%Y-%m-%d})")
            return 0
        except Exception as error:
            log.exception(lambda error=error: f"Calendar Download: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())