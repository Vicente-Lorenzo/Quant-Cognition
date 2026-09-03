from __future__ import annotations

import uuid

from datetime import datetime
from typing import Union, ClassVar, TYPE_CHECKING
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey, DatabaseAPI
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Dataclass import overridefield, coerce
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Universe.Universe import UniverseAPI
from Library.Universe.Security import SecurityAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from Library.Portfolio.Account import AccountAPI
    from Library.System.System import SystemType

@dataclass
class SessionAPI(DatapointAPI):

    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Session"

    UID: Union[str, None] = None
    Type: InitVar[Union[SystemType, str, None]] = field(default=MISSING)
    Strategy: Union[str, None] = None
    Security: InitVar[Union[int, SecurityAPI, None]] = field(default=MISSING)
    StartTimestamp: Union[datetime, None] = None
    StopTimestamp: Union[datetime, None] = None
    InitialAccount: InitVar[Union[int, AccountAPI, None]] = field(default=MISSING)
    FinalAccount: InitVar[Union[int, AccountAPI, None]] = field(default=MISSING)

    _type_: Union[SystemType, None] = field(default=None, init=False, repr=False)
    _security_: Union[SecurityAPI, None] = field(default=None, init=False, repr=False)
    _initial_account_: Union[AccountAPI, None] = field(default=None, init=False, repr=False)
    _final_account_: Union[AccountAPI, None] = field(default=None, init=False, repr=False)

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Type: pl.String(),
            self.ID.Strategy: pl.String(),
            self.ID.Security: ForeignKey(pl.Int64, reference=f'"{UniverseAPI.Schema}"."{SecurityAPI.Table}"("{SecurityAPI.ID.UID}")'),
            self.ID.StartTimestamp: pl.Datetime(),
            self.ID.StopTimestamp: pl.Datetime(),
            self.ID.InitialAccount: pl.Int64(),
            self.ID.FinalAccount: pl.Int64(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool,
                      type: Union[SystemType, str, None],
                      security: Union[int, SecurityAPI, None],
                      initial_account: Union[int, AccountAPI, None],
                      final_account: Union[int, AccountAPI, None]) -> None:
        from Library.Portfolio.Account import AccountAPI
        from Library.System.System import SystemType
        type = coerce(type)
        security = coerce(security)
        initial_account = coerce(initial_account)
        final_account = coerce(final_account)
        self._type_ = SystemType.parse(type) if type is not MISSING and type is not None else None
        if isinstance(security, SecurityAPI): self._security_ = security
        elif security is not MISSING and security is not None:
            self._security_ = SecurityAPI(UID=security, db=db, autoload=True)
        if isinstance(initial_account, AccountAPI): self._initial_account_ = initial_account
        elif initial_account is not MISSING and initial_account is not None:
            self._initial_account_ = AccountAPI(UID=initial_account, db=db, autoload=False, autooverload=False)
        if isinstance(final_account, AccountAPI): self._final_account_ = final_account
        elif final_account is not MISSING and final_account is not None:
            self._final_account_ = AccountAPI(UID=final_account, db=db, autoload=False, autooverload=False)
        if self.UID is None:
            self.UID = self._generate_uid_(self._type_)
        if self.StartTimestamp is None:
            self.StartTimestamp = datetime.now()
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def _pull_(self, overload: bool) -> Union[dict, None]:
        from Library.System.System import SystemType
        row = super()._pull_(overload=overload)
        if row:
            self._type_ = SystemType.parse(row.get(self.ID.Type))
        return row

    @property
    @overridefield
    def Type(self) -> Union[SystemType, None]:
        return self._type_
    @Type.setter
    def Type(self, val: Union[SystemType, str, None]) -> None:
        from Library.System.System import SystemType
        self._type_ = SystemType.parse(val)

    @property
    @overridefield
    def Security(self) -> Union[SecurityAPI, None]:
        return self._security_
    @Security.setter
    def Security(self, val: Union[int, SecurityAPI, None]) -> None:
        if isinstance(val, SecurityAPI): self._security_ = val
        elif val is not None: self._security_ = SecurityAPI(UID=val, db=self._db_, autoload=True)

    @property
    @overridefield
    def InitialAccount(self) -> Union[AccountAPI, None]:
        return self._initial_account_
    @InitialAccount.setter
    def InitialAccount(self, val: Union[int, AccountAPI, None]) -> None:
        from Library.Portfolio.Account import AccountAPI
        if isinstance(val, AccountAPI): self._initial_account_ = val
        elif val is not None: self._initial_account_ = AccountAPI(UID=val, db=self._db_, autoload=False, autooverload=False)

    @property
    @overridefield
    def FinalAccount(self) -> Union[AccountAPI, None]:
        return self._final_account_
    @FinalAccount.setter
    def FinalAccount(self, val: Union[int, AccountAPI, None]) -> None:
        from Library.Portfolio.Account import AccountAPI
        if isinstance(val, AccountAPI): self._final_account_ = val
        elif val is not None: self._final_account_ = AccountAPI(UID=val, db=self._db_, autoload=False, autooverload=False)

    @property
    def Duration(self) -> Union[float, None]:
        if self.StartTimestamp is None or self.StopTimestamp is None: return None
        return (self.StopTimestamp - self.StartTimestamp).total_seconds()

    @staticmethod
    def _generate_uid_(type: Union[SystemType, None]) -> str:
        prefix = type.name if type is not None else "Session"
        return f"{prefix}-{uuid.uuid4().hex[:12]}"