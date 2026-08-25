from __future__ import annotations

import secrets
from datetime import datetime
from typing import Union, TYPE_CHECKING

from Library.Auth.Identity import IdentityAPI, AnonymousAPI
from Library.Auth.Password import PasswordAPI
from Library.Auth.Provider import AuthProviderAPI, LocalAuthProviderAPI
from Library.Auth.Role import RoleAPI
from Library.Auth.User import UserAPI
from Library.Database import PostgresDatabaseAPI, QueryAPI

if TYPE_CHECKING:
    from flask import Flask, Request
    from flask_login import LoginManager

class AuthAPI:

    Schema: str = "Auth"
    Table: str = "User"

    def __init__(self, *,
                 database: str = "Quant",
                 providers: Union[list[AuthProviderAPI], None] = None,
                 secret: Union[str, None] = None,
                 secure: bool = True) -> None:
        self._database_ = database
        self._secret_ = secret or secrets.token_hex(32)
        self._secure_ = secure
        self._providers_ = providers if providers is not None else [LocalAuthProviderAPI(self)]
        self._manager_ = None

    def install(self, server: Flask, *, login: str = "/login") -> LoginManager:
        from flask_login import LoginManager
        from werkzeug.middleware.proxy_fix import ProxyFix
        server.secret_key = self._secret_
        server.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=self._secure_)
        server.wsgi_app = ProxyFix(server.wsgi_app, x_for=1, x_proto=1, x_host=1)
        manager = LoginManager()
        manager.init_app(server)
        manager.login_view = login
        manager.anonymous_user = AnonymousAPI
        manager.user_loader(self.identity)
        manager.request_loader(self._sso_)
        self._manager_ = manager
        return manager

    def _select_(self, condition: str, parameters: dict) -> Union[UserAPI, None]:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            frame = db.select(schema=self.Schema, table=self.Table, condition=condition, parameters=parameters, limit=1, legacy=False)
        if frame.is_empty(): return None
        return UserAPI.parse(frame.row(0, named=True))

    def _update_(self, assignment: str, parameters: dict) -> None:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            sql = f'UPDATE {db._target_(self.Schema, self.Table)} SET {assignment} WHERE "UID" = :key:'
            db.execute(QueryAPI(sql), [parameters])

    def find(self, username: str) -> Union[UserAPI, None]:
        return self._select_('"UID" = :key:', {"key": username}) if username else None

    def locate(self, email: str) -> Union[UserAPI, None]:
        return self._select_('"Email" = :key:', {"key": email}) if email else None

    def identity(self, username: str) -> Union[IdentityAPI, None]:
        user = self.find(username)
        if user is None or not user.Active: return None
        return IdentityAPI.of(user)

    def touch(self, username: str) -> None:
        self._update_('"LastLogin" = :ts:', {"ts": datetime.now(), "key": username})

    def password(self, username: str, password: str) -> None:
        self._update_('"Password" = :hash:', {"hash": PasswordAPI.hash(password), "key": username})

    def authenticate(self, **credentials) -> Union[IdentityAPI, None]:
        for provider in self._providers_:
            user = provider.authenticate(**credentials)
            if user is not None:
                self.touch(user.UID)
                return IdentityAPI.of(user)
        return None

    def _sso_(self, request: Request) -> Union[IdentityAPI, None]:
        for provider in self._providers_:
            user = provider.identify(request)
            if user is not None:
                self.touch(user.UID)
                return IdentityAPI.of(user)
        return None

    def login(self, **credentials) -> Union[IdentityAPI, None]:
        from flask_login import login_user
        identity = self.authenticate(**credentials)
        if identity is not None: login_user(identity)
        return identity

    def logout(self) -> None:
        from flask_login import logout_user
        logout_user()

    def provision(self, *, email: str, provider: str, name: Union[str, None] = None, role: Union[str, int, RoleAPI] = RoleAPI.Viewer) -> Union[UserAPI, None]:
        user = self.locate(email) or self.find(email)
        if user is not None: return user
        return self.create(username=email, email=email, name=name, role=role, provider=provider)

    def create(self, *,
               username: str,
               email: Union[str, None] = None,
               name: Union[str, None] = None,
               password: Union[str, None] = None,
               role: Union[str, int, RoleAPI] = RoleAPI.Viewer,
               provider: str = "Local",
               active: bool = True) -> UserAPI:
        with PostgresDatabaseAPI.attach(database=self._database_) as db:
            user = UserAPI(db=db, UID=username, Email=email, Name=name,
                           Password=PasswordAPI.hash(password) if password else None,
                           Role=RoleAPI.coerce(role, RoleAPI.Viewer), Provider=provider,
                           Active=active)
            user.save(by=provider)
        return user