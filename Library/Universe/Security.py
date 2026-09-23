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
            self.ID.Provider: ForeignKey(pl.String, reference=ProviderAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Category: ForeignKey(pl.String, reference=CategoryAPI.reference(), primary=True),
            self.ID.Ticker: ForeignKey(pl.String, reference=TickerAPI.reference("ON DELETE CASCADE"), primary=True),
            self.ID.Contract: ForeignKey(pl.Int64, reference=ContractAPI.reference(), primary=True),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autoload: bool,
                      autooverload: bool,
                      autosave: bool,
                      provider: Union[str, ProviderAPI, None],
                      category: Union[str, CategoryAPI, None],
                      ticker: Union[str, TickerAPI, None],
                      contract: Union[int, str, ContractType, ContractAPI, None]) -> None:
        provider = coerce(provider)
        category = coerce(category)
        ticker = coerce(ticker)
        contract = coerce(contract)
        self._provider_ = self._relate_(provider, ProviderAPI, normalize=ProviderAPI.normalize, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        self._ticker_ = self._relate_(ticker, TickerAPI, normalize=TickerAPI.normalize, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        self._category_ = self._relate_(category, CategoryAPI, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        if self._category_ is None and self._ticker_: self._category_ = self._ticker_.Category
        if isinstance(contract, ContractAPI): self._contract_ = contract
        elif contract is not MISSING and contract is not None:
            if isinstance(contract, int):
                self._contract_ = ContractAPI(UID=contract, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
            else:
                tuid = self._ticker_.UID if self._ticker_ else None
                puid = self._provider_.UID if self._provider_ else None
                if tuid and puid: self._contract_ = ContractAPI(Ticker=tuid, Provider=puid, Type=contract, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        elif self._ticker_ and self._provider_:
            ct = TickerAPI.detect(self._ticker_.UID)
            self._contract_ = ContractAPI(Ticker=self._ticker_.UID, Provider=self._provider_.UID, Type=ct, db=db, migrate=migrate, autoload=autoload, autooverload=autooverload)
        super().__post_init__(db=db, migrate=migrate, autoload=autoload, autooverload=autooverload, autosave=autosave)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        row = super()._pull_(overload=overload)
        if not row and self._db_ is not None and self.UID is None and self._ticker_ and self._provider_:
            category = self._category_.UID if self._category_ else MISSING
            contract = self._contract_.UID if self._contract_ and self._contract_.UID is not None else MISSING
            condition, parameters = self._db_.where(Provider=self._provider_.UID, Ticker=self._ticker_.UID, Category=category, Contract=contract)
            row = self._fetch_(condition=condition, parameters=parameters, overload=overload)
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
        if val is not None: self._provider_ = self._relate_(val, ProviderAPI, normalize=ProviderAPI.normalize, db=self._db_, autoload=True)

    @property
    @overridefield
    def Category(self) -> Union[CategoryAPI, None]:
        return self._category_
    @Category.setter
    def Category(self, val: Union[str, CategoryAPI, None]) -> None:
        if val is not None: self._category_ = self._relate_(val, CategoryAPI, db=self._db_, autoload=True)

    @property
    @overridefield
    def Ticker(self) -> Union[TickerAPI, None]:
        return self._ticker_
    @Ticker.setter
    def Ticker(self, val: Union[str, TickerAPI, None]) -> None:
        if val is not None: self._ticker_ = self._relate_(val, TickerAPI, normalize=TickerAPI.normalize, db=self._db_, autoload=True)

    @property
    @overridefield
    def Contract(self) -> Union[ContractAPI, None]:
        return self._contract_
    @Contract.setter
    def Contract(self, val: Union[int, ContractAPI, None]) -> None:
        if isinstance(val, ContractAPI): self._contract_ = val
        elif isinstance(val, int): self._contract_ = ContractAPI(UID=val, db=self._db_, autoload=True)