from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
    from Library.Universe.Category import CategoryAPI
    from Library.Universe.Provider import ProviderAPI
    from Library.Universe.Ticker import TickerAPI
    from Library.Universe.Timeframe import TimeframeAPI
    from Library.Universe.Contract import ContractAPI
    from Library.Universe.Security import SecurityAPI

@dataclass(kw_only=True)
class UniverseAPI(DatapointAPI):
    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Universe"
    Table: ClassVar[str] = "Universe"

    @staticmethod
    def save_categories(data: CategoryAPI | Sequence[CategoryAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def load_categories(data: CategoryAPI | Sequence[CategoryAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.load()
        else: data.load()

    @staticmethod
    def pull_categories(db: DatabaseAPI, as_dataframe: bool = True) -> pl.DataFrame | list[CategoryAPI]:
        from Library.Universe.Category import CategoryAPI
        sql = f'SELECT * FROM "{UniverseAPI.Schema}"."{CategoryAPI.Table}" ORDER BY "UID"'
        df = db.executeone(QueryAPI(sql), schema=CategoryAPI.Schema, table=CategoryAPI.Table).fetchall(legacy=False)
        if as_dataframe: return df
        return [CategoryAPI.parse(row) for row in df.iter_rows(named=True)]

    @staticmethod
    def push_categories(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        from Library.Universe.Category import CategoryAPI
        db.upsert(schema=CategoryAPI.Schema, table=CategoryAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def save_providers(data: ProviderAPI | Sequence[ProviderAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def load_providers(data: ProviderAPI | Sequence[ProviderAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.load()
        else: data.load()

    @staticmethod
    def pull_providers(db: DatabaseAPI, as_dataframe: bool = True) -> pl.DataFrame | list[ProviderAPI]:
        from Library.Universe.Provider import ProviderAPI
        sql = f'SELECT * FROM "{UniverseAPI.Schema}"."{ProviderAPI.Table}" ORDER BY "UID"'
        df = db.executeone(QueryAPI(sql), schema=ProviderAPI.Schema, table=ProviderAPI.Table).fetchall(legacy=False)
        if as_dataframe: return df
        return [ProviderAPI.parse(row) for row in df.iter_rows(named=True)]

    @staticmethod
    def push_providers(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        from Library.Universe.Provider import ProviderAPI
        db.upsert(schema=ProviderAPI.Schema, table=ProviderAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def save_tickers(data: TickerAPI | Sequence[TickerAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def load_tickers(data: TickerAPI | Sequence[TickerAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.load()
        else: data.load()

    @staticmethod
    def pull_tickers(db: DatabaseAPI, as_dataframe: bool = True) -> pl.DataFrame | list[TickerAPI]:
        from Library.Universe.Ticker import TickerAPI
        sql = f'SELECT * FROM "{UniverseAPI.Schema}"."{TickerAPI.Table}" ORDER BY "UID"'
        df = db.executeone(QueryAPI(sql), schema=TickerAPI.Schema, table=TickerAPI.Table).fetchall(legacy=False)
        if as_dataframe: return df
        return [TickerAPI.parse(row) for row in df.iter_rows(named=True)]

    @staticmethod
    def push_tickers(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        from Library.Universe.Ticker import TickerAPI
        db.upsert(schema=TickerAPI.Schema, table=TickerAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def save_timeframes(data: TimeframeAPI | Sequence[TimeframeAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def load_timeframes(data: TimeframeAPI | Sequence[TimeframeAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.load()
        else: data.load()

    @staticmethod
    def pull_timeframes(db: DatabaseAPI, as_dataframe: bool = True) -> pl.DataFrame | list[TimeframeAPI]:
        from Library.Universe.Timeframe import TimeframeAPI
        sql = f'SELECT * FROM "{UniverseAPI.Schema}"."{TimeframeAPI.Table}" ORDER BY "UID"'
        df = db.executeone(QueryAPI(sql), schema=TimeframeAPI.Schema, table=TimeframeAPI.Table).fetchall(legacy=False)
        if as_dataframe: return df
        return [TimeframeAPI.parse(row) for row in df.iter_rows(named=True)]

    @staticmethod
    def push_timeframes(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        from Library.Universe.Timeframe import TimeframeAPI
        db.upsert(schema=TimeframeAPI.Schema, table=TimeframeAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def save_contracts(data: ContractAPI | Sequence[ContractAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def load_contracts(data: ContractAPI | Sequence[ContractAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.load()
        else: data.load()

    @staticmethod
    def pull_contracts(db: DatabaseAPI, as_dataframe: bool = True) -> pl.DataFrame | list[ContractAPI]:
        from Library.Universe.Contract import ContractAPI
        sql = f'SELECT * FROM "{UniverseAPI.Schema}"."{ContractAPI.Table}" ORDER BY "UID"'
        df = db.executeone(QueryAPI(sql), schema=ContractAPI.Schema, table=ContractAPI.Table).fetchall(legacy=False)
        if as_dataframe: return df
        return [ContractAPI.parse(row) for row in df.iter_rows(named=True)]

    @staticmethod
    def push_contracts(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        from Library.Universe.Contract import ContractAPI
        db.upsert(schema=ContractAPI.Schema, table=ContractAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def save_securities(data: SecurityAPI | Sequence[SecurityAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def load_securities(data: SecurityAPI | Sequence[SecurityAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for item in data: item.load()
        else: data.load()

    @staticmethod
    def pull_securities(db: DatabaseAPI, as_dataframe: bool = True) -> pl.DataFrame | list[SecurityAPI]:
        from Library.Universe.Security import SecurityAPI
        sql = f'SELECT * FROM "{UniverseAPI.Schema}"."{SecurityAPI.Table}" ORDER BY "UID"'
        df = db.executeone(QueryAPI(sql), schema=SecurityAPI.Schema, table=SecurityAPI.Table).fetchall(legacy=False)
        if as_dataframe: return df
        return [SecurityAPI.parse(row) for row in df.iter_rows(named=True)]

    @staticmethod
    def push_securities(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        from Library.Universe.Security import SecurityAPI
        db.upsert(schema=SecurityAPI.Schema, table=SecurityAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])