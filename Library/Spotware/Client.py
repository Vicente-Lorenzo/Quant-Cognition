import time
import certifi

from pathlib import Path
from collections import deque
from datetime import datetime
from functools import lru_cache
from ctrader_open_api.factory import Factory
from twisted.internet import reactor, ssl, task
from ctrader_open_api import Client, TcpProtocol
from twisted.application.internet import ClientService
from twisted.internet.endpoints import SSL4ClientEndpoint
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import PROTO_OA_GET_TICKDATA_REQ, PROTO_OA_GET_TRENDBARS_REQ

from Library.Utility.IO import read_text
from Library.Utility.Math import EPSILON

class ProtocolAPI(TcpProtocol):

    def connectionMade(self) -> None:
        self._send_queue = deque()
        self._lanes_ = {True: (deque(), deque()), False: (deque(), deque())}
        self._drain_call_ = None
        super().connectionMade()

    def connectionLost(self, reason) -> None:
        if self._drain_call_ is not None and self._drain_call_.active(): self._drain_call_.cancel()
        self._drain_call_ = None
        super().connectionLost(reason)

    def _drain_(self) -> None:
        if self._drain_call_ is not None and self._drain_call_.active(): self._drain_call_.cancel()
        self._drain_call_, now, wait = None, time.monotonic(), None
        for historical, (queue, window) in self._lanes_.items():
            rate = self.factory.client.rate(historical)
            while window and now - window[0] >= 1: window.popleft()
            while queue and len(window) < rate and (not window or now - window[-1] >= 1 / rate - EPSILON):
                canceled, data = queue.popleft()
                if canceled is not None and canceled(): continue
                self.sendString(data)
                window.append(now)
                self._lastSendMessageTime = datetime.now()
            if queue:
                ready = max(window[-1] + 1 / rate, window[0] + 1 if len(window) >= rate else 0)
                wait = ready - now if wait is None else min(wait, ready - now)
        if wait is not None: self._drain_call_ = reactor.callLater(max(wait, 0.001), self._drain_)

    def send(self, message, instant=False, clientMsgId=None, isCanceled=None) -> None:
        if instant or isinstance(message, (bytes, ProtoMessage)): return super().send(message, instant, clientMsgId, isCanceled)
        data = ProtoMessage(payload=message.SerializeToString(), clientMsgId=clientMsgId, payloadType=message.payloadType).SerializeToString()
        self._lanes_[ClientAPI.historical(message.payloadType)][0].append((isCanceled, data))
        self._drain_()

class ClientAPI(Client):

    def __init__(self, host: str, port: int, *, rate: int = 45, historical: int = 4, silence: float = 75.0) -> None:
        self._runningReactor = reactor
        self.numberOfMessagesToSendPerSecond = rate
        self._historical_ = historical
        self._silence_ = silence
        self._protocol_ = None
        self._heard_ = time.monotonic()
        self._watch_ = None
        ClientService.__init__(self, SSL4ClientEndpoint(reactor, host, port, self.options(host)), Factory.forProtocol(ProtocolAPI, client=self))
        self._responseDeferreds, self.isConnected = {}, False

    def _connected(self, protocol) -> None:
        self._protocol_, self._heard_ = protocol, time.monotonic()
        self._watch_ = task.LoopingCall(self._check_)
        self._watch_.start(self._silence_ / 5, now=False)
        super()._connected(protocol)

    def _disconnected(self, reason) -> None:
        pending = list(self._responseDeferreds.values())
        if self._watch_ is not None and self._watch_.running: self._watch_.stop()
        self._protocol_, self._watch_ = None, None
        super()._disconnected(reason)
        for deferred in pending:
            if not deferred.called: deferred.errback(ConnectionError("Request Operation: Failed · Connection lost in flight"))

    def drop(self) -> None:
        if self._protocol_ is not None and self._protocol_.transport is not None: self._protocol_.transport.abortConnection()

    def stopService(self):
        return ClientService.stopService(self)

    def _received(self, message) -> None:
        self._heard_ = time.monotonic()
        super()._received(message)

    def _check_(self) -> None:
        if time.monotonic() - self._heard_ > self._silence_: self.drop()

    @staticmethod
    @lru_cache(maxsize=1)
    def _trust_():
        blocks = read_text(Path(certifi.where()), encoding="ascii", safe=False).split("-----END CERTIFICATE-----")
        return ssl.trustRootFromCertificates([ssl.Certificate.loadPEM(block + "-----END CERTIFICATE-----") for block in blocks if "-----BEGIN CERTIFICATE-----" in block])

    @staticmethod
    def historical(payload: int) -> bool:
        return payload in (PROTO_OA_GET_TRENDBARS_REQ, PROTO_OA_GET_TICKDATA_REQ)

    def rate(self, historical: bool) -> int:
        return self._historical_ if historical else self.numberOfMessagesToSendPerSecond

    @classmethod
    def options(cls, host: str):
        return ssl.optionsForClientTLS(host, trustRoot=cls._trust_())