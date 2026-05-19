import psycopg
from typing import Union, Callable, Any
from collections.abc import Sequence

from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Database.Database import DatabaseAPI

class PostgresAPI(DatabaseAPI):
    """
    Postgres SQL database implementation.
    """

    _ADMIN_: str = "postgres"
    _PARAMETER_TOKEN_: Callable[[int], str] = staticmethod(lambda i: "%s")
    _PARAMETER_LIMIT_: int = 60000

    _CHECK_DATATYPE_MAPPING_: dict = {
        pl.Binary: "bytea",
        pl.Boolean: "boolean",

        pl.Int8: "smallint",
        pl.Int16: "smallint",
        pl.Int32: "integer",
        pl.Int64: "bigint",

        pl.UInt8: "integer",
        pl.UInt16: "integer",
        pl.UInt32: "bigint",
        pl.UInt64: "numeric",

        pl.Float32: "real",
        pl.Float64: "double precision",
        pl.Decimal: "numeric",

        pl.String: "character varying",
        pl.Utf8: "character varying",

        pl.Date: "date",
        pl.Time: "time without time zone",
        pl.Datetime: "timestamp without time zone",
        pl.Duration: "interval",

        pl.List: "character varying",
        pl.Array: "character varying",
        pl.Field: "character varying",
        pl.Struct: "character varying",

        pl.Enum: "character varying",
        pl.Categorical: "character varying",
        pl.Object: "character varying"
    }

    _CREATE_DATATYPE_MAPPING_: dict = {
        pl.Binary: "BYTEA",
        pl.Boolean: "BOOLEAN",

        pl.Int8: "SMALLINT",
        pl.Int16: "SMALLINT",
        pl.Int32: "INTEGER",
        pl.Int64: "BIGINT",

        pl.UInt8: "INTEGER",
        pl.UInt16: "INTEGER",
        pl.UInt32: "BIGINT",
        pl.UInt64: "NUMERIC",

        pl.Float32: "REAL",
        pl.Float64: "DOUBLE PRECISION",
        pl.Decimal: "NUMERIC",

        pl.String: "VARCHAR",
        pl.Utf8: "VARCHAR",

        pl.Date: "DATE",
        pl.Time: "TIME",
        pl.Datetime: "TIMESTAMP",
        pl.Duration: "INTERVAL",

        pl.List: "VARCHAR",
        pl.Array: "VARCHAR",
        pl.Field: "VARCHAR",
        pl.Struct: "VARCHAR",

        pl.Enum: "VARCHAR",
        pl.Categorical: "VARCHAR",
        pl.Object: "VARCHAR"
    }

    _DESCRIPTION_DATATYPE_MAPPING_: tuple = (
        (psycopg.DATETIME, pl.Datetime),
        (psycopg.STRING, pl.String),
        (psycopg.BINARY, pl.Binary)
    )

    def __init__(self, *,
                 host: str = "localhost",
                 port: int = 5432,
                 user: str = "postgres",
                 password: str = "postgres",
                 admin: bool = False,
                 database: Union[str, None] = None,
                 schema: Union[str, None] = None,
                 table: Union[str, None] = None,
                 legacy: bool = False,
                 migrate: bool = False,
                 autocommit: bool = True) -> None:
        """
        Initializes the Postgres SQL database connection.
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
            admin=admin,
            password=password,
            database=database,
            schema=schema,
            table=table,
            legacy=legacy,
            migrate=migrate,
            autocommit=autocommit
        )

    def _driver_(self, admin: bool) -> Any:
        database = self._ADMIN_ if admin or not self.database else self.database
        connection = psycopg.connect(
            host=self._host_,
            port=self._port_,
            user=self._user_,
            password=self._password_,
            dbname=database
        )
        connection.autocommit = self._autocommit_
        return connection

    @property
    def _quote_(self) -> tuple[str, str]:
        return '"', '"'

    def _cast_(self, column: str) -> str:
        return f"{column}::TEXT"

    def _limit_(self, sql: str, limit: int) -> str:
        return f"{sql} LIMIT {limit}"

    def _upsert_(self, target: str, columns: Sequence[str], keys: Sequence[str], exclude: Sequence[str] = (), returning: Sequence[str] = (), rows: int = 1) -> str:
        ql, qr = self._quote_
        n = QueryAPI.Named
        cols_str = self._quoted_(*columns)
        if rows == 1: vals_str = "(" + ", ".join(f"{n}{c}{n}" for c in columns) + ")"
        else: vals_str = ", ".join("(" + ", ".join(f"{n}{c}_{i}{n}" for c in columns) + ")" for i in range(rows))
        key_str = self._quoted_(*keys)
        updates = ", ".join(f"{ql}{c}{qr} = EXCLUDED.{ql}{c}{qr}" for c in columns if c not in keys and c not in exclude)
        sql = f"INSERT INTO {target} ({cols_str}) VALUES {vals_str} ON CONFLICT ({key_str})"
        sql += f" DO UPDATE SET {updates}" if updates else " DO NOTHING"
        if returning: sql += f" RETURNING {self._quoted_(*returning)}"
        return sql