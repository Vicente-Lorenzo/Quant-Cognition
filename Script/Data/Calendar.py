import sys
import time
import argparse
from pathlib import Path
from typing import Union
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database import PostgresDatabaseAPI
from Library.Indicator.Fundamental.Calendar import CalendarAPI, CalendarHistoryAPI
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Utility.Datetime import parse_datetime, utc_now, week_start
from Library.Utility.Typing import MISSING, Missing
from Script.Data.Horizon import HORIZON
from Script.Data.Service import DataServiceAPI

class CalendarServiceAPI(DataServiceAPI):

    def __init__(self, *, horizon: datetime, database: str = "Quant", vault: Union[str, Missing] = MISSING, delay: float = 3.0, cycle: float = 300.0, release: float = 30.0, ahead: float = 21_600.0, recent: int = 30) -> None:
        super().__init__(database=database, vault=vault)
        self._horizon_ = horizon
        self._delay_ = delay
        self._cycle_ = cycle
        self._release_ = release
        self._ahead_ = ahead
        self._recent_ = timedelta(days=recent)

    @staticmethod
    def by() -> str:
        return "Calendar"

    def _missing_(self, db: PostgresDatabaseAPI, now: datetime) -> list[datetime]:
        stored, week, weeks = CalendarAPI.weeks(db), week_start(self._horizon_), []
        current = week_start(now)
        while week < current:
            if week not in stored: weeks.append(week)
            week += timedelta(days=7)
        return sorted(set(weeks) | {week for week in CalendarAPI.incomplete(db, now - self._recent_, now) if week < current})

    def _read_(self, db: PostgresDatabaseAPI, week: datetime) -> tuple[int, int]:
        return CalendarAPI.store(db, CalendarAPI.week(week), self.by())

    def _pending_(self, db: PostgresDatabaseAPI, now: datetime) -> set:
        return CalendarAPI.incomplete(db, now - timedelta(minutes=10), now)

    def _backfill_(self, db: PostgresDatabaseAPI) -> int:
        missing = self._missing_(db, utc_now())
        if missing: self._log_.info(lambda: f"Calendar Backfill: Started · {len(missing)} Weeks · {missing[0]:%Y-%m-%d} to {missing[-1]:%Y-%m-%d}")
        failed = 0
        for index, week in enumerate(missing):
            if self.stopped(self._delay_ if index else None): break
            try: self._read_(db, week)
            except Exception as error:
                failed += 1
                self._log_.warning(lambda week=week, error=error: f"Calendar Backfill: Failed ({week:%Y-%m-%d}) · {error}")
        if missing: self._log_.info(lambda: f"Calendar Backfill: Completed · {len(missing) - failed} Weeks · {failed} Failed")
        return failed

    def work(self) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            CalendarAPI(db=db, migrate=True, autoload=False)
            CalendarHistoryAPI(db=db, migrate=True, autoload=False)
            failed = self._backfill_(db)
            now = utc_now()
            self._read_(db, week_start(now))
            self.ready(f"{failed} Failed Weeks")
            cycled, ahead, backfilled = time.monotonic(), float("-inf"), time.monotonic()
            while not self.stopped(self._release_):
                now, clock = utc_now(), time.monotonic()
                try:
                    pending = self._pending_(db, now)
                    if pending or clock - cycled >= self._cycle_:
                        for week in sorted(pending | {week_start(now)}):
                            rows, changed = self._read_(db, week)
                            if changed: self._log_.info(lambda rows=rows, changed=changed: f"Calendar Refresh: Updated · {changed} Changed Of {rows} Events")
                        cycled = clock
                    if clock - ahead >= self._ahead_:
                        self._read_(db, week_start(now) + timedelta(days=7))
                        ahead = clock
                    if clock - backfilled >= self._ahead_:
                        self._backfill_(db)
                        backfilled = clock
                except Exception as error:
                    if self.stopped(): break
                    self._log_.warning(lambda error=error: f"Calendar Refresh: Failed · {error}")

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