from __future__ import annotations

from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Database import IdentityKey, PrimaryKey, ForeignKey
from Library.Database.Query import QueryAPI
from Library.Utility.Datetime import utc_now
from Library.Utility.Enumeration import EnumerationAPI
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database import DatabaseAPI

class SecurityStatus(EnumerationAPI):

    Enabled = 0
    Disabled = 1
    Archived = 2

@dataclass
class SecurityAPI(UniverseAPI):

    Table: ClassVar[str] = "Security"
    Enums: ClassVar[dict] = {"Type": ContractType, "Status": SecurityStatus}

    UID: Union[int, None] = None

    Provider: InitVar[Union[str, ProviderAPI, None]] = field(default=MISSING)
    Ticker: InitVar[Union[str, TickerAPI, None]] = field(default=MISSING)
    Type: Union[ContractType, str, None] = None
    Symbol: Union[int, None] = None
    Status: Union[SecurityStatus, str, None] = None
    Tracked: Union[bool, None] = None
    Contract: InitVar[Union[ContractAPI, None]] = field(default=MISSING)

    _provider_: Union[ProviderAPI, None] = field(default=None, init=False, repr=False)
    _ticker_: Union[TickerAPI, None] = field(default=None, init=False, repr=False)
    _contract_: Union[ContractAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Provider: ForeignKey(pl.String, reference=ProviderAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Ticker: ForeignKey(pl.String, reference=TickerAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Type: PrimaryKey(pl.String),
            self.ID.Symbol: pl.Int64(),
            self.ID.Status: pl.String(),
            self.ID.Tracked: pl.Boolean(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool,
                      provider: Union[str, ProviderAPI, None],
                      ticker: Union[str, TickerAPI, None],
                      contract: Union[ContractAPI, None]) -> None:
        provider = coerce(provider)
        ticker = coerce(ticker)
        contract = coerce(contract)
        self._provider_ = self._relate_(provider, ProviderAPI, normalize=ProviderAPI.normalize, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        self._ticker_ = self._relate_(ticker, TickerAPI, normalize=TickerAPI.normalize, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        if self.Type is None and self._ticker_ is not None and self._ticker_.UID: self.Type = TickerAPI.detect(self._ticker_.UID)
        if isinstance(contract, ContractAPI): self._contract_ = contract
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)
        if self._contract_ is None and self._db_ is not None and self.UID is not None and (autoload or autooverload): self._contract_ = ContractAPI.current(self._db_, self.UID)
        if self._contract_ is not None: self._contract_.attach(self)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        if self._db_ is None: return None
        if self.UID is not None: row = super()._pull_(overload=overload)
        elif self._provider_ is not None and self._ticker_ is not None:
            kind = self.Type.name if isinstance(self.Type, ContractType) else self.Type
            condition, parameters = self._db_.where(Provider=self._provider_.UID, Ticker=self._ticker_.UID, Type=kind)
            row = self._fetch_(condition=condition, parameters=parameters, overload=overload)
            if row is None:
                condition, parameters = self._db_.where(Provider=self._provider_.UID, Ticker=self._ticker_.UID)
                kinds = self._db_.records(schema=self.Schema, table=self.Table, columns=[str(self.ID.Type)], condition=condition, parameters=parameters)
                if len(kinds) == 1:
                    self.Type = ContractType.parse(kinds[0][str(self.ID.Type)])
                    condition, parameters = self._db_.where(Provider=self._provider_.UID, Ticker=self._ticker_.UID, Type=self.Type.name)
                    row = self._fetch_(condition=condition, parameters=parameters, overload=overload)
        else: return None
        if row is None: raise LookupError(f"Security Lookup: Failed · {self._provider_.UID if self._provider_ else '?'} {self._ticker_.UID if self._ticker_ else self.UID} is not in the Universe")
        for name, enumeration in self.Enums.items(): setattr(self, name, enumeration.parse(getattr(self, name)))
        if self._provider_ is None and row.get("Provider"): self._provider_ = ProviderAPI(UID=row["Provider"], db=self._db_, autoload=True)
        if self._ticker_ is None and row.get("Ticker"): self._ticker_ = TickerAPI(UID=row["Ticker"], db=self._db_, autoload=True)
        return row

    @property
    @overridefield
    def Provider(self) -> Union[ProviderAPI, None]:
        return self._provider_
    @Provider.setter
    def Provider(self, val: Union[str, ProviderAPI, None]) -> None:
        if val is not None: self._provider_ = self._relate_(val, ProviderAPI, normalize=ProviderAPI.normalize, db=self._db_, autoload=True)

    @property
    @overridefield
    def Ticker(self) -> Union[TickerAPI, None]:
        return self._ticker_
    @Ticker.setter
    def Ticker(self, val: Union[str, TickerAPI, None]) -> None:
        if val is not None: self._ticker_ = self._relate_(val, TickerAPI, normalize=TickerAPI.normalize, db=self._db_, autoload=True)

    @property
    def Category(self) -> Union[CategoryAPI, None]:
        return self._ticker_.Category if self._ticker_ is not None else None

    @property
    def Contract(self) -> Union[ContractAPI, None]:
        return self._contract_
    @Contract.setter
    def Contract(self, val: Union[ContractAPI, None]) -> None:
        if isinstance(val, ContractAPI):
            self._contract_ = val
            val.attach(self)

    @classmethod
    def overview(cls, db: DatabaseAPI) -> pl.DataFrame:
        terms = ", ".join(f'c."{name}"' for name in ("Digits", "PipSize", "LotSize", "VolumeMin", "CommissionMode", "Commission", "SwapLong", "SwapShort", "TradingMode"))
        return db.executeone(QueryAPI(f'''SELECT s."UID", s."Provider", s."Ticker", s."Type", s."Symbol", s."Status", s."Tracked", t."Category", t."Description", {terms}, c."Timestamp" AS "Terms"
            FROM "{cls.Schema}"."{cls.Table}" s JOIN "{TickerAPI.Schema}"."{TickerAPI.Table}" t ON t."UID" = s."Ticker"
            LEFT JOIN LATERAL (SELECT * FROM "{ContractAPI.Schema}"."{ContractAPI.Table}" k WHERE k."Security" = s."UID" ORDER BY k."Timestamp" DESC LIMIT 1) c ON TRUE
            ORDER BY s."Provider", s."Ticker", s."Type"''')).fetchall(legacy=False)

    @classmethod
    def track(cls, db: DatabaseAPI, uids: list[int], tracked: bool, by: str) -> int:
        if not uids: return 0
        db.update(schema=cls.Schema, table=cls.Table, data={"Tracked": bool(tracked), "UpdatedAt": utc_now(), "UpdatedBy": by}, condition='"UID" = ANY(:uids:)', parameters={"uids": [int(uid) for uid in uids]})
        return len(uids)