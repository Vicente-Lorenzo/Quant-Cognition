import requests

from typing import Union
from urllib.parse import urlencode
from datetime import datetime, timedelta
from ctrader_open_api.endpoints import EndPoints

from Library.Utility.Datetime import utc_now

class TokenAPI:

    @staticmethod
    def plain(value) -> Union[str, None]:
        value = getattr(value, "Value", value)
        return None if value is None else str(value)

    @staticmethod
    def _get_(parameters: dict, timeout: float) -> Union[str, requests.Response]:
        try: return requests.get(EndPoints.TOKEN_URI, params=parameters, timeout=timeout)
        except requests.RequestException as error: return type(error).__name__

    @classmethod
    def _grant_(cls, parameters: dict, timeout: float) -> tuple[dict, datetime]:
        response = cls._get_(parameters, timeout)
        if isinstance(response, str): raise RuntimeError(f"Spotware Token: Failed · {response}")
        try: payload = response.json()
        except ValueError: payload = {}
        if response.status_code != 200 or payload.get("errorCode") or not payload.get("accessToken"):
            raise RuntimeError(f"Spotware Token: Failed · {payload.get('errorCode') or f'HTTP {response.status_code}'} · {payload.get('description') or 'No token returned'}")
        tokens = {"AccessToken": payload["accessToken"]}
        if payload.get("refreshToken"): tokens["RefreshToken"] = payload["refreshToken"]
        return tokens, utc_now() + timedelta(seconds=int(payload.get("expiresIn") or 0))

    @classmethod
    def consent(cls, client_id, redirect_uri: str, scope: str = "trading") -> str:
        return f"{EndPoints.AUTH_URI}?{urlencode({'client_id': cls.plain(client_id), 'redirect_uri': redirect_uri, 'scope': scope})}"

    @classmethod
    def exchange(cls, code: str, *, client_id, client_secret, redirect_uri: str, timeout: float = 30.0) -> tuple[dict, datetime]:
        return cls._grant_({"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "client_id": cls.plain(client_id), "client_secret": cls.plain(client_secret)}, timeout)

    @classmethod
    def refresh(cls, values: dict, timeout: float = 30.0) -> tuple[dict, datetime]:
        return cls._grant_({"grant_type": "refresh_token", "refresh_token": cls.plain(values["RefreshToken"]), "client_id": cls.plain(values["Identifier"]), "client_secret": cls.plain(values["Secret"])}, timeout)