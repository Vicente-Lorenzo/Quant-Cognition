import pytest
import Library.Market
import Library.Portfolio
from Library.Spotware import SpotwareAPI
from ctrader_open_api.messages.OpenApiCommonMessages_pb2 import ProtoMessage
class FakeClient:
    def __init__(self):
        self.isConnected = True
class FakeSpotwareAPI(SpotwareAPI):
    def __init__(self, account_id: int = 123, **kwargs):
        kwargs.setdefault("client_id", "test_client")
        kwargs.setdefault("client_secret", "test_secret")
        kwargs.setdefault("access_token", "test_token")
        kwargs.setdefault("account_id", account_id)
        kwargs.setdefault("environment", "demo")
        super().__init__(**kwargs)
        self._responses_: list = []
        self._sent_: list = []
        self._connection_ = FakeClient()
    def _connect_(self, **kwargs):
        pass
    def _send_(self, request, timeout=None):
        self._sent_.append(request)
        if not self._responses_:
            return None
        response = self._responses_.pop(0)
        if callable(response):
            return response(request, self)
        return response
    def _disconnect_(self):
        self._connection_ = None
        self._subscribers_.clear()
    def push(self, payload):
        message = ProtoMessage()
        message.payloadType = payload.payloadType
        message.payload = payload.SerializeToString()
        self._on_message_(self._connection_, message)
    def connected(self) -> bool:
        return True
    def disconnected(self) -> bool:
        return False
@pytest.fixture
def spotware():
    api = FakeSpotwareAPI()
    yield api
    api.disconnect()