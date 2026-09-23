from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Market.Market import MarketAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Market.Timestamp import TimestampAPI
from Library.Market.Price import PriceAPI
from Library.Universe.Security import SecurityAPI
from Library.Utility.Datetime import datetime_to_epoch
from Library.Utility.Typing import MISSING

@dataclass
class TickAPI(DatapointAPI):

    _MS_BITS_: ClassVar[int] = 42

    Schema: ClassVar[str] = MarketAPI.Schema
    Table: ClassVar[str] = "Tick"

    UID: Union[int, None] = field(default=None, kw_only=True)
    Security: InitVar[Union[int, str, SecurityAPI, None]] = field(default=MISSING)
    Timestamp: InitVar[Union[datetime, TimestampAPI, None]] = field(default=MISSING)
    Ask: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    Mid: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    Bid: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    Volume: Union[float, None] = None
    AskBaseConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    BidBaseConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    AskQuoteConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)
    BidQuoteConversion: InitVar[Union[float, PriceAPI, None]] = field(default=MISSING)

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
            self.ID.UID: PrimaryKey(pl.Int64),
            self.ID.Security: ForeignKey(pl.Int64, reference=SecurityAPI.reference()),
            self.ID.Timestamp: pl.Datetime(),
            self.ID.Ask: pl.Float64(),
            self.ID.Mid: pl.Float64(),
            self.ID.Bid: pl.Float64(),
            self.ID.Volume: pl.Float64(),
            self.ID.AskBaseConversion: pl.Float64(),
            self.ID.BidBaseConversion: pl.Float64(),
            self.ID.AskQuoteConversion: pl.Float64(),
            self.ID.BidQuoteConversion: pl.Float64(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool,
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
        self._security_ = self._relate_(security, SecurityAPI, db=db, autoload=autoload)
        self._timestamp_ = TimestampAPI(DateTime=timestamp) if isinstance(timestamp, datetime) else TimestampAPI.assign(None, timestamp)
        contract = self._security_.Contract if self._security_ is not None else None
        ask = PriceAPI(Price=ask, Reference=None, Contract=contract) if isinstance(ask, float) else PriceAPI.assign(None, ask, None, contract)
        mid = PriceAPI(Price=mid, Reference=None, Contract=contract) if isinstance(mid, float) else PriceAPI.assign(None, mid, None, contract)
        bid = PriceAPI(Price=bid, Reference=None, Contract=contract) if isinstance(bid, float) else PriceAPI.assign(None, bid, None, contract)
        if ask is not None and bid is not None:
            if ask.Reference is None: ask.Reference = bid.Price
            if bid.Reference is None: bid.Reference = ask.Price
            if mid is None: mid = PriceAPI(Price=(ask.Price + bid.Price) / 2, Reference=None, Contract=contract)
        self._ask_, self._mid_, self._bid_ = ask, mid, bid
        self._ask_base_conversion_ = PriceAPI(Price=ask_base_conversion, Reference=None, Contract=contract) if isinstance(ask_base_conversion, float) else PriceAPI.assign(None, ask_base_conversion, None, contract)
        self._bid_base_conversion_ = PriceAPI(Price=bid_base_conversion, Reference=None, Contract=contract) if isinstance(bid_base_conversion, float) else PriceAPI.assign(None, bid_base_conversion, None, contract)
        self._ask_quote_conversion_ = PriceAPI(Price=ask_quote_conversion, Reference=None, Contract=contract) if isinstance(ask_quote_conversion, float) else PriceAPI.assign(None, ask_quote_conversion, None, contract)
        self._bid_quote_conversion_ = PriceAPI(Price=bid_quote_conversion, Reference=None, Contract=contract) if isinstance(bid_quote_conversion, float) else PriceAPI.assign(None, bid_quote_conversion, None, contract)
        self._encode_uid_()
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

    @classmethod
    def encode(cls, value: Union[int, pl.DataFrame], timestamp: Union[datetime, None] = None) -> Union[int, pl.DataFrame]:
        return cls._encode_frame_(value) if isinstance(value, pl.DataFrame) else cls._encode_value_(value, timestamp)

    @classmethod
    def _encode_value_(cls, security: int, timestamp: datetime) -> int:
        return (security << cls._MS_BITS_) | datetime_to_epoch(timestamp)

    @classmethod
    def _encode_frame_(cls, frame: pl.DataFrame) -> pl.DataFrame:
        if frame.is_empty() or str(cls.ID.UID) in frame.columns: return frame
        return frame.with_columns((pl.col(str(cls.ID.Security)).cast(pl.Int64) * (1 << cls._MS_BITS_) + pl.col(str(cls.ID.Timestamp)).dt.epoch("ms")).alias(str(cls.ID.UID)))

    def _encode_uid_(self) -> None:
        if self._security_ is not None and self._security_.UID is not None and self._timestamp_ is not None and self._timestamp_.DateTime is not None:
            self.UID = self._encode_value_(self._security_.UID, self._timestamp_.DateTime)

    @classmethod
    def _ingest_(cls, db, security, timestamp, ask, bid, ask_base, bid_base, ask_quote, bid_quote, volume) -> "TickAPI":
        self = cls.__new__(cls)
        s = object.__setattr__
        s(self, "_db_", db)
        s(self, "_migrate_", False)
        s(self, "_autoload_", False)
        s(self, "_autooverload_", False)
        s(self, "_security_", security)
        s(self, "_timestamp_", timestamp)
        s(self, "_ask_", ask)
        s(self, "_bid_", bid)
        s(self, "_mid_", (ask + bid) / 2 if ask is not None and bid is not None else None)
        s(self, "_ask_base_conversion_", ask_base)
        s(self, "_bid_base_conversion_", bid_base)
        s(self, "_ask_quote_conversion_", ask_quote)
        s(self, "_bid_quote_conversion_", bid_quote)
        s(self, "Volume", volume)
        s(self, "UpdatedAt", None)
        s(self, "UpdatedBy", None)
        s(self, "UID", (security.UID << cls._MS_BITS_) | datetime_to_epoch(timestamp) if security is not None and security.UID is not None and timestamp is not None else None)
        return self

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, str, SecurityAPI, None]) -> None:
        if val is not None: self._security_ = self._relate_(val, SecurityAPI, db=self._db_, autoload=self._autoload_)
        contract = self._security_.Contract if self._security_ is not None else None
        if self._ask_: self._ask_.Contract = contract
        if self._mid_: self._mid_.Contract = contract
        if self._bid_: self._bid_.Contract = contract
        if self._ask_base_conversion_: self._ask_base_conversion_.Contract = contract
        if self._bid_base_conversion_: self._bid_base_conversion_.Contract = contract
        if self._ask_quote_conversion_: self._ask_quote_conversion_.Contract = contract
        if self._bid_quote_conversion_: self._bid_quote_conversion_.Contract = contract
        self._encode_uid_()

    @property
    @overridefield
    def Timestamp(self) -> Union[TimestampAPI, None]:
        return self._timestamp_
    @Timestamp.setter
    def Timestamp(self, val: Union[datetime, TimestampAPI, None]) -> None:
        if self._timestamp_ is not None and isinstance(val, datetime): self._timestamp_.DateTime = val
        else: self._timestamp_ = TimestampAPI.assign(self._timestamp_, val)
        self._encode_uid_()

    @property
    @overridefield
    def Ask(self) -> Union[PriceAPI, None]:
        return self._ask_
    @Ask.setter
    def Ask(self, val: Union[float, PriceAPI, None]) -> None:
        if self._ask_ is not None and isinstance(val, float): self._ask_.Price = val
        else: self._ask_ = PriceAPI.assign(self._ask_, val, self._bid_.Price if self._bid_ else None, self._security_.Contract if self._security_ is not None else None)

    @property
    def InvertedAsk(self) -> Union[float, None]:
        return self._ask_.InvertedPrice if self._ask_ is not None else None

    @property
    @overridefield
    def Bid(self) -> Union[PriceAPI, None]:
        return self._bid_
    @Bid.setter
    def Bid(self, val: Union[float, PriceAPI, None]) -> None:
        if self._bid_ is not None and isinstance(val, float): self._bid_.Price = val
        else: self._bid_ = PriceAPI.assign(self._bid_, val, self._ask_.Price if self._ask_ else None, self._security_.Contract if self._security_ is not None else None)

    @property
    def InvertedBid(self) -> Union[float, None]:
        return self._bid_.InvertedPrice if self._bid_ is not None else None

    @property
    @overridefield
    def AskBaseConversion(self) -> Union[PriceAPI, None]:
        return self._ask_base_conversion_
    @AskBaseConversion.setter
    def AskBaseConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if self._ask_base_conversion_ is not None and isinstance(val, float): self._ask_base_conversion_.Price = val
        else: self._ask_base_conversion_ = PriceAPI.assign(self._ask_base_conversion_, val, None, self._security_.Contract if self._security_ is not None else None)

    @property
    @overridefield
    def BidBaseConversion(self) -> Union[PriceAPI, None]:
        return self._bid_base_conversion_
    @BidBaseConversion.setter
    def BidBaseConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if self._bid_base_conversion_ is not None and isinstance(val, float): self._bid_base_conversion_.Price = val
        else: self._bid_base_conversion_ = PriceAPI.assign(self._bid_base_conversion_, val, None, self._security_.Contract if self._security_ is not None else None)

    @property
    @overridefield
    def AskQuoteConversion(self) -> Union[PriceAPI, None]:
        return self._ask_quote_conversion_
    @AskQuoteConversion.setter
    def AskQuoteConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if self._ask_quote_conversion_ is not None and isinstance(val, float): self._ask_quote_conversion_.Price = val
        else: self._ask_quote_conversion_ = PriceAPI.assign(self._ask_quote_conversion_, val, None, self._security_.Contract if self._security_ is not None else None)

    @property
    @overridefield
    def BidQuoteConversion(self) -> Union[PriceAPI, None]:
        return self._bid_quote_conversion_
    @BidQuoteConversion.setter
    def BidQuoteConversion(self, val: Union[float, PriceAPI, None]) -> None:
        if self._bid_quote_conversion_ is not None and isinstance(val, float): self._bid_quote_conversion_.Price = val
        else: self._bid_quote_conversion_ = PriceAPI.assign(self._bid_quote_conversion_, val, None, self._security_.Contract if self._security_ is not None else None)

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
        if self._mid_ is not None and isinstance(val, float): self._mid_.Price = val
        else: self._mid_ = PriceAPI.assign(self._mid_, val, None, self._security_.Contract if self._security_ is not None else None)

    @property
    def InvertedMid(self) -> Union[float, None]:
        return self._mid_.InvertedPrice if self._mid_ is not None else None