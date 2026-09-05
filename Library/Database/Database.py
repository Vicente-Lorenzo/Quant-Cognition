import time
import uuid
import datetime
import threading
import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from typing_extensions import Self
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Union, Callable, Any

from Library.Utility.Profiler import Timer
from Library.Database.Dataframe import DataframeAPI, pd, pl
from Library.Database.Query import QueryAPI
from Library.Utility.Service import ServiceAPI
from Library.Utility.Memory import memory_to_string
from Library.Logging import LoggingAPI
from Library.Utility.Path import PathAPI, traceback_package
from Library.Utility.Typing import MISSING, Missing

@dataclass
class IdentityKey:
    """
    Represents an auto-generated identity column (surrogate key).
    """
    dtype: Union[type, pl.DataType]
    primary: bool = False

@dataclass
class PrimaryKey:
    """
    Represents a primary key in the database structure.
    """
    dtype: Union[type, pl.DataType]

@dataclass
class ForeignKey:
    """
    Represents a foreign key in the database structure.
    """
    dtype: Union[type, pl.DataType]
    reference: str
    primary: bool = False

class DatabaseAPI(ServiceAPI, DataframeAPI, ABC):
    """
    Abstract base class for database integrations.
    """

    _ALL_: str = "*"
    _ADMIN_: Union[str, None] = None
    _PARAMETER_TOKEN_: Callable[[int], str] | None = None
    _PARAMETER_LIMIT_: int = 1000
    _SCOPES_: contextvars.ContextVar = contextvars.ContextVar("_SCOPES_", default=None)

    _PYTHON_DATATYPE_MAPPING_: dict = {
        bytes: pl.Binary,
        bool: pl.Boolean,
        int: pl.Int64,
        float: pl.Float64,
        str: pl.String,
        datetime.date: pl.Date,
        datetime.datetime: pl.Datetime,
    }

    _CHECK_DATATYPE_MAPPING_: Union[dict, None] = None
    _CREATE_DATATYPE_MAPPING_: Union[dict, None] = None
    _DESCRIPTION_DATATYPE_MAPPING_: Union[tuple, None] = None
    _STRUCTURE_: dict[str, type | type[pl.DataType] | pl.DataType | IdentityKey | PrimaryKey | ForeignKey] | None = None

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if DatabaseAPI not in cls.__bases__: return
        module: str = traceback_package(package=cls.__module__)
        cls._CHECK_DATABASE_QUERY_ = QueryAPI(PathAPI(path="Database/Check.sql", module=module))
        cls._CREATE_DATABASE_QUERY_ = QueryAPI(PathAPI(path="Database/Create.sql", module=module))
        cls._DELETE_DATABASE_QUERY_ = QueryAPI(PathAPI(path="Database/Delete.sql", module=module))
        cls._REFACTOR_DATABASE_QUERY_ = QueryAPI(PathAPI(path="Database/Refactor.sql", module=module))
        cls._CHECK_SCHEMA_QUERY_ = QueryAPI(PathAPI(path="Schema/Check.sql", module=module))
        cls._CREATE_SCHEMA_QUERY_ = QueryAPI(PathAPI(path="Schema/Create.sql", module=module))
        cls._DELETE_SCHEMA_QUERY_ = QueryAPI(PathAPI(path="Schema/Delete.sql", module=module))
        cls._REFACTOR_SCHEMA_QUERY_ = QueryAPI(PathAPI(path="Schema/Refactor.sql", module=module))
        cls._CHECK_TABLE_QUERY_ = QueryAPI(PathAPI(path="Table/Check.sql", module=module))
        cls._CREATE_TABLE_QUERY_ = QueryAPI(PathAPI(path="Table/Create.sql", module=module))
        cls._DELETE_TABLE_QUERY_ = QueryAPI(PathAPI(path="Table/Delete.sql", module=module))
        cls._REFACTOR_TABLE_QUERY_ = QueryAPI(PathAPI(path="Table/Refactor.sql", module=module))
        cls._RENAME_COLUMN_QUERY_ = QueryAPI(PathAPI(path="Table/Rename.sql", module=module))
        cls._CHECK_STRUCTURE_QUERY_ = QueryAPI(PathAPI(path="Table/Structure.sql", module=module))
        cls._LIST_CATALOG_QUERY_ = QueryAPI(PathAPI(path="System/List.sql", module=module))
        cls._SEARCH_CATALOG_QUERY_ = QueryAPI(PathAPI(path="System/Search.sql", module=module))
        cls._LIST_SESSIONS_QUERY_ = QueryAPI(PathAPI(path="System/Sessions.sql", module=module))
        cls._KILL_SESSION_QUERY_ = QueryAPI(PathAPI(path="System/Kill.sql", module=module))
        cls._SIZE_CATALOG_QUERY_ = QueryAPI(PathAPI(path="System/Size.sql", module=module))

    def __init__(self, *,
                 host: str,
                 port: int,
                 user: str,
                 password: str,
                 admin: bool,
                 database: Union[str, None],
                 schema: Union[str, None],
                 table: Union[str, None],
                 legacy: bool,
                 migrate: bool,
                 autocommit: bool) -> None:
        super().__init__(legacy=legacy)

        self._host_: str = host
        self._port_: int = port
        self._user_: str = user
        self._password_: str = password
        self._admin_: bool = admin
        self._migrate_: bool = migrate
        self._autocommit_: bool = autocommit

        self._database_: Union[str, None] = database
        self._schema_: Union[str, None] = schema
        self._table_: Union[str, None] = table

        self._connection_ = None
        self._transaction_ = None
        self._cursor_ = None
        self._origin_ = None
        self._borrowed_ = False
        self._pool_ = {}
        self._lock_ = threading.RLock()

        self._log_ = LoggingAPI(*(value for value in (database, schema, table) if value is not None))

    @property
    @abstractmethod
    def _quote_(self) -> tuple[str, str]: raise NotImplementedError

    @abstractmethod
    def _cast_(self, column: str) -> str: raise NotImplementedError

    @abstractmethod
    def _limit_(self, sql: str, limit: int) -> str: raise NotImplementedError

    @abstractmethod
    def _upsert_(self, target: str, columns: Sequence[str], keys: Sequence[str], exclude: Sequence[str] = (), returning: Sequence[str] = (), rows: int = 1) -> str: raise NotImplementedError

    @abstractmethod
    def _driver_(self, admin: bool) -> Any: raise NotImplementedError

    def _borrow_(self, admin: bool) -> Any:
        origin = self._origin_
        if admin or origin is None or not self.autocommited() or not origin.connected(): return None
        return origin._connection_ if origin._link_ == self._link_ else None

    def _connect_(self, admin: bool = False) -> None:
        shared = self._borrow_(admin)
        self._borrowed_ = shared is not None
        self._connection_ = shared if self._borrowed_ else self._driver_(admin=admin or self._admin_)
        self._transaction_ = False
        self._cursor_ = self._connection_.cursor()

    def __enter__(self) -> Self: return self.migration() if self._migrate_ else self.connect()

    def _disconnect_(self) -> None:
        if self._cursor_ is not None:
            self._cursor_.close()
            self._cursor_ = None
        if self._connection_ is not None:
            if not self._borrowed_: self._connection_.close()
            self._connection_ = None
            self._borrowed_ = False

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type or exc_val or exc_tb: self.rollback()
        else: self.commit()
        return super().__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def _select_(target: str, columns: str) -> str:
        return f"SELECT {columns} FROM {target}"

    @staticmethod
    def _condition_(sql: str, condition: Union[str, None]) -> str:
        return f"{sql} WHERE {condition}" if condition else sql

    @staticmethod
    def _order_(sql: str, order: Union[str, None]) -> str:
        return f"{sql} ORDER BY {order}" if order else sql

    @staticmethod
    def _insert_(target: str, columns: str, values: str) -> str:
        return f"INSERT INTO {target} ({columns}) VALUES ({values})" if columns else f"INSERT INTO {target} VALUES ({values})"

    @staticmethod
    def _update_(target: str, set_string: str) -> str:
        return f"UPDATE {target} SET {set_string}"

    @staticmethod
    def _delete_(target: str) -> str:
        return f"DELETE FROM {target}"

    @staticmethod
    def _add_(target: str, column: str, datatype: str) -> str:
        return f"ALTER TABLE {target} ADD {column} {datatype}"

    @staticmethod
    def _drop_(target: str, column: str) -> str:
        return f"ALTER TABLE {target} DROP COLUMN {column}"

    @staticmethod
    def _concat_(frames: Sequence) -> pl.DataFrame:
        if not frames: return pl.DataFrame()
        return pl.concat(frames, how="vertical_relaxed") if isinstance(frames[0], pl.DataFrame) else pd.concat(frames)

    @classmethod
    def _normalize_(cls, dtype) -> type:
        if isinstance(dtype, (IdentityKey, PrimaryKey, ForeignKey)): dtype = dtype.dtype
        dtype = cls._PYTHON_DATATYPE_MAPPING_.get(dtype, dtype)
        if isinstance(dtype, type) and issubclass(dtype, pl.DataType): return dtype
        if isinstance(dtype, pl.DataType): return dtype.__class__
        raise TypeError(f"Not a valid Structure dtype: {dtype}")

    def _target_(self, schema: str, table: str) -> str:
        ql, qr = self._quote_
        return f"{ql}{schema}{qr}.{ql}{table}{qr}"

    def _quoted_(self, *columns: str) -> str:
        ql, qr = self._quote_
        return ", ".join(f"{ql}{c}{qr}" for c in columns)

    @staticmethod
    def _records_(frame: Union[pd.DataFrame, pl.DataFrame]) -> list:
        return frame.to_dicts() if hasattr(frame, "to_dicts") else frame.to_dict("records")

    @property
    def _params_(self) -> dict:
        keys = ["_host_", "_port_", "_user_", "_password_", "_admin_", "_database_", "_schema_", "_table_", "_legacy_", "_migrate_", "_autocommit_"]
        return {k.strip("_"): v for k, v in self.__dict__.items() if k in keys}

    @property
    def _link_(self) -> tuple:
        return self._host_, self._port_, self._user_, self._password_, self._admin_, self._database_, self._autocommit_

    @property
    def _hash_(self) -> int:
        return hash(tuple(sorted(self._params_.items())))

    def _query_(self, query: QueryAPI, **kwargs) -> tuple[str, list[Union[int, str]], dict]:
        defaults = {}
        if self.database is not None: defaults["database"] = self.database
        if self.schema is not None: defaults["schema"] = self.schema
        if self.table is not None: defaults["table"] = self.table
        kwargs = {**defaults, **kwargs}
        sql, configuration = query.compile(self._PARAMETER_TOKEN_, **kwargs)
        return sql, configuration, kwargs

    def _frame_(self, result, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        if result is None: rows = []
        elif isinstance(result, list): rows = result
        elif isinstance(result, tuple): rows = [result]
        else: rows = list(result)
        schema = {}
        for col_name, type_code, *_ in self._cursor_.description or []:
            if self._STRUCTURE_ and col_name in self._STRUCTURE_:
                schema[col_name] = self._normalize_(self._STRUCTURE_[col_name])
            elif self._DESCRIPTION_DATATYPE_MAPPING_:
                schema[col_name] = next((p for d, p in self._DESCRIPTION_DATATYPE_MAPPING_ if type_code == d), None)
            else:
                schema[col_name] = None
        return self.frame(data=rows, schema=schema, legacy=legacy)

    def _check_(self, structure: Union[dict, None] = None) -> str:
        structure = structure if structure is not None else self._STRUCTURE_
        values = []
        for name, dtype in structure.items():
            datatype = self._CHECK_DATATYPE_MAPPING_[self._normalize_(dtype)]
            is_pk = int(isinstance(dtype, PrimaryKey) or (isinstance(dtype, (IdentityKey, ForeignKey)) and dtype.primary))
            is_fk = int(isinstance(dtype, ForeignKey))
            values.append(f"('{name}', '{datatype}', {is_pk}, {is_fk})")
        return ",\n    ".join(values)

    def _create_(self, structure: Union[dict, None] = None) -> str:
        structure = structure if structure is not None else self._STRUCTURE_
        ql, qr = self._quote_
        defs = []
        pks = []
        for name, dtype in structure.items():
            indexed = isinstance(dtype, (PrimaryKey, IdentityKey, ForeignKey))
            base = self._datatype_(dtype, indexed=indexed)
            if isinstance(dtype, IdentityKey):
                if dtype.primary: pks.append(name)
                else: base += " UNIQUE"
                base += self._identity_()
            elif isinstance(dtype, PrimaryKey):
                pks.append(name)
            elif isinstance(dtype, ForeignKey):
                if dtype.primary: pks.append(name)
                base += f" REFERENCES {dtype.reference}"
            defs.append(f"{ql}{name}{qr} {base}")
        if pks:
            pk_cols = ", ".join(f"{ql}{c}{qr}" for c in pks)
            defs.append(f"PRIMARY KEY ({pk_cols})")
        return ",\n    ".join(defs)

    def _datatype_(self, dtype, *, indexed: bool = False) -> str:
        return self._CREATE_DATATYPE_MAPPING_[self._normalize_(dtype)]

    def _identity_(self) -> str:
        return " GENERATED ALWAYS AS IDENTITY"

    def _structure_keys_(self) -> list:
        if not self._STRUCTURE_: return []
        return [name for name, dtype in self._STRUCTURE_.items() if isinstance(dtype, PrimaryKey) or (isinstance(dtype, (IdentityKey, ForeignKey)) and dtype.primary)]

    def _route_(self, method: str, database: Any, schema: Any, table: Any, args: tuple = (), **kwargs) -> Union[tuple[str | None, str | None, str | None], list]:
        db = database if database is not MISSING else self._database_
        sc = schema if schema is not MISSING else self._schema_
        tb = table if table is not MISSING else self._table_
        def resolve_refactor(items, field_name):
            names = kwargs.get("name")
            if not isinstance(names, (list, tuple)) or len(names) != len(items):
                raise ValueError(f"Name must be a list/tuple of the same length as {field_name}")
            for item, n in zip(items, names):
                kw = {"database": db, "schema": sc, "table": tb}
                kw.update({k: v for k, v in kwargs.items() if k != "name"})
                kw.update({field_name.lower(): item, "name": n})
                getattr(self, method)(*args, **kw)
            return [self]
        if isinstance(db, (list, tuple)):
            if method == "refactor" and isinstance(kwargs.get("name"), (list, tuple)): return resolve_refactor(db, "Database")
            return [getattr(self, method)(*args, database=d, schema=sc, table=tb, **{**kwargs, "legacy": False} if "legacy" in kwargs else kwargs) for d in db]
        if isinstance(sc, (list, tuple)):
            if method == "refactor" and isinstance(kwargs.get("name"), (list, tuple)): return resolve_refactor(sc, "Schema")
            return [getattr(self, method)(*args, database=db, schema=s, table=tb, **{**kwargs, "legacy": False} if "legacy" in kwargs else kwargs) for s in sc]
        if isinstance(tb, (list, tuple)):
            if method == "refactor" and isinstance(kwargs.get("name"), (list, tuple)): return resolve_refactor(tb, "Table")
            return [getattr(self, method)(*args, database=db, schema=sc, table=t, **{**kwargs, "legacy": False} if "legacy" in kwargs else kwargs) for t in tb]
        return db, sc, tb

    def _clone_(self, method: str, args: tuple, database: Any, schema: Any, table: Any, admin: Any, **kwargs) -> Union[Self, None]:
        target_admin = admin if admin is not MISSING else self._admin_
        db = self.clone(database=database, schema=schema, table=table, admin=target_admin)
        if db is not self:
            db.connect()
            return getattr(db, method)(*args, database=database, schema=schema, table=table, admin=admin, **kwargs)
        return None

    @property
    def database(self) -> Union[str, None]:
        """Returns the current database name."""
        if self._admin_ or not self._database_: return self._ADMIN_
        return self._database_

    @property
    def schema(self) -> Union[str, None]:
        """Returns the current schema name."""
        return self._schema_

    @property
    def table(self) -> Union[str, None]:
        """Returns the current table name."""
        return self._table_

    @property
    def rowcount(self) -> int:
        """Returns the number of rows affected by the last executed statement."""
        return self._cursor_.rowcount if self._cursor_ is not None else 0

    def connected(self) -> bool:
        """Checks if the database connection is active."""
        return self._connection_ is not None and self._cursor_ is not None

    def disconnected(self) -> bool:
        """Checks if the database connection is closed."""
        return self._connection_ is None and self._cursor_ is None

    def autocommited(self) -> bool:
        """Checks if autocommit mode is enabled."""
        return self._autocommit_ is True

    def transitioned(self) -> bool:
        """Checks if a transaction is currently open."""
        return self._transaction_ is True

    def databased(self) -> bool:
        """Checks if a database is currently selected."""
        return self.database is not None

    def schemed(self) -> bool:
        """Checks if a schema is currently selected."""
        return self.schema is not None

    def tabled(self) -> bool:
        """Checks if a table is currently selected."""
        return self.table is not None

    def structured(self) -> bool:
        """Checks if a table structure is defined."""
        return self._STRUCTURE_ is not None

    @classmethod
    @contextmanager
    def scope(cls, **params) -> Any:
        """
        Binds one connection to the enclosing block, for every attach() nested inside it to reuse.
        :param params: Connection parameters, as passed to the constructor.
        :return: A context manager yielding the bound instance.

        A caller that makes several calls in a row otherwise pays a fresh connection for each, and a
        connection is the expensive part by an order of magnitude — the server builds a backend
        process for it. Scoping one to the unit of work spends that once. The binding lives in a
        context variable, so concurrent requests never see each other's connection, and it is
        released when the block exits — a connection is never reused across scopes, which is what
        keeps the count bounded by work in flight rather than by uptime.

        The binding is lazy: the connection opens on the first attach() that needs it, so wrapping a
        unit of work that turns out to touch nothing costs nothing.
        """
        db = cls(**params)
        scopes = {**(cls._SCOPES_.get() or {}), (cls, db._link_): db}
        token = cls._SCOPES_.set(scopes)
        try: yield db
        finally:
            cls._SCOPES_.reset(token)
            db.disconnect()

    @classmethod
    @contextmanager
    def attach(cls, **params) -> Any:
        """
        Yields the connection an enclosing scope() bound, or opens one for this block when there is none.
        :param params: Connection parameters, as passed to the constructor.
        :return: A context manager yielding a connected instance.
        """
        db = cls(**params)
        scoped = (cls._SCOPES_.get() or {}).get((cls, db._link_))
        if scoped is not None:
            if scoped.disconnected(): scoped.connect()
            yield scoped
            return
        with db as opened: yield opened

    def clone(self, **kwargs) -> Self:
        """
        Creates and returns a clone of the database instance with updated parameters.
        :param kwargs: Updated connection or structural parameters.
        :return: A cloned instance of the DatabaseAPI.
        """
        params = self._params_
        for k, v in kwargs.items():
            if v is not MISSING: params[k] = v
        key = hash(tuple(sorted(params.items())))
        if key == self._hash_:
            self._log_.debug(lambda: "Clone Operation: Skipped (Parameters match self)")
            return self
        with self._lock_:
            if key in self._pool_:
                self._log_.debug(lambda: "Clone Operation: Skipped (Retrieved from pool)")
                return self._pool_[key]
            self._log_.debug(lambda: "Clone Operation: Created (Added to pool)")
            clone = self.__class__(**params)
            clone._origin_ = self
            self._pool_[key] = clone
            return clone

    def disconnect(self) -> bool:
        """
        Closes the database connection and clears the connection pool.
        :return: Boolean indicating successful disconnection.
        """
        with self._lock_:
            for db in self._pool_.values():
                db.disconnect()
            self._pool_.clear()
        return super().disconnect()

    def commit(self) -> Self:
        """
        Commits the current transaction.
        :return: Self reference.
        """
        if not self.connected(): self._log_.debug(lambda: "Commit Operation: Skipped (Not Connected)")
        elif self.autocommited(): self._log_.debug(lambda: "Commit Operation: Skipped (Autocommit Enabled)")
        elif not self.transitioned(): self._log_.debug(lambda: "Commit Operation: Skipped (No Open Transaction)")
        else:
            timer = Timer()
            timer.start()
            self._connection_.commit()
            self._transaction_ = False
            timer.stop()
            self._log_.debug(lambda: f"Commit Operation: Closed Transaction ({timer.result()})")
        return self

    def rollback(self) -> Self:
        """
        Rolls back the current transaction.
        :return: Self reference.
        """
        if not self.connected(): self._log_.debug(lambda: "Rollback Operation: Skipped (Not Connected)")
        elif self.autocommited(): self._log_.debug(lambda: "Rollback Operation: Skipped (Autocommit Enabled)")
        elif not self.transitioned(): self._log_.debug(lambda: "Rollback Operation: Skipped (No Open Transaction)")
        else:
            timer = Timer()
            timer.start()
            self._connection_.rollback()
            self._transaction_ = False
            timer.stop()
            self._log_.debug(lambda: f"Rollback Operation: Closed Transaction ({timer.result()})")
        return self

    def fetchone(self, *, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Fetches the next row of a query result set.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the fetched row.
        """
        timer, df = self._fetch_(callback=lambda: self._frame_(self._cursor_.fetchone(), legacy=legacy), abort=self.rollback)
        self._log_.debug(lambda: f"Fetch One Operation: Fetched {len(df)} Data Points ({timer.result()})")
        return df

    def fetchmany(self, *, n: int, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Fetches the next set of rows of a query result.
        :param n: The number of rows to fetch.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the fetched rows.
        """
        timer, df = self._fetch_(callback=lambda: self._frame_(self._cursor_.fetchmany(n), legacy=legacy), abort=self.rollback)
        self._log_.debug(lambda: f"Fetch Many Operation: Fetched {len(df)} Data Points ({timer.result()})")
        return df

    def fetchall(self, *, legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Fetches all remaining rows of a query result.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the fetched rows.
        """
        timer, df = self._fetch_(callback=lambda: self._frame_(self._cursor_.fetchall(), legacy=legacy), abort=self.rollback)
        self._log_.debug(lambda: f"Fetch All Operation: Fetched {len(df)} Data Points ({timer.result()})")
        return df

    def executeone(self, query: QueryAPI, *args, database: Union[str, Sequence, None, Missing] = MISSING, schema: Union[str, Sequence, None, Missing] = MISSING, table: Union[str, Sequence, None, Missing] = MISSING, admin: Union[bool, Missing] = MISSING, **kwargs) -> Self:
        """
        Executes a query with a single set of parameters.
        :param query: The QueryAPI instance to execute.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param admin: If True, executes with administrative privileges.
        :param kwargs: Additional query parameters.
        :return: Self reference.
        """
        routed = self._route_("executeone", database, schema, table, args=(query, *args), admin=admin, **kwargs)
        if isinstance(routed, list): return self
        database, schema, table = routed
        clone_result = self._clone_("executeone", (query, *args), database, schema, table, admin, **kwargs)
        if clone_result is not None: return clone_result
        if database is not MISSING: kwargs["database"] = database
        if schema is not MISSING: kwargs["schema"] = schema
        if table is not MISSING: kwargs["table"] = table
        sql, configuration, kwargs = self._query_(query, **kwargs)
        parameters = query.bind(configuration, *args, **kwargs) if configuration else None
        def _execute_():
            if parameters is not None: self._cursor_.execute(sql, parameters)
            else: self._cursor_.execute(sql)
            self._transaction_ = True
        timer = self._execute_(callback=_execute_, abort=self.rollback)
        self._log_.debug(lambda: f"Execute One Operation: Executed ({timer.result()})")
        return self

    def executemany(self, query: QueryAPI, *args, database: Union[str, Sequence, None, Missing] = MISSING, schema: Union[str, Sequence, None, Missing] = MISSING, table: Union[str, Sequence, None, Missing] = MISSING, admin: Union[bool, Missing] = MISSING, **kwargs) -> Self:
        """
        Executes a query repeatedly with a batch of parameters.
        :param query: The QueryAPI instance to execute.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param admin: If True, executes with administrative privileges.
        :param kwargs: Additional query parameters.
        :return: Self reference.
        """
        routed = self._route_("executemany", database, schema, table, args=(query, *args), admin=admin, **kwargs)
        if isinstance(routed, list): return self
        database, schema, table = routed
        clone_result = self._clone_("executemany", (query, *args), database, schema, table, admin, **kwargs)
        if clone_result is not None: return clone_result
        if database is not MISSING: kwargs["database"] = database
        if schema is not MISSING: kwargs["schema"] = schema
        if table is not MISSING: kwargs["table"] = table
        batch = self.flatten(args[0]) if len(args) == 1 else self.flatten(args)
        if not batch or not all(isinstance(row, (list, tuple, dict)) for row in batch):
            e = ValueError("Expecting batch as tuple/list of tuples/lists or tuple/list of dicts")
            self._log_.error(lambda: f"Execute Many Operation: Failed · {e}")
            self._log_.exception(lambda: f"Execute Many Operation: Failed · {e}")
            raise e
        if not all(isinstance(row, type(batch[0])) for row in batch):
            e = ValueError("Expecting batch to be the same type (all tuples, all lists, or all dicts)")
            self._log_.error(lambda: f"Execute Many Operation: Failed · {e}")
            self._log_.exception(lambda: f"Execute Many Operation: Failed · {e}")
            raise e
        sql, configuration, kwargs = self._query_(query, **kwargs)
        parameters = []
        for row in batch:
            if isinstance(row, dict): parameters.append(query.bind(configuration, **{**kwargs, **row}))
            else: parameters.append(query.bind(configuration, *row, **kwargs))
        def _execute_():
            self._cursor_.executemany(sql, parameters)
            self._transaction_ = True
        timer = self._execute_(callback=_execute_, abort=self.rollback)
        self._log_.debug(lambda: f"Execute Many Operation: Executed ({timer.result()})")
        return self

    def execute(self, query: QueryAPI, *args, database: Union[str, Sequence, None, Missing] = MISSING, schema: Union[str, Sequence, None, Missing] = MISSING, table: Union[str, Sequence, None, Missing] = MISSING, admin: Union[bool, Missing] = MISSING, **kwargs) -> Self:
        """
        Executes a query, handling either single or multiple parameter sets automatically.
        :param query: The QueryAPI instance to execute.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param admin: If True, executes with administrative privileges.
        :param kwargs: Additional query parameters.
        :return: Self reference.
        """
        if not args:
            return self.executeone(query, database=database, schema=schema, table=table, admin=admin, **kwargs)
        data = args[0] if len(args) == 1 else args
        columns, records, multiple = self.parse(data)
        if not records: return self
        if multiple:
            self.executemany(query, records, database=database, schema=schema, table=table, admin=admin, **kwargs)
        elif columns:
            self.executeone(query, database=database, schema=schema, table=table, admin=admin, **{**kwargs, **records[0]})
        else:
            self.executeone(query, *records[0], database=database, schema=schema, table=table, admin=admin, **kwargs)
        return self

    def list(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               system: bool = False,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Lists available databases, schemas, and tables.
        :param database: Target database(s).
        :param schema: Target schema(s).
        :param table: Target table(s).
        :param system: If True, includes system tables.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the catalog structure.
        """
        routed = self._route_("list", database, schema, table, system=system, legacy=legacy)
        if isinstance(routed, list): return self.frame(self._concat_(routed), legacy=legacy)
        database, schema, table = routed
        database = database or "%"
        schema = schema or "%"
        table = table or "%"
        system = 1 if system else 0
        self._log_.debug(lambda: "List Operation: Fetching structural catalog")
        df = self.executeone(self._LIST_CATALOG_QUERY_, database=database, schema=schema, table=table, system=system, admin=True).fetchall(legacy=False)
        if df.is_empty() or "Database" not in df.columns:
            return self.frame(df, legacy=legacy)
        databases = df["Database"].unique().to_list()
        expansion = database == "%" or any(d != self.database for d in databases)
        if not expansion:
            return self.frame(df, legacy=legacy)
        frames = []
        for db_name in databases:
            db_df = self.executeone(self._LIST_CATALOG_QUERY_, database=db_name, schema=schema, table=table, system=system, admin=False).fetchall(legacy=False)
            frames.append(db_df if not db_df.is_empty() else df.filter(pl.col("Database") == db_name))
        return self.frame(self._concat_(frames) if frames else df, legacy=legacy)

    def search(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               column: Union[str, Sequence, None] = None,
               row: Union[int, float, str, None] = None,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Searches for specific values within the catalog.
        :param database: Target database(s).
        :param schema: Target schema(s).
        :param table: Target table(s).
        :param column: Target column(s) to search in.
        :param row: The value to search for.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the search results.
        """
        if column is None and row is None:
            raise ValueError("Column or Row must be provided to search")
        routed = self._route_("search", database, schema, table, column=column, row=row, legacy=legacy)
        if isinstance(routed, list): return self.frame(self._concat_(routed), legacy=legacy)
        database, schema, table = routed
        if isinstance(column, (list, tuple)):
            return self.frame(self._concat_([self.search(database=database, schema=schema, table=table, column=c, row=row, legacy=False) for c in column]), legacy=legacy)
        database = database or "%"
        schema = schema or "%"
        table = table or "%"
        column = column or "%"
        self._log_.debug(lambda: "Search Operation: Searching catalog")
        databases = self.executeone(self._LIST_CATALOG_QUERY_, database=database, schema="%", table="%", system=0, admin=True).fetchall(legacy=False)
        if databases.is_empty() or "Database" not in databases.columns:
            return self.frame(pl.DataFrame({"Database": [], "Schema": [], "Table": [], "Column": []}), legacy=legacy)
        catalog_frames = []
        for db_name in databases["Database"].unique().to_list():
            df = self.executeone(self._SEARCH_CATALOG_QUERY_, database=db_name, schema=schema, table=table, column=column, admin=False).fetchall(legacy=False)
            if not df.is_empty():
                catalog_frames.append(df)
        catalog = self._concat_(catalog_frames) if catalog_frames else pl.DataFrame({"Database": [], "Schema": [], "Table": [], "Column": []})
        if catalog.is_empty() or row is None:
            return self.frame(catalog, legacy=legacy)
        ql, qr = self._quote_
        value = str(row)
        frames = []
        for db_name, s_name, t_name, c_name in catalog.iter_rows():
            target = self._target_(s_name, t_name)
            condition = f"{self._cast_(f'{ql}{c_name}{qr}')} = {QueryAPI.Positional}"
            sql = self._limit_(self._condition_(self._select_(target, "1"), condition), 1)
            try:
                df = self.executeone(QueryAPI(sql), value, database=db_name, schema=s_name, table=t_name, admin=False).fetchall(legacy=False)
                if not df.is_empty():
                    frames.append(pl.DataFrame({"Database": [db_name], "Schema": [s_name], "Table": [t_name], "Column": [c_name]}))
            except Exception:
                pass
        return self.frame(self._concat_(frames) if frames else pl.DataFrame({"Database": [], "Schema": [], "Table": [], "Column": []}), legacy=legacy)

    def exists(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING) -> bool:
        """
        Checks if a database, schema, or table exists.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :return: True if the structure exists, False otherwise.
        """
        routed = self._route_("exists", database, schema, table)
        if isinstance(routed, list): return all(routed)
        database, schema, table = routed
        if table and (not database or not schema):
            raise ValueError("Schema and Database must be provided to operate on a Table")
        if schema and not database:
            raise ValueError("Database must be provided to operate on a Schema")
        if not database and not schema and not table:
            raise ValueError("At least one structure must be specified")
        kwargs = {k: v for k, v in {"database": database, "schema": schema, "table": table}.items() if v}
        if database:
            self._log_.debug(lambda: f"Check Operation: Checking {database} Database")
            db = self.executeone(self._CHECK_DATABASE_QUERY_, **kwargs, admin=True)
            empty = db.fetchall(legacy=False).is_empty()
            if empty: return False
        if schema:
            self._log_.debug(lambda: f"Check Operation: Checking {schema} Schema")
            db = self.executeone(self._CHECK_SCHEMA_QUERY_, **kwargs, admin=False)
            empty = db.fetchall(legacy=False).is_empty()
            if empty: return False
        if table:
            self._log_.debug(lambda: f"Check Operation: Checking {table} Table")
            db = self.executeone(self._CHECK_TABLE_QUERY_, **kwargs, admin=False)
            empty = db.fetchall(legacy=False).is_empty()
            if empty: return False
        return True

    def diff(self, *,
               database: Union[str, None, Missing] = MISSING,
               schema: Union[str, None, Missing] = MISSING,
               table: Union[str, None, Missing] = MISSING,
               structure: Union[dict, None, Missing] = MISSING) -> bool:
        """
        Checks for differences between the expected structure and the actual table structure.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param structure: The expected table structure.
        :return: True if differences exist, False otherwise.

        Column order counts as a difference. A declaration states the order its columns should be
        read in, so a table whose physical order has drifted from it is out of date even when every
        column is present with the right type.
        """
        routed = self._route_("diff", database, schema, table, structure=structure)
        if isinstance(routed, list): return any(routed)
        database, schema, table = routed
        structure = structure if structure is not MISSING else self._STRUCTURE_
        if not structure:
            raise ValueError("Structure must be provided to diff a Table")
        if table and (not database or not schema):
            raise ValueError("Schema and Database must be provided to operate on a Table")
        if schema and not database:
            raise ValueError("Database must be provided to operate on a Schema")
        if not database and not schema and not table:
            raise ValueError("At least one structure must be specified")
        kwargs = {k: v for k, v in {"database": database, "schema": schema, "table": table}.items() if v}
        definitions = self._check_(structure=structure)
        self._log_.debug(lambda: f"Diff Operation: Checking {table} Structure")
        db = self.executeone(self._CHECK_STRUCTURE_QUERY_, definitions=definitions, **kwargs, admin=False)
        empty = db.fetchall(legacy=False).is_empty()
        if not empty: return True
        return self.disordered(database=database, schema=schema, table=table, structure=structure)

    def disordered(self, *,
                   database: Union[str, None, Missing] = MISSING,
                   schema: Union[str, None, Missing] = MISSING,
                   table: Union[str, None, Missing] = MISSING,
                   structure: Union[dict, None, Missing] = MISSING) -> bool:
        """
        Checks whether the physical column order has drifted from the declared order.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param structure: The expected table structure.
        :return: True when the table lists its columns in a different order than the structure declares.

        Reads the standard information schema, which every driver exposing one orders by the same
        ordinal. A driver without one overrides this with its own catalog.
        """
        structure = structure if structure is not MISSING else self._STRUCTURE_
        if not structure or not table: return False
        actual = self._ordinals_(database=database, schema=schema, table=table)
        declared = [str(column) for column in structure]
        return bool(actual) and actual != declared

    def _ordinals_(self, *,
                   database: Union[str, None, Missing] = MISSING,
                   schema: Union[str, None, Missing] = MISSING,
                   table: Union[str, None, Missing] = MISSING) -> list:
        """Lists the columns of a table in the physical order the driver stores them in."""
        frame = self.select(
            database=database,
            schema="information_schema",
            table="columns",
            columns="column_name",
            condition="table_schema = :order_schema: AND table_name = :order_table: ORDER BY ordinal_position",
            parameters={"order_schema": schema, "order_table": table}
        )
        return [next(iter(row.values())) for row in self._records_(frame)]

    def sessions(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Retrieves active database sessions.
        :param database: Target database.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the active sessions.
        """
        database = database if database is not MISSING else self.database
        if isinstance(database, (list, tuple)):
            return self.frame(self._concat_([self.sessions(database=d, legacy=False) for d in database]), legacy=legacy)
        self._log_.debug(lambda: "Sessions Operation: Fetching active sessions")
        return self.executeone(self._LIST_SESSIONS_QUERY_, database=database or "%", admin=True).fetchall(legacy=legacy)

    def size(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Retrieves the storage consumption of databases, schemas, and tables.
        :param database: Target database(s).
        :param schema: Target schema(s).
        :param table: Target table(s).
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing storage usage details.
        """
        routed = self._route_("size", database, schema, table, legacy=legacy)
        if isinstance(routed, list): return self.frame(self._concat_(routed), legacy=legacy)
        database, schema, table = routed
        database = database or "%"
        schema = schema or "%"
        table = table or "%"
        self._log_.debug(lambda: "Size Operation: Fetching storage usage catalog")
        df = self.executeone(self._SIZE_CATALOG_QUERY_, database=database, schema=schema, table=table, admin=True).fetchall(legacy=False)
        if df.is_empty() or "Database" not in df.columns:
            return self.frame(df, legacy=legacy)
        databases = df["Database"].unique().to_list()
        expansion = database == "%" or any(d != self.database for d in databases)
        if expansion:
            frames = []
            for db_name in databases:
                db_df = self.executeone(self._SIZE_CATALOG_QUERY_, database=db_name, schema=schema, table=table, admin=False).fetchall(legacy=False)
                frames.append(db_df if not db_df.is_empty() else df.filter(pl.col("Database") == db_name))
            df = self._concat_(frames) if frames else df
        if not df.is_empty() and "Size" in df.columns:
            df = df.with_columns(pl.col("Size").map_elements(memory_to_string, return_dtype=pl.String).alias("Formatted"))
        return self.frame(df, legacy=legacy)

    def create(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               structure: Union[dict, None, Missing] = MISSING) -> Self:
        """
        Creates a database, schema, or table if it does not exist.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param structure: The table structure definition.
        :return: Self reference.
        """
        routed = self._route_("create", database, schema, table, structure=structure)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if table and (not database or not schema):
            raise ValueError("Schema and Database must be provided to operate on a Table")
        if schema and not database:
            raise ValueError("Database must be provided to operate on a Schema")
        if not database and not schema and not table:
            raise ValueError("At least one structure must be specified")
        kwargs = {k: v for k, v in {"database": database, "schema": schema, "table": table}.items() if v}
        if database:
            if not self.exists(database=database, schema=None, table=None):
                self._log_.warning(lambda: f"Create Operation: Missing {database} Database")
                self.executeone(self._CREATE_DATABASE_QUERY_, **kwargs, admin=True).commit()
                self._log_.alert(lambda: f"Create Operation: Created {database} Database")
        if schema:
            if not self.exists(database=database, schema=schema, table=None):
                self._log_.warning(lambda: f"Create Operation: Missing {schema} Schema")
                db = self.executeone(self._CREATE_SCHEMA_QUERY_, **kwargs, admin=False)
                db.commit()
                self._log_.alert(lambda: f"Create Operation: Created {schema} Schema")
        if table:
            structure_val = structure if structure is not MISSING else self._STRUCTURE_
            if structure_val is None:
                raise ValueError("Structure must be provided to create a Table")
            if not self.exists(database=database, schema=schema, table=table):
                self._log_.warning(lambda: f"Create Operation: Missing {table} Table")
                definitions = self._create_(structure=structure_val)
                db = self.executeone(self._CREATE_TABLE_QUERY_, definitions=definitions, **kwargs, admin=False)
                db.commit()
                self._log_.alert(lambda: f"Create Operation: Created {table} Table")
            else:
                if self.diff(database=database, schema=schema, table=table, structure=structure_val):
                    self._log_.warning(lambda: f"Create Operation: Mismatched {table} Structure")
                    db = self.executeone(self._DELETE_TABLE_QUERY_, **kwargs, admin=False)
                    db.commit()
                    self._log_.warning(lambda: f"Create Operation: Missing {table} Table")
                    definitions = self._create_(structure=structure_val)
                    db = self.executeone(self._CREATE_TABLE_QUERY_, definitions=definitions, **kwargs, admin=False)
                    db.commit()
                    self._log_.alert(lambda: f"Create Operation: Created {table} Table")
        return self

    def delete(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING) -> Self:
        """
        Deletes a database, schema, or table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :return: Self reference.
        """
        routed = self._route_("delete", database, schema, table)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if table and (not database or not schema):
            raise ValueError("Schema and Database must be provided to operate on a Table")
        if schema and not database:
            raise ValueError("Database must be provided to operate on a Schema")
        if not database and not schema and not table:
            raise ValueError("At least one structure must be specified")
        kwargs = {k: v for k, v in {"database": database, "schema": schema, "table": table}.items() if v}
        if table:
            if self.exists(database=database, schema=schema, table=table):
                self.executeone(self._DELETE_TABLE_QUERY_, **kwargs, admin=False).commit()
                self._log_.alert(lambda: f"Delete Operation: Deleted {table} Table")
        elif schema:
            if self.exists(database=database, schema=schema, table=None):
                self.executeone(self._DELETE_SCHEMA_QUERY_, **kwargs, admin=False).commit()
                self._log_.alert(lambda: f"Delete Operation: Deleted {schema} Schema")
        elif database:
            if self.exists(database=database, schema=None, table=None):
                self.disconnect()
                self.executeone(self._DELETE_DATABASE_QUERY_, **kwargs, admin=True).commit()
                self._log_.alert(lambda: f"Delete Operation: Deleted {database} Database")
        return self

    def refactor(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               name: Union[str, Sequence, None] = None) -> Self:
        """
        Renames a database, schema, or table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param name: The new name for the structure.
        :return: Self reference.
        """
        if name is None:
            raise ValueError("Name must be provided to refactor a structure")
        routed = self._route_("refactor", database, schema, table, name=name)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if table:
            if not database or not schema:
                raise ValueError("Schema and Database must be provided to operate on a Table")
            if not self.exists(database=database, schema=schema, table=table):
                raise ValueError(f"Table {table} does not exist in {database}.{schema}")
            self.executeone(self._REFACTOR_TABLE_QUERY_, database=database, schema=schema, table=table, name=name, admin=False).commit()
            if self._table_ == table: self._table_ = name
            self._log_.alert(lambda: f"Refactor Operation: Refactored {table} Table to {name}")
        elif schema:
            if not database:
                raise ValueError("Database must be provided to operate on a Schema")
            if not self.exists(database=database, schema=schema, table=None):
                raise ValueError(f"Schema {schema} does not exist in {database}")
            self.executeone(self._REFACTOR_SCHEMA_QUERY_, database=database, schema=schema, name=name, admin=False).commit()
            if self._schema_ == schema: self._schema_ = name
            self._log_.alert(lambda: f"Refactor Operation: Refactored {schema} Schema to {name}")
        elif database:
            if not self.exists(database=database, schema=None, table=None):
                raise ValueError(f"Database {database} does not exist")
            self.disconnect()
            self.executeone(self._REFACTOR_DATABASE_QUERY_, database=database, name=name, admin=True).commit()
            if self._database_ == database: self._database_ = name
            self._log_.alert(lambda: f"Refactor Operation: Refactored {database} Database to {name}")
        else: raise ValueError("At least one structure must be specified")
        return self

    def migrate(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               structure: Union[dict, None, Missing] = MISSING) -> Self:
        """
        Migrates the structure of a database, schema, or table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param structure: The updated table structure definition.
        :return: Self reference.
        """
        routed = self._route_("migrate", database, schema, table, structure=structure)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if table and (not database or not schema):
            raise ValueError("Schema and Database must be provided to operate on a Table")
        if schema and not database:
            raise ValueError("Database must be provided to operate on a Schema")
        if not database and not schema and not table:
            raise ValueError("At least one structure must be specified")
        kwargs = {k: v for k, v in {"database": database, "schema": schema, "table": table}.items() if v}
        if database:
            if not self.exists(database=database, schema=None, table=None):
                self._log_.warning(lambda: f"Migrate Operation: Missing {database} Database")
                self.executeone(self._CREATE_DATABASE_QUERY_, **kwargs, admin=True).commit()
                self._log_.alert(lambda: f"Migrate Operation: Created {database} Database")
        if schema:
            if not self.exists(database=database, schema=schema, table=None):
                self._log_.warning(lambda: f"Migrate Operation: Missing {schema} Schema")
                self.executeone(self._CREATE_SCHEMA_QUERY_, **kwargs, admin=False).commit()
                self._log_.alert(lambda: f"Migrate Operation: Created {schema} Schema")
        if table:
            structure_val = structure if structure is not MISSING else self._STRUCTURE_
            if structure_val is None:
                raise ValueError("Structure must be provided to migrate a Table")
            if not self.exists(database=database, schema=schema, table=table):
                self._log_.warning(lambda: f"Migrate Operation: Missing {table} Table")
                definitions = self._create_(structure=structure_val)
                self.executeone(self._CREATE_TABLE_QUERY_, definitions=definitions, **kwargs, admin=False).commit()
                self._log_.alert(lambda: f"Migrate Operation: Created {table} Table")
            elif self.diff(database=database, schema=schema, table=table, structure=structure_val):
                self._log_.warning(lambda: f"Migrate Operation: Structure mismatch for {table} Table")
                definitions = self._check_(structure=structure_val)
                diff_df = self.executeone(self._CHECK_STRUCTURE_QUERY_, definitions=definitions, **kwargs, admin=False).fetchall(legacy=False)
                new_only = set(diff_df["expected_column_name"].drop_nulls().to_list())
                actual = set(diff_df["actual_column_name"].drop_nulls().to_list())
                new_only -= actual
                common = [c for c in structure_val if c not in new_only]
                if not common:
                    self.executeone(self._DELETE_TABLE_QUERY_, **kwargs, admin=False).commit()
                    definitions = self._create_(structure=structure_val)
                    self.executeone(self._CREATE_TABLE_QUERY_, definitions=definitions, **kwargs, admin=False).commit()
                    self._log_.alert(lambda: f"Migrate Operation: Recreated {table} Table")
                else:
                    temp_table = f"{table}_{uuid.uuid4().hex[:8]}"
                    original_table = self._table_
                    self.refactor(database=database, schema=schema, table=table, name=temp_table)
                    if original_table == table: self._table_ = original_table
                    try:
                        self.create(database=database, schema=schema, table=table, structure=structure_val)
                        target_temp = self._target_(schema, temp_table)
                        cols_str = self._quoted_(*common)
                        carry = self._carry_(database=database, schema=schema, table=table, columns=cols_str, source=target_temp)
                        self.executeone(QueryAPI(carry), database=database, schema=schema, table=table, admin=False)
                        moved = self.count(database=database, schema=schema, table=table)
                        kept = self.count(database=database, schema=schema, table=temp_table)
                        if moved != kept:
                            raise RuntimeError(f"Migrate Operation: Refused to drop {temp_table} · {moved} of {kept} rows copied")
                        self.realign(database=database, schema=schema, table=table, source=temp_table)
                        self.discard(database=database, schema=schema, table=temp_table)
                    except Exception:
                        self.revert(database=database, schema=schema, table=table, source=temp_table)
                        raise
                    self._log_.alert(lambda: f"Migrate Operation: Migrated {table} Table")
        return self

    def realign(self, *,
                database: Union[str, None, Missing] = MISSING,
                schema: Union[str, None, Missing] = MISSING,
                table: Union[str, None, Missing] = MISSING,
                source: Union[str, None] = None) -> Self:
        """
        Re-points foreign keys that followed a table through a rebuild.

        Renaming a table carries its dependents with it, so every inbound key ends up referencing the
        temporary copy the rebuild is about to drop. Left alone the drop fails, or worse succeeds and
        takes referential integrity with it. Each driver reads its own catalog to find those keys.
        """
        return self

    def discard(self, *,
                database: Union[str, None, Missing] = MISSING,
                schema: Union[str, None, Missing] = MISSING,
                table: Union[str, None, Missing] = MISSING) -> Self:
        """
        Drops a table without cascading, so anything still depending on it refuses the drop.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :return: Self reference.

        `delete()` cascades, which is right when the intent is to remove a table and everything tied
        to it. A rebuild has the opposite intent: the temporary copy must go, and a foreign key still
        pointing at it means realign() missed one. Cascading there destroys that key silently and
        leaves the database referentially poorer than it started; refusing says so instead.
        """
        self.executeone(QueryAPI(f"DROP TABLE {self._target_(schema, table)}"), database=database, schema=schema, table=table, admin=False)
        self._log_.alert(lambda: f"Discard Operation: Dropped {table} Table")
        return self

    def revert(self, *,
               database: Union[str, None, Missing] = MISSING,
               schema: Union[str, None, Missing] = MISSING,
               table: Union[str, None, Missing] = MISSING,
               source: Union[str, None] = None) -> Self:
        """
        Puts a failed rebuild back the way it was, restoring the original table under its own name.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param source: The temporary copy holding the original rows.
        :return: Self reference.

        Without this a failure leaves the rows stranded in a temporary table nobody will look for and
        the declared name owned by a half-filled copy. Foreign keys track a table by identity rather
        than by name, so renaming the original back also restores every key that followed it.
        """
        if not source or not table: return self
        try:
            if self.exists(database=database, schema=schema, table=table):
                self.discard(database=database, schema=schema, table=table)
            self.refactor(database=database, schema=schema, table=source, name=table)
            self._log_.alert(lambda: f"Revert Operation: Restored {table} Table ({source})")
        except Exception as error:
            self._log_.error(lambda error=error: f"Revert Operation: Failed · {error}")
            self._log_.error(lambda: f"Revert Operation: Rows remain in {source} · Restore it manually before retrying")
        return self

    def _carry_(self, *,
                database: Union[str, None, Missing] = MISSING,
                schema: Union[str, None, Missing] = MISSING,
                table: Union[str, None, Missing] = MISSING,
                columns: str = "",
                source: str = "") -> str:
        """
        Builds the statement a rebuild copies rows across with.

        A generated identity column rejects an explicit value, and each driver lifts that differently:
        one takes a clause inside the insert, another a session switch around it. Returning the whole
        statement keeps whatever a driver needs in a single execution, so a switch cannot be stranded
        on a connection the insert never sees.
        """
        return f"INSERT INTO {self._target_(schema, table)} ({columns}) SELECT {columns} FROM {source}"

    def count(self, *,
              database: Union[str, None, Missing] = MISSING,
              schema: Union[str, None, Missing] = MISSING,
              table: Union[str, None, Missing] = MISSING) -> int:
        """Counts the rows a table currently holds."""
        frame = self.executeone(QueryAPI(f"SELECT COUNT(*) FROM {self._target_(schema, table)}"), database=database, schema=schema, table=table, admin=False).fetchall(legacy=False)
        records = self._records_(frame)
        return int(next(iter(records[0].values()))) if records else 0

    def add(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               structure: Union[dict, None] = None) -> Self:
        """
        Adds new columns to an existing table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param structure: A dictionary mapping column names to their data types.
        :return: Self reference.
        """
        if not structure:
            raise ValueError("Structure must be provided to add a Column")
        routed = self._route_("add", database, schema, table, structure=structure)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table:
            raise ValueError("Database, Schema and Table must be provided to add a Column")
        target = self._target_(schema, table)
        for name, dtype in structure.items():
            datatype = self._CREATE_DATATYPE_MAPPING_[self._normalize_(dtype)]
            if isinstance(dtype, IdentityKey):
                if dtype.primary: datatype += " PRIMARY KEY"
                else: datatype += " UNIQUE"
                datatype += self._identity_()
            elif isinstance(dtype, PrimaryKey):
                datatype += " PRIMARY KEY"
            elif isinstance(dtype, ForeignKey):
                datatype += f" REFERENCES {dtype.reference}"
            sql = self._add_(target, self._quoted_(name), datatype)
            self.executeone(QueryAPI(sql), database=database, schema=schema, table=table, admin=False)
        self._log_.alert(lambda: f"Add Operation: Added Columns to {table} Table")
        return self

    def drop(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               column: Union[str, Sequence, None] = None) -> Self:
        """
        Drops a column from an existing table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param column: The name of the column to drop.
        :return: Self reference.
        """
        if column is None:
            raise ValueError("Column must be provided to drop a Column")
        routed = self._route_("drop", database, schema, table, column=column)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table:
            raise ValueError("Database, Schema and Table must be provided to drop a Column")
        if isinstance(column, (list, tuple)):
            for c in column: self.drop(database=database, schema=schema, table=table, column=c)
            return self
        target = self._target_(schema, table)
        sql = self._drop_(target, self._quoted_(column))
        self.executeone(QueryAPI(sql), database=database, schema=schema, table=table, admin=False)
        self._log_.alert(lambda: f"Drop Operation: Dropped {column} Column from {table} Table")
        return self

    def rename(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               column: Union[str, Sequence, None] = None,
               name: Union[str, Sequence, None] = None) -> Self:
        """
        Renames a column in an existing table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param column: The current column name.
        :param name: The new column name.
        :return: Self reference.
        """
        if column is None or name is None:
            raise ValueError("Column and Name must be provided to rename a Column")
        routed = self._route_("rename", database, schema, table, column=column, name=name)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table:
            raise ValueError("Database, Schema and Table must be provided to rename a Column")
        if isinstance(column, (list, tuple)):
            if not isinstance(name, (list, tuple)) or len(name) != len(column):
                raise ValueError("Name must be a list/tuple of the same length as Column")
            for c, n in zip(column, name): self.rename(database=database, schema=schema, table=table, column=c, name=n)
            return self
        if not self.exists(database=database, schema=schema, table=table):
            raise ValueError(f"Table {table} does not exist in {database}.{schema}")
        self.executeone(self._RENAME_COLUMN_QUERY_, database=database, schema=schema, table=table, column=column, name=name, admin=False).commit()
        self._log_.alert(lambda: f"Rename Operation: Renamed {column} Column to {name} in {table} Table")
        return self

    def reorder(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               columns: Union[Sequence[str], None] = None,
               structure: Union[dict, None] = None) -> Self:
        """
        Reorders the columns in an existing table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param columns: The new order of column names.
        :param structure: The table structure definition.
        :return: Self reference.
        """
        if not columns:
            raise ValueError("Columns must be provided to reorder a Table")
        if isinstance(columns, str): columns = [columns]
        routed = self._route_("reorder", database, schema, table, columns=columns, structure=structure)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table:
            raise ValueError("Database, Schema and Table must be provided to reorder a Table")
        source = structure or self._STRUCTURE_
        if source is None:
            df = self.select(database=database, schema=schema, table=table, columns=columns, limit=1, legacy=False)
            if not isinstance(df, pl.DataFrame):
                raise ValueError("Structure must be provided to reorder a Table without Polars DataFrames")
            source = {k: v for k, v in df.schema.items()}
            if any(v == pl.Null for v in source.values()):
                raise ValueError("Cannot infer structure from empty table or null columns. Structure must be provided explicitly.")
        missing = [c for c in columns if c not in source]
        if missing:
            raise ValueError(f"Columns {missing} not found in Structure")
        new_structure = {c: source[c] for c in columns}
        self.migrate(database=database, schema=schema, table=table, structure=new_structure)
        self._log_.alert(lambda: f"Reorder Operation: Reordered Columns in {table} Table")
        return self

    def select(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               columns: Union[str, Sequence, None] = None,
               condition: Union[str, None] = None,
               order: Union[str, None] = None,
               limit: Union[int, None] = None,
               parameters: Union[dict, None] = None,
               legacy: Union[bool, Missing] = MISSING) -> Union[pd.DataFrame, pl.DataFrame]:
        """
        Selects data from a table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param columns: Columns to retrieve.
        :param condition: The WHERE condition.
        :param order: The ORDER BY clause.
        :param limit: The maximum number of rows to retrieve.
        :param parameters: Parameters for the query.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        :return: A DataFrame containing the selected data.
        """
        routed = self._route_("select", database, schema, table, columns=columns, condition=condition, order=order, limit=limit, parameters=parameters, legacy=legacy)
        if isinstance(routed, list): return self.frame(self._concat_(routed), legacy=legacy)
        database, schema, table = routed
        if not database or not schema or not table:
            raise ValueError("Database, Schema and Table must be provided to select rows")
        target = self._target_(schema, table)
        cols_str = self._ALL_ if columns is None else self._quoted_(*columns) if isinstance(columns, (list, tuple)) else columns
        sql = self._select_(target, cols_str)
        sql = self._condition_(sql, condition)
        sql = self._order_(sql, order)
        if limit is not None: sql = self._limit_(sql, limit)
        db = self.executeone(QueryAPI(sql), database=database, schema=schema, table=table, admin=False, **(parameters or {}))
        return db.fetchall(legacy=legacy)

    def fingerprint(self, *,
                    database: Union[str, Sequence, None, Missing] = MISSING,
                    schema: Union[str, Sequence, None, Missing] = MISSING,
                    table: Union[str, Sequence, None, Missing] = MISSING,
                    condition: Union[str, None] = None,
                    parameters: Union[dict, None] = None,
                    column: Union[str, None] = None) -> str:
        """
        Computes a lightweight change token for a relation without pulling its rows, cheap
        enough to poll: the token only changes when the target rows change. Drivers may expose
        an O(1) statistics-based token via the ``_fingerprint_`` hook; otherwise (or for a
        filtered or non-concrete target) the portable fallback counts the rows and optionally
        folds in the maximum of a stamp column.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param condition: Optional WHERE condition to fingerprint a filtered subset.
        :param parameters: Parameters for the condition.
        :param column: Optional column whose maximum is folded into the token (e.g. an UpdatedAt stamp).
        :return: A stable string token that changes whenever the target rows change.
        """
        if condition is None and isinstance(schema, str) and isinstance(table, str):
            try: token = self._fingerprint_(database=database, schema=schema, table=table)
            except Exception: token = None
            if token is not None: return token
        expression = "COUNT(*)" if column is None else f"COUNT(*), MAX({self._quoted_(column)})"
        frame = self.select(database=database, schema=schema, table=table, columns=expression, condition=condition, parameters=parameters)
        records = self._records_(frame)
        if not records: return ""
        return "|".join("" if value is None else str(value) for value in records[0].values())

    def _fingerprint_(self, *,
                      database: Union[str, Sequence, None, Missing] = MISSING,
                      schema: Union[str, Sequence, None, Missing] = MISSING,
                      table: Union[str, Sequence, None, Missing] = MISSING) -> Union[str, None]:
        return None

    def listen(self, *, channel: str) -> bool:
        """
        Subscribes this connection to a named notification channel so that subsequent
        ``wait`` calls return as soon as a ``notify`` on that channel arrives. Drivers
        without native push support keep the portable default and report False, in which
        case ``wait`` degrades to plain sleeping.
        :param channel: The notification channel name.
        :return: True when the subscription is active, False when unsupported.
        """
        return False

    def notify(self, *, channel: str) -> bool:
        """
        Publishes a notification on a named channel, waking every connection currently
        listening on it. Drivers without native push support keep the portable default
        and report False.
        :param channel: The notification channel name.
        :return: True when the notification was published, False when unsupported.
        """
        return False

    def wait(self, *, timeout: float) -> bool:
        """
        Blocks until a notification arrives on a channel this connection listens to, or
        until the timeout elapses. The portable default simply sleeps for the timeout so
        that callers can poll uniformly regardless of driver capability.
        :param timeout: The maximum number of seconds to block.
        :return: True when a notification arrived, False on timeout or when unsupported.
        """
        time.sleep(timeout)
        return False

    def insert(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               data: Any = None) -> Self:
        """
        Inserts data into a table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param data: The data to insert.
        :return: Self reference.
        """
        if data is None: raise ValueError("Data must be provided to insert rows")
        routed = self._route_("insert", database, schema, table, data=data)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table: raise ValueError("Database, Schema and Table must be provided to insert rows")
        columns, records, multiple = self.parse(data)
        if not records: return self
        target = self._target_(schema, table)
        if columns:
            cols_str = self._quoted_(*columns)
            vals_str = ", ".join(f"{QueryAPI.Named}{c}{QueryAPI.Named}" for c in columns)
            sql = self._insert_(target, cols_str, vals_str)
        else:
            vals_str = ", ".join(QueryAPI.Positional for _ in records[0])
            sql = self._insert_(target, "", vals_str)
        self.execute(QueryAPI(sql), records, database=database, schema=schema, table=table, admin=False)
        self._log_.alert(lambda: f"Insert Operation: Processed {len(records)} rows in {table} Table")
        return self

    def update(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               data: Any = None,
               condition: Union[str, None] = None) -> Self:
        """
        Updates data in a table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param data: The data to update.
        :param condition: The WHERE condition.
        :return: Self reference.
        """
        if data is None: raise ValueError("Data must be provided to update rows")
        routed = self._route_("update", database, schema, table, data=data, condition=condition)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table: raise ValueError("Database, Schema and Table must be provided to update rows")
        columns, records, multiple = self.parse(data)
        if not records: return self
        if not columns: raise ValueError("Dictionary or DataFrame structure required for updates to identify columns")
        target = self._target_(schema, table)
        n = QueryAPI.Named
        set_str = ", ".join(f"{self._quoted_(c)} = {n}{c}{n}" for c in columns)
        sql = self._update_(target, set_str)
        sql = self._condition_(sql, condition)
        self.execute(QueryAPI(sql), records, database=database, schema=schema, table=table, admin=False)
        self._log_.alert(lambda: f"Update Operation: Processed {len(records)} rows in {table} Table")
        return self

    def upsert(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               data: Any = None,
               key: Union[str, Sequence[str], None] = None,
               exclude: Union[Sequence[str], None] = None,
               returning: Union[str, Sequence[str], None] = None) -> Union[Self, pd.DataFrame, pl.DataFrame]:
        """
        Upserts (inserts or updates) data in a table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param data: The data to upsert.
        :param key: The primary key or constraint for conflict resolution.
        :param exclude: Columns to exclude from the update on conflict.
        :param returning: Columns to return from the upserted rows (e.g. auto-generated UID). When set, returns a DataFrame instead of self.
        :return: Self reference, or a DataFrame of returned columns when ``returning`` is set.
        """
        if not key:
            key = self._structure_keys_()
            if not key:
                raise ValueError("Key must be provided to upsert rows")
        routed = self._route_("upsert", database, schema, table, data=data, key=key, exclude=exclude, returning=returning)
        if isinstance(routed, list):
            if returning: raise ValueError("returning is not supported with multiple targets")
            return self
        database, schema, table = routed
        if not database or not schema or not table: raise ValueError("Database, Schema and Table must be provided to upsert rows")
        columns, records, _ = self.parse(data)
        if not records: return self
        if not columns: raise ValueError("Dictionary or DataFrame structure required for upserts to identify columns")
        target = self._target_(schema, table)
        keys = [key] if isinstance(key, str) else list(key)
        returning_cols = [returning] if isinstance(returning, str) else (list(returning) if returning else ())
        if not returning_cols:
            sql = self._upsert_(target, columns, keys, exclude or (), ())
            self.execute(QueryAPI(sql), records, database=database, schema=schema, table=table, admin=False)
            self._log_.alert(lambda: f"Upsert Operation: Processed {len(records)} rows in {table} Table")
            return self
        chunk_size = max(1, self._PARAMETER_LIMIT_ // max(1, len(columns)))
        frames: list = []
        for start in range(0, len(records), chunk_size):
            chunk = records[start:start + chunk_size]
            sql = self._upsert_(target, columns, keys, exclude or (), returning_cols, rows=len(chunk))
            bindings = chunk[0] if len(chunk) == 1 else {f"{c}_{i}": rec[c] for i, rec in enumerate(chunk) for c in columns}
            db = self.executeone(QueryAPI(sql), database=database, schema=schema, table=table, admin=False, **bindings)
            frames.append(db.fetchall(legacy=False))
        self._log_.alert(lambda: f"Upsert Operation: Processed {len(records)} rows in {table} Table")
        return self.frame(self._concat_(frames) if frames else pl.DataFrame(), legacy=self._legacy_)

    def copy(self, *,
             database: Union[str, Sequence, None, Missing] = MISSING,
             schema: Union[str, Sequence, None, Missing] = MISSING,
             table: Union[str, Sequence, None, Missing] = MISSING,
             data: Any = None,
             columns: Union[Sequence[str], None] = None) -> Self:
        raise NotImplementedError(f"{self.__class__.__name__}.copy() is not implemented")

    def merge(self, *,
              database: Union[str, Sequence, None, Missing] = MISSING,
              schema: Union[str, Sequence, None, Missing] = MISSING,
              table: Union[str, Sequence, None, Missing] = MISSING,
              data: Any = None,
              key: Union[str, Sequence[str], None] = None,
              exclude: Union[Sequence[str], None] = None) -> Self:
        return self.upsert(database=database, schema=schema, table=table, data=data, key=key, exclude=exclude)

    def remove(self, *,
               database: Union[str, Sequence, None, Missing] = MISSING,
               schema: Union[str, Sequence, None, Missing] = MISSING,
               table: Union[str, Sequence, None, Missing] = MISSING,
               condition: Union[str, None] = None,
               parameters: Union[dict, None] = None) -> Self:
        """
        Removes rows from a table.
        :param database: Target database.
        :param schema: Target schema.
        :param table: Target table.
        :param condition: The WHERE condition.
        :param parameters: Parameters for the query.
        :return: Self reference.
        """
        routed = self._route_("remove", database, schema, table, condition=condition, parameters=parameters)
        if isinstance(routed, list): return self
        database, schema, table = routed
        if not database or not schema or not table:
            raise ValueError("Database, Schema and Table must be provided to remove rows")
        target = self._target_(schema, table)
        sql = self._delete_(target)
        sql = self._condition_(sql, condition)
        self.executeone(QueryAPI(sql), database=database, schema=schema, table=table, admin=False, **(parameters or {}))
        self._log_.alert(lambda: f"Remove Operation: Removed rows from {table} Table")
        return self

    def migration(self) -> Self:
        """
        Performs a full migration of the database, schema, and table structures.
        :return: Self reference.
        """
        try:
            timer = Timer()
            timer.start()
            if self.databased():
                subtimer = Timer()
                subtimer.start()
                self.disconnect()
                self.connect(admin=True)
                self.create(database=self._database_, schema=None, table=None)
                subtimer.stop()
                self._log_.info(lambda: f"Migration Operation: Migrated Database ({subtimer.result()})")
            self.disconnect()
            self.connect()
            if self.schemed():
                subtimer = Timer()
                subtimer.start()
                self.create(database=self._database_, schema=self._schema_, table=None)
                subtimer.stop()
                self._log_.info(lambda: f"Migration Operation: Migrated Schema ({subtimer.result()})")
            if self.tabled():
                subtimer = Timer()
                subtimer.start()
                self.migrate()
                subtimer.stop()
                self._log_.info(lambda: f"Migration Operation: Migrated Table ({subtimer.result()})")
            timer.stop()
            self._log_.info(lambda: f"Migration Operation: Migrated ({timer.result()})")
            return self
        except Exception as e:
            self.rollback()
            self._log_.error(lambda: "Migration Operation: Failed")
            self._log_.exception(lambda: str(e))
            raise

    def kill(self, *,
               id: Union[int, str, Sequence, None, Missing] = MISSING,
               database: Union[str, Sequence, None, Missing] = MISSING) -> Self:
        """
        Terminates active database sessions.
        :param id: The session ID(s) to kill.
        :param database: Target database.
        :return: Self reference.
        """
        database = database if database is not MISSING else self.database
        if isinstance(database, (list, tuple)):
            for d in database: self.kill(id=id, database=d)
            return self
        with self._lock_:
            for clone_db in list(self._pool_.values()):
                if clone_db._database_ == database:
                    clone_db.disconnect()
        if isinstance(id, (list, tuple)):
            for i in id: self.kill(id=i, database=database)
            return self
        if id is MISSING:
            self._log_.debug(lambda: "Kill Operation: Fetching all active sessions to terminate")
            df = self.sessions(database=database, legacy=False)
            if not df.is_empty():
                self.kill(id=df["Id"].to_list(), database=database)
            return self
        self._log_.alert(lambda: f"Kill Operation: Terminating session {id}")
        try:
            self.executeone(self._KILL_SESSION_QUERY_, id=id, admin=True).commit()
        except Exception as e:
            self._log_.error(lambda: f"Kill Operation: Failed to terminate session {id}")
            self._log_.exception(lambda: str(e))
        return self