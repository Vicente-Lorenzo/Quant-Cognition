from __future__ import annotations

import json
import time
import argparse
import urllib.request
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING

from Library.Logging import LoggingAPI
from Library.Logging import VerboseLevel
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI

@dataclass
class CalendarAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Indicator"
    Table: ClassVar[str] = "Calendar"

    _BASE_: ClassVar[str] = "https://www.forexfactory.com/calendar?week="
    _HEADERS_: ClassVar[dict] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close"
    }
    _IMPACT_: ClassVar[dict] = {
        "icon--ff-impact-red": "High",
        "icon--ff-impact-ora": "Medium",
        "icon--ff-impact-yel": "Low",
        "icon--ff-impact-gra": "Holiday"
    }
    _BETTER_: ClassVar[dict] = {1: 1, 0: 0, 2: -1}
    _SCALE_: ClassVar[dict] = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}

    UID: int | None = None
    Timestamp: datetime | None = None
    Event: int | None = None
    Currency: str | None = None
    Country: str | None = None
    Title: str | None = None
    Impact: str | None = None
    Actual: str | None = None
    Forecast: str | None = None
    Previous: str | None = None
    Revision: str | None = None
    ActualValue: float | None = None
    ForecastValue: float | None = None
    PreviousValue: float | None = None
    RevisionValue: float | None = None
    ActualBetter: int | None = None
    RevisionBetter: int | None = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.Int64),
            self.ID.Timestamp: pl.Datetime(),
            self.ID.Event: pl.Int64(),
            self.ID.Currency: pl.String(),
            self.ID.Country: pl.String(),
            self.ID.Title: pl.String(),
            self.ID.Impact: pl.String(),
            self.ID.Actual: pl.String(),
            self.ID.Forecast: pl.String(),
            self.ID.Previous: pl.String(),
            self.ID.Revision: pl.String(),
            self.ID.ActualValue: pl.Float64(),
            self.ID.ForecastValue: pl.Float64(),
            self.ID.PreviousValue: pl.Float64(),
            self.ID.RevisionValue: pl.Float64(),
            self.ID.ActualBetter: pl.Int64(),
            self.ID.RevisionBetter: pl.Int64(),
            **super().Structure
        }

    @staticmethod
    def _url_(day: datetime) -> str:
        return f"{CalendarAPI._BASE_}{day.strftime('%b').lower()}{day.day}.{day.year}"

    @classmethod
    def _value_(cls, text: str | None) -> float | None:
        if not text: return None
        token = text.split("|")[0].replace(",", "").strip("<> %")
        scale = cls._SCALE_.get(token[-1:].upper(), 1)
        try: return float(token[:-1] if scale != 1 else token) * scale
        except ValueError: return None

    @classmethod
    def _request_(cls, url: str, retries: int = 3, backoff: float = 3.0) -> str:
        for attempt in range(1, retries + 1):
            try:
                request = urllib.request.Request(url, headers=cls._HEADERS_)
                with urllib.request.urlopen(request, timeout=30) as response:
                    raw = response.read()
                try:
                    return raw.decode("utf-8")
                except UnicodeDecodeError:
                    return raw.decode("windows-1252", "replace")
            except Exception:
                if attempt == retries: raise
                time.sleep(backoff * attempt)
        return ""

    @staticmethod
    def _extract_(html: str) -> list:
        marker = html.find("calendarComponentStates[1]")
        if marker == -1: return []
        anchor = html.find("days:", marker)
        if anchor == -1: return []
        start = html.find("[", anchor)
        if start == -1: return []
        depth, index, quoted, escaped = 0, start, False, False
        while index < len(html):
            char = html[index]
            if quoted:
                if escaped: escaped = False
                elif char == "\\": escaped = True
                elif char == '"': quoted = False
            elif char == '"': quoted = True
            elif char == "[": depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0: return json.loads(html[start:index + 1])
            index += 1
        return []

    @classmethod
    def _rows_(cls, days: list) -> list:
        rows = []
        for day in days:
            for event in day.get("events", []):
                dateline = event.get("dateline")
                actual = event.get("actual") or None
                forecast = event.get("forecast") or None
                previous = event.get("previous") or None
                revision = event.get("revision") or None
                rows.append({
                    str(cls.ID.UID): event.get("id"),
                    str(cls.ID.Timestamp): datetime.fromtimestamp(dateline, tz=timezone.utc).replace(tzinfo=None) if dateline else None,
                    str(cls.ID.Event): event.get("ebaseId"),
                    str(cls.ID.Currency): event.get("currency") or None,
                    str(cls.ID.Country): event.get("country") or None,
                    str(cls.ID.Title): event.get("name") or None,
                    str(cls.ID.Impact): cls._IMPACT_.get(event.get("impactClass")),
                    str(cls.ID.Actual): actual,
                    str(cls.ID.Forecast): forecast,
                    str(cls.ID.Previous): previous,
                    str(cls.ID.Revision): revision,
                    str(cls.ID.ActualValue): cls._value_(actual),
                    str(cls.ID.ForecastValue): cls._value_(forecast),
                    str(cls.ID.PreviousValue): cls._value_(previous),
                    str(cls.ID.RevisionValue): cls._value_(revision),
                    str(cls.ID.ActualBetter): cls._BETTER_.get(event.get("actualBetterWorse")) if actual else None,
                    str(cls.ID.RevisionBetter): cls._BETTER_.get(event.get("revisionBetterWorse")) if revision else None
                })
        return rows

    @classmethod
    def _frame_(cls, rows: list) -> pl.DataFrame:
        return pl.DataFrame(rows, schema={
            str(cls.ID.UID): pl.Int64,
            str(cls.ID.Timestamp): pl.Datetime,
            str(cls.ID.Event): pl.Int64,
            str(cls.ID.Currency): pl.String,
            str(cls.ID.Country): pl.String,
            str(cls.ID.Title): pl.String,
            str(cls.ID.Impact): pl.String,
            str(cls.ID.Actual): pl.String,
            str(cls.ID.Forecast): pl.String,
            str(cls.ID.Previous): pl.String,
            str(cls.ID.Revision): pl.String,
            str(cls.ID.ActualValue): pl.Float64,
            str(cls.ID.ForecastValue): pl.Float64,
            str(cls.ID.PreviousValue): pl.Float64,
            str(cls.ID.RevisionValue): pl.Float64,
            str(cls.ID.ActualBetter): pl.Int64,
            str(cls.ID.RevisionBetter): pl.Int64
        })

    @classmethod
    def _week_(cls, day: datetime) -> list:
        return cls._rows_(cls._extract_(cls._request_(cls._url_(day))))

    @staticmethod
    def push(db: DatabaseAPI, data) -> None:
        db.upsert(schema=CalendarAPI.Schema, table=CalendarAPI.Table, data=data, key=["UID"])

    @staticmethod
    def pull(db: DatabaseAPI) -> pl.DataFrame:
        return db.select(schema=CalendarAPI.Schema, table=CalendarAPI.Table, order='"Timestamp"', legacy=False)

    @classmethod
    def download(cls, db: DatabaseAPI, start: datetime, stop: datetime, by: str = "Calendar", delay: float = 3.0) -> int:
        log = LoggingAPI()
        cls(db=db, migrate=True, autosave=False, autoload=False)
        total, week = 0, start - timedelta(days=start.weekday())
        while week <= stop:
            rows = cls._week_(week)
            if rows:
                frame = cls._frame_(rows).filter(pl.col(str(cls.ID.UID)).is_not_null()).unique(subset=[str(cls.ID.UID)], keep="last")
                frame = frame.with_columns(pl.lit(by).alias(str(cls.ID.UpdatedBy)), pl.lit(datetime.now()).alias(str(cls.ID.UpdatedAt)))
                cls.push(db, frame)
                total += frame.height
            log.debug(lambda moment=week, count=len(rows): f"Fetch Operation: Retrieved {count} Events ({moment:%Y-%m-%d})")
            week += timedelta(days=7)
            if week <= stop: time.sleep(delay)
        return total

def main() -> int:
    from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
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
            now = datetime.now()
            start = datetime.strptime(args.start, "%Y-%m-%d") if args.start else now - timedelta(days=6)
            stop = datetime.strptime(args.stop, "%Y-%m-%d") if args.stop else now
            with PostgresDatabaseAPI(database=args.database) as db:
                total = CalendarAPI.download(db, start, stop, by="Backfill" if args.start or args.stop else "Daily", delay=args.delay)
            log.info(lambda: f"Calendar Download: Completed ({total} Events · {start:%Y-%m-%d} · {stop:%Y-%m-%d})")
            return 0
        except Exception as error:
            log.exception(lambda: f"Calendar Download: Failed · Due to {error}")
            return 1

if __name__ == "__main__":
    raise SystemExit(main())