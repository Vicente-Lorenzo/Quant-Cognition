from types import SimpleNamespace

import pytest

import Library.Spotware.Client as Client
from Library.Spotware.Client import ClientAPI, ProtocolAPI
from Library.Spotware.Messages import HEARTBEAT_EVENT, ProtoMessage

class _Loop_:

    def __init__(self, function) -> None:
        self.function, self.running = function, False

    def start(self, interval, now=False) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

@pytest.fixture
def wire(monkeypatch):
    clock, sent, scheduled = [100.0], [], []
    monkeypatch.setattr(Client.task, "LoopingCall", _Loop_)
    monkeypatch.setattr(Client.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(Client.reactor, "callLater", lambda delay, function: scheduled.append(delay) or SimpleNamespace(active=lambda: False, cancel=lambda: None))
    protocol = ProtocolAPI()
    protocol.factory = SimpleNamespace(client=ClientAPI("demo.ctraderapi.com", 5035, rate=3, historical=2))
    protocol.connectionMade()
    protocol.sendString = lambda data: sent.append(ProtoMessage.FromString(data).payloadType)
    return protocol, clock, sent, scheduled

def _request_(historical: bool = False):
    return ClientAPI.message("ProtoOAGetTickDataReq", ctidTraderAccountId=1, symbolId=1, type=1, fromTimestamp=0, toTimestamp=1) if historical else ClientAPI.message("ProtoOAVersionReq")

def _client_(monkeypatch, **kwargs):
    monkeypatch.setattr(Client.task, "LoopingCall", _Loop_)
    return ClientAPI("demo.ctraderapi.com", 5035, silence=75.0, **kwargs)

def test_the_trust_root_is_the_certifi_bundle():
    assert ClientAPI._trust_() is ClientAPI._trust_()
    assert ClientAPI.options("demo.ctraderapi.com") is not None

def test_the_endpoint_verifies_the_server_by_its_name(monkeypatch):
    built = []
    monkeypatch.setattr(Client, "SSL4ClientEndpoint", lambda reactor, host, port, options: built.append(options) or SimpleNamespace())
    ClientAPI("demo.ctraderapi.com", 5035)
    assert built[0]._hostnameASCII == "demo.ctraderapi.com"

def test_a_message_is_built_by_name_and_its_payload_read_by_type():
    request = ClientAPI.message("ProtoOAVersionReq")
    wrapped = ProtoMessage.FromString(ProtoMessage(payload=request.SerializeToString(), payloadType=request.payloadType).SerializeToString())
    decoded = ClientAPI.payload(wrapped)
    assert type(decoded).__name__ == "ProtoOAVersionReq" and decoded == request
    with pytest.raises(KeyError): ClientAPI.message("ProtoOANothingReq")

def test_only_messages_with_a_payload_type_are_known():
    names = ClientAPI._kinds_()[0]
    assert "ProtoOANewOrderReq" in names and "ProtoHeartbeatEvent" in names and "ProtoOASymbol" not in names
    assert len(ClientAPI._kinds_()[1]) == len(names)

def test_every_connection_owns_its_lanes(monkeypatch):
    monkeypatch.setattr(Client.task, "LoopingCall", _Loop_)
    first, second = ProtocolAPI(), ProtocolAPI()
    for protocol in (first, second):
        protocol.factory = SimpleNamespace(client=ClientAPI("demo.ctraderapi.com", 5035))
        protocol.connectionMade()
    first._lanes_[True][0].append("only mine")
    assert first._lanes_[True][0] is not second._lanes_[True][0] and list(second._lanes_[True][0]) == []

def test_a_new_client_starts_disconnected_with_nothing_pending():
    client = ClientAPI("demo.ctraderapi.com", 5035, rate=3)
    assert client.Connected is False and client._pending_ == {}
    assert client.rate(False) == 3 and client.rate(True) == 4

def test_market_history_and_account_history_share_the_historical_lane():
    for name in ("ProtoOAGetTickDataReq", "ProtoOAGetTrendbarsReq", "ProtoOADealListReq", "ProtoOAOrderListReq", "ProtoOACashFlowHistoryListReq"): assert ClientAPI.historical(ClientAPI.message(name).payloadType)
    for name in ("ProtoOAVersionReq", "ProtoOATraderReq", "ProtoOAReconcileReq", "ProtoOANewOrderReq", "ProtoOASymbolsListReq"): assert not ClientAPI.historical(ClientAPI.message(name).payloadType)

def test_the_first_request_leaves_at_once_and_the_rest_are_spaced(wire):
    protocol, clock, sent, scheduled = wire
    for _ in range(3): protocol.send(_request_(), "m")
    assert len(sent) == 1 and scheduled[-1] == pytest.approx(1 / 3)
    clock[0] += 1 / 3
    protocol._drain_()
    assert len(sent) == 2
    clock[0] += 1 / 3
    protocol._drain_()
    assert len(sent) == 3

def test_a_burst_never_leaves_faster_than_the_spacing(wire):
    protocol, clock, sent, scheduled = wire
    for _ in range(3): protocol.send(_request_())
    clock[0] += 0.2
    protocol._drain_()
    assert len(sent) == 1 and scheduled[-1] == pytest.approx(1 / 3 - 0.2)

def test_the_historical_lane_never_holds_the_other_back(wire):
    protocol, clock, sent, scheduled = wire
    for _ in range(3): protocol.send(_request_(historical=True))
    protocol.send(_request_())
    assert sent == [_request_(historical=True).payloadType, _request_().payloadType]

def test_no_window_ever_carries_more_than_the_rate(wire):
    protocol, clock, sent, scheduled = wire
    stamps = []
    protocol.sendString = lambda data: stamps.append(clock[0])
    for step in range(40):
        clock[0] = 100 + step * 0.125
        if step < 10: protocol.send(_request_(historical=True))
        else: protocol._drain_()
    assert stamps == [100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5]
    assert all(sum(start <= stamp < start + 1 for stamp in stamps) <= 2 for start in stamps)

def test_a_canceled_request_is_dropped(wire):
    protocol, clock, sent, scheduled = wire
    protocol.send(_request_(), canceled=lambda: True)
    protocol.send(_request_())
    assert len(sent) == 1

def test_a_heartbeat_skips_the_lanes(wire):
    protocol, clock, sent, scheduled = wire
    for _ in range(4): protocol.send(_request_())
    protocol.heartbeat()
    assert len(sent) == 2 and sent[-1] == HEARTBEAT_EVENT

def test_a_server_heartbeat_is_answered_and_passed_on(wire):
    protocol, clock, sent, scheduled = wire
    heard = []
    protocol.factory.client._on_received_ = lambda client, message: heard.append(message.payloadType)
    protocol.stringReceived(ProtoMessage(payloadType=HEARTBEAT_EVENT).SerializeToString())
    assert sent == [HEARTBEAT_EVENT] and heard == [HEARTBEAT_EVENT]

def test_a_quiet_connection_sends_a_heartbeat_after_twenty_seconds(wire):
    protocol, clock, sent, scheduled = wire
    clock[0] += 20
    protocol._beat_()
    assert sent == []
    clock[0] += 0.5
    protocol._beat_()
    assert sent == [HEARTBEAT_EVENT]

def test_a_lost_connection_cancels_the_pending_drain(wire):
    protocol, clock, sent, scheduled = wire
    canceled = []
    protocol._drain_call_ = SimpleNamespace(active=lambda: True, cancel=lambda: canceled.append(True))
    protocol.connectionLost(None)
    assert canceled == [True] and protocol._drain_call_ is None and not protocol._pulse_.running

def test_a_response_resolves_its_request_by_key(monkeypatch):
    from twisted.internet import defer
    client = _client_(monkeypatch)
    pending, answers = defer.Deferred(), []
    pending.addCallback(answers.append)
    client._pending_["key"] = pending
    client._received_(ProtoMessage(payloadType=HEARTBEAT_EVENT, clientMsgId="key"))
    assert client._pending_ == {} and answers[0].clientMsgId == "key"

def test_a_lost_connection_fails_every_request_in_flight_at_once(monkeypatch):
    from twisted.internet import defer
    lost = []
    client = _client_(monkeypatch, disconnected=lambda client, reason: lost.append(reason))
    pending = defer.Deferred()
    client._pending_["m"] = pending
    failures = []
    pending.addErrback(lambda failure: failures.append(failure))
    client._disconnected_(SimpleNamespace(getErrorMessage=lambda: "lost"))
    assert client._pending_ == {} and failures[0].check(ConnectionError) and len(lost) == 1

def test_the_watchdog_drops_a_silent_connection_only(monkeypatch):
    connected = []
    client = _client_(monkeypatch, connected=connected.append)
    aborted = []
    client._connected_(SimpleNamespace(transport=SimpleNamespace(abortConnection=lambda: aborted.append(True))))
    assert connected == [client] and client.Connected
    client._check_()
    assert aborted == []
    client._heard_ -= 80
    client._check_()
    assert aborted == [True]

def test_every_message_counts_as_heard(monkeypatch):
    client = _client_(monkeypatch)
    aborted = []
    client._connected_(SimpleNamespace(transport=SimpleNamespace(abortConnection=lambda: aborted.append(True))))
    client._heard_ -= 80
    client._received_(SimpleNamespace(clientMsgId=None))
    client._check_()
    assert aborted == [] and 0 <= Client.time.monotonic() - client._heard_ < 1

def test_a_stop_stops_even_while_disconnected(monkeypatch):
    client = _client_(monkeypatch)
    stopped = []
    monkeypatch.setattr(Client.ClientService, "stopService", lambda self: stopped.append(self))
    client.stopService()
    assert stopped == [client] and client.Connected is False

def test_a_drop_without_a_connection_does_nothing(monkeypatch):
    _client_(monkeypatch).drop()