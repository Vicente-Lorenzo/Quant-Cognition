import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Union

from Library.Database import PostgresDatabaseAPI
from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Data.Service import DataServiceAPI, SupervisorAPI
from Library.Market.Download import DownloadAPI, DownloadStatus
from Library.Market.Tape import TapeAPI
from Library.Universe.Security import SecurityAPI, SecurityStatus
from Library.Utility.Datetime import epoch_to_datetime, utc_now
from Library.Utility.Typing import MISSING, Missing

class MarketWorkerAPI(DataServiceAPI):

    def __init__(self, *, security: int, horizon: datetime, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING, poll: float = 1.0, overlap: float = 10.0, retry: float = 3_600.0) -> None:
        super().__init__(database=database, credential=credential, vault=vault)
        self._security_ = security
        self._horizon_ = horizon
        self._poll_ = poll
        self._overlap_ = timedelta(seconds=overlap)
        self._retry_ = retry
        self._symbol_ = None
        self._label_ = str(security)

    @staticmethod
    def by() -> str:
        return "Market"

    @staticmethod
    def _midnight_(moment: datetime) -> datetime:
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)

    @staticmethod
    def _fetch_(api, symbol: int, start: datetime, stop: datetime) -> tuple[pl.DataFrame, pl.DataFrame]:
        return api.market.ticks(symbol, start, stop, quote="Ask", legacy=False), api.market.ticks(symbol, start, stop, quote="Bid", legacy=False)

    def _record_(self, db: PostgresDatabaseAPI, day: datetime, ticks: Union[int, None], status: DownloadStatus, through: Union[datetime, None]) -> None:
        DownloadAPI(Security=self._security_, Timestamp=day, Ticks=ticks, Status=status, Through=through, db=db).save(by=self.by())

    @classmethod
    def rewrite(cls, api, db: PostgresDatabaseAPI, security: int, symbol: int, day: datetime) -> DownloadStatus:
        following = day + timedelta(days=1)
        ticks = TapeAPI.write(db, security, TapeAPI.merge(*cls._fetch_(api, symbol, day, following), TapeAPI.previous(db, security, day)), day, following, cls.by())
        status = DownloadStatus.Complete if ticks else DownloadStatus.Empty
        DownloadAPI(Security=security, Timestamp=day, Ticks=ticks, Status=status, Through=following, db=db).save(by=cls.by())
        return status

    def _day_(self, api, db: PostgresDatabaseAPI, day: datetime) -> DownloadStatus:
        try:
            return self.rewrite(api, db, self._security_, self._symbol_, day)
        except Exception as error:
            if self.stopped(): raise
            self._log_.warning(lambda error=error: f"Market Download: Failed ({self._label_} {day:%Y-%m-%d}) · {error}")
            self._record_(db, day, None, DownloadStatus.Failed, None)
            return DownloadStatus.Failed

    def _missing_(self, db: PostgresDatabaseAPI, today: datetime) -> list[datetime]:
        settled = {day for day, status in DownloadAPI.settled(db, self._security_).items() if status in (DownloadStatus.Complete.name, DownloadStatus.Empty.name)}
        days, day = [], self._midnight_(self._horizon_)
        while day < today:
            if day not in settled: days.append(day)
            day += timedelta(days=1)
        return days

    def _backfill_(self, api, db: PostgresDatabaseAPI) -> int:
        today = self._midnight_(utc_now())
        missing = self._missing_(db, today)
        if missing: self._log_.info(lambda: f"Market Backfill: Started ({self._label_}) · {len(missing)} Days · {missing[0]:%Y-%m-%d} to {missing[-1]:%Y-%m-%d}")
        clock, failed, month, pending = time.monotonic(), 0, None, set(missing)
        for index, day in enumerate(missing):
            if self.stopped(): break
            if self._day_(api, db, day) is DownloadStatus.Failed: failed += 1
            elif day + timedelta(days=1) not in pending:
                following = DownloadAPI.successor(db, self._security_, day, today)
                if following is not None and self._day_(api, db, following) is DownloadStatus.Failed: failed += 1
            if month is not None and day.month != month: TapeAPI.compress(db, self._security_, day)
            month = day.month
            if index and index % 250 == 0: self._log_.info(lambda index=index, day=day: f"Market Backfill: Progress ({self._label_}) · {index}/{len(missing)} Days · {day:%Y-%m-%d} · {time.monotonic() - clock:.0f}s")
        if missing: self._log_.info(lambda: f"Market Backfill: Completed ({self._label_}) · {len(missing) - failed} Days · {failed} Failed · {time.monotonic() - clock:.0f}s")
        return failed

    def _poll_window_(self, api, db: PostgresDatabaseAPI, day: datetime, frontier: datetime) -> datetime:
        now = utc_now()
        start = max(day, frontier - self._overlap_)
        asks, bids = self._fetch_(api, self._symbol_, start, now)
        frame = TapeAPI.merge(asks, bids, TapeAPI.previous(db, self._security_, start))
        if TapeAPI.extend(db, self._security_, frame, start, self.by()): frontier = epoch_to_datetime(int(frame["Stamp"].max()))
        self._record_(db, day, None, DownloadStatus.Live, now - self._overlap_)
        return frontier

    def _roll_(self, api, db: PostgresDatabaseAPI, day: datetime, today: datetime) -> None:
        self._day_(api, db, day)
        try: TapeAPI.compress(db, self._security_, today)
        except Exception as error: self._log_.warning(lambda error=error: f"Market Compress: Failed ({self._label_}) · {error}")

    def _live_(self, api, db: PostgresDatabaseAPI, frontier: datetime) -> None:
        day = self._midnight_(utc_now())
        retried = time.monotonic()
        while not self.stopped(self._poll_):
            today = self._midnight_(utc_now())
            if today > day:
                self._roll_(api, db, day, today)
                day, frontier = today, today
            try: frontier = self._poll_window_(api, db, day, frontier)
            except Exception as error:
                if self.stopped(): break
                self._log_.warning(lambda error=error: f"Market Poll: Failed ({self._label_}) · {error}")
            if time.monotonic() - retried >= self._retry_:
                self._backfill_(api, db)
                retried = time.monotonic()

    def work(self) -> None:
        with PostgresDatabaseAPI(database=self._database_) as db:
            row = db.first(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition='"UID" = :uid:', parameters={"uid": self._security_})
            if row is None or row["Symbol"] is None: raise LookupError(f"Market Worker: Failed · Security {self._security_} has no provider symbol")
            self._symbol_, self._label_ = int(row["Symbol"]), row["Ticker"]
            account = next((account for account in self.accounts() if account.get("Broker")), None)
            if account is None: raise LookupError("Market Worker: Failed · No demo account names its broker")
            with self.client(int(account["AccountId"])) as api:
                failed = self._backfill_(api, db)
                frontier = self._poll_window_(api, db, self._midnight_(utc_now()), self._midnight_(utc_now()))
                self.ready(f"{self._label_} · {failed} Failed Days")
                self._live_(api, db, frontier)

