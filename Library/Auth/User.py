from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Auth.Role import RoleAPI
from Library.Auth.Team import TeamAPI
from Library.Auth.Office import OfficeAPI
from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Database import PrimaryKey, ForeignKey

@dataclass
class UserAPI(DatapointAPI):

    Schema: ClassVar[str] = "Auth"
    Table: ClassVar[str] = "User"
    Enums: ClassVar[dict] = {"Role": RoleAPI}

    UID: Union[str, None] = None
    Office: Union[str, None] = None
    Team: Union[str, None] = None
    Provider: Union[str, None] = None
    Active: Union[bool, None] = None
    Role: Union[str, RoleAPI, None] = None
    Name: Union[str, None] = None
    Forename: Union[str, None] = None
    Middlename: Union[str, None] = None
    Surname: Union[str, None] = None
    Email: Union[str, None] = None
    Telephone: Union[str, None] = None
    Password: Union[str, None] = None
    LastLogin: Union[datetime, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Office: ForeignKey(pl.String, reference=f'"{OfficeAPI.Schema}"."{OfficeAPI.Table}"("{OfficeAPI.ID.UID}")'),
            self.ID.Team: ForeignKey(pl.String, reference=f'"{TeamAPI.Schema}"."{TeamAPI.Table}"("{TeamAPI.ID.UID}")'),
            self.ID.Provider: pl.String(),
            self.ID.Active: pl.Boolean(),
            self.ID.Role: pl.String(),
            self.ID.Name: pl.String(),
            self.ID.Forename: pl.String(),
            self.ID.Middlename: pl.String(),
            self.ID.Surname: pl.String(),
            self.ID.Email: pl.String(),
            self.ID.Telephone: pl.String(),
            self.ID.Password: pl.String(),
            self.ID.LastLogin: pl.Datetime(),
            **super().Structure
        }

    def authority(self) -> RoleAPI:
        return RoleAPI.coerce(self.Role)