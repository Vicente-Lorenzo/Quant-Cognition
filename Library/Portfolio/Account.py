from __future__ import annotations

from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Enumeration import Enumeration
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Provider import ProviderAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database import DatabaseAPI

class AccountType(Enumeration):
    Hedged = 0
    Netted = 1

class MarginMode(Enumeration):
    Sum = 0
    Max = 1
    Net = 2

class Environment(Enumeration):
    Live = 0
    Demo = 1

@dataclass
class AccountAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Account"

    UID: Union[str, None] = None
    Environment: InitVar[Union[Environment, str, None]] = field(default=MISSING)
    AccountType: InitVar[Union[AccountType, str, None]] = field(default=MISSING)
    MarginMode: InitVar[Union[MarginMode, str, None]] = field(default=MISSING)
    Asset: Union[str, None] = None
    Balance: Union[float, None] = None
    Equity: Union[float, None] = None
    Credit: Union[float, None] = None
    Leverage: Union[float, None] = None
    MarginUsed: Union[float, None] = None
    MarginFree: Union[float, None] = None
    MarginLevel: Union[float, None] = None
    MarginStopLevel: Union[float, None] = None

    Provider: InitVar[Union[str, ProviderAPI, None]] = field(default=MISSING)

    _environment_: Union[Environment, None] = field(default=None, init=False, repr=False)
    _account_type_: Union[AccountType, None] = field(default=None, init=False, repr=False)
    _margin_mode_: Union[MarginMode, None] = field(default=None, init=False, repr=False)
    _provider_: Union[ProviderAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Key(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String)
        }

    @property
    def Columns(self) -> dict:
        return {
            self.ID.Provider: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{ProviderAPI.Table}"("{ProviderAPI.ID.UID}")'),
            self.ID.Environment: pl.String(),
            self.ID.AccountType: pl.String(),
            self.ID.MarginMode: pl.String(),
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
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      environment: Union[Environment, str, None],
                      account_type: Union[AccountType, str, None],
                      margin_mode: Union[MarginMode, str, None],
                      provider: Union[str, ProviderAPI, None]) -> None:
        environment = coerce(environment)
        account_type = coerce(account_type)
        margin_mode = coerce(margin_mode)
        provider = coerce(provider)
        self._environment_ = Environment.parse(environment) if environment is not MISSING else None
        self._account_type_ = AccountType.parse(account_type) if account_type is not MISSING else None
        self._margin_mode_ = MarginMode.parse(margin_mode) if margin_mode is not MISSING else None
        if isinstance(provider, ProviderAPI): self._provider_ = provider
        elif provider is not MISSING and provider is not None:
            self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(provider), db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if row:
            self._environment_ = Environment.parse(row.get(self.ID.Environment))
            self._account_type_ = AccountType.parse(row.get(self.ID.AccountType))
            self._margin_mode_ = MarginMode.parse(row.get(self.ID.MarginMode))
        return row

    @property
    @overridefield
    def Environment(self) -> Union[Environment, None]:
        return self._environment_
    @Environment.setter
    def Environment(self, val: Union[Environment, str, None]) -> None:
        self._environment_ = Environment.parse(val)

    @property
    @overridefield
    def AccountType(self) -> Union[AccountType, None]:
        return self._account_type_
    @AccountType.setter
    def AccountType(self, val: Union[AccountType, str, None]) -> None:
        self._account_type_ = AccountType.parse(val)

    @property
    @overridefield
    def MarginMode(self) -> Union[MarginMode, None]:
        return self._margin_mode_
    @MarginMode.setter
    def MarginMode(self, val: Union[MarginMode, str, None]) -> None:
        self._margin_mode_ = MarginMode.parse(val)

    @property
    @overridefield
    def Provider(self) -> Union[ProviderAPI, None]:
        return self._provider_
    @Provider.setter
    def Provider(self, val: Union[str, ProviderAPI, None]) -> None:
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
    def UnrealizedPnL(self) -> Union[float, None]:
        if self.Equity is None or self.Balance is None: return None
        return self.Equity - self.Balance
    @property
    def UnrealizedReturn(self) -> Union[float, None]:
        pnl = self.UnrealizedPnL
        if pnl is None or not self.Balance: return None
        return pnl / self.Balance
    @property
    def MarginRatio(self) -> Union[float, None]:
        if not self.Equity or self.MarginUsed is None: return None
        return self.MarginUsed / self.Equity
    @property
    def FreeMarginRatio(self) -> Union[float, None]:
        if not self.Equity or self.MarginFree is None: return None
        return self.MarginFree / self.Equity
    @property
    def CreditRatio(self) -> Union[float, None]:
        if not self.Balance or self.Credit is None: return None
        return self.Credit / self.Balance