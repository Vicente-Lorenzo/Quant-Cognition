from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Union, ClassVar, TYPE_CHECKING
from typing_extensions import Self
from dataclasses import dataclass, field

from Library.Database.Dataframe import pl
from Library.Utility.Enumeration import EnumerationAPI
from Library.Database import IdentityKey, PrimaryKey, ForeignKey
from Library.Universe.Universe import UniverseAPI
from Library.Utility.Datetime import Weekday, parse_datetime
from Library.Utility.Typing import MISSING, Missing

if TYPE_CHECKING:
    from Library.Database import DatabaseAPI
    from Library.Universe.Security import SecurityAPI

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
    Units = 3
    Lots = 4
    Accurate = 5
    Auto = 6

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
    Points = 2

class TradingMode(EnumerationAPI):

    Enabled = 0
    DisabledWithoutPendingsExecution = 1
    DisabledWithPendingsExecution = 2
    CloseOnlyMode = 3

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
    Enums: ClassVar[dict] = {"CommissionMode": CommissionMode, "SwapMode": SwapMode, "SwapExtraDay": Weekday, "TradingMode": TradingMode, "Variant": VariantType, "Payoff": PayoffType, "Exercise": ExerciseType}

    UID: Union[int, None] = None
    Security: Union[int, None] = None
    Timestamp: Union[datetime, None] = None
    Digits: Union[int, None] = None
    PointSize: Union[float, None] = None
    PipSize: Union[float, None] = None
    LotSize: Union[int, None] = None
    VolumeMin: Union[float, None] = None
    VolumeMax: Union[float, None] = None
    VolumeStep: Union[float, None] = None
    CommissionMode: Union[CommissionMode, str, None] = None
    Commission: Union[float, None] = None
    MinCommission: Union[float, None] = None
    MinCommissionAsset: Union[str, None] = None
    ConversionFee: Union[float, None] = None
    SwapMode: Union[SwapMode, str, None] = None
    SwapLong: Union[float, None] = None
    SwapShort: Union[float, None] = None
    SwapPeriod: Union[int, None] = None
    SwapTime: Union[int, None] = None
    SwapSkip: Union[int, None] = None
    SwapExtraDay: Union[Weekday, str, None] = None
    SwapWeekends: Union[bool, None] = None
    TradingMode: Union[TradingMode, str, None] = None
    Variant: Union[VariantType, str, None] = None
    Payoff: Union[PayoffType, str, None] = None
    Strike: Union[float, None] = None
    Maturity: Union[datetime, None] = None
    Exercise: Union[ExerciseType, str, None] = None

    _owner_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        from Library.Universe.Security import SecurityAPI
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Security: ForeignKey(pl.Int64, reference=SecurityAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Timestamp: PrimaryKey(pl.Datetime),
            self.ID.Digits: pl.Int32(),
            self.ID.PointSize: pl.Float64(),
            self.ID.PipSize: pl.Float64(),
            self.ID.LotSize: pl.Int32(),
            self.ID.VolumeMin: pl.Float64(),
            self.ID.VolumeMax: pl.Float64(),
            self.ID.VolumeStep: pl.Float64(),
            self.ID.CommissionMode: pl.String(),
            self.ID.Commission: pl.Float64(),
            self.ID.MinCommission: pl.Float64(),
            self.ID.MinCommissionAsset: pl.String(),
            self.ID.ConversionFee: pl.Float64(),
            self.ID.SwapMode: pl.String(),
            self.ID.SwapLong: pl.Float64(),
            self.ID.SwapShort: pl.Float64(),
            self.ID.SwapPeriod: pl.Int32(),
            self.ID.SwapTime: pl.Int32(),
            self.ID.SwapSkip: pl.Int32(),
            self.ID.SwapExtraDay: pl.String(),
            self.ID.SwapWeekends: pl.Boolean(),
            self.ID.TradingMode: pl.String(),
            self.ID.Variant: pl.String(),
            self.ID.Payoff: pl.String(),
            self.ID.Strike: pl.Float64(),
            self.ID.Maturity: pl.Datetime(),
            self.ID.Exercise: pl.String(),
            **super().Structure
        }

    def attach(self, owner: SecurityAPI) -> Self:
        self._owner_ = owner
        if owner.UID is not None: self.Security = owner.UID
        return self

    @property
    def Type(self):
        return self._owner_.Type if self._owner_ is not None else None

    @property
    def IsSpot(self) -> bool:
        from Library.Universe.Ticker import ContractType
        return self.Type == ContractType.Spot

    @property
    def IsDerivative(self) -> bool:
        from Library.Universe.Ticker import ContractType
        return self.Type in [ContractType.Option, ContractType.Future, ContractType.Swap]

    @property
    def IsLinear(self) -> bool:
        from Library.Universe.Ticker import ContractType
        return self.Type in [ContractType.Spot, ContractType.CFD, ContractType.Future, ContractType.Swap]

    @property
    def IsNonLinear(self) -> bool:
        from Library.Universe.Ticker import ContractType
        return self.Type == ContractType.Option or self.Payoff not in [PayoffType.Vanilla, PayoffType.Trivial, None]

    @classmethod
    def _identity_(cls) -> tuple:
        return "Provider", "Ticker", "Type"

    @classmethod
    def terms(cls) -> tuple:
        return (str(cls.ID.Digits), str(cls.ID.PointSize), str(cls.ID.PipSize), str(cls.ID.LotSize),
                str(cls.ID.VolumeMin), str(cls.ID.VolumeMax), str(cls.ID.VolumeStep),
                str(cls.ID.CommissionMode), str(cls.ID.Commission), str(cls.ID.MinCommission), str(cls.ID.MinCommissionAsset), str(cls.ID.ConversionFee),
                str(cls.ID.SwapMode), str(cls.ID.SwapLong), str(cls.ID.SwapShort), str(cls.ID.SwapPeriod), str(cls.ID.SwapTime), str(cls.ID.SwapSkip), str(cls.ID.SwapExtraDay), str(cls.ID.SwapWeekends),
                str(cls.ID.TradingMode), str(cls.ID.Variant), str(cls.ID.Payoff), str(cls.ID.Strike), str(cls.ID.Maturity), str(cls.ID.Exercise))

    @classmethod
    def _provenance_(cls) -> tuple:
        return str(cls.ID.Timestamp), str(cls.ID.UpdatedAt), str(cls.ID.UpdatedBy)

    @staticmethod
    def _plain_(value: Any) -> Any:
        return value.name if isinstance(value, EnumerationAPI) else value

    def _parsed_(self, name: str, value: Any) -> Any:
        if value is None: return None
        if name in self.Enums:
            enumeration = self.Enums[name]
            parsed = enumeration.parse(value)
            if not isinstance(parsed, enumeration): raise ValueError(f"Contract Pin: Failed · Unknown {name} {value} · Expected one of {' · '.join(enumeration.names())}")
            return parsed
        if name == str(self.ID.Maturity): return parse_datetime(value)
        return value

    def plain(self) -> dict:
        return {name: self._plain_(getattr(self, name)) for name in self.terms()}

    def differs(self, terms: dict) -> bool:
        current = self.plain()
        return any(self._plain_(terms.get(name)) != current[name] for name in self.terms())

    def snapshot(self) -> dict:
        owner = self._owner_
        provider = owner.Provider.UID if owner is not None and owner.Provider is not None else None
        ticker = owner.Ticker.UID if owner is not None and owner.Ticker is not None else None
        return {"Provider": provider, "Ticker": ticker, "Type": self._plain_(self.Type),
                **self.plain(),
                **{name: getattr(self, name) for name in self._provenance_()}}

    def pin(self, snapshot: dict) -> Self:
        expected = (*self._identity_(), *self.terms())
        missing = [name for name in expected if name not in snapshot]
        unknown = [name for name in snapshot if name not in expected and name not in self._provenance_()]
        if missing or unknown:
            reasons = ([f"Missing {' · '.join(missing)}"] if missing else []) + ([f"Unknown {' · '.join(unknown)}"] if unknown else [])
            raise ValueError(f"Contract Pin: Failed · {' · '.join(reasons)}")
        current = self.snapshot()
        foreign = [f"{name} {snapshot[name]} Against {current[name]}" for name in self._identity_() if snapshot[name] != current[name]]
        if foreign: raise ValueError(f"Contract Pin: Failed · Due to another contract · {' · '.join(foreign)}")
        for name in self.terms(): setattr(self, name, self._parsed_(name, snapshot[name]))
        for name in self._provenance_(): setattr(self, name, parse_datetime(snapshot[name]) if name != str(self.ID.UpdatedBy) and snapshot.get(name) is not None else snapshot.get(name))
        return self

    def rolls(self, start: datetime, stop: datetime) -> list[tuple[datetime, int]]:
        if self.SwapTime is None or not self.SwapPeriod: return []
        step = timedelta(hours=int(self.SwapPeriod))
        moment = start.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=int(self.SwapTime))
        while moment - step > start: moment -= step
        while moment <= start: moment += step
        extra, weekends, rolls = self.SwapExtraDay.value if self.SwapExtraDay is not None else None, bool(self.SwapWeekends), []
        while moment < stop:
            weekday = moment.weekday()
            days = 3 if weekday == extra else 0 if weekday in (Weekday.Saturday.value, Weekday.Sunday.value) and not weekends else 1
            if days: rolls.append((moment, days))
            moment += step
        return rolls

    def swap(self, long: bool, volume: float, price: float, days: int) -> float:
        rate = (self.SwapLong if long else self.SwapShort) or 0.0
        match self.SwapMode:
            case SwapMode.Pips: return volume * rate * (self.PipSize or 0.0) * days
            case SwapMode.Points: return volume * rate * (self.PointSize or 0.0) * days
            case SwapMode.Percentage: return volume * price * rate / 100.0 * days / 365.0
        return 0.0

    @classmethod
    def current(cls, db: DatabaseAPI, security: int, at: Union[datetime, Missing] = MISSING) -> Union[Self, None]:
        condition, parameters = '"Security" = :security:', {"security": security}
        if at is not MISSING: condition, parameters = f'{condition} AND "Timestamp" <= :at:', {**parameters, "at": at}
        row = db.first(schema=cls.Schema, table=cls.Table, condition=condition, order='"Timestamp" DESC', parameters=parameters)
        return None if row is None else cls(**row)

    @classmethod
    def history(cls, db: DatabaseAPI, security: int) -> list[Self]:
        return [cls(**row) for row in db.records(schema=cls.Schema, table=cls.Table, condition='"Security" = :security:', order='"Timestamp"', parameters={"security": security})]

    @classmethod
    def revise(cls, db: DatabaseAPI, security: int, terms: dict, at: datetime, by: str) -> Union[Self, None]:
        latest = cls.current(db, security)
        if latest is not None and not latest.differs(terms): return None
        revision = cls(Security=security, Timestamp=at, **{name: terms.get(name) for name in cls.terms()}, db=db)
        revision.save(by=by)
        return revision