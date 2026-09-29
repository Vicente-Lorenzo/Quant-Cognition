import threading
from types import SimpleNamespace
import pytest

import Library.Market
import Library.Portfolio
from Library.Spotware import SpotwareAPI
from Library.Spotware.Client import ClientAPI
from Library.Spotware.Messages import ProtoMessage, ProtoOAAccountDisconnectEvent, ProtoOAAccountsTokenInvalidatedEvent, ProtoOAClientDisconnectEvent
import Library.Spotware.Spotware as Spotware
from Library.Utility.Typing import MISSING, Missing

class Recorder:

    def __init__(self, failures: dict | Missing = MISSING) -> None:
        self.sent, self.failures = [], dict(failures or {})

    def __call__(self, request, timeout=None):
        name = type(request).__name__
        self.sent.append((name, getattr(request, "accessToken", None)))
        if self.failures.get(name):
            self.failures[name] -= 1
            raise RuntimeError("CH_ACCESS_TOKEN_INVALID · Invalid access token")
        return SimpleNamespace(payloadType=0)

def _session_(monkeypatch, *, renew=MISSING, failures=MISSING, account=7):
    api = SpotwareAPI(client_id="cid", client_secret="cs", access_token="old", account_id=account, renew=renew)
    recorder = Recorder(failures)
    monkeypatch.setattr(api, "_send_", recorder)
    monkeypatch.setattr(api, "connected", lambda: True)
    api._connection_ = SimpleNamespace(drop=lambda: None, Connected=True)
    api._connected_event_ = threading.Event()
    return api, recorder

def _wrapped_(payload):
    return ProtoMessage(payloadType=payload.payloadType, payload=payload.SerializeToString())

def test_a_lost_connection_closes_the_gate_and_forgets_the_session(monkeypatch):
    api, _ = _session_(monkeypatch)
    api._ready_.set()
    api._app_authed_ = api._account_authed_ = True
    api._on_disconnected_(None, SimpleNamespace(getErrorMessage=lambda: "Connection lost"))
    assert not api._ready_.is_set() and not api._app_authed_ and not api._account_authed_

