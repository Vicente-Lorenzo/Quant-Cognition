from __future__ import annotations

from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Dataclass import overridefield, coerce
from Library.Database.Database import IdentityKey, ForeignKey
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Ticker import TickerAPI, ContractType
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING: from Library.Database import DatabaseAPI

@dataclass
class SecurityAPI(UniverseAPI):

    Table: ClassVar[str] = "Security"

    UID: Union[int, None] = None

    Provider: InitVar[Union[str, ProviderAPI, None]] = field(default=MISSING)
    Category: InitVar[Union[str, CategoryAPI, None]] = field(default=MISSING)
    Ticker: InitVar[Union[str, TickerAPI, None]] = field(default=MISSING)
    Contract: InitVar[Union[int, str, ContractType, ContractAPI, None]] = field(default=MISSING)

    _provider_: Union[ProviderAPI, None] = field(default=None, init=False, repr=False)
    _category_: Union[CategoryAPI, None] = field(default=None, init=False, repr=False)
    _ticker_: Union[TickerAPI, None] = field(default=None, init=False, repr=False)
    _contract_: Union[ContractAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: IdentityKey(pl.Int64),
            self.ID.Provider: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{ProviderAPI.Table}"("{ProviderAPI.ID.UID}") ON DELETE CASCADE', primary=True),
            self.ID.Category: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{CategoryAPI.Table}"("{CategoryAPI.ID.UID}")', primary=True),
            self.ID.Ticker: ForeignKey(pl.String, reference=f'"{UniverseAPI.Schema}"."{TickerAPI.Table}"("{TickerAPI.ID.UID}") ON DELETE CASCADE', primary=True),
            self.ID.Contract: ForeignKey(pl.Int64, reference=f'"{UniverseAPI.Schema}"."{ContractAPI.Table}"("{ContractAPI.ID.UID}")', primary=True),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      provider: Union[str, ProviderAPI, None],
                      category: Union[str, CategoryAPI, None],
                      ticker: Union[str, TickerAPI, None],
                      contract: Union[int, str, ContractType, ContractAPI, None]) -> None:
        provider = coerce(provider)
        category = coerce(category)
        ticker = coerce(ticker)
        contract = coerce(contract)
        if isinstance(provider, ProviderAPI): self._provider_ = provider
        elif provider is not MISSING and provider is not None:
            self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(provider), db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if isinstance(ticker, TickerAPI): self._ticker_ = ticker
        elif ticker is not MISSING and ticker is not None:
            self._ticker_ = TickerAPI(UID=TickerAPI.normalize(ticker), db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        if isinstance(category, CategoryAPI): self._category_ = category
        elif category is not MISSING and category is not None:
            self._category_ = CategoryAPI(UID=category, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        elif self._ticker_ and self._ticker_.Category:
            self._category_ = self._ticker_.Category
        if isinstance(contract, ContractAPI): self._contract_ = contract
        elif contract is not MISSING and contract is not None:
            if isinstance(contract, int):
                self._contract_ = ContractAPI(UID=contract, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
            else:
                tuid = self._ticker_.UID if self._ticker_ else None
                puid = self._provider_.UID if self._provider_ else None
                if tuid and puid: self._contract_ = ContractAPI(Ticker=tuid, Provider=puid, Type=contract, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        elif self._ticker_ and self._provider_:
            ct = TickerAPI.detect(self._ticker_.UID)
            self._contract_ = ContractAPI(Ticker=self._ticker_.UID, Provider=self._provider_.UID, Type=ct, db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if not row and self.UID is None and self._ticker_ and self._provider_:
            clauses = ['"Provider" = :provider:', '"Ticker" = :ticker:']
            params = {"provider": self._provider_.UID, "ticker": self._ticker_.UID}
            if self._category_:
                clauses.append('"Category" = :category:')
                params["category"] = self._category_.UID
            if self._contract_ and self._contract_.UID is not None:
                clauses.append('"Contract" = :contract:')
                params["contract"] = self._contract_.UID
            row = self._fetch_(condition=" AND ".join(clauses), parameters=params, overload=overload)
        return row

    def save(self, by: str = "Autosave") -> None:
        if self._ticker_: self._ticker_.save(by=by)
        if self._provider_: self._provider_.save(by=by)
        if self._category_: self._category_.save(by=by)
        if self._contract_: self._contract_.save(by=by)
        super().save(by=by)
        if self.UID is None: self.load()

    @property
    @overridefield
    def Provider(self) -> Union[ProviderAPI, None]:
        return self._provider_
    @Provider.setter
    def Provider(self, val: Union[str, ProviderAPI, None]) -> None:
        if isinstance(val, ProviderAPI): self._provider_ = val
        elif val is not None: self._provider_ = ProviderAPI(UID=ProviderAPI.normalize(val), db=self._db_, autoload=True)

    @property
    @overridefield
    def Category(self) -> Union[CategoryAPI, None]:
        return self._category_
    @Category.setter
    def Category(self, val: Union[str, CategoryAPI, None]) -> None:
        if isinstance(val, CategoryAPI): self._category_ = val
        elif val is not None: self._category_ = CategoryAPI(UID=val, db=self._db_, autoload=True)

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
    def Contract(self) -> Union[ContractAPI, None]:
        return self._contract_
    @Contract.setter
    def Contract(self, val: Union[int, ContractAPI, None]) -> None:
        if isinstance(val, ContractAPI): self._contract_ = val
        elif isinstance(val, int): self._contract_ = ContractAPI(UID=val, db=self._db_, autoload=True)