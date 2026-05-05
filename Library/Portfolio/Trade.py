from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import IdentityKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.PnL import PnLAPI
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI, Direction
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Universe.Security import SecurityAPI
    from Library.Portfolio.Order import OrderAPI

@dataclass
class TradeAPI(PositionAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Trade"

    UID: Union[int, None] = None

    Position: InitVar[Union[int, PositionAPI, None]] = field(default=MISSING)
    ExitTimestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    ExitBalance: InitVar[Union[float, None]] = field(default=MISSING)

    _position_: Union[PositionAPI, None] = field(default=None, init=False, repr=False)
    _exit_timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _exit_balance_: Union[float, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        from Library.Universe.Security import SecurityAPI
        s = super().Structure
        cols = {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{SecurityAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")'),
            self.ID.Position: ForeignKey(pl.Int64, reference=f'"{PortfolioAPI.Schema}"."{PositionAPI.Table}"("{PositionAPI.ID.UID}")'),
            self.ID.Type: pl.String(),
            self.ID.Direction: pl.String(),
            self.ID.Volume: pl.Float64(),
            self.ID.Quantity: pl.Float64(),
            self.ID.EntryTimestamp: pl.Datetime(),
            self.ID.ExitTimestamp: pl.Datetime(),
            self.ID.EntryPrice: pl.Float64(),
            self.ID.ExitPrice: pl.Float64(),
            self.ID.GrossPnL: pl.Float64(),
            self.ID.CommissionPnL: pl.Float64(),
            self.ID.SwapPnL: pl.Float64(),
            self.ID.NetPnL: pl.Float64(),
            self.ID.EntryBalance: pl.Float64(),
            self.ID.MidBalance: pl.Float64(),
            self.ID.ExitBalance: pl.Float64(),
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
                      order: Union[int, OrderAPI, None],
                      position: Union[int, PositionAPI, None],
                      exit_timestamp: Union[datetime, TimestampAPI, None],
                      exit_balance: Union[float, None]) -> None:
        position = coerce(position)
        exit_timestamp = coerce(exit_timestamp)
        exit_balance = coerce(exit_balance)
        if isinstance(position, PositionAPI): self._position_ = position
        elif position is not MISSING and position is not None:
            self._position_ = PositionAPI(UID=position, db=db, autoload=True)
        self._exit_balance_ = exit_balance if exit_balance is not MISSING else None
        if isinstance(exit_timestamp, TimestampAPI): self._exit_timestamp_ = exit_timestamp
        elif exit_timestamp is not MISSING and exit_timestamp is not None:
            self._exit_timestamp_ = TimestampAPI(DateTime=exit_timestamp)
        super().__post_init__(db=db, 
                              migrate=migrate, 
                              autosave=autosave, 
                              autoload=autoload, 
                              autooverload=autooverload,
                              type=type,
                              direction=direction,
                              security=security,
                              entry_timestamp=entry_timestamp, 
                              entry_price=entry_price,
                              stop_loss_price=stop_loss_price, 
                              take_profit_price=take_profit_price,
                              max_run_up_price=max_run_up_price, 
                              max_draw_down_price=max_draw_down_price,
                              exit_price=exit_price,
                              stop_loss_pnl=stop_loss_pnl, 
                              take_profit_pnl=take_profit_pnl,
                              max_run_up_pnl=max_run_up_pnl, 
                              max_draw_down_pnl=max_draw_down_pnl,
                              gross_pnl=gross_pnl, 
                              commission_pnl=commission_pnl,
                              swap_pnl=swap_pnl, 
                              net_pnl=net_pnl,
                              entry_balance=entry_balance, 
                              order=order)

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
    def ExitTimestamp(self) -> Union[TimestampAPI, None]:
        return self._exit_timestamp_
    @ExitTimestamp.setter
    def ExitTimestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        if isinstance(val, TimestampAPI): self._exit_timestamp_ = val
        elif val is not None:
            if self._exit_timestamp_: self._exit_timestamp_.DateTime = val
            else: self._exit_timestamp_ = TimestampAPI(DateTime=val)

    @property
    @overridefield
    def ExitBalance(self) -> Union[float, None]:
        return self._exit_balance_
    @ExitBalance.setter
    def ExitBalance(self, val: Union[float, None]) -> None:
        self._exit_balance_ = val

    @property
    def ExitReturn(self) -> Union[PnLAPI, None]:
        if self._exit_balance_ is None or self._entry_balance_ is None: return None
        return PnLAPI(PnL=self._exit_balance_ - self._entry_balance_, Reference=self._entry_balance_)

    @property
    def Duration(self) -> Union[float, None]:
        if self._entry_timestamp_ is None or self._exit_timestamp_ is None: return None
        return (self._exit_timestamp_.DateTime - self._entry_timestamp_.DateTime).total_seconds()

    @property
    def DurationDays(self) -> Union[float, None]:
        seconds = self.Duration
        return seconds / 86400.0 if seconds is not None else None

    @property
    def HoldingPeriod(self) -> Union[float, None]:
        return self.Duration

    @property
    def IsClosed(self) -> bool:
        return self._exit_timestamp_ is not None