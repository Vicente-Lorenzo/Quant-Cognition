from __future__ import annotations

from datetime import datetime
from typing import ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Enumeration import Enumeration, as_enum
from Library.Database import IdentityKey, PrimaryKey, ForeignKey
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI
from Library.Utility.DateTime import Weekday
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database import DatabaseAPI

class SpreadType(Enumeration):
    Points = 0
    Percentage = 1
    Random = 2
    Approximate = 3
    Accurate = 4

class CommissionType(Enumeration):
    Points = 0
    Percentage = 1
    Amount = 2
    Accurate = 3

class CommissionMode(Enumeration):
    BaseAssetPerMillionVolume = 0
    BaseAssetPerOneLot = 1
    PercentageOfVolume = 2
    QuoteAssetPerOneLot = 3

class SwapType(Enumeration):
    Points = 0
    Percentage = 1
    Amount = 2
    Accurate = 3

class SwapMode(Enumeration):
    Pips = 0
    Percentage = 1

@dataclass
class ContractAPI(UniverseAPI):

    Table: ClassVar[str] = "Contract"

    UID: int | None = None
    Type: ContractType | str | None = None

    Ticker: InitVar[str | TickerAPI | None] = field(default=MISSING)
    Provider: InitVar[str | ProviderAPI | None] = field(default=MISSING)

    Digits: int | None = None
    PointSize: float | None = None
    PipSize: float | None = None
    LotSize: int | None = None
    VolumeMin: float | None = None
    VolumeMax: float | None = None
    VolumeStep: float | None = None
    Commission: float | None = None
    CommissionMode: CommissionMode | str | None = None
    SwapLong: float | None = None
    SwapShort: float | None = None
    SwapMode: SwapMode | str | None = None
    SwapExtraDay: Weekday | str | None = None
    SwapSummerTime: int = 22
    SwapWinterTime: int = 21
    SwapPeriod: int = 24
    Expiry: datetime | None = None

    _ticker_: TickerAPI | None = field(default=None, init=False, repr=False)
    _provider_: ProviderAPI | None = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Ticker: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{TickerAPI.Table}"("{TickerAPI.ID.UID}")', primary=True),
            self.ID.Provider: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{ProviderAPI.Table}"("{ProviderAPI.ID.UID}")', primary=True),
            self.ID.Type: PrimaryKey(pl.Enum([i.name for i in ContractType])),
            self.ID.Digits: pl.Int32(),
            self.ID.PointSize: pl.Float64(),
            self.ID.PipSize: pl.Float64(),
            self.ID.LotSize: pl.Int32(),
            self.ID.VolumeMin: pl.Float64(),
            self.ID.VolumeMax: pl.Float64(),
            self.ID.VolumeStep: pl.Float64(),
            self.ID.Commission: pl.Float64(),
            self.ID.CommissionMode: pl.Enum([c.name for c in CommissionMode]),
            self.ID.SwapLong: pl.Float64(),
            self.ID.SwapShort: pl.Float64(),
            self.ID.SwapMode: pl.Enum([s.name for s in SwapMode]),
            self.ID.SwapExtraDay: pl.Enum([d.name for d in Weekday]),
            self.ID.SwapSummerTime: pl.Int32(),
            self.ID.SwapWinterTime: pl.Int32(),
            self.ID.SwapPeriod: pl.Int32(),
            self.ID.Expiry: pl.Datetime(),
            **super().Structure
        }

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      ticker: str | TickerAPI | None,
                      provider: str | ProviderAPI | None) -> None:
        ticker = coerce(ticker)
        provider = coerce(provider)
        if isinstance(ticker, TickerAPI): self._ticker_ = ticker
        elif ticker is not MISSING and ticker is not None:
            self._ticker_ = TickerAPI(UID=TickerAPI.normalize(ticker), db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if isinstance(provider, ProviderAPI): self._provider_ = provider
        elif provider is not MISSING and provider is not None:
            self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(provider), db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if self.Type is None and self._ticker_ is not None and self._ticker_.UID:
            self.Type = TickerAPI.detect(self._ticker_.UID)
        self.Type = as_enum(ContractType, self.Type)
        self.CommissionMode = as_enum(CommissionMode, self.CommissionMode)
        self.SwapMode = as_enum(SwapMode, self.SwapMode)
        self.SwapExtraDay = as_enum(Weekday, self.SwapExtraDay)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> dict | None:
        row = super()._pull_(overload=overload)
        if not row and self.UID is None and self._ticker_ and self._provider_ and self.Type is not None:
            tval = self.Type.name if isinstance(self.Type, ContractType) else self.Type
            row = self._fetch_(
                condition='"Ticker" = :ticker: AND "Provider" = :provider: AND "Type" = :type:',
                parameters={"ticker": self._ticker_.UID, "provider": self._provider_.UID, "type": tval},
                overload=overload
            )
        if row:
            self.Type = as_enum(ContractType, self.Type)
            self.CommissionMode = as_enum(CommissionMode, self.CommissionMode)
            self.SwapMode = as_enum(SwapMode, self.SwapMode)
            self.SwapExtraDay = as_enum(Weekday, self.SwapExtraDay)
        return row

    def save(self, by: str = "Autosave") -> None:
        if self._ticker_: self._ticker_.save(by=by)
        if self._provider_: self._provider_.save(by=by)
        super().save(by=by)
        if self.UID is None: self.load()

    @property
    @overridefield
    def Ticker(self) -> TickerAPI | None:
        return self._ticker_
    @Ticker.setter
    def Ticker(self, val: str | TickerAPI | None) -> None:
        if isinstance(val, TickerAPI): self._ticker_ = val
        elif val is not None: self._ticker_ = TickerAPI(UID=TickerAPI.normalize(val), db=self._db_, autoload=True)

    @property
    @overridefield
    def Provider(self) -> ProviderAPI | None:
        return self._provider_
    @Provider.setter
    def Provider(self, val: str | ProviderAPI | None) -> None:
        if isinstance(val, ProviderAPI): self._provider_ = val
        elif val is not None: self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(val), db=self._db_, autoload=True)