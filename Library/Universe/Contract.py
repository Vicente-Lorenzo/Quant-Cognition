from __future__ import annotations

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import overridefield, coerce
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database import IdentityKey, PrimaryKey, ForeignKey
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI
from Library.Utility.Datetime import Weekday
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database import DatabaseAPI

class SpreadType(EnumerationAPI):

    Points = 0
    Percentage = 1
    Random = 2
    Approximate = 3
    Accurate = 4
    Auto = 5

class CommissionType(EnumerationAPI):

    Points = 0
    Percentage = 1
    Amount = 2
    Accurate = 3
    Auto = 4

class CommissionMode(EnumerationAPI):

    BaseAssetPerMillionVolume = 0
    BaseAssetPerOneLot = 1
    PercentageOfVolume = 2
    QuoteAssetPerOneLot = 3

class SwapType(EnumerationAPI):

    Points = 0
    Percentage = 1
    Amount = 2
    Accurate = 3
    Auto = 4

class SwapMode(EnumerationAPI):

    Pips = 0
    Percentage = 1

class VariantType(EnumerationAPI):

    Call = 0
    Put = 1
    Deliverable = 2
    NDF = 3

class PayoffType(EnumerationAPI):

    Trivial = 0
    Vanilla = 1
    Asian = 2
    Barrier = 3
    KnockOut = 4
    Digital = 5

class ExerciseType(EnumerationAPI):

    European = 0
    American = 1
    Bermudan = 2

@dataclass
class ContractAPI(UniverseAPI):

    Table: ClassVar[str] = "Contract"
    Enums: ClassVar[dict] = {"Type": ContractType, "CommissionMode": CommissionMode, "SwapMode": SwapMode, "SwapExtraDay": Weekday, "Variant": VariantType, "Payoff": PayoffType, "Exercise": ExerciseType}

    UID: Union[int, None] = None
    Ticker: InitVar[Union[str, TickerAPI, None]] = field(default=MISSING)
    Provider: InitVar[Union[str, ProviderAPI, None]] = field(default=MISSING)
    Type: Union[ContractType, str, None] = None
    Digits: Union[int, None] = None
    PointSize: Union[float, None] = None
    PipSize: Union[float, None] = None
    LotSize: Union[int, None] = None
    VolumeMin: Union[float, None] = None
    VolumeMax: Union[float, None] = None
    VolumeStep: Union[float, None] = None
    CommissionMode: Union[CommissionMode, str, None] = None
    Commission: Union[float, None] = None
    SwapMode: Union[SwapMode, str, None] = None
    SwapLong: Union[float, None] = None
    SwapShort: Union[float, None] = None
    SwapPeriod: int = 24
    SwapExtraDay: Union[Weekday, str, None] = None
    SwapSummerTime: int = 22
    SwapWinterTime: int = 21
    Variant: Union[VariantType, str, None] = None
    Payoff: Union[PayoffType, str, None] = None
    Strike: Union[float, None] = None
    Maturity: Union[datetime, None] = None
    Exercise: Union[ExerciseType, str, None] = None

    _ticker_: Union[TickerAPI, None] = field(default=None, init=False, repr=False)
    _provider_: Union[ProviderAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Ticker: ForeignKey(pl.String, reference=TickerAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Provider: ForeignKey(pl.String, reference=ProviderAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Type: PrimaryKey(pl.String),
            self.ID.Digits: pl.Int32(),
            self.ID.PointSize: pl.Float64(),
            self.ID.PipSize: pl.Float64(),
            self.ID.LotSize: pl.Int32(),
            self.ID.VolumeMin: pl.Float64(),
            self.ID.VolumeMax: pl.Float64(),
            self.ID.VolumeStep: pl.Float64(),
            self.ID.CommissionMode: pl.String(),
            self.ID.Commission: pl.Float64(),
            self.ID.SwapMode: pl.String(),
            self.ID.SwapLong: pl.Float64(),
            self.ID.SwapShort: pl.Float64(),
            self.ID.SwapPeriod: pl.Int32(),
            self.ID.SwapExtraDay: pl.String(),
            self.ID.SwapSummerTime: pl.Int32(),
            self.ID.SwapWinterTime: pl.Int32(),
            self.ID.Variant: pl.String(),
            self.ID.Payoff: pl.String(),
            self.ID.Strike: pl.Float64(),
            self.ID.Maturity: pl.Datetime(),
            self.ID.Exercise: pl.String(),
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
        self._ticker_ = self._relate_(ticker, TickerAPI, normalize=TickerAPI.normalize, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        self._provider_ = self._relate_(provider, ProviderAPI, normalize=ProviderAPI.normalize, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if self.Type is None and self._ticker_ is not None and self._ticker_.UID:
            self.Type = TickerAPI.detect(self._ticker_.UID)
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
            for name, enumeration in self.Enums.items(): setattr(self, name, enumeration.parse(getattr(self, name)))
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
        if val is not None: self._ticker_ = self._relate_(val, TickerAPI, normalize=TickerAPI.normalize, db=self._db_, autoload=True)

    @property
    @overridefield
    def Provider(self) -> Union[ProviderAPI, None]:
        return self._provider_
    @Provider.setter
    def Provider(self, val: Union[str, ProviderAPI, None]) -> None:
        if val is not None: self._provider_ = self._relate_(val, ProviderAPI, normalize=ProviderAPI.normalize, db=self._db_, autoload=True)

    @property
    def IsSpot(self) -> bool:
        return self.Type == ContractType.Spot

    @property
    def IsDerivative(self) -> bool:
        return self.Type in [ContractType.Option, ContractType.Future, ContractType.Swap]

    @property
    def IsLinear(self) -> bool:
        return self.Type in [ContractType.Spot, ContractType.CFD, ContractType.Future, ContractType.Swap]

    @property
    def IsNonLinear(self) -> bool:
        return self.Type == ContractType.Option or self.Payoff not in [PayoffType.Vanilla, PayoffType.Trivial, None]