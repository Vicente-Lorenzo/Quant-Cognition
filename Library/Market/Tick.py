from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import IdentityKey, PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Market.Market import MarketAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI
from Library.Utility.Typing import MISSING

@dataclass
class TickAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = MarketAPI.Schema
    Table: ClassVar[str] = "Tick"

    UID: Union[int, None] = field(default=None, kw_only=True)
    Security: InitVar[Union[int, str, SecurityAPI, None]] = field(default=MISSING)
    Timestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)

    Ask: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    Mid: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    Bid: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)

    AskBaseConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    BidBaseConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    AskQuoteConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    BidQuoteConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)

    Volume: Union[float, None] = None

    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _timestamp_: Union[TimestampAPI, None] = field(default=None, init=False, repr=False)
    _ask_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _mid_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _bid_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _ask_base_conversion_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _bid_base_conversion_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _ask_quote_conversion_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)
    _bid_quote_conversion_: Union[PriceAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Timestamp: PrimaryKey(pl.Datetime),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{SecurityAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")', primary=True),
            self.ID.Ask: pl.Float64(),
            self.ID.Mid: pl.Float64(),
            self.ID.Bid: pl.Float64(),
            self.ID.AskBaseConversion: pl.Float64(),
            self.ID.BidBaseConversion: pl.Float64(),
            self.ID.AskQuoteConversion: pl.Float64(),
            self.ID.BidQuoteConversion: pl.Float64(),
            self.ID.Volume: pl.Float64(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      security: Union[int, str, SecurityAPI, None],
                      timestamp: Union[datetime, TimestampAPI, None],
                      ask: Union[float, PriceAPI, None],
                      mid: Union[float, PriceAPI, None],
                      bid: Union[float, PriceAPI, None],
                      ask_base_conversion: Union[float, PriceAPI, None],
                      bid_base_conversion: Union[float, PriceAPI, None],
                      ask_quote_conversion: Union[float, PriceAPI, None],
                      bid_quote_conversion: Union[float, PriceAPI, None]) -> None:
        security = coerce(security)
        timestamp = coerce(timestamp)
        ask = coerce(ask)
        mid = coerce(mid)
        bid = coerce(bid)
        ask_base_conversion = coerce(ask_base_conversion)
        bid_base_conversion = coerce(bid_base_conversion)
        ask_quote_conversion = coerce(ask_quote_conversion)
        bid_quote_conversion = coerce(bid_quote_conversion)
        if isinstance(security, SecurityAPI):
            self._security_ = security
        elif security is not MISSING and security is not None:
            self._security_ = SecurityAPI(UID=security, db=db, autoload=autoload)
        if isinstance(timestamp, TimestampAPI):
            self._timestamp_ = timestamp
        elif timestamp is not MISSING and timestamp is not None:
            self._timestamp_ = TimestampAPI(DateTime=timestamp)
        contract = self._security_.Contract if self._security_ is not None else None
        if isinstance(ask, PriceAPI): self._ask_ = ask
        elif ask is not MISSING and ask is not None: self._ask_ = PriceAPI(Price=ask, Reference=None, Contract=contract)
        if isinstance(mid, PriceAPI): self._mid_ = mid
        elif mid is not MISSING and mid is not None: self._mid_ = PriceAPI(Price=mid, Reference=None, Contract=contract)
        if isinstance(bid, PriceAPI): self._bid_ = bid
        elif bid is not MISSING and bid is not None: self._bid_ = PriceAPI(Price=bid, Reference=None, Contract=contract)
        if self._ask_ is not None and self._bid_ is not None:
            if self._ask_.Reference is None: self._ask_.Reference = self._bid_.Price
            if self._bid_.Reference is None: self._bid_.Reference = self._ask_.Price
            if self._mid_ is None:
                self._mid_ = PriceAPI(Price=(self._ask_.Price + self._bid_.Price) / 2, Reference=None, Contract=contract)
        def _init_conv_(val: Union[float, PriceAPI, None]) -> Union[PriceAPI, None]:
            if isinstance(val, PriceAPI): return val
            if val is not MISSING and val is not None: return PriceAPI(Price=val, Reference=None, Contract=contract)
            return None
        self._ask_base_conversion_ = _init_conv_(ask_base_conversion)
        self._bid_base_conversion_ = _init_conv_(bid_base_conversion)
        self._ask_quote_conversion_ = _init_conv_(ask_quote_conversion)
        self._bid_quote_conversion_ = _init_conv_(bid_quote_conversion)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def save(self, by: str = "Autosave") -> None:
        super().save(by=by)
        if self.UID is None: self.load()

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, str, SecurityAPI, None]) -> None:
        if isinstance(val, SecurityAPI): self._security_ = val
        elif val is not None: self._security_ = SecurityAPI(UID=val, db=self._db_, autoload=self._autoload_)
        contract = self._security_.Contract if self._security_ is not None else None
        if self._ask_: self._ask_.Contract = contract
        if self._mid_: self._mid_.Contract = contract
        if self._bid_: self._bid_.Contract = contract
        if self._ask_base_conversion_: self._ask_base_conversion_.Contract = contract
        if self._bid_base_conversion_: self._bid_base_conversion_.Contract = contract
        if self._ask_quote_conversion_: self._ask_quote_conversion_.Contract = contract
        if self._bid_quote_conversion_: self._bid_quote_conversion_.Contract = contract

    @property
    @overridefield
    def Timestamp(self) -> Union[TimestampAPI, None]:
        return self._timestamp_
    @Timestamp.setter
    def Timestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        if isinstance(val, TimestampAPI): self._timestamp_ = val
        elif val is not None:
            if self._timestamp_: self._timestamp_.DateTime = val
            else: self._timestamp_ = TimestampAPI(DateTime=val)

    @property
    @overridefield
    def Ask(self) -> Union[PriceAPI, None]:
        return self._ask_
    @Ask.setter
    def Ask(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._ask_ = val
        elif val is not None:
            if self._ask_: self._ask_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._ask_ = PriceAPI(Price=val, Reference=self._bid_.Price if self._bid_ else None, Contract=contract)
    @property
    def InvertedAsk(self) -> Union[float, None]:
        if self._ask_ is None or not self._ask_.Price: return None
        return 1.0 / self._ask_.Price

    @property
    @overridefield
    def Bid(self) -> Union[PriceAPI, None]:
        return self._bid_
    @Bid.setter
    def Bid(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._bid_ = val
        elif val is not None:
            if self._bid_: self._bid_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._bid_ = PriceAPI(Price=val, Reference=self._ask_.Price if self._ask_ else None, Contract=contract)
    @property
    def InvertedBid(self) -> Union[float, None]:
        if self._bid_ is None or not self._bid_.Price: return None
        return 1.0 / self._bid_.Price

    @property
    @overridefield
    def AskBaseConversion(self) -> Union[PriceAPI, None]:
        return self._ask_base_conversion_
    @AskBaseConversion.setter
    def AskBaseConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._ask_base_conversion_ = val
        elif val is not None:
            if self._ask_base_conversion_: self._ask_base_conversion_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._ask_base_conversion_ = PriceAPI(Price=val, Reference=None, Contract=contract)

    @property
    @overridefield
    def BidBaseConversion(self) -> Union[PriceAPI, None]:
        return self._bid_base_conversion_
    @BidBaseConversion.setter
    def BidBaseConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._bid_base_conversion_ = val
        elif val is not None:
            if self._bid_base_conversion_: self._bid_base_conversion_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._bid_base_conversion_ = PriceAPI(Price=val, Reference=None, Contract=contract)

    @property
    @overridefield
    def AskQuoteConversion(self) -> Union[PriceAPI, None]:
        return self._ask_quote_conversion_
    @AskQuoteConversion.setter
    def AskQuoteConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._ask_quote_conversion_ = val
        elif val is not None:
            if self._ask_quote_conversion_: self._ask_quote_conversion_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._ask_quote_conversion_ = PriceAPI(Price=val, Reference=None, Contract=contract)

    @property
    @overridefield
    def BidQuoteConversion(self) -> Union[PriceAPI, None]:
        return self._bid_quote_conversion_
    @BidQuoteConversion.setter
    def BidQuoteConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._bid_quote_conversion_ = val
        elif val is not None:
            if self._bid_quote_conversion_: self._bid_quote_conversion_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._bid_quote_conversion_ = PriceAPI(Price=val, Reference=None, Contract=contract)

    @property
    def Spread(self) -> Union[PriceAPI, None]:
        if self._ask_ is None or self._bid_ is None or self._ask_.Price is None or self._bid_.Price is None: return None
        contract = self._security_.Contract if self._security_ is not None else None
        return PriceAPI(Price=self._ask_.Price - self._bid_.Price, Reference=self._ask_.Price, Contract=contract)

    @property
    @overridefield
    def Mid(self) -> Union[PriceAPI, None]:
        return self._mid_
    @Mid.setter
    def Mid(self, val: Union[float, PriceAPI, None]) -> None:
        if isinstance(val, PriceAPI): self._mid_ = val
        elif val is not None:
            if self._mid_: self._mid_.Price = val
            else:
                contract = self._security_.Contract if self._security_ is not None else None
                self._mid_ = PriceAPI(Price=val, Reference=None, Contract=contract)

    @property
    def InvertedMid(self) -> Union[float, None]:
        if self._mid_ is None or not self._mid_.Price: return None
        return 1.0 / self._mid_.Price