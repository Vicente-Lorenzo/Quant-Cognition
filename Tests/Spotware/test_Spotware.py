import pytest
import Library.Market
import Library.Portfolio
from Library.Spotware import SpotwareAPI, UniverseAPI, MarketAPI, StreamingAPI, PortfolioAPI
from ctrader_open_api.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthRes,
    ProtoOAAccountAuthRes,
    ProtoOAErrorRes
)
def test_initialization_defaults():
    api = SpotwareAPI(client_id="cid", client_secret="csec")
    assert api._client_id_ == "cid"
    assert api._client_secret_ == "csec"
    assert api._access_token_ is None
    assert api._account_id_ is None
    assert api._host_ == "demo.ctraderapi.com"
    assert api._port_ == 5035
    assert api.connected() is False
    assert api.disconnected() is True
def test_initialization_live_environment():
    api = SpotwareAPI(client_id="cid", client_secret="csec", environment="live")
    assert api._host_ == "live.ctraderapi.com"
def test_initialization_custom_host():
    api = SpotwareAPI(client_id="cid", client_secret="csec", host="custom.example.com", port=6000)
    assert api._host_ == "custom.example.com"
    assert api._port_ == 6000
def test_sub_apis_are_bound():
    api = SpotwareAPI(client_id="cid", client_secret="csec")
    assert isinstance(api.universe, UniverseAPI)
    assert isinstance(api.market, MarketAPI)
    assert isinstance(api.streaming, StreamingAPI)
    assert isinstance(api.portfolio, PortfolioAPI)
    assert api.universe._api_ is api
    assert api.market._api_ is api
    assert api.streaming._api_ is api
    assert api.portfolio._api_ is api
def test_authenticate_sends_application_auth(spotware):
    spotware._responses_.append(ProtoOAApplicationAuthRes())
    spotware._responses_.append(ProtoOAAccountAuthRes())
    spotware._app_authed_ = False
    spotware._account_authed_ = False
    spotware._authenticate_()
    assert spotware._app_authed_ is True
    assert spotware._account_authed_ is True
    assert type(spotware._sent_[0]).__name__ == "ProtoOAApplicationAuthReq"
    assert spotware._sent_[0].clientId == "test_client"
    assert spotware._sent_[0].clientSecret == "test_secret"
    assert type(spotware._sent_[1]).__name__ == "ProtoOAAccountAuthReq"
    assert spotware._sent_[1].ctidTraderAccountId == 123
    assert spotware._sent_[1].accessToken == "test_token"
def test_authenticate_skips_account_without_credentials(spotware):
    spotware._access_token_ = None
    spotware._account_id_ = None
    spotware._app_authed_ = False
    spotware._account_authed_ = False
    spotware._responses_.append(ProtoOAApplicationAuthRes())
    spotware._authenticate_()
    assert spotware._app_authed_ is True
    assert spotware._account_authed_ is False
    assert len(spotware._sent_) == 1
@pytest.mark.skip(reason="Hangs during execution")
def test_send_raises_on_error_payload():
    from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
    class _Reactor:
        pass
    api = SpotwareAPI(client_id="x", client_secret="y")
    api._reactor_ = _Reactor()
    class _Conn:
        def send(self, request, responseTimeoutInSeconds=None):
            pass
    api._connection_ = _Conn()
    err = ProtoOAErrorRes(errorCode="BAD", description="nope")
    wrapped = ProtoMessage(payloadType=err.payloadType, payload=err.SerializeToString())
    from twisted.internet import threads as _threads
    original = _threads.blockingCallFromThread
    _threads.blockingCallFromThread = lambda reactor, f, *args, **kwargs: wrapped
    try:
        with pytest.raises(RuntimeError) as exc:
            api._send_(object())
        assert "BAD" in str(exc.value)
        assert "nope" in str(exc.value)
    finally:
        _threads.blockingCallFromThread = original
def test_subscribe_and_unsubscribe_handlers(spotware):
    received = []
    def handler(msg): received.append(msg)
    spotware._subscribe_(handler)
    assert handler in spotware._subscribers_
    spotware._unsubscribe_(handler)
    assert handler not in spotware._subscribers_
def test_on_message_dispatches_to_all_subscribers(spotware):
    calls = []
    spotware._subscribe_(lambda m: calls.append(("a", m)))
    spotware._subscribe_(lambda m: calls.append(("b", m)))
    spotware._on_message_(spotware._connection_, "dummy")
    assert calls == [("a", "dummy"), ("b", "dummy")]
def test_on_message_swallows_subscriber_exceptions(spotware):
    calls = []
    def bad(m): raise ValueError("boom")
    def good(m): calls.append(m)
    spotware._subscribe_(bad)
    spotware._subscribe_(good)
    spotware._on_message_(spotware._connection_, "dummy")
    assert calls == ["dummy"]