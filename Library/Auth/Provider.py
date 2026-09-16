from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Union, TYPE_CHECKING

from Library.Auth.Password import PasswordAPI
from Library.Auth.Role import RoleAPI
from Library.Auth.User import UserAPI
from Library.Utility.Typing import MISSING

if TYPE_CHECKING:
    from flask import Request
    from Library.Auth.Auth import AuthAPI

class AuthProviderAPI(ABC):

    Name: str = "Provider"

    def __init__(self, auth: AuthAPI) -> None:
        self._auth_ = auth

    @abstractmethod
    def authenticate(self, **credentials) -> Union[UserAPI, None]: ...

    def identify(self, request: Request) -> Union[UserAPI, None]:
        return None

    @staticmethod
    def _claims_(token: str, jwks: str, audience: Union[str, None], issuer: Union[str, None] = MISSING) -> Union[dict, None]:
        try:
            import jwt
            from jwt import PyJWKClient
        except ImportError:
            return None
        try:
            key = PyJWKClient(jwks).get_signing_key_from_jwt(token).key
            return jwt.decode(token, key, algorithms=["RS256"], audience=audience, issuer=None if issuer is MISSING else issuer)
        except Exception:
            return None

class LocalAuthProviderAPI(AuthProviderAPI):

    Name: str = "Local"

    def authenticate(self, *, username: Union[str, None] = None, password: Union[str, None] = None, **_) -> Union[UserAPI, None]:
        if not username or not password: return None
        user = self._auth_.find(username)
        if user is None or not user.Active or not user.Password: return None
        if not PasswordAPI.verify(user.Password, password): return None
        if PasswordAPI.stale(user.Password): self._auth_.password(user.UID, password)
        return user

class CloudflareAuthProviderAPI(AuthProviderAPI):

    Name: str = "Cloudflare"

    _EMAIL_: str = "Cf-Access-Authenticated-User-Email"
    _TOKEN_: str = "Cf-Access-Jwt-Assertion"

    def __init__(self, auth: AuthAPI, *, team: Union[str, None] = None, audience: Union[str, None] = None, trust: bool = False) -> None:
        super().__init__(auth)
        self._team_ = team
        self._audience_ = audience
        self._trust_ = trust

    def authenticate(self, **_) -> Union[UserAPI, None]:
        return None

    def identify(self, request: Request) -> Union[UserAPI, None]:
        email = request.headers.get(self._EMAIL_)
        token = request.headers.get(self._TOKEN_)
        if not email: return None
        if not self._trust_ and not self._verify_(token, email): return None
        return self._auth_.provision(email=email, provider=self.Name, role=RoleAPI.Viewer)

    def _verify_(self, token: Union[str, None], email: str) -> bool:
        if not token or not self._team_ or not self._audience_: return False
        claims = self._claims_(token, f"https://{self._team_}.cloudflareaccess.com/cdn-cgi/access/certs", self._audience_)
        return claims is not None and str(claims.get("email", "")).lower() == email.lower()

class OIDCAuthProviderAPI(AuthProviderAPI):

    Name: str = "OIDC"

    def __init__(self, auth: AuthAPI, *, issuer: Union[str, None] = None, audience: Union[str, None] = None) -> None:
        super().__init__(auth)
        self._issuer_ = issuer
        self._audience_ = audience

    def authenticate(self, *, token: Union[str, None] = None, **_) -> Union[UserAPI, None]:
        if not token or not self._issuer_: return None
        claims = self._claims_(token, f"{self._issuer_.rstrip('/')}/.well-known/jwks.json", self._audience_, self._issuer_)
        if claims is None: return None
        email = claims.get("email")
        if not email: return None
        return self._auth_.provision(email=email, provider=self.Name, name=claims.get("name"), role=RoleAPI.Viewer)