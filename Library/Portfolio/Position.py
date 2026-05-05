from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import IdentityKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Enumeration import Enumeration
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.PnL import PnLAPI
from Library.Universe.Universe import UniverseAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI, Direction
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Universe.Security import SecurityAPI
    from Library.Portfolio.Order import OrderAPI

class PositionType(Enumeration):
    Normal = 0
    Continuation = 1

@dataclass
class PositionAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Position"

    UID: Union[int, None] = None
    Type: InitVar[Union[PositionType, str, None]] = field(default=MISSING)
    Direction: InitVar[Union[Direction, str, None]] = field(default=MISSING)
    Volume: Union[float, None] = None
    Quantity: Union[float, None] = None
    UsedMargin: Union[float, None] = None
    MidBalance: Union[float, None] = None
    Label: Union[str, None] = None
    Comment: Union[str, None] = None

    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)

    EntryTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    EntryPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    StopLossPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    TakeProfitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    MaxRunUpPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    MaxDrawDownPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    ExitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)

    StopLossPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    TakeProfitPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    MaxRunUpPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    MaxDrawDownPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    GrossPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    CommissionPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    SwapPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    NetPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)

    EntryBalance: InitVar[Union[float, None]] = field(default=MISSING)

    Order: InitVar[Union[int, OrderAPI, None]] = field(default=MISSING)

    _type_: Union[PositionType, None] = field(default=None, init=False, repr=False)
    _direction_: Union[Direction, None] = field(default=None, init=False, repr=False)

    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _entry_timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _entry_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _stop_loss_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _take_profit_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _max_run_up_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _max_draw_down_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _exit_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _stop_loss_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _take_profit_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _max_run_up_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _max_draw_down_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _gross_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _commission_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _swap_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _net_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _entry_balance_: Union[float, None] = field(default=None, init=False, repr=False)
    _order_: Union[OrderAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        from Library.Universe.Security import SecurityAPI
        from Library.Portfolio.Order import OrderAPI
        s = super().Structure
        cols = {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{UniverseAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")'),
            self.ID.Order: ForeignKey(pl.Int64, reference=f'"{PortfolioAPI.Schema}"."{OrderAPI.Table}"("{OrderAPI.ID.UID}")'),
            self.ID.Type: pl.String(),
            self.ID.Direction: pl.String(),
            self.ID.Volume: pl.Float64(),
            self.ID.Quantity: pl.Float64(),
            self.ID.EntryTimestamp: pl.Datetime(),
            self.ID.EntryPrice: pl.Float64(),
            self.ID.StopLossPrice: pl.Float64(),
            self.ID.TakeProfitPrice: pl.Float64(),
            self.ID.MaxRunUpPrice: pl.Float64(),
            self.ID.MaxDrawDownPrice: pl.Float64(),
            self.ID.ExitPrice: pl.Float64(),
            self.ID.StopLossPnL: pl.Float64(),
            self.ID.TakeProfitPnL: pl.Float64(),
            self.ID.MaxRunUpPnL: pl.Float64(),
            self.ID.MaxDrawDownPnL: pl.Float64(),
            self.ID.GrossPnL: pl.Float64(),
            self.ID.CommissionPnL: pl.Float64(),
            self.ID.SwapPnL: pl.Float64(),
            self.ID.NetPnL: pl.Float64(),
            self.ID.UsedMargin: pl.Float64(),
            self.ID.EntryBalance: pl.Float64(),
            self.ID.MidBalance: pl.Float64(),
            self.ID.Label: pl.String(),
            self.ID.Comment: pl.String(),
        }
        for k, v in s.items():
            if k not in cols:
                cols[k] = v
        return cols

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      type: Union[PositionType, str, None],
                      direction: Union[Direction, str, None],
                      security: Union[int, SecurityAPI, None],
                      entry_timestamp: Union[datetime, TimestampAPI, None],
                      entry_price: Union[float, PriceAPI, None],
                      stop_loss_price: Union[float, PriceAPI, None],
                      take_profit_price: Union[float, PriceAPI, None],
                      max_run_up_price: Union[float, PriceAPI, None],
                      max_draw_down_price: Union[float, PriceAPI, None],
                      exit_price: Union[float, PriceAPI, None],
                      stop_loss_pnl: Union[float, PnLAPI, None],
                      take_profit_pnl: Union[float, PnLAPI, None],
                      max_run_up_pnl: Union[float, PnLAPI, None],
                      max_draw_down_pnl: Union[float, PnLAPI, None],
                      gross_pnl: Union[float, PnLAPI, None],
                      commission_pnl: Union[float, PnLAPI, None],
                      swap_pnl: Union[float, PnLAPI, None],
                      net_pnl: Union[float, PnLAPI, None],
                      entry_balance: Union[float, None],
                      order: Union[int, OrderAPI, None]) -> None:
        from Library.Universe.Security import SecurityAPI
        from Library.Portfolio.Order import OrderAPI
        type = coerce(type)
        direction = coerce(direction)
        security = coerce(security)
        entry_timestamp = coerce(entry_timestamp)
        entry_price = coerce(entry_price)
        stop_loss_price = coerce(stop_loss_price)
        take_profit_price = coerce(take_profit_price)
        max_run_up_price = coerce(max_run_up_price)
        max_draw_down_price = coerce(max_draw_down_price)
        exit_price = coerce(exit_price)
        stop_loss_pnl = coerce(stop_loss_pnl)
        take_profit_pnl = coerce(take_profit_pnl)
        max_run_up_pnl = coerce(max_run_up_pnl)
        max_draw_down_pnl = coerce(max_draw_down_pnl)
        gross_pnl = coerce(gross_pnl)
        commission_pnl = coerce(commission_pnl)
        swap_pnl = coerce(swap_pnl)
        net_pnl = coerce(net_pnl)
        entry_balance = coerce(entry_balance)
        order = coerce(order)

        self._type_ = PositionType.parse(type) if type is not MISSING else None
        self._direction_ = Direction.parse(direction) if direction is not MISSING else None

        if isinstance(security, SecurityAPI): self._security_ = security
        elif security is not MISSING and security is not None:
            self._security_ = SecurityAPI(UID=security, db=db, autoload=True)
        order = coerce(order)
        if isinstance(order, OrderAPI): self._order_ = order
        elif order is not MISSING and order is not None:
            self._order_ = OrderAPI(UID=order, db=db, autoload=True)
        self._entry_balance_ = entry_balance if entry_balance is not MISSING else None
        if isinstance(entry_timestamp, TimestampAPI): self._entry_timestamp_ = entry_timestamp
        elif entry_timestamp is not MISSING and entry_timestamp is not None:
            self._entry_timestamp_ = TimestampAPI(DateTime=entry_timestamp)
        ep = self._unwrap_price_(entry_price)
        self._entry_price_ = self._make_price_(entry_price, reference=ep)
        self._stop_loss_price_ = self._make_price_(stop_loss_price, reference=ep)
        self._take_profit_price_ = self._make_price_(take_profit_price, reference=ep)
        self._max_run_up_price_ = self._make_price_(max_run_up_price, reference=ep)
        self._max_draw_down_price_ = self._make_price_(max_draw_down_price, reference=ep)
        self._exit_price_ = self._make_price_(exit_price, reference=ep)
        eb = self._entry_balance_
        self._stop_loss_pnl_ = self._make_pnl_(stop_loss_pnl, reference=eb)
        self._take_profit_pnl_ = self._make_pnl_(take_profit_pnl, reference=eb)
        self._max_run_up_pnl_ = self._make_pnl_(max_run_up_pnl, reference=eb)
        self._max_draw_down_pnl_ = self._make_pnl_(max_draw_down_pnl, reference=eb)
        self._gross_pnl_ = self._make_pnl_(gross_pnl, reference=eb)
        self._commission_pnl_ = self._make_pnl_(commission_pnl, reference=eb)
        self._swap_pnl_ = self._make_pnl_(swap_pnl, reference=eb)
        self._net_pnl_ = self._make_pnl_(net_pnl, reference=eb)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if row:
            self._type_ = PositionType.parse(row.get(self.ID.Type))
            self._direction_ = Direction.parse(row.get(self.ID.Direction))
        return row

    @staticmethod
    def _unwrap_price_(val: Union[float, PriceAPI, None]) -> Union[float, None]:
        if isinstance(val, PriceAPI): return val.Price
        return val if val is not MISSING else None

    @staticmethod
    def _unwrap_pnl_(val: Union[float, PnLAPI, None]) -> Union[float, None]:
        if isinstance(val, PnLAPI): return val.PnL
        return val if val is not MISSING else None

    def _make_price_(self, val: Union[float, PriceAPI, None], reference: Union[float, None]) -> Union[PriceAPI, None]:
        if isinstance(val, PriceAPI):
            if val.Contract is None: val.Contract = self._security_.Contract if self._security_ else None
            if val.Reference is None: val.Reference = reference
            return val
        if val is MISSING or val is None: return None
        return PriceAPI(Price=val, Reference=reference, Contract=self._security_.Contract if self._security_ else None)

    @staticmethod
    def _make_pnl_(val: Union[float, PnLAPI, None], reference: Union[float, None]) -> Union[PnLAPI, None]:
        if isinstance(val, PnLAPI):
            if val.Reference is None: val.Reference = reference
            return val
        if val is MISSING or val is None: return None
        return PnLAPI(PnL=val, Reference=reference)

    @property
    @overridefield
    def Type(self) -> Union[PositionType, None]:
        return self._type_
    @Type.setter
    def Type(self, val: Union[PositionType, str, None]) -> None:
        self._type_ = PositionType.parse(val)

    @property
    @overridefield
    def Direction(self) -> Union[Direction, None]:
        return self._direction_
    @Direction.setter
    def Direction(self, val: Union[Direction, str, None]) -> None:
        self._direction_ = Direction.parse(val)

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, SecurityAPI, None]) -> None:
        from Library.Universe.Security import SecurityAPI
        if isinstance(val, SecurityAPI): self._security_ = val
        elif val is not None: self._security_ = SecurityAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def EntryTimestamp(self) -> Union[TimestampAPI, None]:
        return self._entry_timestamp_
    @EntryTimestamp.setter
    def EntryTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        if isinstance(val, TimestampAPI): self._entry_timestamp_ = val
        elif val is not None:
            if self._entry_timestamp_: self._entry_timestamp_.DateTime = val
            else: self._entry_timestamp_ = TimestampAPI(DateTime=val)

    @property
    @overridefield
    def EntryPrice(self) -> Union[PriceAPI, None]:
        return self._entry_price_
    @EntryPrice.setter
    def EntryPrice(self, val: Union[float, PriceAPI, None]) -> None:
        price = val.Price if isinstance(val, PriceAPI) else val
        if price is None: return
        if self._entry_price_:
            self._entry_price_.Price = price
            self._entry_price_.Reference = price
        else:
            self._entry_price_ = PriceAPI(Price=price, Reference=price, Contract=self._security_.Contract if self._security_ else None)
        for backing in (self._stop_loss_price_, self._take_profit_price_, self._max_run_up_price_, self._max_draw_down_price_, self._exit_price_):
            if backing: backing.Reference = price

    @property
    @overridefield
    def StopLossPrice(self) -> Union[PriceAPI, None]:
        return self._stop_loss_price_
    @StopLossPrice.setter
    def StopLossPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._stop_loss_price_ = self._assign_price_(self._stop_loss_price_, val)

    @property
    @overridefield
    def TakeProfitPrice(self) -> Union[PriceAPI, None]:
        return self._take_profit_price_
    @TakeProfitPrice.setter
    def TakeProfitPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._take_profit_price_ = self._assign_price_(self._take_profit_price_, val)

    @property
    @overridefield
    def MaxRunUpPrice(self) -> Union[PriceAPI, None]:
        return self._max_run_up_price_
    @MaxRunUpPrice.setter
    def MaxRunUpPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._max_run_up_price_ = self._assign_price_(self._max_run_up_price_, val)

    @property
    @overridefield
    def MaxDrawDownPrice(self) -> Union[PriceAPI, None]:
        return self._max_draw_down_price_
    @MaxDrawDownPrice.setter
    def MaxDrawDownPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._max_draw_down_price_ = self._assign_price_(self._max_draw_down_price_, val)

    @property
    @overridefield
    def ExitPrice(self) -> Union[PriceAPI, None]:
        return self._exit_price_
    @ExitPrice.setter
    def ExitPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._exit_price_ = self._assign_price_(self._exit_price_, val)

    def _assign_price_(self, backing: Union[PriceAPI, None], val: Union[float, PriceAPI, None]) -> Union[PriceAPI, None]:
        if isinstance(val, PriceAPI): return val
        if val is None: return backing
        if backing:
            backing.Price = val
            return backing
        ref = self._entry_price_.Price if self._entry_price_ else val
        return PriceAPI(Price=val, Reference=ref, Contract=self._security_.Contract if self._security_ else None)

    @property
    @overridefield
    def StopLossPnL(self) -> Union[PnLAPI, None]:
        return self._stop_loss_pnl_
    @StopLossPnL.setter
    def StopLossPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._stop_loss_pnl_ = self._assign_pnl_(self._stop_loss_pnl_, val)

    @property
    @overridefield
    def TakeProfitPnL(self) -> Union[PnLAPI, None]:
        return self._take_profit_pnl_
    @TakeProfitPnL.setter
    def TakeProfitPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._take_profit_pnl_ = self._assign_pnl_(self._take_profit_pnl_, val)

    @property
    @overridefield
    def MaxRunUpPnL(self) -> Union[PnLAPI, None]:
        return self._max_run_up_pnl_
    @MaxRunUpPnL.setter
    def MaxRunUpPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._max_run_up_pnl_ = self._assign_pnl_(self._max_run_up_pnl_, val)

    @property
    @overridefield
    def MaxDrawDownPnL(self) -> Union[PnLAPI, None]:
        return self._max_draw_down_pnl_
    @MaxDrawDownPnL.setter
    def MaxDrawDownPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._max_draw_down_pnl_ = self._assign_pnl_(self._max_draw_down_pnl_, val)

    @property
    @overridefield
    def GrossPnL(self) -> Union[PnLAPI, None]:
        return self._gross_pnl_
    @GrossPnL.setter
    def GrossPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._gross_pnl_ = self._assign_pnl_(self._gross_pnl_, val)

    @property
    @overridefield
    def CommissionPnL(self) -> Union[PnLAPI, None]:
        return self._commission_pnl_
    @CommissionPnL.setter
    def CommissionPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._commission_pnl_ = self._assign_pnl_(self._commission_pnl_, val)

    @property
    @overridefield
    def SwapPnL(self) -> Union[PnLAPI, None]:
        return self._swap_pnl_
    @SwapPnL.setter
    def SwapPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._swap_pnl_ = self._assign_pnl_(self._swap_pnl_, val)

    @property
    @overridefield
    def NetPnL(self) -> Union[PnLAPI, None]:
        return self._net_pnl_
    @NetPnL.setter
    def NetPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._net_pnl_ = self._assign_pnl_(self._net_pnl_, val)

    def _assign_pnl_(self, backing: Union[PnLAPI, None], val: Union[float, PnLAPI, None]) -> Union[PnLAPI, None]:
        if isinstance(val, PnLAPI): return val
        if val is None: return backing
        if backing:
            backing.PnL = val
            return backing
        return PnLAPI(PnL=val, Reference=self._entry_balance_)

    @property
    @overridefield
    def EntryBalance(self) -> Union[float, None]:
        return self._entry_balance_
    @EntryBalance.setter
    def EntryBalance(self, val: Union[float, None]) -> None:
        self._entry_balance_ = val
        for backing in (self._stop_loss_pnl_, self._take_profit_pnl_, self._max_run_up_pnl_, self._max_draw_down_pnl_, self._gross_pnl_, self._commission_pnl_, self._swap_pnl_, self._net_pnl_):
            if backing: backing.Reference = val

    @property
    def IsLong(self) -> bool:
        return self._direction_ == Direction.Buy
    @property
    def IsShort(self) -> bool:
        return self._direction_ == Direction.Sell
    @property
    def RiskReward(self) -> Union[float, None]:
        if self._entry_price_ is None or self._stop_loss_price_ is None or self._take_profit_price_ is None: return None
        ep, sl, tp = self._entry_price_.Price, self._stop_loss_price_.Price, self._take_profit_price_.Price
        if ep is None or sl is None or tp is None: return None
        risk, reward = abs(ep - sl), abs(tp - ep)
        if not risk: return None
        return reward / risk
    @property
    def RiskAmount(self) -> Union[float, None]:
        if self._stop_loss_pnl_ and self._stop_loss_pnl_.PnL is not None:
            return abs(self._stop_loss_pnl_.PnL)
        return None

    @property
    def RewardAmount(self) -> Union[float, None]:
        if self._take_profit_pnl_ and self._take_profit_pnl_.PnL is not None:
            return abs(self._take_profit_pnl_.PnL)
        return None

    @property
    def MarginUtilization(self) -> Union[float, None]:
        if not self.UsedMargin or not self._entry_balance_: return None
        return self.UsedMargin / self._entry_balance_

    @property
    def IsProfitable(self) -> Union[bool, None]:
        if self._net_pnl_ and self._net_pnl_.PnL is not None:
            return self._net_pnl_.PnL > 0
        return None

    @property
    def NetReturn(self) -> Union[float, None]:
        if self._net_pnl_:
            return self._net_pnl_.Return
        return None

    @property
    def Drawdown(self) -> Union[float, None]:
        if self._max_draw_down_pnl_:
            return self._max_draw_down_pnl_.Return
        return None

    @property
    def Runup(self) -> Union[float, None]:
        if self._max_run_up_pnl_:
            return self._max_run_up_pnl_.Return
        return None

    @property
    def Leverage(self) -> Union[float, None]:
        if not self.UsedMargin or self.Volume is None: return None
        return self.Volume / self.UsedMargin

    @property
    @overridefield
    def Order(self) -> Union[OrderAPI, None]:
        return self._order_
    @Order.setter
    def Order(self, val: Union[int, OrderAPI, None]) -> None:
        from Library.Portfolio.Order import OrderAPI
        if isinstance(val, OrderAPI): self._order_ = val
        elif val is not None: self._order_ = OrderAPI(UID=val, db=self._db_, autoload=True)