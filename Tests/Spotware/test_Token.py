from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from Library.Credential import SecretAPI
from Library.Spotware.Token import TokenAPI
from Library.Utility.Datetime import utc_now

class _Response_:

    def __init__(self, status: int, payload) -> None:
        self.status_code, self._payload_ = status, payload

    def json(self):
        if self._payload_ is None: raise ValueError("Not JSON")
        return self._payload_

def _answer_(monkeypatch, status: int, payload) -> list:
    calls = []
    def get(url, params=None, timeout=None):
        calls.append((url, dict(params)))
        return _Response_(status, payload)
    monkeypatch.setattr("Library.Spotware.Token.requests.get", get)
    return calls

def test_the_consent_address_carries_the_application_and_the_redirect():
    query = parse_qs(urlparse(TokenAPI.consent("app-id", "http://127.0.0.1:8765/callback")).query)
    assert query == {"client_id": ["app-id"], "redirect_uri": ["http://127.0.0.1:8765/callback"], "scope": ["trading"]}

def test_an_exchange_returns_both_tokens_and_their_expiry(monkeypatch):
    calls = _answer_(monkeypatch, 200, {"accessToken": "at", "refreshToken": "rt", "expiresIn": 2628000, "tokenType": "bearer"})
    tokens, expires = TokenAPI.exchange("code", client_id=SecretAPI("id"), client_secret=SecretAPI("secret"), redirect_uri="http://127.0.0.1/cb")
    assert tokens["AccessToken"] == "at" and tokens["RefreshToken"] == "rt"
    assert abs((expires - utc_now()) - timedelta(seconds=2628000)) < timedelta(seconds=5) and "ExpiresAt" not in tokens
    assert calls[0][1] == {"grant_type": "authorization_code", "code": "code", "redirect_uri": "http://127.0.0.1/cb", "client_id": "id", "client_secret": "secret"}

def test_a_refused_grant_names_the_error_and_never_the_secret(monkeypatch):
    _answer_(monkeypatch, 200, {"errorCode": "ACCESS_DENIED", "description": "Invalid refresh token"})
    with pytest.raises(RuntimeError) as failure:
        TokenAPI.refresh({"RefreshToken": SecretAPI("rt-secret"), "Identifier": "id", "Secret": SecretAPI("cs-secret")})
    assert "ACCESS_DENIED" in str(failure.value) and "secret" not in str(failure.value).lower()

def test_a_non_json_answer_reports_its_status(monkeypatch):
    _answer_(monkeypatch, 502, None)
    with pytest.raises(RuntimeError, match="HTTP 502"):
        TokenAPI.exchange("code", client_id="id", client_secret="secret", redirect_uri="http://127.0.0.1/cb")

def test_a_refresh_keeps_the_old_refresh_token_when_none_comes_back(monkeypatch):
    calls = _answer_(monkeypatch, 200, {"accessToken": "new", "expiresIn": 60})
    secrets, expires = TokenAPI.refresh({"RefreshToken": SecretAPI("rt"), "Identifier": "id", "Secret": SecretAPI("cs")})
    assert secrets == {"AccessToken": "new"} and expires > utc_now()
    assert calls[0][1]["grant_type"] == "refresh_token" and calls[0][1]["refresh_token"] == "rt"

def test_a_transport_failure_never_carries_the_query_that_holds_the_secret(monkeypatch):
    import requests
    def get(url, params=None, timeout=None): raise requests.ConnectionError(f"Max retries exceeded with url: /apps/token?refresh_token={params['refresh_token']}&client_secret={params['client_secret']}")
    monkeypatch.setattr("Library.Spotware.Token.requests.get", get)
    with pytest.raises(RuntimeError) as failure:
        TokenAPI.refresh({"RefreshToken": SecretAPI("rt-secret"), "Identifier": "id", "Secret": SecretAPI("cs-secret")})
    assert str(failure.value) == "Spotware Token: Failed · ConnectionError" and failure.value.__context__ is None and failure.value.__cause__ is None