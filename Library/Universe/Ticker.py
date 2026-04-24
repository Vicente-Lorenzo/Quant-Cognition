from __future__ import annotations

import re
from typing import ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Enumeration import Enumeration
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Universe.Category import CategoryAPI
from Library.Utility.Typing import MISSING
from Library.Universe.Universe import UniverseAPI

if TYPE_CHECKING: from Library.Database import DatabaseAPI

_FUTURES_PATTERNS_ = (re.compile(r"-F$"), re.compile(r"-[A-Z]{3}\d{2}$"), re.compile(r"[FGHJKMNQUVXZ]\d{1,2}$"), re.compile(r"\d!$"))
_PREFIX_PATTERN_ = re.compile(r"^[^:]+:")
_TRIM_PATTERN_ = re.compile(r"[#.+\-_]+$")
_SUFFIX_LIST_ = sorted([".m", ".micro", ".pro", ".p", ".raw", ".ecn", ".s", ".std", ".i", ".ins", ".z", ".v", ".x", ".plus", "+", "-", "_sb", ".c", ".cfd"], key=len, reverse=True)

class Contract(Enumeration):
    Spot = 0
    Future = 1
    Swap = 2
    Option = 3

@dataclass
class TickerAPI(UniverseAPI):

    Table: ClassVar[str] = "Ticker"

    UID: str | None = None
    Category: InitVar[str | CategoryAPI | None] = field(default=MISSING)
    BaseAsset: str | None = None
    BaseName: str | None = None
    QuoteAsset: str | None = None
    QuoteName: str | None = None
    Description: str | None = None

    _category_: CategoryAPI | None = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Category: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{CategoryAPI.Table}"("{CategoryAPI.ID.UID}")'),
            self.ID.BaseAsset: pl.String(),
            self.ID.BaseName: pl.String(),
            self.ID.QuoteAsset: pl.String(),
            self.ID.QuoteName: pl.String(),
            self.ID.Description: pl.String(),
            **super().Structure
        }

    @staticmethod
    def normalize(uid: str) -> str:
        uid = _PREFIX_PATTERN_.sub("", uid)
        uid = _TRIM_PATTERN_.sub("", uid)
        for pattern in _FUTURES_PATTERNS_: uid = pattern.sub("", uid)
        lower_uid = uid.lower()
        for suffix in _SUFFIX_LIST_:
            if lower_uid.endswith(suffix):
                uid = uid[:-len(suffix)]
                break
        return _TRIM_PATTERN_.sub("", uid).upper()

    @staticmethod
    def detect(uid: str) -> Contract:
        for pattern in _FUTURES_PATTERNS_:
            if pattern.search(uid): return Contract.Future
        return Contract.Spot

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      category: str | CategoryAPI | None) -> None:
        if self.UID: self.UID = self.normalize(self.UID)
        category = coerce(category)
        if isinstance(category, CategoryAPI): self._category_ = category
        elif category is not MISSING and category is not None:
            self._category_ = CategoryAPI(UID=category, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    @property
    @overridefield
    def Category(self) -> CategoryAPI | None:
        return self._category_

    @Category.setter
    def Category(self, val: str | CategoryAPI | None) -> None:
        print("SETTING TICKER CATEGORY:", val)
        if isinstance(val, CategoryAPI): self._category_ = val
        elif val is not None: self._category_ = CategoryAPI(UID=val, db=self._db_, autoload=True)

    def _pull_(self, overload: bool) -> dict | None:
        condition, parameters = None, None
        if not self.UID and self.Description:
            condition, parameters = '"Description" = :value:', {"value": self.Description}
        row = super()._pull_(overload=overload) if condition is None else self._fetch_(condition=condition, parameters=parameters, overload=overload)
        if not row and not condition:
            if self.BaseAsset is None and self.QuoteAsset is None:
                raise ValueError(f"Ticker '{self.UID}' not found in database and lacks required fields for creation.")
        return row

    @property
    def Upper(self) -> str:
        return self.UID.upper() if self.UID else ""

    @property
    def Lower(self) -> str:
        return self.UID.lower() if self.UID else ""

    @property
    def Dashed(self) -> str | None:
        return f"{self.BaseAsset}-{self.QuoteAsset}" if self.BaseAsset and self.QuoteAsset else None

    @property
    def Slashed(self) -> str | None:
        return f"{self.BaseAsset}/{self.QuoteAsset}" if self.BaseAsset and self.QuoteAsset else None

    @property
    def Underscored(self) -> str | None:
        return f"{self.BaseAsset}_{self.QuoteAsset}" if self.BaseAsset and self.QuoteAsset else None