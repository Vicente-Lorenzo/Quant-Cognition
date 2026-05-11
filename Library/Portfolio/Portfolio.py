from __future__ import annotations

from datetime import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field, InitVar
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Query import QueryAPI
from Library.Market.Price import Direction
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI
    from Library.Portfolio.Account import AccountAPI
    from Library.Portfolio.Order import OrderAPI
    from Library.Portfolio.Position import PositionAPI
    from Library.Portfolio.Trade import TradeAPI
    from Library.Market.Tick import TickAPI
    from Library.Market.Bar import BarAPI
    from Library.Parameters import Parameters
    from Library.Universe.Security import SecurityAPI

@dataclass(kw_only=True)
class PortfolioAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Portfolio"
    Table: ClassVar[str] = "Portfolio"

    Parameters: InitVar[Union[Parameters, None]] = field(default=MISSING)

    _account_: Union[AccountAPI, None] = field(default=None, init=False)
    _security_: Union[SecurityAPI, None] = field(default=None, init=False)
    _orders_: dict[int, OrderAPI] = field(default_factory=dict, init=False)
    _positions_: dict[int, PositionAPI] = field(default_factory=dict, init=False)
    _trades_: list[TradeAPI] = field(default_factory=list, init=False)

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      parameters: Union[Parameters, None] = None) -> None:
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    @staticmethod
    def load_accounts(data: Union[AccountAPI, Sequence[AccountAPI]]) -> None:
        if isinstance(data, (list, tuple)):
            for acc in data: acc.load()
        else: data.load()

    @staticmethod
    def save_accounts(data: Union[AccountAPI, Sequence[AccountAPI]], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for acc in data: acc.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def pull_accounts(db: DatabaseAPI) -> pl.DataFrame:
        from Library.Portfolio.Account import AccountAPI
        sql = f'''
        SELECT a.*,
               p."UID" AS "Provider_UID", p."Platform" AS "Provider_Platform", p."Name" AS "Provider_Name", p."Abbreviation" AS "Provider_Abbreviation", p."CreatedAt" AS "Provider_CreatedAt", p."CreatedBy" AS "Provider_CreatedBy", p."UpdatedAt" AS "Provider_UpdatedAt", p."UpdatedBy" AS "Provider_UpdatedBy"
        FROM "{AccountAPI.Schema}"."{AccountAPI.Table}" a
        LEFT JOIN "Universe"."Provider" p ON a."Provider" = p."UID"
        '''
        df = db.executeone(QueryAPI(sql), schema=AccountAPI.Schema, table=AccountAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_accounts(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Account import AccountAPI
        db.upsert(schema=AccountAPI.Schema, table=AccountAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def load_orders(data: Union[OrderAPI, Sequence[OrderAPI]]) -> None:
        if isinstance(data, (list, tuple)):
            for ord in data: ord.load()
        else: data.load()

    @staticmethod
    def save_orders(data: Union[OrderAPI, Sequence[OrderAPI]], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for ord in data: ord.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def pull_orders(db: DatabaseAPI, start: Union[datetime, None] = None, stop: Union[datetime, None] = None) -> pl.DataFrame:
        from Library.Portfolio.Order import OrderAPI
        sql = f'''
        SELECT o.*,
               s."UID" AS "Security_UID", s."Provider" AS "Security_Provider", s."Category" AS "Security_Category", s."Ticker" AS "Security_Ticker", s."Contract" AS "Security_Contract", s."CreatedAt" AS "Security_CreatedAt", s."CreatedBy" AS "Security_CreatedBy", s."UpdatedAt" AS "Security_UpdatedAt", s."UpdatedBy" AS "Security_UpdatedBy",
               c."UID" AS "Contract_UID", c."Ticker" AS "Contract_Ticker", c."Provider" AS "Contract_Provider", c."Type" AS "Contract_Type", c."Digits" AS "Contract_Digits", c."PointSize" AS "Contract_PointSize", c."PipSize" AS "Contract_PipSize", c."LotSize" AS "Contract_LotSize", c."VolumeMin" AS "Contract_VolumeMin", c."VolumeMax" AS "Contract_VolumeMax", c."VolumeStep" AS "Contract_VolumeStep", c."Commission" AS "Contract_Commission", c."CommissionMode" AS "Contract_CommissionMode", c."SwapLong" AS "Contract_SwapLong", c."SwapShort" AS "Contract_SwapShort", c."SwapMode" AS "Contract_SwapMode", c."SwapExtraDay" AS "Contract_SwapExtraDay", c."SwapSummerTime" AS "Contract_SwapSummerTime", c."SwapWinterTime" AS "Contract_SwapWinterTime", c."SwapPeriod" AS "Contract_SwapPeriod", c."Expiry" AS "Contract_Expiry", c."CreatedAt" AS "Contract_CreatedAt", c."CreatedBy" AS "Contract_CreatedBy", c."UpdatedAt" AS "Contract_UpdatedAt", c."UpdatedBy" AS "Contract_UpdatedBy",
               p."UID" AS "Position_UID", p."Security" AS "Position_Security", p."PositionType" AS "Position_PositionType", p."Direction" AS "Position_TradeType", p."Volume" AS "Position_Volume", p."Quantity" AS "Position_Quantity", p."EntryTimestamp" AS "Position_EntryTimestamp", p."EntryPrice" AS "Position_EntryPrice", p."StopLossPrice" AS "Position_StopLossPrice", p."TakeProfitPrice" AS "Position_TakeProfitPrice", p."MaxRunUpPrice" AS "Position_MaxRunUpPrice", p."MaxDrawDownPrice" AS "Position_MaxDrawDownPrice", p."ExitPrice" AS "Position_ExitPrice", p."StopLossPnL" AS "Position_StopLossPnL", p."TakeProfitPnL" AS "Position_TakeProfitPnL", p."MaxRunUpPnL" AS "Position_MaxRunUpPnL", p."MaxDrawDownPnL" AS "Position_MaxDrawDownPnL", p."GrossPnL" AS "Position_GrossPnL", p."CommissionPnL" AS "Position_CommissionPnL", p."SwapPnL" AS "Position_SwapPnL", p."NetPnL" AS "Position_NetPnL", p."UsedMargin" AS "Position_UsedMargin", p."EntryBalance" AS "Position_EntryBalance", p."MidBalance" AS "Position_MidBalance", p."CreatedAt" AS "Position_CreatedAt", p."CreatedBy" AS "Position_CreatedBy", p."UpdatedAt" AS "Position_UpdatedAt", p."UpdatedBy" AS "Position_UpdatedBy"
        FROM "{OrderAPI.Schema}"."{OrderAPI.Table}" o
        LEFT JOIN "Universe"."Security" s ON o."Security" = s."UID"
        LEFT JOIN "Universe"."Contract" c ON s."Contract" = c."UID"
        LEFT JOIN "Portfolio"."Position" p ON o."Position" = p."UID"
        '''
        params = {}
        if start and stop:
            sql += f' WHERE o."{OrderAPI.ID.EntryTimestamp}" BETWEEN :start: AND :stop:'
            params = {"start": start, "stop": stop}
        df = db.executeone(QueryAPI(sql), **params, schema=OrderAPI.Schema, table=OrderAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_orders(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Order import OrderAPI
        db.upsert(schema=OrderAPI.Schema, table=OrderAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def load_positions(data: Union[PositionAPI, Sequence[PositionAPI]]) -> None:
        if isinstance(data, (list, tuple)):
            for pos in data: pos.load()
        else: data.load()

    @staticmethod
    def save_positions(data: Union[PositionAPI, Sequence[PositionAPI]], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for pos in data: pos.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def pull_positions(db: DatabaseAPI, start: Union[datetime, None] = None, stop: Union[datetime, None] = None) -> pl.DataFrame:
        from Library.Portfolio.Position import PositionAPI
        sql = f'''
        SELECT pos.*,
               s."UID" AS "Security_UID", s."Provider" AS "Security_Provider", s."Category" AS "Security_Category", s."Ticker" AS "Security_Ticker", s."Contract" AS "Security_Contract", s."CreatedAt" AS "Security_CreatedAt", s."CreatedBy" AS "Security_CreatedBy", s."UpdatedAt" AS "Security_UpdatedAt", s."UpdatedBy" AS "Security_UpdatedBy",
               c."UID" AS "Contract_UID", c."Ticker" AS "Contract_Ticker", c."Provider" AS "Contract_Provider", c."Type" AS "Contract_Type", c."Digits" AS "Contract_Digits", c."PointSize" AS "Contract_PointSize", c."PipSize" AS "Contract_PipSize", c."LotSize" AS "Contract_LotSize", c."VolumeMin" AS "Contract_VolumeMin", c."VolumeMax" AS "Contract_VolumeMax", c."VolumeStep" AS "Contract_VolumeStep", c."Commission" AS "Contract_Commission", c."CommissionMode" AS "Contract_CommissionMode", c."SwapLong" AS "Contract_SwapLong", c."SwapShort" AS "Contract_SwapShort", c."SwapMode" AS "Contract_SwapMode", c."SwapExtraDay" AS "Contract_SwapExtraDay", c."SwapSummerTime" AS "Contract_SwapSummerTime", c."SwapWinterTime" AS "Contract_SwapWinterTime", c."SwapPeriod" AS "Contract_SwapPeriod", c."Expiry" AS "Contract_Expiry", c."CreatedAt" AS "Contract_CreatedAt", c."CreatedBy" AS "Contract_CreatedBy", c."UpdatedAt" AS "Contract_UpdatedAt", c."UpdatedBy" AS "Contract_UpdatedBy"
        FROM "{PositionAPI.Schema}"."{PositionAPI.Table}" pos
        LEFT JOIN "Universe"."Security" s ON pos."Security" = s."UID"
        LEFT JOIN "Universe"."Contract" c ON s."Contract" = c."UID"
        '''
        params = {}
        if start and stop:
            sql += f' WHERE pos."{PositionAPI.ID.EntryTimestamp}" BETWEEN :start: AND :stop:'
            params = {"start": start, "stop": stop}
        df = db.executeone(QueryAPI(sql), **params, schema=PositionAPI.Schema, table=PositionAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_positions(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Position import PositionAPI
        db.upsert(schema=PositionAPI.Schema, table=PositionAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    @staticmethod
    def load_trades(data: Union[TradeAPI, Sequence[TradeAPI]]) -> None:
        if isinstance(data, (list, tuple)):
            for tr in data: tr.load()
        else: data.load()

    @staticmethod
    def save_trades(data: Union[TradeAPI, Sequence[TradeAPI]], by: str = "Autosave") -> None:
        if isinstance(data, (list, tuple)):
            for tr in data: tr.save(by=by)
        else: data.save(by=by)

    @staticmethod
    def pull_trades(db: DatabaseAPI, start: Union[datetime, None] = None, stop: Union[datetime, None] = None) -> pl.DataFrame:
        from Library.Portfolio.Trade import TradeAPI
        sql = f'''
        SELECT t.*,
               p."UID" AS "Position_UID", p."Security" AS "Position_Security", p."PositionType" AS "Position_PositionType", p."Direction" AS "Position_TradeType", p."Volume" AS "Position_Volume", p."Quantity" AS "Position_Quantity", p."EntryTimestamp" AS "Position_EntryTimestamp", p."EntryPrice" AS "Position_EntryPrice", p."StopLossPrice" AS "Position_StopLossPrice", p."TakeProfitPrice" AS "Position_TakeProfitPrice", p."MaxRunUpPrice" AS "Position_MaxRunUpPrice", p."MaxDrawDownPrice" AS "Position_MaxDrawDownPrice", p."ExitPrice" AS "Position_ExitPrice", p."StopLossPnL" AS "Position_StopLossPnL", p."TakeProfitPnL" AS "Position_TakeProfitPnL", p."MaxRunUpPnL" AS "Position_MaxRunUpPnL", p."MaxDrawDownPnL" AS "Position_MaxDrawDownPnL", p."GrossPnL" AS "Position_GrossPnL", p."CommissionPnL" AS "Position_CommissionPnL", p."SwapPnL" AS "Position_SwapPnL", p."NetPnL" AS "Position_NetPnL", p."UsedMargin" AS "Position_UsedMargin", p."EntryBalance" AS "Position_EntryBalance", p."MidBalance" AS "Position_MidBalance", p."CreatedAt" AS "Position_CreatedAt", p."CreatedBy" AS "Position_CreatedBy", p."UpdatedAt" AS "Position_UpdatedAt", p."UpdatedBy" AS "Position_UpdatedBy",
               s."UID" AS "Security_UID", s."Provider" AS "Security_Provider", s."Category" AS "Security_Category", s."Ticker" AS "Security_Ticker", s."Contract" AS "Security_Contract", s."CreatedAt" AS "Security_CreatedAt", s."CreatedBy" AS "Security_CreatedBy", s."UpdatedAt" AS "Security_UpdatedAt", s."UpdatedBy" AS "Security_UpdatedBy",
               c."UID" AS "Contract_UID", c."Ticker" AS "Contract_Ticker", c."Provider" AS "Contract_Provider", c."Type" AS "Contract_Type", c."Digits" AS "Contract_Digits", c."PointSize" AS "Contract_PointSize", c."PipSize" AS "Contract_PipSize", c."LotSize" AS "Contract_LotSize", c."VolumeMin" AS "Contract_VolumeMin", c."VolumeMax" AS "Contract_VolumeMax", c."VolumeStep" AS "Contract_VolumeStep", c."Commission" AS "Contract_Commission", c."CommissionMode" AS "Contract_CommissionMode", c."SwapLong" AS "Contract_SwapLong", c."SwapShort" AS "Contract_SwapShort", c."SwapMode" AS "Contract_SwapMode", c."SwapExtraDay" AS "Contract_SwapExtraDay", c."SwapSummerTime" AS "Contract_SwapSummerTime", c."SwapWinterTime" AS "Contract_SwapWinterTime", c."SwapPeriod" AS "Contract_SwapPeriod", c."Expiry" AS "Contract_Expiry", c."CreatedAt" AS "Contract_CreatedAt", c."CreatedBy" AS "Contract_CreatedBy", c."UpdatedAt" AS "Contract_UpdatedAt", c."UpdatedBy" AS "Contract_UpdatedBy"
        FROM "{TradeAPI.Schema}"."{TradeAPI.Table}" t
        LEFT JOIN "Portfolio"."Position" p ON t."Position" = p."UID"
        LEFT JOIN "Universe"."Security" s ON p."Security" = s."UID"
        LEFT JOIN "Universe"."Contract" c ON s."Contract" = c."UID"
        '''
        params = {}
        if start and stop:
            sql += f' WHERE t."{TradeAPI.ID.ExitTimestamp}" BETWEEN :start: AND :stop:'
            params = {"start": start, "stop": stop}
        df = db.executeone(QueryAPI(sql), **params, schema=TradeAPI.Schema, table=TradeAPI.Table).fetchall(legacy=False)
        return df

    @staticmethod
    def push_trades(db: DatabaseAPI, data: Union[pl.DataFrame, list[dict], tuple, dict]) -> None:
        from Library.Portfolio.Trade import TradeAPI
        db.upsert(schema=TradeAPI.Schema, table=TradeAPI.Table, data=data, key=["UID"], exclude=["CreatedAt", "CreatedBy"])

    def init_data(self, account: AccountAPI, orders: list[OrderAPI] = None, positions: list[PositionAPI] = None, trades: list[TradeAPI] = None) -> None:
        self._account_ = account
        if orders:
            for o in orders: self._orders_[o.UID] = o
        if positions:
            for p in positions: self._positions_[p.UID] = p
        if trades:
            self._trades_.extend(trades)

    def update_data(self, data: Union[TickAPI, BarAPI]) -> None:
        from Library.Market.Tick import TickAPI
        from Library.Portfolio.Statistic import calculate_pnl_difference, calculate_gross_pnl, calculate_net_pnl
        for pos in self._positions_.values():
            if isinstance(data, TickAPI):
                bid, ask, timestamp = data.Bid.Price, data.Ask.Price, data.Timestamp.DateTime
            else:
                bid, ask, timestamp = data.CloseTick.Bid.Price, data.CloseTick.Ask.Price, data.Timestamp.DateTime
            current_price = bid if pos.IsLong else ask
            if pos.NetPnL:
                pnl_diff = calculate_pnl_difference(current_price, pos.EntryPrice.Price, pos.IsLong)
                if pos.GrossPnL: pos.GrossPnL.PnL = calculate_gross_pnl(pnl_diff, pos.Volume)
                pos.NetPnL.PnL = calculate_net_pnl(pos.GrossPnL.PnL if pos.GrossPnL else 0.0,
                                                   pos.CommissionPnL.PnL if pos.CommissionPnL else 0.0,
                                                   pos.SwapPnL.PnL if pos.SwapPnL else 0.0)
                if pos.EntryTimestamp:
                    duration_sec = (timestamp - pos.EntryTimestamp.DateTime).total_seconds()
                    pos.NetPnL.Duration = duration_sec if duration_sec > 0 else None
                if self._account_ and self._account_.Balance: pos.NetPnL.Reference = self._account_.Balance
                
                if pos.MaxRunupPnL and (pos.MaxRunupPnL.PnL is None or pos.NetPnL.PnL > pos.MaxRunupPnL.PnL):
                    pos.MaxRunupPnL.PnL = pos.NetPnL.PnL
                    pos.MaxRunupPnL.Reference = pos.NetPnL.Reference
                    pos.MaxRunupPnL.Duration = pos.NetPnL.Duration
                if pos.MaxDrawdownPnL and (pos.MaxDrawdownPnL.PnL is None or pos.NetPnL.PnL < pos.MaxDrawdownPnL.PnL):
                    pos.MaxDrawdownPnL.PnL = pos.NetPnL.PnL
                    pos.MaxDrawdownPnL.Reference = pos.NetPnL.Reference
                    pos.MaxDrawdownPnL.Duration = pos.NetPnL.Duration
                    
            if pos.MaxRunupPrice is None or (pos.IsLong and current_price > pos.MaxRunupPrice.Price) or (pos.IsShort and current_price < pos.MaxRunupPrice.Price):
                if pos.MaxRunupPrice: pos.MaxRunupPrice.Price = current_price
            if pos.MaxDrawdownPrice is None or (pos.IsLong and current_price < pos.MaxDrawdownPrice.Price) or (pos.IsShort and current_price > pos.MaxDrawdownPrice.Price):
                if pos.MaxDrawdownPrice: pos.MaxDrawdownPrice.Price = current_price

    def open_order(self, order: OrderAPI) -> None:
        self._orders_[order.UID] = order

    def modify_order(self, order: OrderAPI) -> None:
        if order.UID in self._orders_:
            self._orders_[order.UID] = order

    def close_order(self, order_uid: int) -> None:
        if order_uid in self._orders_:
            del self._orders_[order_uid]

    def open_position(self, order_uid: int, position: PositionAPI) -> None:
        if order_uid in self._orders_:
            del self._orders_[order_uid]
        self._positions_[position.UID] = position
        position.EntryBalance = self._account_.Balance if self._account_ else 0.0

    def modify_position(self, position: PositionAPI) -> None:
        if position.UID in self._positions_:
            self._positions_[position.UID] = position

    def close_position(self, position_uid: int, trade: TradeAPI) -> None:
        if position_uid in self._positions_:
            old_pos = self._positions_[position_uid]
            if trade.MaxDrawdownPnL is None: trade.MaxDrawdownPnL = old_pos.MaxDrawdownPnL
            if old_pos.MaxDrawdownPrice:
                trade.MaxDrawdownPrice = old_pos.MaxDrawdownPrice
            trade.EntryBalance = old_pos.EntryBalance
            if self._account_ and trade.NetPnL:
                trade.ExitBalance = trade.EntryBalance + (trade.NetPnL.PnL or 0.0) if trade.EntryBalance else 0.0
                self._account_.Balance += (trade.NetPnL.PnL or 0.0)
            del self._positions_[position_uid]
        self._trades_.append(trade)

    def calculate_statistics(self, start: datetime, stop: datetime) -> pl.DataFrame:
        from Library.Portfolio.Statistic import generate_net_report
        if not self._account_: return pl.DataFrame()
        return generate_net_report(self.Trades, self.Positions, self._account_, start, stop)

    @property
    def BuyOrders(self) -> list[OrderAPI]:
        return [o for o in self._orders_.values() if o.IsBuy]

    @property
    def SellOrders(self) -> list[OrderAPI]:
        return [o for o in self._orders_.values() if o.IsSell]

    @property
    def BuyPositions(self) -> list[PositionAPI]:
        return [p for p in self._positions_.values() if p.IsLong]

    @property
    def SellPositions(self) -> list[PositionAPI]:
        return [p for p in self._positions_.values() if p.IsShort]

    @property
    def BuyTrades(self) -> list[TradeAPI]:
        return [t for t in self._trades_ if t.IsLong]

    @property
    def SellTrades(self) -> list[TradeAPI]:
        return [t for t in self._trades_ if t.IsShort]

    @property
    def UnrealizedPnL(self) -> float:
        return sum((p.NetPnL.PnL or 0.0) for p in self._positions_.values() if p.NetPnL)

    @property
    def Direction(self) -> Direction:
        from Library.Portfolio.Statistic import calculate_direction
        return calculate_direction(self.UnrealizedPnL)

    @property
    def Return(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_pnl_return
        if not self._account_ or not self._account_.Balance: return None
        return calculate_pnl_return(self.UnrealizedPnL, self._account_.Balance)

    @property
    def LogReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_return
        ret = self.Return
        if ret is None: return None
        return calculate_log_return(ret)

    @property
    def Percentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_percentage
        ret = self.Return
        if ret is None: return None
        return calculate_percentage(ret)

    @property
    def LogPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_percentage
        log_ret = self.LogReturn
        if log_ret is None: return None
        return calculate_log_percentage(log_ret)

    @property
    def AnnualizedReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_annualized_return
        ret = self.Return
        if ret is None or not self._positions_: return None
        first = min(p.EntryTimestamp.DateTime for p in self._positions_.values() if p.EntryTimestamp)
        if not first: return None
        now = datetime.now()
        duration_sec = (now - first).total_seconds()
        return calculate_annualized_return(ret, duration_sec)

    @property
    def AnnualizedLogReturn(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_annualized_log_return
        log_ret = self.LogReturn
        if log_ret is None or not self._positions_: return None
        first = min(p.EntryTimestamp.DateTime for p in self._positions_.values() if p.EntryTimestamp)
        if not first: return None
        now = datetime.now()
        duration_sec = (now - first).total_seconds()
        return calculate_annualized_log_return(log_ret, duration_sec)

    @property
    def AnnualizedPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_percentage
        return calculate_percentage(self.AnnualizedReturn)

    @property
    def AnnualizedLogPercentage(self) -> Union[float, None]:
        from Library.Portfolio.Statistic import calculate_log_percentage
        return calculate_log_percentage(self.AnnualizedLogReturn)

    @property
    def Trades(self) -> pl.DataFrame:
        if not self._trades_: return pl.DataFrame()
        return pl.DataFrame([t.dict() for t in self._trades_], strict=False)

    @property
    def Positions(self) -> pl.DataFrame:
        if not self._positions_: return pl.DataFrame()
        return pl.DataFrame([p.dict() for p in self._positions_.values()], strict=False)
        
    @property
    def Orders(self) -> pl.DataFrame:
        if not self._orders_: return pl.DataFrame()
        return pl.DataFrame([o.dict() for o in self._orders_.values()], strict=False)

    def __repr__(self) -> str:
        return repr(self.Positions)