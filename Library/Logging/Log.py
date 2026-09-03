from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Database import PrimaryKey

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass
class LogAPI(DatapointAPI):
    """
    One durable row per captured log.

    The row is created when the log opens so that consumers can reach it while the work is still
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
    def prune(cls, db: "DatabaseAPI", days: int) -> int:
        """
        Deletes log rows whose StoppedAt is older than the retention horizon.

        Rows still referenced by a Scheduler run are removed all the same because that foreign key
        is declared ON DELETE SET NULL, so run history survives while its bulk content is reclaimed.
        :param db: An open database connection.
        :param days: Retention horizon in days; a value of zero disables pruning.
        :return: The number of rows deleted.
        """
        if days <= 0: return 0
        from Library.Database.Query import QueryAPI
        statement = f'DELETE FROM {db._target_(cls.Schema, cls.Table)} WHERE "{cls.ID.StoppedAt}" < :horizon:'
        horizon = datetime.now().timestamp() - days * 86400
        db.execute(QueryAPI(statement), [{"horizon": datetime.fromtimestamp(horizon)}])
        db.commit()
        return db.rowcount if hasattr(db, "rowcount") else 0