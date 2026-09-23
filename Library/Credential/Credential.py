from __future__ import annotations

import json
from datetime import datetime
from dataclasses import dataclass
from typing import Any, ClassVar, Union

from Library.Auth.Role import RoleAPI
from Library.Auth.User import UserAPI
from Library.Credential.Type import CredentialType, LayoutAPI
from Library.Credential.Secret import SecretAPI
from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI
from Library.Utility.Enumeration import EnumerationAPI

class Validity(EnumerationAPI):

    Permanent = 0
    Valid = 1
    Expiring = 2
    Expired = 3

@dataclass
class CredentialAPI(DatapointAPI):

    Schema: ClassVar[str] = "Credential"
    Table: ClassVar[str] = "Credential"
    Enums: ClassVar[dict] = {"Kind": CredentialType, "ViewRole": RoleAPI, "EditRole": RoleAPI}

    Defaults: ClassVar[dict] = {"Kind": CredentialType.Password.name}

    Nullable: ClassVar[tuple] = ("ViewRole", "EditRole", "Parent", "ExpiresAt")

    UID: Union[str, None] = None
    Service: Union[str, None] = None
    Name: Union[str, None] = None
    Kind: Union[str, CredentialType, None] = None
    Username: Union[str, None] = None
    Secret: Union[str, None] = None
    Fields: Union[str, None] = None
    ExpiresAt: Union[datetime, None] = None
    Parent: Union[str, None] = None
    Owner: Union[str, None] = None
    ViewRole: Union[str, RoleAPI, None] = None
    EditRole: Union[str, RoleAPI, None] = None
    UsedAt: Union[datetime, None] = None
    UsedBy: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Service: pl.String(),
            self.ID.Name: pl.String(),
            self.ID.Kind: pl.String(),
            self.ID.Username: pl.String(),
            self.ID.Secret: pl.String(),
            self.ID.Fields: pl.String(),
            self.ID.ExpiresAt: pl.Datetime(),
            self.ID.Parent: pl.String(),
            self.ID.Owner: ForeignKey(pl.String, reference=UserAPI.reference()),
            self.ID.ViewRole: pl.String(),
            self.ID.EditRole: pl.String(),
            self.ID.UsedAt: pl.Datetime(),
            self.ID.UsedBy: pl.String(),
            **super().Structure
        }

    @staticmethod
    def pack(value: Any) -> Union[str, None]:
        if value is None: return None
        if isinstance(value, SecretAPI): value = value.Value
        if isinstance(value, dict): value = {name: item.Value if isinstance(item, SecretAPI) else item for name, item in value.items()}
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def unpack(value: Union[str, None]) -> Any:
        if value is None or value == "": return None
        try: return json.loads(value)
        except ValueError: return value

    @staticmethod
    def entry(text: Union[str, None]) -> Any:
        if text is None or not str(text).strip(): return None
        text = str(text).strip()
        try: decoded = json.loads(text)
        except ValueError: return text
        return decoded if isinstance(decoded, dict) else text

    @classmethod
    def spread(cls, value: Union[str, None], name: str) -> dict:
        decoded = cls.unpack(value)
        if decoded is None: return {}
        return dict(decoded) if isinstance(decoded, dict) else {name: decoded}

    def usernames(self) -> dict:
        return self.spread(self.Username, LayoutAPI.username(self.Kind))

    def secrets(self) -> dict:
        return SecretAPI.wrap(self.spread(self.Secret, LayoutAPI.secret(self.Kind)))

    def extras(self) -> dict:
        return self.spread(self.Fields, "Field")

    def values(self, parent: Union[CredentialAPI, None] = None) -> dict:
        inherited = parent.values() if parent is not None else {}
        return {**inherited, **self.extras(), **self.usernames(), **self.secrets()}