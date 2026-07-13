from __future__ import annotations

from typing import Union
from typing_extensions import Self

from flask_login import AnonymousUserMixin

from Library.Auth.Role import RoleAPI
from Library.Auth.User import UserAPI

class IdentityAPI:

    def __init__(self, *,
                 username: str,
                 email: Union[str, None] = None,
                 name: Union[str, None] = None,
                 role: Union[str, int, RoleAPI] = RoleAPI.Viewer,
                 provider: Union[str, None] = None,
                 active: bool = True) -> None:
        self.Username = username
        self.Email = email
        self.Name = name
        self.Role = RoleAPI.coerce(role, RoleAPI.Viewer)
        self.Provider = provider
        self._active_ = active

    @property
    def is_authenticated(self) -> bool: return True

    @property
    def is_active(self) -> bool: return self._active_

    @property
    def is_anonymous(self) -> bool: return False

    def get_id(self) -> str: return self.Username

    def grants(self, required: Union[str, int, RoleAPI]) -> bool: return self.Role.grants(required)

    @classmethod
    def of(cls, user: UserAPI) -> Self:
        return cls(username=user.UID, email=user.Email, name=user.Name, role=user.authority(), provider=user.Provider, active=bool(user.Active))

class AnonymousAPI(AnonymousUserMixin):

    Username: Union[str, None] = None
    Email: Union[str, None] = None
    Name: Union[str, None] = None
    Role: RoleAPI = RoleAPI.Public

    def grants(self, required: Union[str, int, RoleAPI]) -> bool: return RoleAPI.Public.grants(required)