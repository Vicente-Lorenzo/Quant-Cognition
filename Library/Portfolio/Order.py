from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import IdentityKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Enumeration import Enumeration
from Library.Portfolio.Position import PositionAPI
from Library.Universe.Universe import UniverseAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI, Direction
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Universe.Security import SecurityAPI
    from Library.Universe.Contract import ContractAPI

class OrderType(Enumeration):
    Market = 1
    Limit = 2
    Stop = 3
    StopLossTakeProfit = 4
    MarketRange = 5
    StopLimit = 6

class OrderStatus(Enumeration):
    Accepted = 1
    Filled = 2
    Rejected = 3
    Expired = 4
    Cancelled = 5

class TimeInForce(Enumeration):
    GoodTillDate = 1
    GoodTillCancel = 2
    ImmediateOrCancel = 3
    FillOrKill = 4
    MarketOnOpen = 5

@dataclass
class OrderAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Order"

    UID: Union[int, None] = None
    Direction: InitVar[Union[Direction, str, None]] = field(default=MISSING)
    OrderType: InitVar[Union[OrderType, str, None]] = field(default=MISSING)
    OrderStatus: InitVar[Union[OrderStatus, str, None]] = field(default=MISSING)
    TimeInForce: InitVar[Union[TimeInForce, str, None]] = field(default=MISSING)
    Volume: Union[float, None] = None
    ExecutedVolume: Union[float, None] = None
    RelativeStopLoss: Union[float, None] = None
    RelativeTakeProfit: Union[float, None] = None
    SlippageInPoints: Union[int, None] = None
    ClosingOrder: Union[bool, None] = None
    ClientOrderID: Union[str, None] = None
    IsStopOut: Union[bool, None] = None
    TrailingStopLoss: Union[bool, None] = None
    StopTriggerMethod: Union[int, None] = None
    Label: Union[str, None] = None
    Comment: Union[str, None] = None

    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)
    Position: InitVar[Union[int, PositionAPI, None]] = field(default=MISSING)

    ExecutionPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    LimitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    StopPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    StopLossPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    TakeProfitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    BaseSlippagePrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)

    EntryTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    ExpirationTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    LastUpdateTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)

    Contract: InitVar[Union[ContractAPI, None]] = field(default=MISSING)

    _direction_: Union[Direction, None] = field(default=None, init=False, repr=False)
    _order_type_: Union[OrderType, None] = field(default=None, init=False, repr=False)
    _order_status_: Union[OrderStatus, None] = field(default=None, init=False, repr=False)
    _time_in_force_: Union[TimeInForce, None] = field(default=None, init=False, repr=False)

    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _position_: Union[PositionAPI, None] = field(default=None, init=False, repr=False)
    _execution_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _limit_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _stop_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _stop_loss_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _take_profit_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _base_slippage_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _entry_timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _expiration_timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _last_update_timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _contract_: Union[ContractAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        from Library.Universe.Security import SecurityAPI
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{UniverseAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")'),
            self.ID.Position: pl.Int64(),
            self.ID.Direction: pl.String(),
            self.ID.OrderType: pl.String(),
            self.ID.OrderStatus: pl.String(),
            self.ID.TimeInForce: pl.String(),
            self.ID.Volume: pl.Float64(),
            self.ID.ExecutedVolume: pl.Float64(),
            self.ID.ExecutionPrice: pl.Float64(),
            self.ID.LimitPrice: pl.Float64(),
            self.ID.StopPrice: pl.Float64(),
            self.ID.StopLossPrice: pl.Float64(),
            self.ID.TakeProfitPrice: pl.Float64(),
            self.ID.RelativeStopLoss: pl.Float64(),
            self.ID.RelativeTakeProfit: pl.Float64(),
            self.ID.BaseSlippagePrice: pl.Float64(),
            self.ID.SlippageInPoints: pl.Int32(),
            self.ID.ClosingOrder: pl.Boolean(),
            self.ID.ClientOrderID: pl.String(),
            self.ID.IsStopOut: pl.Boolean(),
            self.ID.TrailingStopLoss: pl.Boolean(),
            self.ID.StopTriggerMethod: pl.Int32(),
            self.ID.EntryTimestamp: pl.Datetime(),
            self.ID.ExpirationTimestamp: pl.Datetime(),
            self.ID.LastUpdateTimestamp: pl.Datetime(),
            self.ID.Label: pl.String(),
            self.ID.Comment: pl.String(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      direction: Union[Direction, str, None],
                      order_type: Union[OrderType, str, None],
                      order_status: Union[OrderStatus, str, None],
                      time_in_force: Union[TimeInForce, str, None],
                      security: Union[int, SecurityAPI, None],
                      position: Union[int, PositionAPI, None],
                      execution_price: Union[float, PriceAPI, None],
                      limit_price: Union[float, PriceAPI, None],
                      stop_price: Union[float, PriceAPI, None],
                      stop_loss_price: Union[float, PriceAPI, None],
                      take_profit_price: Union[float, PriceAPI, None],
                      base_slippage_price: Union[float, PriceAPI, None],
                      entry_timestamp: Union[datetime, TimestampAPI, None],
                      expiration_timestamp: Union[datetime, TimestampAPI, None],
                      last_update_timestamp: Union[datetime, TimestampAPI, None],
                      contract: Union[ContractAPI, None]) -> None:
        from Library.Universe.Security import SecurityAPI
        direction = coerce(direction)
        order_type = coerce(order_type)
        order_status = coerce(order_status)
        time_in_force = coerce(time_in_force)
        
        self._direction_ = Direction.parse(direction) if direction is not MISSING else None
        self._order_type_ = OrderType.parse(order_type) if order_type is not MISSING else None
        self._order_status_ = OrderStatus.parse(order_status) if order_status is not MISSING else None
        self._time_in_force_ = TimeInForce.parse(time_in_force) if time_in_force is not MISSING else None

        security = coerce(security)
        position = coerce(position)
        execution_price = coerce(execution_price)
        limit_price = coerce(limit_price)
        stop_price = coerce(stop_price)
        stop_loss_price = coerce(stop_loss_price)
        take_profit_price = coerce(take_profit_price)
        base_slippage_price = coerce(base_slippage_price)
        entry_timestamp = coerce(entry_timestamp)
        expiration_timestamp = coerce(expiration_timestamp)
        last_update_timestamp = coerce(last_update_timestamp)
        contract = coerce(contract)

        if isinstance(security, SecurityAPI): self._security_ = security
        elif security is not MISSING and security is not None:
            self._security_ = SecurityAPI(UID=security, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if isinstance(position, PositionAPI): self._position_ = position
        elif position is not MISSING and position is not None:
            self._position_ = PositionAPI(UID=position, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if contract is not MISSING: self._contract_ = contract
        ep = self._unwrap_price_(execution_price)
        self._execution_price_ = self._make_price_(execution_price, reference=ep)
        self._limit_price_ = self._make_price_(limit_price, reference=ep)
        self._stop_price_ = self._make_price_(stop_price, reference=ep)
        self._stop_loss_price_ = self._make_price_(stop_loss_price, reference=ep)
        self._take_profit_price_ = self._make_price_(take_profit_price, reference=ep)
        self._base_slippage_price_ = self._make_price_(base_slippage_price, reference=ep)
        self._entry_timestamp_ = self._make_timestamp_(entry_timestamp)
        self._expiration_timestamp_ = self._make_timestamp_(expiration_timestamp)
        self._last_update_timestamp_ = self._make_timestamp_(last_update_timestamp)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if row:
            self._direction_ = Direction.parse(row.get(self.ID.Direction))
            self._order_type_ = OrderType.parse(row.get(self.ID.OrderType))
            self._order_status_ = OrderStatus.parse(row.get(self.ID.OrderStatus))
            self._time_in_force_ = TimeInForce.parse(row.get(self.ID.TimeInForce))
        return row

    @staticmethod
    def _unwrap_price_(val: Union[float, PriceAPI, None]) -> Union[float, None]:
        if isinstance(val, PriceAPI): return val.Price
        return val if val is not MISSING else None

    def _make_price_(self, val: Union[float, PriceAPI, None], reference: Union[float, None]) -> Union[PriceAPI, None]:
        if isinstance(val, PriceAPI):
            if val.Contract is None: val.Contract = self._contract_
            if val.Reference is None: val.Reference = reference
            return val
        if val is MISSING or val is None: return None
        return PriceAPI(Price=val, Reference=reference, Contract=self._contract_)

    @staticmethod
    def _make_timestamp_(val: Union[datetime, TimestampAPI, None]) -> Union[TimestampAPI, None]:
        if isinstance(val, TimestampAPI): return val
        if val is MISSING or val is None: return None
        return TimestampAPI(DateTime=val)

    def _assign_price_(self, backing: Union[PriceAPI, None], val: Union[float, PriceAPI, None]) -> Union[PriceAPI, None]:
        if isinstance(val, PriceAPI): return val
        if val is None: return backing
        if backing:
            backing.Price = val
            return backing
        ref = self._execution_price_.Price if self._execution_price_ else val
        return PriceAPI(Price=val, Reference=ref, Contract=self._contract_)

    @staticmethod
    def _assign_timestamp_(backing: Union[TimestampAPI, None], val: Union[datetime, TimestampAPI, None]) -> Union[TimestampAPI, None]:
        if isinstance(val, TimestampAPI): return val
        if val is None: return backing
        if backing:
            backing.DateTime = val
            return backing
        return TimestampAPI(DateTime=val)

    @property
    @overridefield
    def Direction(self) -> Union[Direction, None]:
        return self._direction_
    @Direction.setter
    def Direction(self, val: Union[Direction, str, None]) -> None:
        self._direction_ = Direction.parse(val)

    @property
    @overridefield
    def OrderType(self) -> Union[OrderType, None]:
        return self._order_type_
    @OrderType.setter
    def OrderType(self, val: Union[OrderType, str, None]) -> None:
        self._order_type_ = OrderType.parse(val)

    @property
    @overridefield
    def OrderStatus(self) -> Union[OrderStatus, None]:
        return self._order_status_
    @OrderStatus.setter
    def OrderStatus(self, val: Union[OrderStatus, str, None]) -> None:
        self._order_status_ = OrderStatus.parse(val)

    @property
    @overridefield
    def TimeInForce(self) -> Union[TimeInForce, None]:
        return self._time_in_force_
    @TimeInForce.setter
    def TimeInForce(self, val: Union[TimeInForce, str, None]) -> None:
        self._time_in_force_ = TimeInForce.parse(val)

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
    def Position(self) -> Union[PositionAPI, None]:
        return self._position_
    @Position.setter
    def Position(self, val: Union[int, PositionAPI, None]) -> None:
        if isinstance(val, PositionAPI): self._position_ = val
        elif val is not None: self._position_ = PositionAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def ExecutionPrice(self) -> Union[PriceAPI, None]:
        return self._execution_price_
    @ExecutionPrice.setter
    def ExecutionPrice(self, val: Union[float, PriceAPI, None]) -> None:
        price = val.Price if isinstance(val, PriceAPI) else val
        if price is None: return
        if self._execution_price_:
            self._execution_price_.Price = price
            self._execution_price_.Reference = price
        else:
            self._execution_price_ = PriceAPI(Price=price, Reference=price, Contract=self._contract_)
        for backing in (self._limit_price_, self._stop_price_, self._stop_loss_price_, self._take_profit_price_, self._base_slippage_price_):
            if backing: backing.Reference = price

    @property
    @overridefield
    def LimitPrice(self) -> Union[PriceAPI, None]:
        return self._limit_price_
    @LimitPrice.setter
    def LimitPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._limit_price_ = self._assign_price_(self._limit_price_, val)

    @property
    @overridefield
    def StopPrice(self) -> Union[PriceAPI, None]:
        return self._stop_price_
    @StopPrice.setter
    def StopPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._stop_price_ = self._assign_price_(self._stop_price_, val)

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
    def BaseSlippagePrice(self) -> Union[PriceAPI, None]:
        return self._base_slippage_price_
    @BaseSlippagePrice.setter
    def BaseSlippagePrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._base_slippage_price_ = self._assign_price_(self._base_slippage_price_, val)

    @property
    @overridefield
    def EntryTimestamp(self) -> Union[TimestampAPI, None]:
        return self._entry_timestamp_
    @EntryTimestamp.setter
    def EntryTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._entry_timestamp_ = self._assign_timestamp_(self._entry_timestamp_, val)

    @property
    @overridefield
    def ExpirationTimestamp(self) -> Union[TimestampAPI, None]:
        return self._expiration_timestamp_
    @ExpirationTimestamp.setter
    def ExpirationTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._expiration_timestamp_ = self._assign_timestamp_(self._expiration_timestamp_, val)

    @property
    @overridefield
    def LastUpdateTimestamp(self) -> Union[TimestampAPI, None]:
        return self._last_update_timestamp_
    @LastUpdateTimestamp.setter
    def LastUpdateTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._last_update_timestamp_ = self._assign_timestamp_(self._last_update_timestamp_, val)

    @property
    def IsBuy(self) -> bool:
        return self._direction_ == Direction.Buy
    @property
    def IsSell(self) -> bool:
        return self._direction_ == Direction.Sell
    @property
    def IsFilled(self) -> bool:
        return self._order_status_ == OrderStatus.Filled
    @property
    def IsAccepted(self) -> bool:
        return self._order_status_ == OrderStatus.Accepted
    @property
    def IsRejected(self) -> bool:
        return self._order_status_ == OrderStatus.Rejected
    @property
    def IsCancelled(self) -> bool:
        return self._order_status_ == OrderStatus.Cancelled
    @property
    def IsExpired(self) -> bool:
        return self._order_status_ == OrderStatus.Expired
    @property
    def ExecutionRatio(self) -> Union[float, None]:
        if not self.Volume or self.ExecutedVolume is None: return None
        return self.ExecutedVolume / self.Volume
    @property
    def RiskAmount(self) -> Union[float, None]:
        if self._execution_price_ and self._stop_loss_price_ and self.Volume:
            if self.Contract and self.Contract.LotSize:
                return abs(self._execution_price_.Price - self._stop_loss_price_.Price) * self.Volume * self.Contract.LotSize
        return None

    @property
    def RewardAmount(self) -> Union[float, None]:
        if self._execution_price_ and self._take_profit_price_ and self.Volume:
            if self.Contract and self.Contract.LotSize:
                return abs(self._take_profit_price_.Price - self._execution_price_.Price) * self.Volume * self.Contract.LotSize
        return None

    @property
    def UnfilledVolume(self) -> Union[float, None]:
        if self.Volume is None or self.ExecutedVolume is None: return None
        return self.Volume - self.ExecutedVolume

    @property
    @overridefield
    def Contract(self) -> Union[ContractAPI, None]:
        return self._contract_
    @Contract.setter
    def Contract(self, val: Union[ContractAPI, None]) -> None:
        self._contract_ = val
        for backing in (self._execution_price_, self._limit_price_, self._stop_price_, self._stop_loss_price_, self._take_profit_price_, self._base_slippage_price_):
            if backing: backing.Contract = self._contract_