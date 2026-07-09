from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar, TYPE_CHECKING

from Library.Auth.Role import RoleAPI
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI

if TYPE_CHECKING: from Library.Database.Database import DatabaseAPI

@dataclass
class UserAPI(DatapointAPI):

    Database: ClassVar[str] = DatapointAPI.Database
    Schema: ClassVar[str] = "Auth"
    Table: ClassVar[str] = "User"

    UID: Union[str, None] = None
    Email: Union[str, None] = None
    Name: Union[str, None] = None
    PasswordHash: Union[str, None] = None
    Role: Union[str, RoleAPI, None] = None
    Provider: Union[str, None] = None
    IsActive: Union[bool, None] = None
    CreatedAt: Union[datetime, None] = None
    LastLogin: Union[datetime, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Email: pl.String(),
            self.ID.Name: pl.String(),
            self.ID.PasswordHash: pl.String(),
            self.ID.Role: pl.String(),
            self.ID.Provider: pl.String(),
            self.ID.IsActive: pl.Boolean(),
            self.ID.CreatedAt: pl.Datetime(),
            self.ID.LastLogin: pl.Datetime(),
            **super().Structure
        }

    def __post_init__(self,
                      db: Union[DatabaseAPI, None],
                      migrate: bool,
                      autosave: bool,
                      autoload: bool,
                      autooverload: bool) -> None:
        self.Role = RoleAPI.parse(self.Role)
        super().__post_init__(db=db, migrate=migrate, autosave=autosave, autoload=autoload, autooverload=autooverload)

    def authority(self) -> RoleAPI:
        role = RoleAPI.parse(self.Role)
        return role if isinstance(role, RoleAPI) else RoleAPI.Public