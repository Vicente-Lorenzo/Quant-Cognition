from types import SimpleNamespace

import pytest
from ctrader_open_api import Protobuf, TcpProtocol
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage

import Library.Spotware.Client as Client
from Library.Spotware.Client import ClientAPI, ProtocolAPI

@pytest.fixture
def wire(monkeypatch):
    clock, sent, scheduled = [100.0], [], []
    monkeypatch.setattr(TcpProtocol, "connectionMade", lambda self: None)
    monkeypatch.setattr(Client.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(Client.reactor, "callLater", lambda delay, function: scheduled.append(delay) or SimpleNamespace(active=lambda: False, cancel=lambda: None))
    protocol = ProtocolAPI()
    protocol.factory = SimpleNamespace(client=ClientAPI("demo.ctraderapi.com", 5035, rate=3, historical=2))
    protocol.connectionMade()
    protocol.sendString = lambda data: sent.append(ProtoMessage.FromString(data).payloadType)
    return protocol, clock, sent, scheduled

def _request_(historical: bool = False):
    return Protobuf.get("ProtoOAGetTickDataReq", ctidTraderAccountId=1, symbolId=1, type=1, fromTimestamp=0, toTimestamp=1) if historical else Protobuf.get("ProtoOAVersionReq")

def test_the_trust_root_is_the_certifi_bundle():
    assert ClientAPI._trust_() is ClientAPI._trust_()
    assert ClientAPI.options("demo.ctraderapi.com") is not None

def test_the_endpoint_verifies_the_server_by_its_name(monkeypatch):
    built = []
    monkeypatch.setattr(Client, "SSL4ClientEndpoint", lambda reactor, host, port, options: built.append(options) or SimpleNamespace())
    ClientAPI("demo.ctraderapi.com", 5035)
    assert built[0]._hostnameASCII == "demo.ctraderapi.com"

def test_every_connection_owns_its_send_queue(monkeypatch):
    monkeypatch.setattr(TcpProtocol, "connectionMade", lambda self: None)
    first, second = ProtocolAPI(), ProtocolAPI()
    first.connectionMade()
    second.connectionMade()
    first._send_queue.append("only mine")
    assert first._send_queue is not second._send_queue and list(second._send_queue) == []
    assert first._lanes_[True][0] is not second._lanes_[True][0]
    assert list(TcpProtocol._send_queue) == []

def test_a_client_keeps_the_vendor_state_it_relies_on():
    client = ClientAPI("demo.ctraderapi.com", 5035, rate=3)
    assert client.numberOfMessagesToSendPerSecond == 3 and client.isConnected is False
    assert client._responseDeferreds == {}
    assert client.rate(False) == 3 and client.rate(True) == 4

def test_only_ticks_and_trendbars_are_historical():
    assert ClientAPI.historical(_request_(historical=True).payloadType)
    assert ClientAPI.historical(Protobuf.get("ProtoOAGetTrendbarsReq").payloadType)
    assert not ClientAPI.historical(_request_().payloadType) and not ClientAPI.historical(Protobuf.get("ProtoOADealListReq").payloadType)

def test_the_first_request_leaves_at_once_and_the_rest_are_spaced(wire):
    protocol, clock, sent, scheduled = wire
    for _ in range(3): protocol.send(_request_(), clientMsgId="m")
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
    protocol.send(_request_(), isCanceled=lambda: True)
    protocol.send(_request_())
    assert len(sent) == 1

def test_a_heartbeat_skips_the_lanes(wire):
    protocol, clock, sent, scheduled = wire
    for _ in range(4): protocol.send(_request_())
    protocol.heartbeat()
    assert len(sent) == 2 and sent[-1] == Protobuf.get("ProtoHeartbeatEvent").payloadType

def test_a_lost_connection_cancels_the_pending_drain(wire, monkeypatch):
    protocol, clock, sent, scheduled = wire
    canceled = []
    monkeypatch.setattr(TcpProtocol, "connectionLost", lambda self, reason: None)
    protocol._drain_call_ = SimpleNamespace(active=lambda: True, cancel=lambda: canceled.append(True))
    protocol.connectionLost(None)
    assert canceled == [True] and protocol._drain_call_ is None

def _client_(monkeypatch):
    monkeypatch.setattr(Client.task, "LoopingCall", lambda function: SimpleNamespace(start=lambda interval, now=False: None, running=True, stop=lambda: None))
    return ClientAPI("demo.ctraderapi.com", 5035, silence=75.0)

def test_a_lost_connection_fails_every_request_in_flight_at_once(monkeypatch):
    from twisted.internet import defer
    client = _client_(monkeypatch)
    pending = defer.Deferred()
    client._responseDeferreds["m"] = pending
    failures = []
    pending.addErrback(lambda failure: failures.append(failure))
    client._disconnected(SimpleNamespace(getErrorMessage=lambda: "lost"))
    assert client._responseDeferreds == {} and failures[0].check(ConnectionError)

def test_the_watchdog_drops_a_silent_connection_only(monkeypatch):
    client = _client_(monkeypatch)
    aborted = []
    client._connected(SimpleNamespace(transport=SimpleNamespace(abortConnection=lambda: aborted.append(True))))
    client._check_()
    assert aborted == []
    client._heard_ -= 80
    client._check_()
    assert aborted == [True]

def test_every_message_counts_as_heard(monkeypatch):
    client = _client_(monkeypatch)
    aborted = []
    client._connected(SimpleNamespace(transport=SimpleNamespace(abortConnection=lambda: aborted.append(True))))
    client._heard_ -= 80
    client._received(SimpleNamespace(clientMsgId=None))
    client._check_()
    assert aborted == [] and 0 <= Client.time.monotonic() - client._heard_ < 1

def test_a_stop_stops_even_while_disconnected(monkeypatch):
    client = _client_(monkeypatch)
    stopped = []
    monkeypatch.setattr(Client.ClientService, "stopService", lambda self: stopped.append(self))
    client.stopService()
    assert stopped == [client] and client.isConnected is False

def test_a_drop_without_a_connection_does_nothing(monkeypatch):
    _client_(monkeypatch).drop()