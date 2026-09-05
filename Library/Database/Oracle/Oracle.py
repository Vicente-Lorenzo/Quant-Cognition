import oracledb
from typing import Union, Callable, Any
from typing_extensions import Self
from collections.abc import Sequence

from Library.Database.Dataframe import pl
from Library.Database.Query import QueryAPI
from Library.Database.Database import DatabaseAPI, IdentityKey, PrimaryKey, ForeignKey
from Library.Utility.Typing import MISSING, Missing

class OracleDatabaseAPI(DatabaseAPI):
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

    def listen(self, *, channel: str) -> bool:
        """
        Subscribes this connection to an Oracle alert channel via ``DBMS_ALERT.REGISTER``.
        :param channel: The notification channel name.
        :return: True when the subscription is active.
        """
        cursor = self._connection_.cursor()
        cursor.callproc("DBMS_ALERT.REGISTER", [channel])
        return True

    def notify(self, *, channel: str) -> bool:
        """
        Publishes an Oracle alert on a channel via ``DBMS_ALERT.SIGNAL`` (delivered on commit).
        :param channel: The notification channel name.
        :return: True when the notification was published.
        """
        cursor = self._connection_.cursor()
        cursor.callproc("DBMS_ALERT.SIGNAL", [channel, ""])
        self._connection_.commit()
        return True

    def wait(self, *, timeout: float) -> bool:
        """
        Blocks until any registered alert fires or the timeout elapses via ``DBMS_ALERT.WAITANY``.
        :param timeout: The maximum number of seconds to block.
        :return: True when an alert arrived, False on timeout.
        """
        cursor = self._connection_.cursor()
        name, message, status = cursor.var(str), cursor.var(str), cursor.var(int)
        cursor.callproc("DBMS_ALERT.WAITANY", [name, message, status, timeout])
        return status.getvalue() == 0

    def _limit_(self, sql: str, limit: int) -> str:
        return f"{sql} FETCH FIRST {limit} ROWS ONLY"

    def realign(self, *,
                database: Union[str, None, Missing] = MISSING,
                schema: Union[str, None, Missing] = MISSING,
                table: Union[str, None, Missing] = MISSING,
                source: Union[str, None] = None) -> Self:
        if not source or not table: return self
        sql = ("SELECT c.constraint_name AS name, c.owner AS holder_schema, c.table_name AS holder_table, "
               "c.delete_rule AS deletion, "
               "(SELECT LISTAGG('\"' || k.column_name || '\"', ', ') WITHIN GROUP (ORDER BY k.position) "
               "FROM all_cons_columns k WHERE k.owner = c.owner AND k.constraint_name = c.constraint_name) AS holders, "
               "(SELECT LISTAGG('\"' || k.column_name || '\"', ', ') WITHIN GROUP (ORDER BY k.position) "
               "FROM all_cons_columns k WHERE k.owner = r.owner AND k.constraint_name = r.constraint_name) AS targets "
               "FROM all_constraints c JOIN all_constraints r ON r.owner = c.r_owner AND r.constraint_name = c.r_constraint_name "
               "WHERE c.constraint_type = 'R' AND r.table_name = :realign_source:")
        frame = self.executeone(QueryAPI(sql), database=database, admin=False, realign_source=source).fetchall(legacy=False)
        target = self._target_(schema, table)
        for row in self._records_(frame):
            owner = self._target_(row["holder_schema"], row["holder_table"])
            clause = f'FOREIGN KEY ({row["holders"]}) REFERENCES {target} ({row["targets"]})'
            if row["deletion"] and row["deletion"] != "NO ACTION": clause += f' ON DELETE {row["deletion"]}'
            self.executeone(QueryAPI(f'ALTER TABLE {owner} DROP CONSTRAINT "{row["name"]}"'), database=database, admin=False)
            self.executeone(QueryAPI(f'ALTER TABLE {owner} ADD CONSTRAINT "{row["name"]}" {clause}'), database=database, admin=False)
            self._log_.alert(lambda r=row: f"Realign Operation: Repointed {r['name']} · To {table}")
        return self

    def _ordinals_(self, *,
                   database: Union[str, None, Missing] = MISSING,
                   schema: Union[str, None, Missing] = MISSING,
                   table: Union[str, None, Missing] = MISSING) -> list:
        frame = self.executeone(QueryAPI("SELECT column_name FROM all_tab_columns WHERE owner = :order_schema: "
                                         "AND table_name = :order_table: ORDER BY column_id"),
                                database=database, admin=False, order_schema=schema, order_table=table).fetchall(legacy=False)
        return [next(iter(row.values())) for row in self._records_(frame)]

    def _carry_(self, *,
                database: Union[str, None, Missing] = MISSING,
                schema: Union[str, None, Missing] = MISSING,
                table: Union[str, None, Missing] = MISSING,
                columns: str = "",
                source: str = "") -> str:
        target = self._target_(schema, table)
        insert = f"INSERT INTO {target} ({columns}) SELECT {columns} FROM {source}"
        alter = f"""'ALTER TABLE {target} MODIFY ("' || generated || '" GENERATED """
        return ("DECLARE generated VARCHAR2(128); BEGIN "
                "BEGIN SELECT column_name INTO generated FROM all_tab_identity_cols "
                f"WHERE owner = '{schema}' AND table_name = '{table}' AND generation_type = 'ALWAYS' AND ROWNUM = 1; "
                "EXCEPTION WHEN NO_DATA_FOUND THEN generated := NULL; END; "
                f"IF generated IS NOT NULL THEN EXECUTE IMMEDIATE {alter}BY DEFAULT AS IDENTITY)'; END IF; "
                f"EXECUTE IMMEDIATE '{insert}'; "
                f"IF generated IS NOT NULL THEN EXECUTE IMMEDIATE {alter}ALWAYS AS IDENTITY)'; END IF; END;")

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