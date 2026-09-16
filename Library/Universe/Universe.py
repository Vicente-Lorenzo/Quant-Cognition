from __future__ import annotations

from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI

@dataclass(kw_only=True)
class UniverseAPI(DatapointAPI):

    Schema: ClassVar[str] = "Universe"
    Table: ClassVar[str] = "Universe"

    @staticmethod
    def pull_categories(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Universe.Category import CategoryAPI
        return db.select(schema=CategoryAPI.Schema, table=CategoryAPI.Table, order='"UID"', legacy=False)

    @staticmethod
    def push_categories(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Universe.Category import CategoryAPI
        db.upsert(schema=CategoryAPI.Schema, table=CategoryAPI.Table, data=data, key=["UID"])

    @staticmethod
    def pull_providers(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Universe.Provider import ProviderAPI
        return db.select(schema=ProviderAPI.Schema, table=ProviderAPI.Table, order='"UID"', legacy=False)

    @staticmethod
    def push_providers(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Universe.Provider import ProviderAPI
        db.upsert(schema=ProviderAPI.Schema, table=ProviderAPI.Table, data=data, key=["UID"])

    @staticmethod
    def pull_tickers(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Universe.Ticker import TickerAPI
        return db.select(schema=TickerAPI.Schema, table=TickerAPI.Table, order='"UID"', legacy=False)

    @staticmethod
    def push_tickers(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Universe.Ticker import TickerAPI
        db.upsert(schema=TickerAPI.Schema, table=TickerAPI.Table, data=data, key=["UID"])

    @staticmethod
    def pull_timeframes(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Universe.Timeframe import TimeframeAPI
        return db.select(schema=TimeframeAPI.Schema, table=TimeframeAPI.Table, order='"UID"', legacy=False)

    @staticmethod
    def push_timeframes(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Universe.Timeframe import TimeframeAPI
        db.upsert(schema=TimeframeAPI.Schema, table=TimeframeAPI.Table, data=data, key=["UID"])

    @staticmethod
    def pull_contracts(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Universe.Contract import ContractAPI
        return db.select(schema=ContractAPI.Schema, table=ContractAPI.Table, order='"UID"', legacy=False)

    @staticmethod
    def push_contracts(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Universe.Contract import ContractAPI
        db.upsert(schema=ContractAPI.Schema, table=ContractAPI.Table, data=data, key=["Ticker", "Provider", "Type"])

    @staticmethod
    def pull_securities(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Universe.Security import SecurityAPI
        return db.select(schema=SecurityAPI.Schema, table=SecurityAPI.Table, order='"UID"', legacy=False)

    @staticmethod
    def push_securities(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Universe.Security import SecurityAPI
        db.upsert(schema=SecurityAPI.Schema, table=SecurityAPI.Table, data=data, key=["Ticker", "Provider", "Category", "Contract"])