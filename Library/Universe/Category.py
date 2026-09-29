from __future__ import annotations

from dataclasses import dataclass
from typing_extensions import Self
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI
from Library.Universe.Universe import UniverseAPI
from Library.Utility.Datetime import utc_now

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass
class CategoryAPI(DatapointAPI):

    Schema: ClassVar[str] = UniverseAPI.Schema
    Table: ClassVar[str] = "Category"

    UID: Union[str, None] = None
    Primary: Union[str, None] = None
    Secondary: Union[str, None] = None
    Alternative: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Primary: pl.String(),
            self.ID.Secondary: pl.String(),
            self.ID.Alternative: pl.String(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool) -> None:
        if not self.UID and self.Primary and self.Secondary:
            self.UID = f"{self.Primary}({self.Secondary})"
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        if self._db_ is None: return None
        if not self.UID and not self.Primary: return None
        condition, parameters = None, None
        if self.UID:
            condition = '"UID" = :value: OR "Primary" = :value: OR "Secondary" = :value: OR "Alternative" = :value:'
            parameters = {"value": self.UID}
        elif self.Primary and self.Secondary:
            condition = '"Primary" = :primary: AND "Secondary" = :secondary:'
            parameters = {"primary": self.Primary, "secondary": self.Secondary}
        row = super()._pull_(overload=overload) if condition is None else self._fetch_(condition=condition, parameters=parameters, overload=overload)
        if not row and not condition:
            if self.Primary is None or self.Secondary is None:
                raise ValueError(f"Category '{self.UID or self.Primary}' not found in database and lacks required fields for creation.")
        return row

    @staticmethod
    def _majors_() -> frozenset:
        return frozenset(("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"))

    @staticmethod
    def _region_(currency: Union[str, None]) -> Union[str, None]:
        for region, currencies in (("AMER", ("USD", "CAD", "BRL", "MXN")), ("EMEA", ("EUR", "GBP", "CHF", "NOK", "SEK", "PLN", "ZAR")), ("APAC", ("JPY", "AUD", "NZD", "HKD", "SGD"))):
            if currency in currencies: return region
        return None

    @staticmethod
    def _family_(primary: str) -> Union[str, None]:
        return {"Forex": "Currency", "Crypto": "Currency", "Index": "Equity", "Stock": "Equity", "ETF": "Equity", "Metal": "Commodity", "Energy": "Commodity"}.get(primary)

    @classmethod
    def classify(cls, primary: str, base: Union[str, None] = None, quote: Union[str, None] = None, country: Union[str, None] = None) -> Self:
        alternative = cls._family_(primary)
        match primary:
            case "Forex":
                majors = cls._majors_()
                secondary = ("Major" if "USD" in (base, quote) else "Minor") if base in majors and quote in majors else "Exotic"
            case "Metal": secondary = "Major" if quote in ("USD", "EUR") else "Minor"
            case "Crypto": secondary = "Major" if base in ("BTC", "ETH") else "Minor"
            case "Energy": secondary = "Major"
            case "Index":
                if quote == "INDEX": secondary, alternative = cls._region_(base), "Currency"
                else: secondary = cls._region_(quote)
            case "Stock" | "ETF": secondary = country
            case _: secondary = None
        uid = f"{primary}({secondary})" if secondary else primary
        if primary == "Index" and secondary: uid += alternative
        return cls(UID=uid, Primary=primary, Secondary=secondary, Alternative=alternative)

    @classmethod
    def store(cls, db: DatabaseAPI, primary: str, secondary: Union[str, None], alternative: Union[str, None], by: str) -> str:
        if not primary or not primary.strip(): raise ValueError("Category Store: Failed · A category needs a primary class")
        primary, secondary, alternative = primary.strip(), (secondary or "").strip() or None, (alternative or "").strip() or None
        uid = f"{primary}({secondary})" if secondary else primary
        db.upsert(schema=cls.Schema, table=cls.Table, data=[{"UID": uid, "Primary": primary, "Secondary": secondary, "Alternative": alternative, "UpdatedAt": utc_now(), "UpdatedBy": by}], key=["UID"])
        return uid