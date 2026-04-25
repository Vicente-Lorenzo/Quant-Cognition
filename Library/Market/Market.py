from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING
from collections.abc import Sequence
from datetime import datetime
from dataclasses import dataclass

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI
from Library.Market.Tick import TickAPI
from Library.Market.Bar import BarAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass(kw_only=True)
class MarketAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Market"
    Table: ClassVar[str] = "Market"

    @staticmethod
    def save_ticks(data: TickAPI | Sequence[TickAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for tick in data: tick.save(by=by)
        else:
            data.save(by=by)

    @staticmethod
    def save_bars(data: BarAPI | Sequence[BarAPI], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for bar in data: bar.save(by=by)
        else:
            data.save(by=by)

    @staticmethod
    def load_ticks(data: TickAPI | Sequence[TickAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for tick in data: tick.load()
        else:
            data.load()

    @staticmethod
    def load_bars(data: BarAPI | Sequence[BarAPI]) -> None:
        if isinstance(data, (list, tuple)):
            for bar in data: bar.load()
        else:
            data.load()

    @staticmethod
    def pull_ticks(db: DatabaseAPI, security: int, start: datetime, stop: datetime) -> pl.DataFrame:
        sql = '''
        SELECT * FROM "Market"."Tick"
        WHERE "Security" = :security: AND "Timestamp" BETWEEN :start: AND :stop:
        ORDER BY "Timestamp"
        '''
        df = db.executeone(QueryAPI(sql), security=security, start=start, stop=stop, schema=TickAPI.Schema, table=TickAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def pull_bars(db: DatabaseAPI, security: int, timeframe: str, start: datetime, stop: datetime) -> pl.DataFrame:
        sql = '''
        SELECT b."UID", b."Timestamp", b."Security", b."Timeframe",
               b."GapTick", b."OpenTick", b."HighTick", b."LowTick", b."CloseTick",
               b."Volume", b."CreatedAt", b."CreatedBy", b."UpdatedAt", b."UpdatedBy",
               g."UID" AS "Gap_UID", g."Timestamp" AS "Gap_Timestamp", g."Security" AS "Gap_Security",
               g."Ask" AS "Gap_Ask", g."Bid" AS "Gap_Bid",
               g."AskBaseConversion" AS "Gap_AskBaseConversion", g."BidBaseConversion" AS "Gap_BidBaseConversion",
               g."AskQuoteConversion" AS "Gap_AskQuoteConversion", g."BidQuoteConversion" AS "Gap_BidQuoteConversion",
               g."Volume" AS "Gap_Volume",
               g."CreatedAt" AS "Gap_CreatedAt", g."CreatedBy" AS "Gap_CreatedBy",
               g."UpdatedAt" AS "Gap_UpdatedAt", g."UpdatedBy" AS "Gap_UpdatedBy",
               o."UID" AS "Open_UID", o."Timestamp" AS "Open_Timestamp", o."Security" AS "Open_Security",
               o."Ask" AS "Open_Ask", o."Bid" AS "Open_Bid",
               o."AskBaseConversion" AS "Open_AskBaseConversion", o."BidBaseConversion" AS "Open_BidBaseConversion",
               o."AskQuoteConversion" AS "Open_AskQuoteConversion", o."BidQuoteConversion" AS "Open_BidQuoteConversion",
               o."Volume" AS "Open_Volume",
               o."CreatedAt" AS "Open_CreatedAt", o."CreatedBy" AS "Open_CreatedBy",
               o."UpdatedAt" AS "Open_UpdatedAt", o."UpdatedBy" AS "Open_UpdatedBy",
               h."UID" AS "High_UID", h."Timestamp" AS "High_Timestamp", h."Security" AS "High_Security",
               h."Ask" AS "High_Ask", h."Bid" AS "High_Bid",
               h."AskBaseConversion" AS "High_AskBaseConversion", h."BidBaseConversion" AS "High_BidBaseConversion",
               h."AskQuoteConversion" AS "High_AskQuoteConversion", h."BidQuoteConversion" AS "High_BidQuoteConversion",
               h."Volume" AS "High_Volume",
               h."CreatedAt" AS "High_CreatedAt", h."CreatedBy" AS "High_CreatedBy",
               h."UpdatedAt" AS "High_UpdatedAt", h."UpdatedBy" AS "High_UpdatedBy",
               l."UID" AS "Low_UID", l."Timestamp" AS "Low_Timestamp", l."Security" AS "Low_Security",
               l."Ask" AS "Low_Ask", l."Bid" AS "Low_Bid",
               l."AskBaseConversion" AS "Low_AskBaseConversion", l."BidBaseConversion" AS "Low_BidBaseConversion",
               l."AskQuoteConversion" AS "Low_AskQuoteConversion", l."BidQuoteConversion" AS "Low_BidQuoteConversion",
               l."Volume" AS "Low_Volume",
               l."CreatedAt" AS "Low_CreatedAt", l."CreatedBy" AS "Low_CreatedBy",
               l."UpdatedAt" AS "Low_UpdatedAt", l."UpdatedBy" AS "Low_UpdatedBy",
               c."UID" AS "Close_UID", c."Timestamp" AS "Close_Timestamp", c."Security" AS "Close_Security",
               c."Ask" AS "Close_Ask", c."Bid" AS "Close_Bid",
               c."AskBaseConversion" AS "Close_AskBaseConversion", c."BidBaseConversion" AS "Close_BidBaseConversion",
               c."AskQuoteConversion" AS "Close_AskQuoteConversion", c."BidQuoteConversion" AS "Close_BidQuoteConversion",
               c."Volume" AS "Close_Volume",
               c."CreatedAt" AS "Close_CreatedAt", c."CreatedBy" AS "Close_CreatedBy",
               c."UpdatedAt" AS "Close_UpdatedAt", c."UpdatedBy" AS "Close_UpdatedBy"
        FROM "Market"."Bar" b
        LEFT JOIN "Market"."Tick" g ON b."GapTick"   = g."UID"
        LEFT JOIN "Market"."Tick" o ON b."OpenTick"  = o."UID"
        LEFT JOIN "Market"."Tick" h ON b."HighTick"  = h."UID"
        LEFT JOIN "Market"."Tick" l ON b."LowTick"   = l."UID"
        LEFT JOIN "Market"."Tick" c ON b."CloseTick" = c."UID"
        WHERE b."Security" = :security: AND b."Timeframe" = :timeframe:
          AND b."Timestamp" BETWEEN :start: AND :stop:
        ORDER BY b."Timestamp"
        '''
        df = db.executeone(QueryAPI(sql), security=security, timeframe=timeframe, start=start, stop=stop, schema=BarAPI.Schema, table=BarAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_ticks(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        db.upsert(schema=TickAPI.Schema, table=TickAPI.Table, data=data, key=["Timestamp", "Security"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def push_bars(db: DatabaseAPI, data: pl.DataFrame | list[dict] | tuple | dict) -> None:
        db.upsert(schema=BarAPI.Schema, table=BarAPI.Table, data=data, key=["Timestamp", "Security", "Timeframe"], exclude=["CreatedAt", "CreatedBy"])