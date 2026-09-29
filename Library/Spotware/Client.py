import time
import certifi

from pathlib import Path
from collections import deque
from functools import lru_cache
from typing import Callable, Union
from twisted.internet import defer, reactor, ssl, task
from twisted.internet.protocol import ClientFactory
from twisted.protocols.basic import Int32StringReceiver
from twisted.application.internet import ClientService
from twisted.internet.endpoints import SSL4ClientEndpoint

from Library.Spotware import Messages
from Library.Spotware.Messages import HEARTBEAT_EVENT, PROTO_OA_CASH_FLOW_HISTORY_LIST_REQ, PROTO_OA_DEAL_LIST_REQ, PROTO_OA_GET_TICKDATA_REQ, PROTO_OA_GET_TRENDBARS_REQ, PROTO_OA_ORDER_LIST_REQ, ProtoHeartbeatEvent, ProtoMessage
from Library.Utility.IO import read_text
from Library.Utility.Math import EPSILON
from Library.Utility.Typing import MISSING, Missing

class ProtocolAPI(Int32StringReceiver):

    MAX_LENGTH = 15_000_000

    def connectionMade(self) -> None:
        self._lanes_ = {True: (deque(), deque()), False: (deque(), deque())}
        self._drain_call_, self._sent_ = None, time.monotonic()
        self._pulse_ = task.LoopingCall(self._beat_)
        self._pulse_.start(1, now=False)
        self.factory.client._connected_(self)

    def connectionLost(self, reason) -> None:
        if self._drain_call_ is not None and self._drain_call_.active(): self._drain_call_.cancel()
        if self._pulse_.running: self._pulse_.stop()
        self._drain_call_ = None
        self.factory.client._disconnected_(reason)

    def _write_(self, data: bytes) -> None:
        self.sendString(data)
        self._sent_ = time.monotonic()

    def _beat_(self) -> None:
        if time.monotonic() - self._sent_ > 20: self.heartbeat()

    def _drain_(self) -> None:
        if self._drain_call_ is not None and self._drain_call_.active(): self._drain_call_.cancel()
        self._drain_call_, now, wait = None, time.monotonic(), None
        for historical, (queue, window) in self._lanes_.items():
            rate = self.factory.client.rate(historical)
            while window and now - window[0] >= 1: window.popleft()
            while queue and len(window) < rate and (not window or now - window[-1] >= 1 / rate - EPSILON):
                canceled, data = queue.popleft()
                if canceled is not None and canceled(): continue
                self._write_(data)
                window.append(now)
            if queue:
                ready = max(window[-1] + 1 / rate, window[0] + 1 if len(window) >= rate else 0)
                wait = ready - now if wait is None else min(wait, ready - now)
        if wait is not None: self._drain_call_ = reactor.callLater(max(wait, 0.001), self._drain_)

    def heartbeat(self) -> None:
        self._write_(ProtoMessage(payload=ProtoHeartbeatEvent().SerializeToString(), payloadType=HEARTBEAT_EVENT).SerializeToString())

    def send(self, message, key: Union[str, None] = None, canceled: Union[Callable, None] = None) -> None:
        data = ProtoMessage(payload=message.SerializeToString(), clientMsgId=key, payloadType=message.payloadType).SerializeToString()
        self._lanes_[ClientAPI.historical(message.payloadType)][0].append((canceled, data))
        self._drain_()

    def stringReceived(self, data: bytes) -> None:
        message = ProtoMessage.FromString(data)
        if message.payloadType == HEARTBEAT_EVENT: self.heartbeat()
        self.factory.client._received_(message)