def test_a_reconnect_authenticates_again_and_restores_every_subscription(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._established_ = True
    spots = [api._message_("ProtoOASubscribeSpotsReq", symbolId=[1], subscribeToSpotTimestamp=True)]
    api._subscriptions_[id(spots)] = spots
    api._on_connected_(None)
    assert api._ready_.wait(timeout=5)
    assert [name for name, _ in recorder.sent] == ["ProtoOAApplicationAuthReq", "ProtoOAAccountAuthReq", "ProtoOASubscribeSpotsReq"]

def test_a_subscription_that_survived_counts_as_restored(monkeypatch):
    api, recorder = _session_(monkeypatch)
    def survived(request, timeout=None):
        recorder.sent.append((type(request).__name__, None))
        if type(request).__name__ == "ProtoOASubscribeSpotsReq": raise RuntimeError("ALREADY_SUBSCRIBED · An attempt to subscribe twice")
    monkeypatch.setattr(api, "_send_", survived)
    spots = [api._message_("ProtoOASubscribeSpotsReq", symbolId=[1])]
    api._subscriptions_[id(spots)] = spots
    api._restore_()
    assert api._ready_.is_set() and recorder.sent[-1][0] == "ProtoOASubscribeSpotsReq"

def test_any_other_refused_subscription_fails_the_restore(monkeypatch):
    api, _ = _session_(monkeypatch)
    def refused(request, timeout=None):
        if type(request).__name__ == "ProtoOASubscribeSpotsReq": raise RuntimeError("INVALID_REQUEST · Unknown symbol")
    monkeypatch.setattr(api, "_send_", refused)
    monkeypatch.setattr(Spotware.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(Spotware, "blockingCallFromThread", lambda reactor, function, *args, **kwargs: function(*args, **kwargs))
    spots = [api._message_("ProtoOASubscribeSpotsReq", symbolId=[1])]
    api._subscriptions_[id(spots)] = spots
    api._restore_()
    assert not api._ready_.is_set()

def test_the_first_connection_leaves_authentication_to_connect(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._on_connected_(None)
    assert api._connected_event_.is_set() and recorder.sent == []

def test_an_account_disconnect_reauthenticates_only_its_own_account(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._ready_.set()
    api._app_authed_ = api._account_authed_ = True
    api._on_message_(None, _wrapped_(ProtoOAAccountDisconnectEvent(ctidTraderAccountId=99)))
    assert api._ready_.is_set() and recorder.sent == []
    api._on_message_(None, _wrapped_(ProtoOAAccountDisconnectEvent(ctidTraderAccountId=7)))
    assert api._ready_.wait(timeout=5)
    assert [name for name, _ in recorder.sent] == ["ProtoOAAccountAuthReq"]

def test_an_invalidated_token_is_renewed_before_the_account_authenticates(monkeypatch):
    api, recorder = _session_(monkeypatch, renew=lambda: "new")
    api._app_authed_ = api._account_authed_ = True
    api._on_message_(None, _wrapped_(ProtoOAAccountsTokenInvalidatedEvent(ctidTraderAccountIds=[7], reason="Expired")))
    assert api._ready_.wait(timeout=5)
    assert recorder.sent == [("ProtoOAAccountAuthReq", "new")] and api._access_token_ == "new"

def test_a_server_disconnect_only_announces_the_close(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._ready_.set()
    api._on_message_(None, _wrapped_(ProtoOAClientDisconnectEvent(reason="Maintenance")))
    assert api._ready_.is_set() and recorder.sent == []

def test_events_are_ignored_while_stopping(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._ready_.set()
    api._stopping_ = True
    api._on_message_(None, _wrapped_(ProtoOAAccountDisconnectEvent(ctidTraderAccountId=7)))
    assert api._ready_.is_set() and recorder.sent == []

def test_a_refused_account_auth_renews_the_token_once(monkeypatch):
    api, recorder = _session_(monkeypatch, renew=lambda: "new", failures={"ProtoOAAccountAuthReq": 1})
    api._authenticate_()
    assert recorder.sent == [("ProtoOAApplicationAuthReq", None), ("ProtoOAAccountAuthReq", "old"), ("ProtoOAAccountAuthReq", "new")]
    assert api._account_authed_

def test_a_refused_account_auth_without_a_renewer_raises(monkeypatch):
    api, _ = _session_(monkeypatch, failures={"ProtoOAAccountAuthReq": 1})
    with pytest.raises(RuntimeError, match="CH_ACCESS_TOKEN_INVALID"):
        api._authenticate_()
    assert not api._account_authed_

def test_a_failed_restore_drops_the_connection_to_try_again(monkeypatch):
    api, _ = _session_(monkeypatch, failures={"ProtoOAAccountAuthReq": 1})
    dropped, slept = [], []
    api._connection_ = SimpleNamespace(drop=lambda: dropped.append(True), Connected=True)
    monkeypatch.setattr(Spotware.time, "sleep", slept.append)
    monkeypatch.setattr(Spotware, "blockingCallFromThread", lambda reactor, function, *args, **kwargs: function(*args, **kwargs))
    api._restore_()
    assert dropped == [True] and slept == [api._timeout_] and not api._ready_.is_set()

def test_a_request_waits_for_the_session_and_then_gives_up(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._timeout_ = 0.01
    with pytest.raises(ConnectionError, match="Session Operation: Failed · Not restored within"):
        api._request_("ProtoOAVersionReq")
    assert recorder.sent == []

def test_a_clean_stop_logs_the_account_out_and_forgets_subscriptions(monkeypatch):
    api, recorder = _session_(monkeypatch)
    stopped = []
    api._connection_ = SimpleNamespace(stopService=lambda: stopped.append(True), Connected=True)
    monkeypatch.setattr(Spotware.reactor, "running", True, raising=False)
    monkeypatch.setattr(Spotware, "blockingCallFromThread", lambda reactor, function, *args, **kwargs: function(*args, **kwargs))
    api._account_authed_ = api._established_ = True
    spots = ["spots"]
    api._subscriptions_[id(spots)] = spots
    api._disconnect_()
    assert [name for name, _ in recorder.sent] == ["ProtoOAAccountLogoutReq"] and stopped == [True]
    assert api._subscriptions_ == {} and not api._established_ and api._connection_ is None

def test_a_stream_registers_its_subscription_only_while_it_runs(spotware):
    from Library.Spotware.Messages import ProtoOASpotEvent, ProtoOASubscribeSpotsRes, ProtoOAUnsubscribeSpotsRes
    registered = []
    def fire(request, api):
        registered.append(len(api._subscriptions_))
        api.push(ProtoOASpotEvent(ctidTraderAccountId=123, symbolId=1, bid=105000, ask=105002))
        return ProtoOASubscribeSpotsRes()
    spotware._responses_.extend([fire, ProtoOAUnsubscribeSpotsRes()])
    spotware.streaming.ticks(symbols=1, callback=lambda row: registered.append(len(spotware._subscriptions_)), limit=1, timeout=5)
    assert registered == [1, 1] and spotware._subscriptions_ == {}

def test_a_stream_skips_unsubscribing_from_a_dead_session(spotware):
    from Library.Spotware.Messages import ProtoOASpotEvent, ProtoOASubscribeSpotsRes
    def fire(request, api):
        api.push(ProtoOASpotEvent(ctidTraderAccountId=123, symbolId=1, bid=105000, ask=105002))
        api._ready_.clear()
        return ProtoOASubscribeSpotsRes()
    spotware._responses_.append(fire)
    spotware.streaming.ticks(symbols=1, callback=lambda row: None, limit=1, timeout=5)
    assert [type(sent).__name__ for sent in spotware._sent_] == ["ProtoOASubscribeSpotsReq"]

def test_a_failed_authentication_stops_the_connection_it_opened(monkeypatch):
    stopped = []
    class _Connection_:
        Connected = True
        message, payload = ClientAPI.message, ClientAPI.payload
        def __init__(self, host, port, connected, disconnected, received): self.connected = connected
        def startService(self): self.connected(self)
        def stopService(self): stopped.append(True)
    monkeypatch.setattr(Spotware, "ClientAPI", _Connection_)
    monkeypatch.setattr(Spotware, "blockingCallFromThread", lambda reactor, function, *args, **kwargs: function(*args, **kwargs))
    monkeypatch.setattr(Spotware.reactor, "running", True, raising=False)
    api = SpotwareAPI(client_id="cid", client_secret="cs", access_token="bad", account_id=7)
    monkeypatch.setattr(api, "_send_", Recorder({"ProtoOAApplicationAuthReq": 1}))
    with pytest.raises(RuntimeError, match="CH_ACCESS_TOKEN_INVALID"):
        api._connect_()
    assert stopped == [True] and api._connection_ is None and not api._established_

def test_a_restore_for_a_socket_already_replaced_does_nothing(monkeypatch):
    api, recorder = _session_(monkeypatch)
    api._established_, api._generation_ = True, 3
    api._restore_(generation=2)
    assert recorder.sent == [] and not api._ready_.is_set()

def test_a_stop_wakes_every_stream_still_listening(spotware):
    from Library.Spotware.Messages import ProtoOASubscribeSpotsRes
    spotware._responses_.append(ProtoOASubscribeSpotsRes())
    outcome = {}
    def stream():
        try: spotware.streaming.ticks(symbols=1, callback=lambda row: None)
        except Exception as error: outcome["error"] = error
    worker = threading.Thread(target=stream, daemon=True)
    worker.start()
    deadline = threading.Event()
    while not spotware._listeners_ and not deadline.wait(0.01): pass
    spotware._stopping_ = True
    for done in list(spotware._listeners_): done.set()
    worker.join(timeout=5)
    assert not worker.is_alive() and isinstance(outcome.get("error"), ConnectionError)