import oracledb
from typing import Union, Callable, Any
from collections.abc import Sequence

from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Database.Database import DatabaseAPI, IdentityKey, PrimaryKey, ForeignKey

class OracleAPI(DatabaseAPI):
    """
    Oracle SQL database implementation.
    """

    _ADMIN_: str = "ORCL"
    _PARAMETER_TOKEN_: Callable[[int], str] = staticmethod(lambda i: f":{i}")
    _PARAMETER_LIMIT_: int = 32000

    _CHECK_DATATYPE_MAPPING_: dict = {
        pl.Binary: "BLOB",
        pl.Boolean: "NUMBER",

        pl.Int8: "NUMBER",
        pl.Int16: "NUMBER",
        pl.Int32: "NUMBER",
        pl.Int64: "NUMBER",

        pl.UInt8: "NUMBER",
        pl.UInt16: "NUMBER",
        pl.UInt32: "NUMBER",
        pl.UInt64: "NUMBER",

        pl.Float32: "FLOAT",
        pl.Float64: "FLOAT",
        pl.Decimal: "NUMBER",

        pl.String: "VARCHAR2",
        pl.Utf8: "VARCHAR2",

        pl.Date: "DATE",
        pl.Time: "INTERVAL DAY TO SECOND",
        pl.Datetime: "TIMESTAMP",
        pl.Duration: "INTERVAL DAY TO SECOND",

        pl.List: "VARCHAR2",
        pl.Array: "VARCHAR2",
        pl.Field: "VARCHAR2",
        pl.Struct: "VARCHAR2",

        pl.Enum: "VARCHAR2",
        pl.Categorical: "VARCHAR2",
        pl.Object: "VARCHAR2"
    }

    _CREATE_DATATYPE_MAPPING_: dict = {
        pl.Binary: "BLOB",
        pl.Boolean: "NUMBER(1)",

        pl.Int8: "NUMBER(3)",
        pl.Int16: "NUMBER(5)",
        pl.Int32: "NUMBER(10)",
        pl.Int64: "NUMBER(19)",

        pl.UInt8: "NUMBER(3)",
        pl.UInt16: "NUMBER(5)",
        pl.UInt32: "NUMBER(10)",
        pl.UInt64: "NUMBER(20)",

        pl.Float32: "FLOAT(24)",
        pl.Float64: "FLOAT(53)",
        pl.Decimal: "NUMBER(38, 18)",

        pl.String: "VARCHAR2(4000)",
        pl.Utf8: "VARCHAR2(4000)",

        pl.Date: "DATE",
        pl.Time: "INTERVAL DAY TO SECOND",
        pl.Datetime: "TIMESTAMP",
        pl.Duration: "INTERVAL DAY TO SECOND",

        pl.List: "VARCHAR2(4000)",
        pl.Array: "VARCHAR2(4000)",
        pl.Field: "VARCHAR2(4000)",
        pl.Struct: "VARCHAR2(4000)",

        pl.Enum: "VARCHAR2(4000)",
        pl.Categorical: "VARCHAR2(4000)",
        pl.Object: "VARCHAR2(4000)"
    }

    _DESCRIPTION_DATATYPE_MAPPING_: tuple = (
        (oracledb.DATETIME, pl.Datetime),
        (oracledb.STRING, pl.String),
        (oracledb.BINARY, pl.Binary)
    )

    def __init__(self, *,
                 host: str = "localhost",
                 port: int = 1521,
                 user: str = "ORCL",
                 password: str = "ORCL",
                 admin: bool = False,
                 database: Union[str, None] = None,
                 schema: Union[str, None] = None,
                 table: Union[str, None] = None,
                 legacy: bool = False,
                 migrate: bool = False,
                 autocommit: bool = True) -> None:
        """
        Initializes the Oracle SQL database connection.
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
        dsn = oracledb.makedsn(
            host=self._host_,
            port=self._port_,
            service_name=database
        )
        connection = oracledb.connect(
            user=self._user_,
            password=self._password_,
            dsn=dsn
        )
        connection.autocommit = self._autocommit_
        return connection

    @property
    def _quote_(self) -> tuple[str, str]:
        return '"', '"'

    def _cast_(self, column: str) -> str:
        return f"TO_CHAR({column})"

    def _limit_(self, sql: str, limit: int) -> str:
        return f"{sql} FETCH FIRST {limit} ROWS ONLY"

    def _check_(self, structure: Union[dict, None] = None) -> str:
        structure = structure if structure is not None else self._STRUCTURE_
        values = []
        for name, dtype in structure.items():
            datatype = self._CHECK_DATATYPE_MAPPING_[self._normalize_(dtype)]
            is_pk = int(isinstance(dtype, PrimaryKey) or (isinstance(dtype, (IdentityKey, ForeignKey)) and dtype.primary))
            is_fk = int(isinstance(dtype, ForeignKey))
            values.append(f"SELECT '{name}' AS column_name, '{datatype}' AS data_type, {is_pk} AS is_pk, {is_fk} AS is_fk FROM dual")
        return "\nUNION ALL\n".join(values)

    def _upsert_(self, target: str, columns: Sequence[str], keys: Sequence[str], exclude: Sequence[str] = (), returning: Sequence[str] = (), rows: int = 1) -> str:
        if returning: raise NotImplementedError("Oracle MERGE does not support RETURNING via this driver path")
        ql, qr = self._quote_
        n = QueryAPI.Named
        if rows == 1: source = "SELECT " + ", ".join(f"{n}{c}{n} AS {ql}{c}{qr}" for c in columns) + " FROM dual"
        else: source = " UNION ALL ".join("SELECT " + ", ".join(f"{n}{c}_{i}{n} AS {ql}{c}{qr}" for c in columns) + " FROM dual" for i in range(rows))
        on_cond = " AND ".join(f"target.{ql}{k}{qr} = source.{ql}{k}{qr}" for k in keys)
        updates = ", ".join(f"target.{ql}{c}{qr} = source.{ql}{c}{qr}" for c in columns if c not in keys and c not in exclude)
        insert_cols = self._quoted_(*columns)
        insert_vals = ", ".join(f"source.{ql}{c}{qr}" for c in columns)
        sql = f"MERGE INTO {target} target USING ({source}) source ON ({on_cond})"
        if updates: sql += f" WHEN MATCHED THEN UPDATE SET {updates}"
        sql += f" WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})"
        return sql