class ClientAPI(ClientService):

    def __init__(self, host: str, port: int, *,
                 connected: Union[Callable, Missing] = MISSING,
                 disconnected: Union[Callable, Missing] = MISSING,
                 received: Union[Callable, Missing] = MISSING,
                 rate: int = 45,
                 historical: int = 4,
                 silence: float = 75.0) -> None:
        factory = ClientFactory.forProtocol(ProtocolAPI)
        factory.client = self
        super().__init__(SSL4ClientEndpoint(reactor, host, port, self.options(host)), factory)
        self._on_connected_, self._on_disconnected_, self._on_received_ = connected, disconnected, received
        self._rate_, self._historical_, self._silence_ = rate, historical, silence
        self._protocol_, self._watch_, self._heard_ = None, None, time.monotonic()
        self._pending_: dict = {}
        self.Connected: bool = False

    def _connected_(self, protocol) -> None:
        self._protocol_, self._heard_, self.Connected = protocol, time.monotonic(), True
        self._watch_ = task.LoopingCall(self._check_)
        self._watch_.start(self._silence_ / 5, now=False)
        if self._on_connected_ is not MISSING: self._on_connected_(self)

    def _disconnected_(self, reason) -> None:
        pending = list(self._pending_.values())
        if self._watch_ is not None and self._watch_.running: self._watch_.stop()
        self._protocol_, self._watch_, self.Connected = None, None, False
        self._pending_.clear()
        if self._on_disconnected_ is not MISSING: self._on_disconnected_(self, reason)
        for deferred in pending:
            if not deferred.called: deferred.errback(ConnectionError("Request Operation: Failed · Connection lost in flight"))

    def _received_(self, message) -> None:
        self._heard_ = time.monotonic()
        if self._on_received_ is not MISSING: self._on_received_(self, message)
        deferred = self._pending_.pop(message.clientMsgId, None)
        if deferred is not None: deferred.callback(message)

    def _check_(self) -> None:
        if time.monotonic() - self._heard_ > self._silence_: self.drop()

    def _forget_(self, failure, key: str):
        self._pending_.pop(key, None)
        return failure

    def _cancel_(self, deferred) -> None:
        self._pending_.pop(str(id(deferred)), None)

    @staticmethod
    @lru_cache(maxsize=1)
    def _trust_():
        blocks = read_text(Path(certifi.where()), encoding="ascii", safe=False).split("-----END CERTIFICATE-----")
        return ssl.trustRootFromCertificates([ssl.Certificate.loadPEM(block + "-----END CERTIFICATE-----") for block in blocks if "-----BEGIN CERTIFICATE-----" in block])

    @staticmethod
    @lru_cache(maxsize=1)
    def _kinds_() -> tuple[dict, dict]:
        kinds = [kind for name, kind in vars(Messages).items() if name.startswith("Proto") and isinstance(kind, type) and "payloadType" in kind.DESCRIPTOR.fields_by_name]
        return {kind.__name__: kind for kind in kinds}, {kind().payloadType: kind for kind in kinds}

    @classmethod
    def message(cls, name: str, **fields):
        return cls._kinds_()[0][name](**fields)

    @classmethod
    def payload(cls, message):
        return cls._kinds_()[1][message.payloadType].FromString(message.payload)

    @staticmethod
    def historical(payload: int) -> bool:
        return payload in (PROTO_OA_GET_TRENDBARS_REQ, PROTO_OA_GET_TICKDATA_REQ, PROTO_OA_DEAL_LIST_REQ, PROTO_OA_ORDER_LIST_REQ, PROTO_OA_CASH_FLOW_HISTORY_LIST_REQ)

    @classmethod
    def options(cls, host: str):
        return ssl.optionsForClientTLS(host, trustRoot=cls._trust_())

    def rate(self, historical: bool) -> int:
        return self._historical_ if historical else self._rate_

    def startService(self) -> None:
        if not self.running: super().startService()

    def drop(self) -> None:
        if self._protocol_ is not None and self._protocol_.transport is not None: self._protocol_.transport.abortConnection()

    def send(self, message, timeout: float = 5):
        deferred = defer.Deferred(self._cancel_)
        key = str(id(deferred))
        self._pending_[key] = deferred
        deferred.addErrback(self._forget_, key)
        deferred.addTimeout(timeout, reactor)
        self.whenConnected(failAfterFailures=1).addCallbacks(lambda protocol: protocol.send(message, key, lambda: key not in self._pending_), lambda failure: None if deferred.called else deferred.errback(failure))
        return deferred