from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Utility.Enumeration import EnumerationAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.PnL import PnLAPI
from Library.Portfolio.Session import SessionAPI
from Library.Portfolio.Account import AccountAPI
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Security import SecurityAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI, Direction
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Portfolio.Order import OrderAPI

class PositionMode(EnumerationAPI):
    Hedging = 0
    Netting = 1

class PositionType(EnumerationAPI):
    Normal = 0
    Continuation = 1

class PositionStatus(EnumerationAPI):
    Opened = 1
    Closed = 2

@dataclass
class PositionAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Position"

    UID: Union[int, None] = None
    Session: InitVar[Union[str, SessionAPI, None]] = field(default=MISSING)
    Account: InitVar[Union[int, AccountAPI, None]] = field(default=MISSING)
    Order: InitVar[Union[int, OrderAPI, None]] = field(default=MISSING)
    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)
    Type: InitVar[Union[PositionType, str, None]] = field(default=MISSING)
    Status: InitVar[Union[PositionStatus, str, None]] = field(default=MISSING)
    Direction: InitVar[Union[Direction, str, None]] = field(default=MISSING)
    Volume: Union[float, None] = None
    Quantity: Union[float, None] = None
    EntryTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    EntryPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    EntryBalance: InitVar[Union[float, None]] = field(default=MISSING)
    StopLossPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    TakeProfitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    StopLossPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    TakeProfitPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    MaxEquityDrawdownPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    MaxEquityRunupPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    MaxEquityDrawdownPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    MaxEquityRunupPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    ExitPrice: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    GrossPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    CommissionPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    SwapPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    NetPnL: InitVar[Union[float, PnLAPI, None]] = field(default=MISSING)
    UsedMargin: Union[float, None] = None
    MidBalance: Union[float, None] = None
    Label: Union[str, None] = None
    Comment: Union[str, None] = None

    _session_: Union[SessionAPI, None] = field(default=None, init=False, repr=False)
    _account_: Union[AccountAPI, None] = field(default=None, init=False, repr=False)
    _order_: Union[OrderAPI, None] = field(default=None, init=False, repr=False)
    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _type_: Union[PositionType, None] = field(default=None, init=False, repr=False)
    _status_: Union[PositionStatus, None] = field(default=None, init=False, repr=False)
    _direction_: Union[Direction, None] = field(default=None, init=False, repr=False)
    _entry_timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _entry_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _entry_balance_: Union[float, None] = field(default=None, init=False, repr=False)
    _stop_loss_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _take_profit_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _stop_loss_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _take_profit_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _max_equity_drawdown_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _max_equity_runup_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _max_equity_drawdown_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _max_equity_runup_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _exit_price_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _gross_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _commission_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _swap_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)
    _net_pnl_: Union[PnLAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        from Library.Portfolio.Order import OrderAPI
        s = super().Structure
        cols = {
            self.ID.UID: PrimaryKey(pl.Int64),
            self.ID.Session: ForeignKey(pl.String, reference=f'"{PortfolioAPI.Schema}"."{SessionAPI.Table}"("{SessionAPI.ID.UID}")'),
            self.ID.Account: ForeignKey(pl.Int64, reference=f'"{PortfolioAPI.Schema}"."{AccountAPI.Table}"("{AccountAPI.ID.UID}")'),
            self.ID.Order: ForeignKey(pl.Int64, reference=f'"{PortfolioAPI.Schema}"."{OrderAPI.Table}"("{OrderAPI.ID.UID}")'),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{UniverseAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")'),
            self.ID.Type: pl.String(),
            self.ID.Status: pl.String(),
            self.ID.Direction: pl.String(),
            self.ID.Volume: pl.Float64(),
            self.ID.Quantity: pl.Float64(),
            self.ID.EntryTimestamp: pl.Datetime(),
            self.ID.EntryPrice: pl.Float64(),
            self.ID.EntryBalance: pl.Float64(),
            self.ID.StopLossPrice: pl.Float64(),
            self.ID.TakeProfitPrice: pl.Float64(),
            self.ID.StopLossPnL: pl.Float64(),
            self.ID.TakeProfitPnL: pl.Float64(),
            self.ID.MaxEquityDrawdownPrice: pl.Float64(),
            self.ID.MaxEquityRunupPrice: pl.Float64(),
            self.ID.MaxEquityDrawdownPnL: pl.Float64(),
            self.ID.MaxEquityRunupPnL: pl.Float64(),
            self.ID.ExitPrice: pl.Float64(),
            self.ID.GrossPnL: pl.Float64(),
            self.ID.CommissionPnL: pl.Float64(),
            self.ID.SwapPnL: pl.Float64(),
            self.ID.NetPnL: pl.Float64(),
            self.ID.UsedMargin: pl.Float64(),
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
                      session: Union[str, SessionAPI, None],
                      account: Union[int, AccountAPI, None],
                      order: Union[int, OrderAPI, None],
                      security: Union[int, SecurityAPI, None],
                      type: Union[PositionType, str, None],
                      status: Union[PositionStatus, str, None],
                      direction: Union[Direction, str, None],
                      entry_timestamp: Union[datetime, TimestampAPI, None],
                      entry_price: Union[float, PriceAPI, None],
                      entry_balance: Union[float, None],
                      stop_loss_price: Union[float, PriceAPI, None],
                      take_profit_price: Union[float, PriceAPI, None],
                      stop_loss_pnl: Union[float, PnLAPI, None],
                      take_profit_pnl: Union[float, PnLAPI, None],
                      max_equity_drawdown_price: Union[float, PriceAPI, None],
                      max_equity_runup_price: Union[float, PriceAPI, None],
                      max_equity_drawdown_pnl: Union[float, PnLAPI, None],
                      max_equity_runup_pnl: Union[float, PnLAPI, None],
                      exit_price: Union[float, PriceAPI, None],
                      gross_pnl: Union[float, PnLAPI, None],
                      commission_pnl: Union[float, PnLAPI, None],
                      swap_pnl: Union[float, PnLAPI, None],
                      net_pnl: Union[float, PnLAPI, None]) -> None:
        from Library.Portfolio.Order import OrderAPI
        session = coerce(session)
        account = coerce(account)
        order = coerce(order)
        security = coerce(security)
        type = coerce(type)
        status = coerce(status)
        direction = coerce(direction)
        entry_timestamp = coerce(entry_timestamp)
        entry_price = coerce(entry_price)
        entry_balance = coerce(entry_balance)
        stop_loss_price = coerce(stop_loss_price)
        take_profit_price = coerce(take_profit_price)
        stop_loss_pnl = coerce(stop_loss_pnl)
        take_profit_pnl = coerce(take_profit_pnl)
        max_equity_drawdown_price = coerce(max_equity_drawdown_price)
        max_equity_runup_price = coerce(max_equity_runup_price)
        max_equity_drawdown_pnl = coerce(max_equity_drawdown_pnl)
        max_equity_runup_pnl = coerce(max_equity_runup_pnl)
        exit_price = coerce(exit_price)
        gross_pnl = coerce(gross_pnl)
        commission_pnl = coerce(commission_pnl)
        swap_pnl = coerce(swap_pnl)
        net_pnl = coerce(net_pnl)

        if isinstance(session, SessionAPI): self._session_ = session
        elif session is not MISSING and session is not None:
            self._session_ = SessionAPI(UID=session, db=db, autoload=True)
        if isinstance(account, AccountAPI): self._account_ = account
        elif account is not MISSING and account is not None:
            self._account_ = AccountAPI(UID=account, db=db, autoload=True)
        if isinstance(order, OrderAPI): self._order_ = order
        elif order is not MISSING and order is not None:
            self._order_ = OrderAPI(UID=order, db=db, autoload=True)
        if isinstance(security, SecurityAPI): self._security_ = security
        elif security is not MISSING and security is not None:
            self._security_ = SecurityAPI(UID=security, db=db, autoload=True)
        self._type_ = PositionType.parse(type) if type is not MISSING else None
        self._status_ = PositionStatus.parse(status) if status is not MISSING else PositionStatus.Opened
        self._direction_ = Direction.parse(direction) if direction is not MISSING else None
        if isinstance(entry_timestamp, TimestampAPI): self._entry_timestamp_ = entry_timestamp
        elif entry_timestamp is not MISSING and entry_timestamp is not None:
            self._entry_timestamp_ = TimestampAPI(DateTime=entry_timestamp)
        ep = self._unwrap_price_(entry_price)
        self._entry_price_ = self._make_price_(entry_price, reference=ep)
        self._entry_balance_ = entry_balance if entry_balance is not MISSING else None
        self._stop_loss_price_ = self._make_price_(stop_loss_price, reference=ep)
        self._take_profit_price_ = self._make_price_(take_profit_price, reference=ep)
        eb = self._entry_balance_
        self._stop_loss_pnl_ = self._make_pnl_(stop_loss_pnl, reference=eb)
        self._take_profit_pnl_ = self._make_pnl_(take_profit_pnl, reference=eb)
        self._max_equity_drawdown_price_ = self._make_price_(max_equity_drawdown_price, reference=ep)
        self._max_equity_runup_price_ = self._make_price_(max_equity_runup_price, reference=ep)
        self._max_equity_drawdown_pnl_ = self._make_pnl_(max_equity_drawdown_pnl, reference=eb)
        self._max_equity_runup_pnl_ = self._make_pnl_(max_equity_runup_pnl, reference=eb)
        self._exit_price_ = self._make_price_(exit_price, reference=ep)
        self._gross_pnl_ = self._make_pnl_(gross_pnl, reference=eb)
        self._commission_pnl_ = self._make_pnl_(commission_pnl, reference=eb)
        self._swap_pnl_ = self._make_pnl_(swap_pnl, reference=eb)
        self._net_pnl_ = self._make_pnl_(net_pnl, reference=eb)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if row:
            self._type_ = PositionType.parse(row.get(self.ID.Type))
            self._status_ = PositionStatus.parse(row.get(self.ID.Status))
            self._direction_ = Direction.parse(row.get(self.ID.Direction))
        return row

    @property
    @overridefield
    def Session(self) -> Union[SessionAPI, None]:
        return self._session_
    @Session.setter
    def Session(self, val: Union[str, SessionAPI, None]) -> None:
        if isinstance(val, SessionAPI): self._session_ = val
        elif val is not None: self._session_ = SessionAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def Account(self) -> Union[AccountAPI, None]:
        return self._account_
    @Account.setter
    def Account(self, val: Union[int, AccountAPI, None]) -> None:
        if isinstance(val, AccountAPI): self._account_ = val
        elif val is not None: self._account_ = AccountAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def Order(self) -> Union[OrderAPI, None]:
        return self._order_
    @Order.setter
    def Order(self, val: Union[int, OrderAPI, None]) -> None:
        from Library.Portfolio.Order import OrderAPI
        if isinstance(val, OrderAPI): self._order_ = val
        elif val is not None: self._order_ = OrderAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, SecurityAPI, None]) -> None:
        if isinstance(val, SecurityAPI): self._security_ = val
        elif val is not None: self._security_ = SecurityAPI(UID=val, db=self._db_, autoload=True)
        contract = self._security_.Contract if self._security_ else None
        for backing in (self._entry_price_, self._stop_loss_price_, self._take_profit_price_, self._max_equity_drawdown_price_, self._max_equity_runup_price_, self._exit_price_):
            if backing: backing.Contract = contract

    @property
    @overridefield
    def Type(self) -> Union[PositionType, None]:
        return self._type_
    @Type.setter
    def Type(self, val: Union[PositionType, str, None]) -> None:
        self._type_ = PositionType.parse(val)

    @property
    @overridefield
    def Status(self) -> Union[PositionStatus, None]:
        return self._status_
    @Status.setter
    def Status(self, val: Union[PositionStatus, str, None]) -> None:
        self._status_ = PositionStatus.parse(val)

    @property
    @overridefield
    def Direction(self) -> Union[Direction, None]:
        return self._direction_
    @Direction.setter
    def Direction(self, val: Union[Direction, str, None]) -> None:
        self._direction_ = Direction.parse(val)

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
        for backing in (self._stop_loss_price_, self._take_profit_price_, self._max_equity_drawdown_price_, self._max_equity_runup_price_, self._exit_price_):
            if backing: backing.Reference = price

    @property
    @overridefield
    def EntryBalance(self) -> Union[float, None]:
        return self._entry_balance_
    @EntryBalance.setter
    def EntryBalance(self, val: Union[float, None]) -> None:
        self._entry_balance_ = val
        for backing in (self._stop_loss_pnl_, self._take_profit_pnl_, self._max_equity_drawdown_pnl_, self._max_equity_runup_pnl_, self._gross_pnl_, self._commission_pnl_, self._swap_pnl_, self._net_pnl_):
            if backing: backing.Reference = val

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
    def MaxEquityDrawdownPrice(self) -> Union[PriceAPI, None]:
        return self._max_equity_drawdown_price_
    @MaxEquityDrawdownPrice.setter
    def MaxEquityDrawdownPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._max_equity_drawdown_price_ = self._assign_price_(self._max_equity_drawdown_price_, val)

    @property
    @overridefield
    def MaxEquityRunupPrice(self) -> Union[PriceAPI, None]:
        return self._max_equity_runup_price_
    @MaxEquityRunupPrice.setter
    def MaxEquityRunupPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._max_equity_runup_price_ = self._assign_price_(self._max_equity_runup_price_, val)

    @property
    @overridefield
    def MaxEquityDrawdownPnL(self) -> Union[PnLAPI, None]:
        return self._max_equity_drawdown_pnl_
    @MaxEquityDrawdownPnL.setter
    def MaxEquityDrawdownPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._max_equity_drawdown_pnl_ = self._assign_pnl_(self._max_equity_drawdown_pnl_, val)

    @property
    @overridefield
    def MaxEquityRunupPnL(self) -> Union[PnLAPI, None]:
        return self._max_equity_runup_pnl_
    @MaxEquityRunupPnL.setter
    def MaxEquityRunupPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._max_equity_runup_pnl_ = self._assign_pnl_(self._max_equity_runup_pnl_, val)

    @property
    @overridefield
    def ExitPrice(self) -> Union[PriceAPI, None]:
        return self._exit_price_
    @ExitPrice.setter
    def ExitPrice(self, val: Union[float, PriceAPI, None]) -> None:
        self._exit_price_ = self._assign_price_(self._exit_price_, val)

    @property
    @overridefield
    def GrossPnL(self) -> Union[PnLAPI, None]:
        return self._gross_pnl_
    @GrossPnL.setter
    def GrossPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._gross_pnl_ = self._assign_pnl_(self._gross_pnl_, val)

    @property
    @overridefield
    def GrossPoints(self) -> Union[float, None]:
        if self.GrossPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            return self.GrossPnL.PnL / (self.Volume * self.Security.Contract.PointSize)
        return 0.0

    @property
    @overridefield
    def GrossPips(self) -> Union[float, None]:
        if self.GrossPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            return self.GrossPnL.PnL / (self.Volume * self.Security.Contract.PipSize)
        return 0.0

    @property
    @overridefield
    def CommissionPnL(self) -> Union[PnLAPI, None]:
        return self._commission_pnl_
    @CommissionPnL.setter
    def CommissionPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._commission_pnl_ = self._assign_pnl_(self._commission_pnl_, val)

    @property
    @overridefield
    def CommissionPoints(self) -> Union[float, None]:
        if self.CommissionPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            return self.CommissionPnL.PnL / (self.Volume * self.Security.Contract.PointSize)
        return 0.0

    @property
    @overridefield
    def CommissionPips(self) -> Union[float, None]:
        if self.CommissionPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            return self.CommissionPnL.PnL / (self.Volume * self.Security.Contract.PipSize)
        return 0.0

    @property
    @overridefield
    def SwapPnL(self) -> Union[PnLAPI, None]:
        return self._swap_pnl_
    @SwapPnL.setter
    def SwapPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._swap_pnl_ = self._assign_pnl_(self._swap_pnl_, val)

    @property
    @overridefield
    def SwapPoints(self) -> Union[float, None]:
        if self.SwapPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            return self.SwapPnL.PnL / (self.Volume * self.Security.Contract.PointSize)
        return 0.0

    @property
    @overridefield
    def SwapPips(self) -> Union[float, None]:
        if self.SwapPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            return self.SwapPnL.PnL / (self.Volume * self.Security.Contract.PipSize)
        return 0.0

    @property
    @overridefield
    def NetPnL(self) -> Union[PnLAPI, None]:
        return self._net_pnl_
    @NetPnL.setter
    def NetPnL(self, val: Union[float, PnLAPI, None]) -> None:
        self._net_pnl_ = self._assign_pnl_(self._net_pnl_, val)

    @property
    @overridefield
    def NetPoints(self) -> Union[float, None]:
        if self.NetPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            return self.NetPnL.PnL / (self.Volume * self.Security.Contract.PointSize)
        return 0.0

    @property
    @overridefield
    def NetPips(self) -> Union[float, None]:
        if self.NetPnL and self.Volume and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            return self.NetPnL.PnL / (self.Volume * self.Security.Contract.PipSize)
        return 0.0

    @property
    def IsLong(self) -> bool:
        return self._direction_ == Direction.Buy

    @property
    def IsShort(self) -> bool:
        return self._direction_ == Direction.Sell

    @property
    def MarginUtilization(self) -> Union[float, None]:
        if not self.UsedMargin or not self._entry_balance_: return None
        return self.UsedMargin / self._entry_balance_

    @property
    @overridefield
    def Leverage(self) -> Union[float, None]:
        if not self.UsedMargin or self.Volume is None: return None
        return self.Volume / self.UsedMargin

    @property
    @overridefield
    def Points(self) -> Union[float, None]:
        if self.EntryPrice and self.EntryPrice.Price and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            exit_price = getattr(self, "ExitPrice", None)
            exit_price = exit_price.Price if exit_price else None
            if exit_price is not None:
                diff = exit_price - self.EntryPrice.Price
                diff = diff if self.IsLong else -diff
                return diff / self.Security.Contract.PointSize
        return 0.0

    @property
    @overridefield
    def Pips(self) -> Union[float, None]:
        if self.EntryPrice and self.EntryPrice.Price and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            exit_price = getattr(self, "ExitPrice", None)
            exit_price = exit_price.Price if exit_price else None
            if exit_price is not None:
                diff = exit_price - self.EntryPrice.Price
                diff = diff if self.IsLong else -diff
                return diff / self.Security.Contract.PipSize
        return 0.0

    @property
    @overridefield
    def Return(self) -> Union[float, None]:
        return self.NetPnL.Return if self.NetPnL else 0.0

    @property
    @overridefield
    def LogReturn(self) -> Union[float, None]:
        return self.NetPnL.LogReturn if self.NetPnL else 0.0

    @property
    @overridefield
    def Percentage(self) -> Union[float, None]:
        return self.NetPnL.Percentage if self.NetPnL else 0.0

    @property
    @overridefield
    def LogPercentage(self) -> Union[float, None]:
        return self.NetPnL.LogPercentage if self.NetPnL else 0.0

    @property
    @overridefield
    def AnnualizedReturn(self) -> Union[float, None]:
        return self.NetPnL.AnnualizedReturn if self.NetPnL else None

    @property
    @overridefield
    def AnnualizedLogReturn(self) -> Union[float, None]:
        return self.NetPnL.AnnualizedLogReturn if self.NetPnL else None

    @property
    @overridefield
    def AnnualizedPercentage(self) -> Union[float, None]:
        return self.NetPnL.AnnualizedPercentage if self.NetPnL else None

    @property
    @overridefield
    def AnnualizedLogPercentage(self) -> Union[float, None]:
        return self.NetPnL.AnnualizedLogPercentage if self.NetPnL else None

    @property
    @overridefield
    def MaxBalanceDrawdownPnL(self) -> Union[float, None]:
        return min(0.0, self.NetPnL.PnL) if self.NetPnL and self.NetPnL.PnL is not None else 0.0

    @property
    @overridefield
    def MaxBalanceDrawdownPoints(self) -> Union[float, None]:
        return min(0.0, self.Points or 0.0)

    @property
    @overridefield
    def MaxEquityDrawdownPoints(self) -> Union[float, None]:
        if self.MaxEquityDrawdownPrice and self.MaxEquityDrawdownPrice.Price and self.EntryPrice and self.EntryPrice.Price and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            diff = self.MaxEquityDrawdownPrice.Price - self.EntryPrice.Price
            diff = diff if self.IsLong else -diff
            return diff / self.Security.Contract.PointSize
        return 0.0

    @property
    @overridefield
    def MaxBalanceDrawdownPips(self) -> Union[float, None]:
        return min(0.0, self.Pips or 0.0)

    @property
    @overridefield
    def MaxEquityDrawdownPips(self) -> Union[float, None]:
        if self.MaxEquityDrawdownPrice and self.MaxEquityDrawdownPrice.Price and self.EntryPrice and self.EntryPrice.Price and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            diff = self.MaxEquityDrawdownPrice.Price - self.EntryPrice.Price
            diff = diff if self.IsLong else -diff
            return diff / self.Security.Contract.PipSize
        return 0.0

    @property
    @overridefield
    def MaxBalanceDrawdownReturn(self) -> Union[float, None]:
        return min(0.0, self.Return or 0.0)

    @property
    @overridefield
    def MaxEquityDrawdownReturn(self) -> Union[float, None]:
        return self._max_equity_drawdown_pnl_.Return if self._max_equity_drawdown_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceDrawdownLogReturn(self) -> Union[float, None]:
        return min(0.0, self.LogReturn or 0.0)

    @property
    @overridefield
    def MaxEquityDrawdownLogReturn(self) -> Union[float, None]:
        return self._max_equity_drawdown_pnl_.LogReturn if self._max_equity_drawdown_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceDrawdownPercentage(self) -> Union[float, None]:
        return min(0.0, self.Percentage or 0.0)

    @property
    @overridefield
    def MaxEquityDrawdownPercentage(self) -> Union[float, None]:
        return self._max_equity_drawdown_pnl_.Percentage if self._max_equity_drawdown_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceDrawdownLogPercentage(self) -> Union[float, None]:
        return min(0.0, self.LogPercentage or 0.0)

    @property
    @overridefield
    def MaxEquityDrawdownLogPercentage(self) -> Union[float, None]:
        return self._max_equity_drawdown_pnl_.LogPercentage if self._max_equity_drawdown_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceRunupPnL(self) -> Union[float, None]:
        return max(0.0, self.NetPnL.PnL) if self.NetPnL and self.NetPnL.PnL is not None else 0.0

    @property
    @overridefield
    def MaxBalanceRunupPoints(self) -> Union[float, None]:
        return max(0.0, self.Points or 0.0)

    @property
    @overridefield
    def MaxEquityRunupPoints(self) -> Union[float, None]:
        if self.MaxEquityRunupPrice and self.MaxEquityRunupPrice.Price and self.EntryPrice and self.EntryPrice.Price and self.Security and self.Security.Contract and self.Security.Contract.PointSize:
            diff = self.MaxEquityRunupPrice.Price - self.EntryPrice.Price
            diff = diff if self.IsLong else -diff
            return diff / self.Security.Contract.PointSize
        return 0.0

    @property
    @overridefield
    def MaxBalanceRunupPips(self) -> Union[float, None]:
        return max(0.0, self.Pips or 0.0)

    @property
    @overridefield
    def MaxEquityRunupPips(self) -> Union[float, None]:
        if self.MaxEquityRunupPrice and self.MaxEquityRunupPrice.Price and self.EntryPrice and self.EntryPrice.Price and self.Security and self.Security.Contract and self.Security.Contract.PipSize:
            diff = self.MaxEquityRunupPrice.Price - self.EntryPrice.Price
            diff = diff if self.IsLong else -diff
            return diff / self.Security.Contract.PipSize
        return 0.0

    @property
    @overridefield
    def MaxBalanceRunupReturn(self) -> Union[float, None]:
        return max(0.0, self.Return or 0.0)

    @property
    @overridefield
    def MaxEquityRunupReturn(self) -> Union[float, None]:
        return self._max_equity_runup_pnl_.Return if self._max_equity_runup_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceRunupLogReturn(self) -> Union[float, None]:
        return max(0.0, self.LogReturn or 0.0)

    @property
    @overridefield
    def MaxEquityRunupLogReturn(self) -> Union[float, None]:
        return self._max_equity_runup_pnl_.LogReturn if self._max_equity_runup_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceRunupPercentage(self) -> Union[float, None]:
        return max(0.0, self.Percentage or 0.0)

    @property
    @overridefield
    def MaxEquityRunupPercentage(self) -> Union[float, None]:
        return self._max_equity_runup_pnl_.Percentage if self._max_equity_runup_pnl_ else 0.0

    @property
    @overridefield
    def MaxBalanceRunupLogPercentage(self) -> Union[float, None]:
        return max(0.0, self.LogPercentage or 0.0)

    @property
    @overridefield
    def MaxEquityRunupLogPercentage(self) -> Union[float, None]:
        return self._max_equity_runup_pnl_.LogPercentage if self._max_equity_runup_pnl_ else 0.0

    @property
    @overridefield
    def RiskAdjustedReturn(self) -> Union[float, None]:
        ret, dd = self.Return, self.MaxEquityDrawdownReturn
        return ret / abs(dd) if ret is not None and dd and dd != 0 else 0.0

    @property
    @overridefield
    def RiskAdjustedLogReturn(self) -> Union[float, None]:
        ret, dd = self.LogReturn, self.MaxEquityDrawdownLogReturn
        return ret / abs(dd) if ret is not None and dd and dd != 0 else 0.0

    @property
    @overridefield
    def RiskAdjustedPercentage(self) -> Union[float, None]:
        ret, dd = self.Percentage, self.MaxEquityDrawdownPercentage
        return ret / abs(dd) if ret is not None and dd and dd != 0 else 0.0

    @property
    @overridefield
    def RiskAdjustedLogPercentage(self) -> Union[float, None]:
        ret, dd = self.LogPercentage, self.MaxEquityDrawdownLogPercentage
        return ret / abs(dd) if ret is not None and dd and dd != 0 else 0.0

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

    def _assign_price_(self, backing: Union[PriceAPI, None], val: Union[float, PriceAPI, None]) -> Union[PriceAPI, None]:
        if isinstance(val, PriceAPI): return val
        if val is None: return backing
        if backing:
            backing.Price = val
            return backing
        ref = self._entry_price_.Price if self._entry_price_ else val
        return PriceAPI(Price=val, Reference=ref, Contract=self._security_.Contract if self._security_ else None)

    def _assign_pnl_(self, backing: Union[PnLAPI, None], val: Union[float, PnLAPI, None]) -> Union[PnLAPI, None]:
        if isinstance(val, PnLAPI): return val
        if val is None: return backing
        if backing:
            backing.PnL = val
            return backing
        return PnLAPI(PnL=val, Reference=self._entry_balance_)