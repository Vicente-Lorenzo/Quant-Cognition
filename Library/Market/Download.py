from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Query import QueryAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Utility.Enumeration import EnumerationAPI
from Library.Universe.Security import SecurityAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

class DownloadStatus(EnumerationAPI):

    Complete = 0
    Empty = 1
    Failed = 2
    Live = 3

@dataclass
class DownloadAPI(DatapointAPI):

    Schema: ClassVar[str] = "Market"
    Table: ClassVar[str] = "Download"
    Enums: ClassVar[dict] = {"Status": DownloadStatus}

    Security: Union[int, None] = None
    Timestamp: Union[datetime, None] = None
    Ticks: Union[int, None] = None
    Status: Union[DownloadStatus, str, None] = None
    Through: Union[datetime, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.Security: ForeignKey(pl.Int64, reference=SecurityAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Timestamp: PrimaryKey(pl.Datetime),
            self.ID.Ticks: pl.Int64(),
            self.ID.Status: pl.String(),
            self.ID.Through: pl.Datetime(),
            **super().Structure
        }

    @classmethod
    def settled(cls, db: DatabaseAPI, security: int) -> dict:
        rows = db.records(schema=cls.Schema, table=cls.Table, columns=["Timestamp", "Status"], condition='"Security" = :security:', parameters={"security": security})
        return {row["Timestamp"]: row["Status"] for row in rows}

    @classmethod
    def successor(cls, db: DatabaseAPI, security: int, day: datetime, before: datetime) -> Union[datetime, None]:
        settled, following = cls.settled(db, security), day + timedelta(days=1)
        while following < before and settled.get(following) == DownloadStatus.Empty.name: following += timedelta(days=1)
        return following if following < before and settled.get(following) == DownloadStatus.Complete.name else None

    @classmethod
    def covers(cls, db: DatabaseAPI, security: int, start: datetime, stop: datetime) -> bool:
        first, last = start.replace(hour=0, minute=0, second=0, microsecond=0), stop.replace(hour=0, minute=0, second=0, microsecond=0)
        days = (last - first).days + 1
        stored = db.records(schema=cls.Schema, table=cls.Table, columns=["Timestamp", "Through"], condition='"Security" = :security: AND "Timestamp" BETWEEN :first: AND :last: AND "Status" <> :failed:',
                            parameters={"security": security, "first": first, "last": last, "failed": DownloadStatus.Failed.name})
        return len(stored) == days and max(row["Through"] for row in stored) >= stop

    @classmethod
    def through(cls, db: DatabaseAPI, security: int) -> Union[datetime, None]:
        row = db.first(schema=cls.Schema, table=cls.Table, columns=["Through"], condition='"Security" = :security: AND "Status" <> :failed: AND "Through" IS NOT NULL', order='"Timestamp" DESC', parameters={"security": security, "failed": DownloadStatus.Failed.name})
        return row["Through"] if row else None

    @classmethod
    def summary(cls, db: DatabaseAPI) -> pl.DataFrame:
        return db.executeone(QueryAPI(f'''SELECT "Security", MIN("Timestamp") AS "First", MAX("Timestamp") AS "Last",
            COUNT(*) FILTER (WHERE "Status" = :complete:) AS "Complete", COUNT(*) FILTER (WHERE "Status" = :empty:) AS "Empty",
            COUNT(*) FILTER (WHERE "Status" = :failed:) AS "Failed", MAX("Through") FILTER (WHERE "Status" <> :failed:) AS "Through",
            CAST(SUM("Ticks") FILTER (WHERE "Status" <> :failed:) AS BIGINT) AS "Ticks", MAX("UpdatedAt") AS "UpdatedAt"
            FROM "{cls.Schema}"."{cls.Table}" GROUP BY "Security"'''), complete=DownloadStatus.Complete.name, empty=DownloadStatus.Empty.name, failed=DownloadStatus.Failed.name).fetchall(legacy=False)

    @classmethod
    def months(cls, db: DatabaseAPI) -> pl.DataFrame:
        return db.executeone(QueryAPI(f'''SELECT "Security", DATE_TRUNC('month', "Timestamp") AS "Month", COUNT(*) FILTER (WHERE "Status" = :complete:) AS "Complete",
            COUNT(*) FILTER (WHERE "Status" = :empty:) AS "Empty", COUNT(*) FILTER (WHERE "Status" = :failed:) AS "Failed", COUNT(*) FILTER (WHERE "Status" = :live:) AS "Live",
            CAST(SUM("Ticks") FILTER (WHERE "Status" <> :failed:) AS BIGINT) AS "Ticks" FROM "{cls.Schema}"."{cls.Table}" GROUP BY 1, 2 ORDER BY 1, 2'''),
            complete=DownloadStatus.Complete.name, empty=DownloadStatus.Empty.name, failed=DownloadStatus.Failed.name, live=DownloadStatus.Live.name).fetchall(legacy=False)