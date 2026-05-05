from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Enumeration import Enumeration
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

    UID: Union[int, None] = None
    Type: Union[ContractType, str, None] = None

    Ticker: InitVar[Union[str, TickerAPI, None]] = field(default=MISSING)
    Provider: InitVar[Union[str, ProviderAPI, None]] = field(default=MISSING)

    Digits: Union[int, None] = None
    PointSize: Union[float, None] = None
    PipSize: Union[float, None] = None
    LotSize: Union[int, None] = None
    VolumeMin: Union[float, None] = None
    VolumeMax: Union[float, None] = None
    VolumeStep: Union[float, None] = None
    Commission: Union[float, None] = None
    CommissionMode: Union[CommissionMode, str, None] = None
    SwapLong: Union[float, None] = None
    SwapShort: Union[float, None] = None
    SwapMode: Union[SwapMode, str, None] = None
    SwapExtraDay: Union[Weekday, str, None] = None
    SwapSummerTime: int = 22
    SwapWinterTime: int = 21
    SwapPeriod: int = 24
    Expiry: Union[datetime, None] = None

    _ticker_: Union[TickerAPI, None] = field(default=None, init=False, repr=False)
    _provider_: Union[ProviderAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Ticker: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{TickerAPI.Table}"("{TickerAPI.ID.UID}") ON DELETE CASCADE', primary=True),
            self.ID.Provider: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{ProviderAPI.Table}"("{ProviderAPI.ID.UID}") ON DELETE CASCADE', primary=True),
            self.ID.Type: pl.String(),
            self.ID.Digits: pl.Int32(),
            self.ID.PointSize: pl.Float64(),
            self.ID.PipSize: pl.Float64(),
            self.ID.LotSize: pl.Int32(),
            self.ID.VolumeMin: pl.Float64(),
            self.ID.VolumeMax: pl.Float64(),
            self.ID.VolumeStep: pl.Float64(),
            self.ID.Commission: pl.Float64(),
            self.ID.CommissionMode: pl.String(),
            self.ID.SwapLong: pl.Float64(),
            self.ID.SwapShort: pl.Float64(),
            self.ID.SwapMode: pl.String(),
            self.ID.SwapExtraDay: pl.String(),
            self.ID.SwapSummerTime: pl.Int32(),
            self.ID.SwapWinterTime: pl.Int32(),
            self.ID.SwapPeriod: pl.Int32(),
            self.ID.Expiry: pl.Datetime(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      ticker: Union[str, TickerAPI, None],
                      provider: Union[str, ProviderAPI, None]) -> None:
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
        self.Type = ContractType.parse(self.Type)
        self.CommissionMode = CommissionMode.parse(self.CommissionMode)
        self.SwapMode = SwapMode.parse(self.SwapMode)
        self.SwapExtraDay = Weekday.parse(self.SwapExtraDay)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if not row and self.UID is None and self._ticker_ and self._provider_ and self.Type is not None:
            tval = self.Type.name if isinstance(self.Type, ContractType) else self.Type
            row = self._fetch_(
                condition='"Ticker" = :ticker: AND "Provider" = :provider: AND "Type" = :type:',
                parameters={"ticker": self._ticker_.UID, "provider": self._provider_.UID, "type": tval},
                overload=overload
            )
        if row:
            self.Type = ContractType.parse(self.Type)
            self.CommissionMode = CommissionMode.parse(self.CommissionMode)
            self.SwapMode = SwapMode.parse(self.SwapMode)
            self.SwapExtraDay = Weekday.parse(self.SwapExtraDay)
        return row

    def save(self, by: str = "Autosave") -> None:
        if self._ticker_: self._ticker_.save(by=by)
        if self._provider_: self._provider_.save(by=by)
        super().save(by=by)
        if self.UID is None: self.load()

    @property
    @overridefield
    def Ticker(self) -> Union[TickerAPI, None]:
        return self._ticker_
    @Ticker.setter
    def Ticker(self, val: Union[str, TickerAPI, None]) -> None:
        if isinstance(val, TickerAPI): self._ticker_ = val
        elif val is not None: self._ticker_ = TickerAPI(UID=TickerAPI.normalize(val), db=self._db_, autoload=True)

    @property
    @overridefield
    def Provider(self) -> Union[ProviderAPI, None]:
        return self._provider_
    @Provider.setter
    def Provider(self, val: Union[str, ProviderAPI, None]) -> None:
        if isinstance(val, ProviderAPI): self._provider_ = val
        elif val is not None: self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(val), db=self._db_, autoload=True)