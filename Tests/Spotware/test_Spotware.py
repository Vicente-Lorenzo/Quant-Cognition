import pytest
from datetime import datetime, timedelta, timezone
import Library.Market
import Library.Portfolio
from Library.Portfolio.Order import OrderStatus, TimeInForce
from Library.Spotware import SpotwareAPI, UniverseAPI, MarketAPI, StreamingAPI, PortfolioAPI
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import ProtoOAOrder, ProtoOAOrderType, ProtoOAQuoteType, ProtoOATimeInForce, ProtoOATradeSide, ProtoOATrader
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
def test_send_raises_on_error_payload(monkeypatch):
    api = SpotwareAPI(client_id="x", client_secret="y")
    api._connection_ = type("Connection", (), {"send": None})()
    error = ProtoOAErrorRes(errorCode="BAD", description="nope")
    wrapped = ProtoMessage(payloadType=error.payloadType, payload=error.SerializeToString())
    monkeypatch.setattr("Library.Spotware.Spotware.blockingCallFromThread", lambda reactor, function, *args, **kwargs: wrapped)
    with pytest.raises(RuntimeError, match="BAD · nope"):
        api._send_(object())
def test_disconnect_does_not_block_without_a_running_reactor():
    api = SpotwareAPI(client_id="x", client_secret="y")
    api._connection_ = object()
    api.disconnect()
    assert api.disconnected() is True
def test_message_stamps_the_account_only_where_the_field_exists(spotware):
    assert spotware._message_("ProtoOATraderReq").ctidTraderAccountId == 123
    assert spotware._message_("ProtoOAApplicationAuthReq", clientId="c", clientSecret="s").clientId == "c"
def test_code_resolves_wire_names_framework_members_and_integers():
    assert SpotwareAPI._code_(ProtoOAQuoteType, "BID") == 1
    assert SpotwareAPI._code_(ProtoOAQuoteType, "ask") == 2
    assert SpotwareAPI._code_(ProtoOAQuoteType, 2) == 2
    assert SpotwareAPI._code_(ProtoOAOrderType, "StopLimit") == 6
    assert SpotwareAPI._code_(ProtoOATimeInForce, TimeInForce.GoodTillCancel) == 2
    with pytest.raises(ValueError, match="Not a member"):
        SpotwareAPI._code_(ProtoOAQuoteType, "Mid")
def test_code_refuses_a_bool_instead_of_sending_it_as_a_member():
    with pytest.raises(ValueError, match="Not a member"):
        SpotwareAPI._code_(ProtoOATradeSide, True)
    with pytest.raises(ValueError, match="Not a member"):
        SpotwareAPI._code_(ProtoOATradeSide, False)
def test_optional_decodes_only_when_a_decoder_is_supplied():
    trader = ProtoOATrader(moneyDigits=3)
    assert SpotwareAPI._optional_(trader, "moneyDigits") == 3
    assert SpotwareAPI._optional_(trader, "moneyDigits", lambda digits: digits * 2) == 6
    assert SpotwareAPI._optional_(ProtoOATrader(), "moneyDigits", lambda digits: digits * 2) is None
def test_named_strips_the_shared_prefix_and_matches_framework_enums():
    order = ProtoOAOrder(orderType=5, orderStatus=5)
    assert SpotwareAPI._named_(order, "orderType") == "MarketRange"
    assert OrderStatus[SpotwareAPI._named_(order, "orderStatus")] is OrderStatus.Cancelled
    assert SpotwareAPI._named_(order, "timeInForce") is None
def test_epoch_is_exact_integer_milliseconds_in_utc():
    assert SpotwareAPI._epoch_(datetime(2020, 1, 1)) == 1577836800000
    assert SpotwareAPI._epoch_(datetime(2020, 1, 1, tzinfo=timezone.utc)) == 1577836800000
    assert SpotwareAPI._epoch_(datetime(2020, 1, 1, 1, tzinfo=timezone(timedelta(hours=1)))) == 1577836800000
    assert SpotwareAPI._epoch_(datetime(2020, 1, 1, 0, 0, 0, 123000)) == 1577836800123
    assert SpotwareAPI._stamp_(1577836800123) == datetime(2020, 1, 1, 0, 0, 0, 123000)
    assert SpotwareAPI._stamp_(0) is None
def test_money_honours_zero_money_digits():
    assert SpotwareAPI._money_(ProtoOATrader(moneyDigits=0)) == 1
    assert SpotwareAPI._money_(ProtoOATrader(moneyDigits=8)) == 10 ** 8
    assert SpotwareAPI._money_(ProtoOATrader()) == 100
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