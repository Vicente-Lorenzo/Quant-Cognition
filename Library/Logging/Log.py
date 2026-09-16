from __future__ import annotations

import uuid
import pathlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing_extensions import Self
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Utility.Datetime import utc_now
from Library.Utility.Runtime import find_host
from Library.Utility.Typing import MISSING, Missing
from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Database import PrimaryKey

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass
class LogAPI(DatapointAPI):
    """
    One durable row per captured log.

    The row is created when the log starts so that consumers can reach it while the work is still
    running, and its content is refreshed as the log grows. Bulk content lives here only for the
    small logs a scheduled run produces; large framework logs stay on the filesystem and are
    referenced through Path.
    """

    Schema: ClassVar[str] = "Logging"
    Table: ClassVar[str] = "Log"

    UID: Union[str, None] = None
    Source: Union[str, None] = None
    Level: Union[str, None] = None
    Host: Union[str, None] = None
    User: Union[str, None] = None
    Process: Union[int, None] = None
    StartedAt: Union[datetime, None] = None
    StoppedAt: Union[datetime, None] = None
    Records: Union[int, None] = None
    Dropped: Union[int, None] = None
    Truncated: Union[bool, None] = None
    Path: Union[str, None] = None
    Content: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        """Returns the physical column definition of the Logging.Log table."""
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Source: pl.String(),
            self.ID.Level: pl.String(),
            self.ID.Host: pl.String(),
            self.ID.User: pl.String(),
            self.ID.Process: pl.Int64(),
            self.ID.StartedAt: pl.Datetime(),
            self.ID.StoppedAt: pl.Datetime(),
            self.ID.Records: pl.Int64(),
            self.ID.Dropped: pl.Int64(),
            self.ID.Truncated: pl.Boolean(),
            self.ID.Path: pl.String(),
            self.ID.Content: pl.String(),
            **super().Structure
        }

    @classmethod
    def start(cls, db: DatabaseAPI, *,
              source: str,
              level: str,
              user: Union[str, None] = None,
              process: Union[int, None] = None,
              path: Union[str, pathlib.Path, None] = None,
              started: Union[datetime, None, Missing] = MISSING,
              by: str = "Autosave",
              migrate: bool = False) -> Self:
        """
        Inserts the row a log writes into, before any content exists.

        The row lands immediately rather than at completion so that anything reading the database can
        resolve the log while the work is still in flight.
        :param db: An open database connection owned by the caller.
        :param source: A label identifying what produced the log.
        :param level: The name of the most verbose level the log accepts.
        :param user: The account the work runs under.
        :param process: The identifier of the process producing the log.
        :param path: Optional filesystem location of the same log, for live tailing.
        :param started: When the log started; now when omitted.
        :param by: The audit label stamped on the row.
        :param migrate: Whether to create the table if it is absent.
        :return: The freshly inserted log row.
        """
        record = cls(
            UID=uuid.uuid4().hex,
            Source=source,
            Level=level,
            Host=find_host(),
            User=user,
            Process=process,
            Path=str(path) if path is not None else None,
            Content="",
            Records=0,
            Dropped=0,
            Truncated=False,
            StartedAt=started or utc_now(),
            db=db,
            migrate=migrate
        )
        record.save(by=by)
        return record

    def stop(self, content: str, *, records: int, dropped: int, truncated: bool, by: str = "Autosave", stopped: Union[datetime, None, Missing] = MISSING) -> None:
        """
        Writes the accumulated content and counters back to the row.
        :param content: The log content, already bounded by the caller.
        :param records: The number of records the log received.
        :param dropped: The number of records lost to a full queue.
        :param truncated: Whether content was cut at the size limit.
        :param by: The audit label stamped on the row.
        :param stopped: When the log stopped; the row keeps its current value when omitted.
        """
        self.Content, self.Records, self.Dropped, self.Truncated = content, records, dropped, truncated
        if stopped: self.StoppedAt = stopped
        self.save(by=by)

    @classmethod
    def prune(cls, db: DatabaseAPI, days: int) -> int:
        """
        Deletes log rows whose StoppedAt is older than the retention horizon.

        Rows still referenced by a Scheduler run are removed all the same because that foreign key
        is declared ON DELETE SET NULL, so run history survives while its bulk content is reclaimed.
        :param db: An open database connection.
        :param days: Retention horizon in days; a value of zero disables pruning.
        :return: The number of rows deleted.
        """
        if days <= 0: return 0
        target = db.clone(schema=cls.Schema, table=cls.Table)
        target.remove(condition=f"{target._quoted_(cls.ID.StoppedAt)} < :horizon:", parameters={"horizon": utc_now() - timedelta(days=days)})
        target.commit()
        return target.rowcount