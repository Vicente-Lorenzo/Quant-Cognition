from datetime import datetime
from typing import Union, ClassVar
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Utility.Enumeration import EnumerationAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Account import AccountAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI, Direction
from Library.Utility.Typing import MISSING

class OrderType(EnumerationAPI):

    Market = 0
    Limit = 1
    Stop = 2
    StopLimit = 3

class OrderStatus(EnumerationAPI):

    Accepted = 1
    Filled = 2
    Rejected = 3
    Expired = 4
    Cancelled = 5

class TimeInForce(EnumerationAPI):

    GoodTillDate = 1
    GoodTillCancel = 2
    ImmediateOrCancel = 3
    FillOrKill = 4
    MarketOnOpen = 5

@dataclass
class OrderAPI(DatapointAPI):

    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Order"

    UID: Union[int, None] = None
    Session: InitVar[Union[str, SessionAPI, None]] = field(default=MISSING)
    Account: InitVar[Union[int, AccountAPI, None]] = field(default=MISSING)
    Position: InitVar[Union[int, PositionAPI, None]] = field(default=MISSING)
    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)
    Direction: InitVar[Union[Direction, str, None]] = field(default=MISSING)
    OrderType: InitVar[Union[OrderType, str, None]] = field(default=MISSING)
    OrderStatus: InitVar[Union[OrderStatus, str, None]] = field(default=MISSING)
    TimeInForce: InitVar[Union[TimeInForce, str, None]] = field(default=MISSING)
    Volume: Union[float, None] = None
    ExecutedVolume: Union[float, None] = None
    ExecutionPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    LimitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    StopPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    StopLossPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    TakeProfitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    RelativeStopLoss: Union[float, None] = None
    RelativeTakeProfit: Union[float, None] = None
    BaseSlippagePrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    SlippageInPoints: Union[int, None] = None
    ClosingOrder: Union[bool, None] = None
    ClientOrderID: Union[str, None] = None
    IsStopOut: Union[bool, None] = None
    TrailingStopLoss: Union[bool, None] = None
    StopTriggerMethod: Union[int, None] = None
    EntryTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    ExpirationTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    LastUpdateTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    Contract: InitVar[Union[ContractAPI, None]] = field(default=MISSING)
    Label: Union[str, None] = None
    Comment: Union[str, None] = None

    _session_: Union[SessionAPI, None] = field(default=None, init=False, repr=False)
    _account_: Union[AccountAPI, None] = field(default=None, init=False, repr=False)
    _position_: Union[PositionAPI, None] = field(default=None, init=False, repr=False)
    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _direction_: Union[Direction, None] = field(default=None, init=False, repr=False)
    _order_type_: Union[OrderType, None] = field(default=None, init=False, repr=False)
    _order_status_: Union[OrderStatus, None] = field(default=None, init=False, repr=False)
    _time_in_force_: Union[TimeInForce, None] = field(default=None, init=False, repr=False)
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
        return {
            self.ID.UID: PrimaryKey(pl.Int64),
            self.ID.Session: ForeignKey(pl.String, reference=SessionAPI.reference()),
            self.ID.Account: ForeignKey(pl.Int64, reference=AccountAPI.reference()),
            self.ID.Position: pl.Int64(),
            self.ID.Security: ForeignKey(pl.Int64, reference=SecurityAPI.reference()),
            self.ID.Direction: pl.String(),
            self.ID.OrderType: pl.String(),
            self.ID.OrderStatus: pl.String(),
            self.ID.TimeInForce: pl.String(),
            self.ID.EntryTimestamp: pl.Datetime(),
            self.ID.ExpirationTimestamp: pl.Datetime(),
            self.ID.LastUpdateTimestamp: pl.Datetime(),
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
            self.ID.TrailingStopLoss: pl.Boolean(),
            self.ID.StopTriggerMethod: pl.Int32(),
            self.ID.ClosingOrder: pl.Boolean(),
            self.ID.IsStopOut: pl.Boolean(),
            self.ID.ClientOrderID: pl.String(),
            self.ID.Label: pl.String(),
            self.ID.Comment: pl.String(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool,
                      session: Union[str, SessionAPI, None],
                      account: Union[int, AccountAPI, None],
                      position: Union[int, PositionAPI, None],
                      security: Union[int, SecurityAPI, None],
                      direction: Union[Direction, str, None],
                      order_type: Union[OrderType, str, None],
                      order_status: Union[OrderStatus, str, None],
                      time_in_force: Union[TimeInForce, str, None],
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
        session = coerce(session)
        account = coerce(account)
        position = coerce(position)
        security = coerce(security)
        direction = coerce(direction)
        order_type = coerce(order_type)
        order_status = coerce(order_status)
        time_in_force = coerce(time_in_force)
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

        self._session_ = self._relate_(session, SessionAPI, db=db, autoload=True)
        self._account_ = self._relate_(account, AccountAPI, db=db, autoload=True)
        self._position_ = self._relate_(position, PositionAPI, db=db, migrate=migrate, autoload=False, autooverload=False)
        self._security_ = self._relate_(security, SecurityAPI, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        self._direction_ = Direction.parse(direction) if direction is not MISSING else None
        self._order_type_ = OrderType.parse(order_type) if order_type is not MISSING else None
        self._order_status_ = OrderStatus.parse(order_status) if order_status is not MISSING else None
        self._time_in_force_ = TimeInForce.parse(time_in_force) if time_in_force is not MISSING else None
        if contract is not MISSING: self._contract_ = contract
        ep = PriceAPI.unwrap(execution_price)
        self._execution_price_ = PriceAPI.make(execution_price, ep, self._contract_)
        self._limit_price_ = PriceAPI.make(limit_price, ep, self._contract_)
        self._stop_price_ = PriceAPI.make(stop_price, ep, self._contract_)
        self._stop_loss_price_ = PriceAPI.make(stop_loss_price, ep, self._contract_)
        self._take_profit_price_ = PriceAPI.make(take_profit_price, ep, self._contract_)
        self._base_slippage_price_ = PriceAPI.make(base_slippage_price, ep, self._contract_)
        self._entry_timestamp_ = TimestampAPI.assign(None, entry_timestamp)
        self._expiration_timestamp_ = TimestampAPI.assign(None, expiration_timestamp)
        self._last_update_timestamp_ = TimestampAPI.assign(None, last_update_timestamp)
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if row:
            self._direction_ = Direction.parse(row.get(self.ID.Direction))
            self._order_type_ = OrderType.parse(row.get(self.ID.OrderType))
            self._order_status_ = OrderStatus.parse(row.get(self.ID.OrderStatus))
            self._time_in_force_ = TimeInForce.parse(row.get(self.ID.TimeInForce))
        return row

    @property
    @overridefield
    def Session(self) -> Union[SessionAPI, None]:
        return self._session_
    @Session.setter
    def Session(self, val: Union[str, SessionAPI, None]) -> None:
        if val is not None: self._session_ = self._relate_(val, SessionAPI, db=self._db_, autoload=True)

    @property
    @overridefield
    def Account(self) -> Union[AccountAPI, None]:
        return self._account_
    @Account.setter
    def Account(self, val: Union[int, AccountAPI, None]) -> None:
        if val is not None: self._account_ = self._relate_(val, AccountAPI, db=self._db_, autoload=True)

    @property
    @overridefield
    def Position(self) -> Union[PositionAPI, None]:
        return self._position_
    @Position.setter
    def Position(self, val: Union[int, PositionAPI, None]) -> None:
        if val is not None: self._position_ = self._relate_(val, PositionAPI, db=self._db_, autoload=False, autooverload=False)

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, SecurityAPI, None]) -> None:
        if val is not None: self._security_ = self._relate_(val, SecurityAPI, db=self._db_, autoload=True)
        if self._security_ and self._security_.Contract:
            self.Contract = self._security_.Contract

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
    def ExecutionPrice(self) -> Union[PriceAPI, None]:
        return self._execution_price_
    @ExecutionPrice.setter
    def ExecutionPrice(self, val: Union[float, PriceAPI, None]) -> None:
        price = PriceAPI.unwrap(val)
        if price is None: return
        self._execution_price_ = PriceAPI.assign(self._execution_price_, price, price, self._contract_)
        for backing in (self._execution_price_, self._limit_price_, self._stop_price_, self._stop_loss_price_, self._take_profit_price_, self._base_slippage_price_):
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
        self._entry_timestamp_ = TimestampAPI.assign(self._entry_timestamp_, val)

    @property
    @overridefield
    def ExpirationTimestamp(self) -> Union[TimestampAPI, None]:
        return self._expiration_timestamp_
    @ExpirationTimestamp.setter
    def ExpirationTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._expiration_timestamp_ = TimestampAPI.assign(self._expiration_timestamp_, val)

    @property
    @overridefield
    def LastUpdateTimestamp(self) -> Union[TimestampAPI, None]:
        return self._last_update_timestamp_
    @LastUpdateTimestamp.setter
    def LastUpdateTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        self._last_update_timestamp_ = TimestampAPI.assign(self._last_update_timestamp_, val)

    @property
    @overridefield
    def Contract(self) -> Union[ContractAPI, None]:
        return self._contract_
    @Contract.setter
    def Contract(self, val: Union[ContractAPI, None]) -> None:
        self._contract_ = val
        for backing in (self._execution_price_, self._limit_price_, self._stop_price_, self._stop_loss_price_, self._take_profit_price_, self._base_slippage_price_):
            if backing: backing.Contract = self._contract_

    @property
    def IsBuy(self) -> bool:
        return self._direction_ == Direction.Buy

    @property
    def IsSell(self) -> bool:
        return self._direction_ == Direction.Sell

    @property
    def IsAccepted(self) -> bool:
        return self._order_status_ == OrderStatus.Accepted

    @property
    def IsFilled(self) -> bool:
        return self._order_status_ == OrderStatus.Filled

    @property
    def IsRejected(self) -> bool:
        return self._order_status_ == OrderStatus.Rejected

    @property
    def IsExpired(self) -> bool:
        return self._order_status_ == OrderStatus.Expired

    @property
    def IsCancelled(self) -> bool:
        return self._order_status_ == OrderStatus.Cancelled

    @property
    def ExecutionRatio(self) -> Union[float, None]:
        if not self.Volume or self.ExecutedVolume is None: return None
        return self.ExecutedVolume / self.Volume

    @property
    def UnfilledVolume(self) -> Union[float, None]:
        if self.Volume is None or self.ExecutedVolume is None: return None
        return self.Volume - self.ExecutedVolume

    def _assign_price_(self, backing: Union[PriceAPI, None], val: Union[float, PriceAPI, None]) -> Union[PriceAPI, None]:
        return PriceAPI.assign(backing, val, self._execution_price_.Price if self._execution_price_ else val, self._contract_)