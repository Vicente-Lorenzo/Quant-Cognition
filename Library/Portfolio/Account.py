from __future__ import annotations

from typing import ClassVar, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Enumeration import as_enum
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Provider import ProviderAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database import DatabaseAPI

class AccountType(Enum):
    Hedged = 0
    Netted = 1

class MarginMode(Enum):
    Sum = 0
    Max = 1
    Net = 2

class Environment(Enum):
    Live = 0
    Demo = 1

@dataclass
class AccountAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Portfolio"
    Table: ClassVar[str] = "Account"

    UID: str | None = None
    Environment: InitVar[Environment | str | None] = field(default=MISSING)
    AccountType: InitVar[AccountType | str | None] = field(default=MISSING)
    MarginMode: InitVar[MarginMode | str | None] = field(default=MISSING)
    Asset: str | None = None
    Balance: float | None = None
    Equity: float | None = None
    Credit: float | None = None
    Leverage: float | None = None
    MarginUsed: float | None = None
    MarginFree: float | None = None
    MarginLevel: float | None = None
    MarginStopLevel: float | None = None

    Provider: InitVar[str | ProviderAPI | None] = field(default=MISSING)

    _environment_: Environment | None = field(default=None, init=False, repr=False)
    _account_type_: AccountType | None = field(default=None, init=False, repr=False)
    _margin_mode_: MarginMode | None = field(default=None, init=False, repr=False)
    _provider_: ProviderAPI | None = field(default=None, init=False, repr=False)

    @property
    def Key(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String)
        }

    @property
    def Columns(self) -> dict:
        return {
            self.ID.Provider: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{ProviderAPI.Table}"("{ProviderAPI.ID.UID}")'),
            self.ID.Environment: pl.Enum([e.name for e in Environment]),
            self.ID.AccountType: pl.Enum([e.name for e in AccountType]),
            self.ID.MarginMode: pl.Enum([e.name for e in MarginMode]),
            self.ID.Asset: pl.String(),
            self.ID.Balance: pl.Float64(),
            self.ID.Equity: pl.Float64(),
            self.ID.Credit: pl.Float64(),
            self.ID.Leverage: pl.Float64(),
            self.ID.MarginUsed: pl.Float64(),
            self.ID.MarginFree: pl.Float64(),
            self.ID.MarginLevel: pl.Float64(),
            self.ID.MarginStopLevel: pl.Float64(),
            **super().Columns
        }

    def __post_init__(self,
                      db: DatabaseAPI | None,
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      environment: Environment | str | None,
                      account_type: AccountType | str | None,
                      margin_mode: MarginMode | str | None,
                      provider: str | ProviderAPI | None) -> None:
        environment = MISSING if isinstance(environment, property) else environment
        account_type = MISSING if isinstance(account_type, property) else account_type
        margin_mode = MISSING if isinstance(margin_mode, property) else margin_mode
        provider = coerce(provider)
        self._environment_ = as_enum(Environment, environment) if environment is not MISSING else None
        self._account_type_ = as_enum(AccountType, account_type) if account_type is not MISSING else None
        self._margin_mode_ = as_enum(MarginMode, margin_mode) if margin_mode is not MISSING else None
        if isinstance(provider, ProviderAPI): self._provider_ = provider
        elif provider is not MISSING and provider is not None:
            self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(provider), db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> dict | None:
        row = super()._pull_(overload=overload)
        if row:
            self._environment_ = as_enum(Environment, row.get(self.ID.Environment))
            self._account_type_ = as_enum(AccountType, row.get(self.ID.AccountType))
            self._margin_mode_ = as_enum(MarginMode, row.get(self.ID.MarginMode))
        return row

    @property
    @overridefield
    def Environment(self) -> Environment | None:
        return self._environment_
    @Environment.setter
    def Environment(self, val: Environment | str | None) -> None:
        self._environment_ = as_enum(Environment, val)

    @property
    @overridefield
    def AccountType(self) -> AccountType | None:
        return self._account_type_
    @AccountType.setter
    def AccountType(self, val: AccountType | str | None) -> None:
        self._account_type_ = as_enum(AccountType, val)

    @property
    @overridefield
    def MarginMode(self) -> MarginMode | None:
        return self._margin_mode_
    @MarginMode.setter
    def MarginMode(self, val: MarginMode | str | None) -> None:
        self._margin_mode_ = as_enum(MarginMode, val)

    @property
    @overridefield
    def Provider(self) -> ProviderAPI | None:
        return self._provider_
    @Provider.setter
    def Provider(self, val: str | ProviderAPI | None) -> None:
        if isinstance(val, ProviderAPI): self._provider_ = val
        elif val is not None: self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(val), db=self._db_, autoload=True)

    def __str__(self) -> str:
        return self.UID or ""

    @property
    def IsLive(self) -> bool:
        return self._environment_ == Environment.Live
    @property
    def IsDemo(self) -> bool:
        return self._environment_ == Environment.Demo
    @property
    def IsHedged(self) -> bool:
        return self._account_type_ == AccountType.Hedged
    @property
    def IsNetted(self) -> bool:
        return self._account_type_ == AccountType.Netted
    @property
    def UnrealizedPnL(self) -> float | None:
        if self.Equity is None or self.Balance is None: return None
        return self.Equity - self.Balance
    @property
    def UnrealizedReturn(self) -> float | None:
        pnl = self.UnrealizedPnL
        if pnl is None or not self.Balance: return None
        return pnl / self.Balance
    @property
    def MarginRatio(self) -> float | None:
        if not self.Equity or self.MarginUsed is None: return None
        return self.MarginUsed / self.Equity
    @property
    def FreeMarginRatio(self) -> float | None:
        if not self.Equity or self.MarginFree is None: return None
        return self.MarginFree / self.Equity
    @property
    def CreditRatio(self) -> float | None:
        if not self.Balance or self.Credit is None: return None
        return self.Credit / self.Balance