class MarketServiceAPI(SupervisorAPI):

    def __init__(self, *, script: Path, horizon: datetime, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING, interval: float = 30.0, backoff: float = 60.0, report: float = 300.0) -> None:
        super().__init__(script=script, flag="--security", name="Market", database=database, credential=credential, vault=vault, interval=interval, backoff=backoff)
        self._horizon_ = horizon
        self._report_every_ = report
        self._reported_ = 0.0

    def tracked(self) -> dict:
        with PostgresDatabaseAPI(database=self._database_) as db:
            rows = db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Ticker"], condition='"Tracked" = :tracked: AND "Status" <> :archived:', parameters={"tracked": True, "archived": SecurityStatus.Archived.name})
        return {row["UID"]: row["Ticker"] for row in rows}

    def report(self, tracked: dict) -> None:
        if time.monotonic() - self._reported_ < self._report_every_: return
        self._reported_ = time.monotonic()
        with PostgresDatabaseAPI(database=self._database_) as db:
            frame = db.executeone(QueryAPI('''SELECT "Security", COUNT(*) FILTER (WHERE "Status" IN (:complete:, :empty:)) AS "Settled", COUNT(*) FILTER (WHERE "Status" = :failed:) AS "Failed"
                FROM "Market"."Download" GROUP BY "Security"'''), complete=DownloadStatus.Complete.name, empty=DownloadStatus.Empty.name, failed=DownloadStatus.Failed.name).fetchall(legacy=False)
        counts = {row["Security"]: (row["Settled"], row["Failed"]) for row in frame.iter_rows(named=True)} if frame.height else {}
        days = (utc_now() - self._horizon_).days
        settled = sum(counts.get(uid, (0, 0))[0] for uid in tracked)
        failed = sum(counts.get(uid, (0, 0))[1] for uid in tracked)
        self._log_.info(lambda: f"Market Service: Progress · {self.live(tracked)}/{len(tracked)} Live · {settled:,} of {days * len(tracked):,} Days · {failed} Failed")