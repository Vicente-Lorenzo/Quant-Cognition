import re
import pymssql
from typing import Union, Callable, Any
from collections.abc import Sequence

from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Database.Database import DatabaseAPI
from Library.Utility.Typing import MISSING, Missing

class MicrosoftDatabaseAPI(DatabaseAPI):
    """
    Microsoft SQL Server database implementation.
    """

    _ADMIN_: str = "master"
    _PARAMETER_TOKEN_: Callable[[int], str] = staticmethod(lambda i: "%s")
    _PARAMETER_LIMIT_: int = 2000

    _CHECK_DATATYPE_MAPPING_: dict = {
        pl.Binary: "varbinary",
        pl.Boolean: "bit",

        pl.Int8: "smallint",
        pl.Int16: "smallint",
        pl.Int32: "int",
        pl.Int64: "bigint",

        pl.UInt8: "int",
        pl.UInt16: "int",
        pl.UInt32: "bigint",
        pl.UInt64: "decimal",

        pl.Float32: "real",
        pl.Float64: "float",
        pl.Decimal: "decimal",

        pl.String: "nvarchar",
        pl.Utf8: "nvarchar",

        pl.Date: "date",
        pl.Time: "time",
        pl.Datetime: "datetime2",
        pl.Duration: "bigint",

        pl.List: "nvarchar",
        pl.Array: "nvarchar",
        pl.Field: "nvarchar",
        pl.Struct: "nvarchar",

        pl.Enum: "nvarchar",
        pl.Categorical: "nvarchar",
        pl.Object: "nvarchar"
    }

    _CREATE_DATATYPE_MAPPING_: dict = {
        pl.Binary: "VARBINARY(MAX)",
        pl.Boolean: "BIT",

        pl.Int8: "SMALLINT",
        pl.Int16: "SMALLINT",
        pl.Int32: "INT",
        pl.Int64: "BIGINT",

        pl.UInt8: "INT",
        pl.UInt16: "INT",
        pl.UInt32: "BIGINT",
        pl.UInt64: "DECIMAL(20, 0)",

        pl.Float32: "REAL",
        pl.Float64: "FLOAT",
        pl.Decimal: "DECIMAL(38, 18)",

        pl.String: "NVARCHAR(MAX)",
        pl.Utf8: "NVARCHAR(MAX)",

        pl.Date: "DATE",
        pl.Time: "TIME",
        pl.Datetime: "DATETIME2",
        pl.Duration: "BIGINT",

        pl.List: "NVARCHAR(MAX)",
        pl.Array: "NVARCHAR(MAX)",
        pl.Field: "NVARCHAR(MAX)",
        pl.Struct: "NVARCHAR(MAX)",

        pl.Enum: "NVARCHAR(MAX)",
        pl.Categorical: "NVARCHAR(MAX)",
        pl.Object: "NVARCHAR(MAX)"
    }

    _DESCRIPTION_DATATYPE_MAPPING_: tuple = (
        (pymssql.DATETIME, pl.Datetime),
        (pymssql.STRING, pl.String),
        (pymssql.BINARY, pl.Binary)
    )

    def __init__(self, *,
                 host: str = "localhost",
                 port: int = 1433,
                 user: str = "master",
                 password: str = "master",
                 admin: bool = False,
                 database: Union[str, None] = None,
                 schema: Union[str, None] = None,
                 table: Union[str, None] = None,
                 legacy: bool = False,
                 migrate: bool = False,
                 autocommit: bool = True) -> None:
        """
        Initializes the Microsoft SQL Server database connection.
        :param host: The database host address.
        :param port: The database port number.
        :param user: The database username.
        :param password: The database password.
        :param admin: If True, connects with administrative privileges.
        :param database: The target database name.
        :param schema: The target schema name.
        :param table: The target table name.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :param migrate: If True, performs database migrations on connection.
        :param autocommit: If True, enables autocommit mode.
        """

        super().__init__(
            host=host,
            port=port,
            user=user,
            password=password,
            admin=admin,
            database=database,
            schema=schema,
            table=table,
            legacy=legacy,
            migrate=migrate,
            autocommit=autocommit
        )

    def _driver_(self, admin: bool) -> Any:
        database = self._ADMIN_ if admin or not self.database else self.database
        connection = pymssql.connect(
            server=self._host_,
            port=str(self._port_),
            user=self._user_,
            password=self._password_,
            database=database
        )
        connection.autocommit(self._autocommit_)
        return connection

    @property
    def _quote_(self) -> tuple[str, str]:
        return "[", "]"

    def _cast_(self, column: str) -> str:
        return f"CAST({column} AS NVARCHAR(MAX))"

    def listen(self, *, channel: str) -> bool:
        """
        Subscribes this connection to a Service Broker channel, creating the queue and
        service idempotently (requires the database to have the broker enabled).
        :param channel: The notification channel name.
        :return: True when the subscription is active.
        """
        cursor = self._connection_.cursor()
        cursor.execute(f"IF NOT EXISTS (SELECT 1 FROM sys.service_queues WHERE name = '{channel}') CREATE QUEUE [{channel}]")
        cursor.execute(f"IF NOT EXISTS (SELECT 1 FROM sys.services WHERE name = '{channel}') CREATE SERVICE [{channel}] ON QUEUE [{channel}] ([DEFAULT])")
        self._listened_ = channel
        return True

    def notify(self, *, channel: str) -> bool:
        """
        Publishes a Service Broker message on a channel, waking every ``wait`` on its queue.
        :param channel: The notification channel name.
        :return: True when the notification was published.
        """
        cursor = self._connection_.cursor()
        cursor.execute(f"DECLARE @handle UNIQUEIDENTIFIER; BEGIN DIALOG CONVERSATION @handle FROM SERVICE [{channel}] TO SERVICE '{channel}' WITH ENCRYPTION = OFF; SEND ON CONVERSATION @handle; END CONVERSATION @handle")
        return True

    def wait(self, *, timeout: float) -> bool:
        """
        Blocks on the listened Service Broker queue until a message arrives or the timeout
        elapses via ``WAITFOR (RECEIVE ...)``. Falls back to sleeping when nothing is listened.
        :param timeout: The maximum number of seconds to block.
        :return: True when a notification arrived, False on timeout.
        """
        channel = getattr(self, "_listened_", None)
        if channel is None: return super().wait(timeout=timeout)
        cursor = self._connection_.cursor()
        cursor.execute(f"WAITFOR (RECEIVE TOP (1) conversation_handle FROM [{channel}]), TIMEOUT {int(timeout * 1000)}")
        return cursor.fetchone() is not None

    def _limit_(self, sql: str, limit: int) -> str:
        return re.sub(r"(?i)^SELECT\s+(?:DISTINCT\s+|ALL\s+)?", lambda m: f"{m.group(0)}TOP {limit} ", sql.strip(), count=1)

    def _datatype_(self, dtype, *, indexed: bool = False) -> str:
        datatype = self._CREATE_DATATYPE_MAPPING_[self._normalize_(dtype)]
        return "NVARCHAR(450)" if indexed and datatype == "NVARCHAR(MAX)" else datatype

    def _identity_(self) -> str:
        return " IDENTITY(1, 1)"

    def _fingerprint_(self, *,
                      database: Union[str, Sequence, None, Missing] = MISSING,
                      schema: Union[str, Sequence, None, Missing] = MISSING,
                      table: Union[str, Sequence, None, Missing] = MISSING) -> Union[str, None]:
        sql = ("SELECT SUM(leaf_insert_count + leaf_update_count + leaf_delete_count) AS token "
               "FROM sys.dm_db_index_operational_stats(DB_ID(), OBJECT_ID(:fingerprint_object:), NULL, NULL)")
        db = self.executeone(QueryAPI(sql), database=database, admin=False, fingerprint_object=self._target_(schema, table))
        frame = db.fetchall(legacy=False)
        records = frame.to_dicts() if hasattr(frame, "to_dicts") else frame.to_dict("records")
        if records and records[0].get("token") is not None: return str(records[0]["token"])
        return None

    def _upsert_(self, target: str, columns: Sequence[str], keys: Sequence[str], exclude: Sequence[str] = (), returning: Sequence[str] = (), rows: int = 1) -> str:
        ql, qr = self._quote_
        n = QueryAPI.Named
        source_cols = self._quoted_(*columns)
        if rows == 1: source_vals = "(" + ", ".join(f"{n}{c}{n}" for c in columns) + ")"
        else: source_vals = ", ".join("(" + ", ".join(f"{n}{c}_{i}{n}" for c in columns) + ")" for i in range(rows))
        on_cond = " AND ".join(f"target.{ql}{k}{qr} = source.{ql}{k}{qr}" for k in keys)
        updates = ", ".join(f"target.{ql}{c}{qr} = source.{ql}{c}{qr}" for c in columns if c not in keys and c not in exclude)
        sql = f"MERGE INTO {target} AS target USING (VALUES {source_vals}) AS source({source_cols}) ON {on_cond}"
        if updates: sql += f" WHEN MATCHED THEN UPDATE SET {updates}"
        insert_vals = ", ".join(f"source.{ql}{c}{qr}" for c in columns)
        sql += f" WHEN NOT MATCHED THEN INSERT ({source_cols}) VALUES ({insert_vals})"
        if returning: sql += " OUTPUT " + ", ".join(f"inserted.{ql}{r}{qr}" for r in returning)
        sql += ";"
        return sql