from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING, Sequence
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Contract import ContractAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Database.Database import DatabaseAPI

class TickMode(Enum):
    Accurate = 0
    Inaccurate = 1

@dataclass
class TickAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Market"
    Table: ClassVar[str] = "Tick"

    Security: InitVar[int | str | SecurityAPI]
    Timestamp: InitVar[datetime | TimestampAPI]
    Ask: InitVar[float | PriceAPI | None] = field(default=MISSING)
    Bid: InitVar[float | PriceAPI | None] = field(default=MISSING)
    AskBaseConversion: InitVar[float | PriceAPI | None] = field(default=MISSING)
    BidBaseConversion: InitVar[float | PriceAPI | None] = field(default=MISSING)
    AskQuoteConversion: InitVar[float | PriceAPI | None] = field(default=MISSING)
    BidQuoteConversion: InitVar[float | PriceAPI | None] = field(default=MISSING)
    Contract: InitVar[ContractAPI | None] = field(default=MISSING)

    _security_: SecurityAPI | None = field(default=None, init=False, repr=False)
    _timestamp_: TimestampAPI | None = field(default=None, init=False, repr=False)
    _ask_: PriceAPI | None = field(default=None, init=False, repr=False)
    _bid_: PriceAPI | None = field(default=None, init=False, repr=False)
    _ask_base_conversion_: PriceAPI | None = field(default=None, init=False, repr=False)
    _bid_base_conversion_: PriceAPI | None = field(default=None, init=False, repr=False)
    _ask_quote_conversion_: PriceAPI | None = field(default=None, init=False, repr=False)
    _bid_quote_conversion_: PriceAPI | None = field(default=None, init=False, repr=False)
    _contract_: ContractAPI | None = field(default=None, init=False, repr=False)

    @classmethod
    def Structure(cls) -> dict:
        return {
            cls.ID.Security: ForeignKey(pl.Int64, reference=f'"{SecurityAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")', primary=True),
            cls.ID.Timestamp: PrimaryKey(pl.Datetime),
            cls.ID.Ask: pl.Float64(),
            cls.ID.Bid: pl.Float64(),
            cls.ID.AskBaseConversion: pl.Float64(),
            cls.ID.BidBaseConversion: pl.Float64(),
            cls.ID.AskQuoteConversion: pl.Float64(),
            cls.ID.BidQuoteConversion: pl.Float64(),
            **DatapointAPI.Structure()
        }

    def __post_init__(self,
                      security: int | str | SecurityAPI,
                      timestamp: datetime | TimestampAPI,
                      ask: float | PriceAPI | None,
                      bid: float | PriceAPI | None,
                      ask_base_conversion: float | PriceAPI | None,
                      bid_base_conversion: float | PriceAPI | None,
                      ask_quote_conversion: float | PriceAPI | None,
                      bid_quote_conversion: float | PriceAPI | None,
                      contract: ContractAPI | None,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        if isinstance(security, SecurityAPI): self._security_ = security
        elif security is not MISSING and security is not None: self._security_ = SecurityAPI(UID=security, db=db, autoload=True)
        if isinstance(timestamp, TimestampAPI): self._timestamp_ = timestamp
        elif timestamp is not MISSING and timestamp is not None: self._timestamp_ = TimestampAPI(DateTime=timestamp)
        if contract is not MISSING: self._contract_ = contract
        ask_price = ask.Price if isinstance(ask, PriceAPI) else ask
        bid_price = bid.Price if isinstance(bid, PriceAPI) else bid
        if ask is not MISSING and ask is not None: self._ask_ = ask if isinstance(ask, PriceAPI) else PriceAPI(Price=ask_price, Reference=bid_price, Contract=self._contract_)
        if bid is not MISSING and bid is not None: self._bid_ = bid if isinstance(bid, PriceAPI) else PriceAPI(Price=bid_price, Reference=ask_price, Contract=self._contract_)
        def _init_conversion_(conv: float | PriceAPI | None) -> PriceAPI | None:
            if isinstance(conv, PriceAPI): return conv
            if conv is not MISSING and conv is not None: return PriceAPI(Price=conv, Reference=None, Contract=self._contract_)
            return None
        self._ask_base_conversion_ = _init_conversion_(ask_base_conversion)
        self._bid_base_conversion_ = _init_conversion_(bid_base_conversion)
        self._ask_quote_conversion_ = _init_conversion_(ask_quote_conversion)
        self._bid_quote_conversion_ = _init_conversion_(bid_quote_conversion)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _fetch_(self, condition: str | None = None, parameters: dict | None = None, overload: bool = False) -> dict | None:
        if condition is None:
            if not self._security_ or not self._timestamp_: return None
            condition = '"Security" = :security: AND "Timestamp" = :timestamp:'
            parameters = {"security": getattr(self._security_, 'UID', self._security_), "timestamp": getattr(self._timestamp_, 'UID', self._timestamp_)}
        return super()._pull_(condition=condition, parameters=parameters, overload=overload)

    def save(self, by: str = "Autosave", key: str | Sequence[str] | None = None) -> None:
        super().save(by=by, key=key or ["Security", "Timestamp"])

    @property
    @overridefield
    def Security(self) -> SecurityAPI | None:
        return self._security_
    @Security.setter
    def Security(self, val: int | str | SecurityAPI | None) -> None:
        if isinstance(val, SecurityAPI): self._security_ = val
        elif val is not None: self._security_ = SecurityAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def Timestamp(self) -> TimestampAPI | None:
        return self._timestamp_
    @Timestamp.setter
    def Timestamp(self, val: datetime | TimestampAPI | None) -> None:
        if isinstance(val, TimestampAPI): self._timestamp_ = val
        elif val is not None:
            if self._timestamp_: self._timestamp_.DateTime = val
            else: self._timestamp_ = TimestampAPI(DateTime=val)

    @property
    @overridefield
    def Ask(self) -> PriceAPI | None:
        return self._ask_
    @Ask.setter
    def Ask(self, val: float | PriceAPI | None) -> None:
        if isinstance(val, PriceAPI): self._ask_ = val
        elif val is not None:
            if self._ask_: self._ask_.Price = val
            else: self._ask_ = PriceAPI(Price=val, Reference=self._bid_.Price if self._bid_ else None, Contract=self._contract_)
    @property
    def InvertedAsk(self) -> float | None:
        if self._ask_ is None or not self._ask_.Price: return None
        return 1.0 / self._ask_.Price

    @property
    @overridefield
    def Bid(self) -> PriceAPI | None:
        return self._bid_
    @Bid.setter
    def Bid(self, val: float | PriceAPI | None) -> None:
        if isinstance(val, PriceAPI): self._bid_ = val
        elif val is not None:
            if self._bid_: self._bid_.Price = val
            else: self._bid_ = PriceAPI(Price=val, Reference=self._ask_.Price if self._ask_ else None, Contract=self._contract_)
    @property
    def InvertedBid(self) -> float | None:
        if self._bid_ is None or not self._bid_.Price: return None
        return 1.0 / self._bid_.Price

    @property
    @overridefield
    def AskBaseConversion(self) -> PriceAPI | None:
        return self._ask_base_conversion_
    @AskBaseConversion.setter
    def AskBaseConversion(self, val: float | PriceAPI | None) -> None:
        if isinstance(val, PriceAPI): self._ask_base_conversion_ = val
        elif val is not None:
            if self._ask_base_conversion_: self._ask_base_conversion_.Price = val
            else: self._ask_base_conversion_ = PriceAPI(Price=val, Reference=None, Contract=self._contract_)

    @property
    @overridefield
    def BidBaseConversion(self) -> PriceAPI | None:
        return self._bid_base_conversion_
    @BidBaseConversion.setter
    def BidBaseConversion(self, val: float | PriceAPI | None) -> None:
        if isinstance(val, PriceAPI): self._bid_base_conversion_ = val
        elif val is not None:
            if self._bid_base_conversion_: self._bid_base_conversion_.Price = val
            else: self._bid_base_conversion_ = PriceAPI(Price=val, Reference=None, Contract=self._contract_)

    @property
    @overridefield
    def AskQuoteConversion(self) -> PriceAPI | None:
        return self._ask_quote_conversion_
    @AskQuoteConversion.setter
    def AskQuoteConversion(self, val: float | PriceAPI | None) -> None:
        if isinstance(val, PriceAPI): self._ask_quote_conversion_ = val
        elif val is not None:
            if self._ask_quote_conversion_: self._ask_quote_conversion_.Price = val
            else: self._ask_quote_conversion_ = PriceAPI(Price=val, Reference=None, Contract=self._contract_)

    @property
    @overridefield
    def BidQuoteConversion(self) -> PriceAPI | None:
        return self._bid_quote_conversion_
    @BidQuoteConversion.setter
    def BidQuoteConversion(self, val: float | PriceAPI | None) -> None:
        if isinstance(val, PriceAPI): self._bid_quote_conversion_ = val
        elif val is not None:
            if self._bid_quote_conversion_: self._bid_quote_conversion_.Price = val
            else: self._bid_quote_conversion_ = PriceAPI(Price=val, Reference=None, Contract=self._contract_)

    @property
    def Spread(self) -> PriceAPI | None:
        if self._ask_ is None or self._bid_ is None or self._ask_.Price is None or self._bid_.Price is None: return None
        return PriceAPI(Price=self._ask_.Price - self._bid_.Price, Reference=self._ask_.Price, Contract=self._contract_)

    @property
    def Mid(self) -> float | None:
        if self._ask_ is None or self._bid_ is None or self._ask_.Price is None or self._bid_.Price is None: return None
        return (self._ask_.Price + self._bid_.Price) / 2

    @property
    def InvertedMid(self) -> float | None:
        mid = self.Mid
        if mid is None or not mid: return None
        return 1.0 / mid

    @property
    @overridefield
    def Contract(self) -> ContractAPI | None:
        return self._contract_
    @Contract.setter
    def Contract(self, val: ContractAPI | None) -> None:
        self._contract_ = val
        if self._ask_: self._ask_.Contract = self._contract_
        if self._bid_: self._bid_.Contract = self._contract_
        if self._ask_base_conversion_: self._ask_base_conversion_.Contract = self._contract_
        if self._bid_base_conversion_: self._bid_base_conversion_.Contract = self._contract_
        if self._ask_quote_conversion_: self._ask_quote_conversion_.Contract = self._contract_
        if self._bid_quote_conversion_: self._bid_quote_conversion_.Contract = self._contract_