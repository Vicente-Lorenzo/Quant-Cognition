import os
import threading

from typing import Callable, Union
from twisted.internet import reactor
from datetime import datetime, timezone
from ctrader_open_api import Client, Protobuf, TcpProtocol
from twisted.internet.threads import blockingCallFromThread

from Library.Database.Dataframe import DataframeAPI
from Library.Spotware.Execution import ExecutionAPI
from Library.Spotware.Market import MarketAPI
from Library.Spotware.Portfolio import PortfolioAPI
from Library.Spotware.Streaming import StreamingAPI
from Library.Spotware.Universe import UniverseAPI
from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing, normalize

class SpotwareAPI(ServiceAPI, DataframeAPI):

    _HOSTS_ = {"live": "live.ctraderapi.com", "demo": "demo.ctraderapi.com"}
    _ERRORS_ = ("ProtoOAErrorRes", "ProtoErrorRes")
    _ACCOUNT_ = "ctidTraderAccountId"
    _PRICE_SCALE_ = 100000
    _CENTS_ = 100
    _MONEY_DIGITS_ = 2

    def __init__(self, *,
                 client_id: str,
                 client_secret: str,
                 access_token: Union[str, None] = None,
                 account_id: Union[int, None] = None,
                 environment: str = "demo",
                 host: Union[str, None] = None,
                 port: int = 5035,
                 timeout: int = 10,
                 legacy: bool = False) -> None:
        super().__init__(legacy=legacy)

        self._client_id_: str = client_id
        self._client_secret_: str = client_secret
        self._access_token_: Union[str, None] = access_token
        self._account_id_: Union[int, None] = account_id
        self._host_: str = host or self._HOSTS_.get(str(environment).lower(), environment)
        self._port_: int = port
        self._timeout_: int = timeout

        self._reactor_thread_: Union[threading.Thread, None] = None
        self._connection_ = None
        self._connected_event_: Union[threading.Event, None] = None
        self._app_authed_: bool = False
        self._account_authed_: bool = False
        self._subscribers_: list = []

        self.universe = UniverseAPI(self)
        self.market = MarketAPI(self)
        self.streaming = StreamingAPI(self)
        self.portfolio = PortfolioAPI(self)
        self.execution = ExecutionAPI(self)

    def _connect_(self, **kwargs) -> None:
        if not reactor.running:
            self._reactor_thread_ = threading.Thread(target=reactor.run, kwargs={"installSignalHandlers": False}, daemon=True)
            self._reactor_thread_.start()
        self._connected_event_ = threading.Event()
        self._connection_ = Client(self._host_, self._port_, TcpProtocol)
        self._connection_.setConnectedCallback(lambda client: self._connected_event_.set())
        self._connection_.setMessageReceivedCallback(self._on_message_)
        blockingCallFromThread(reactor, self._connection_.startService)
        if not self._connected_event_.wait(timeout=self._timeout_):
            self._connection_ = None
            raise ConnectionError(f"Server Unreachable ({self._host_}:{self._port_})")
        self._authenticate_()

    def _authenticate_(self) -> None:
        if not self._app_authed_:
            self._request_("ProtoOAApplicationAuthReq", clientId=self._client_id_, clientSecret=self._client_secret_)
            self._app_authed_ = True
        if self._account_id_ and self._access_token_ and not self._account_authed_:
            self._request_("ProtoOAAccountAuthReq", accessToken=self._access_token_)
            self._account_authed_ = True

    def connected(self) -> bool:
        return self._connection_ is not None and bool(getattr(self._connection_, "isConnected", False))

    def _disconnect_(self) -> None:
        if self._connection_ is None: return
        if reactor.running:
            try: blockingCallFromThread(reactor, self._connection_.stopService)
            except Exception as e: self._log_.debug(lambda e=e: f"Disconnect Operation: Failed · {e}")
        self._connection_ = None
        self._app_authed_ = False
        self._account_authed_ = False
        self._subscribers_.clear()

    def disconnected(self) -> bool:
        return self._connection_ is None

    @staticmethod
    def _prefix_(descriptor) -> str:
        common = os.path.commonprefix([value.name for value in descriptor.values])
        return common[:common.rfind("_") + 1]

    @staticmethod
    def _optional_(message, field: str, decode: Union[Callable, Missing] = MISSING):
        if not message.HasField(field): return None
        value = getattr(message, field)
        return value if decode is MISSING else decode(value)

    @staticmethod
    def _epoch_(value: datetime) -> int:
        return datetime_to_epoch(value if value.tzinfo is None else value.astimezone(timezone.utc).replace(tzinfo=None))

    @staticmethod
    def _stamp_(milliseconds: Union[int, None]) -> Union[datetime, None]:
        return epoch_to_datetime(milliseconds) if milliseconds else None

    @classmethod
    def _price_(cls, relative: int) -> float:
        return relative / cls._PRICE_SCALE_

    @classmethod
    def _relative_(cls, price: float) -> int:
        return round(price * cls._PRICE_SCALE_)

    @classmethod
    def _units_(cls, cents: int) -> float:
        return cents / cls._CENTS_

    @classmethod
    def _cents_(cls, units: float) -> int:
        return round(units * cls._CENTS_)

    @classmethod
    def _digits_(cls, message) -> int:
        return message.moneyDigits if message.HasField("moneyDigits") else cls._MONEY_DIGITS_

    @classmethod
    def _money_(cls, message) -> int:
        return 10 ** cls._digits_(message)

    @classmethod
    def _label_(cls, descriptor, number: int) -> Union[str, int]:
        value = descriptor.values_by_number.get(number)
        if value is None: return number
        return "".join(part.capitalize() for part in value.name[len(cls._prefix_(descriptor)):].split("_"))

    @classmethod
    def _named_(cls, message, field: str) -> Union[str, int, None]:
        if not message.HasField(field): return None
        return cls._label_(message.DESCRIPTOR.fields_by_name[field].enum_type, getattr(message, field))

    @classmethod
    def _code_(cls, enumeration, value) -> int:
        if isinstance(value, int) and not isinstance(value, bool): return value
        descriptor = enumeration.DESCRIPTOR
        prefix, key = cls._prefix_(descriptor), normalize(getattr(value, "name", str(value)))
        for member in descriptor.values:
            if key in (normalize(member.name), normalize(member.name[len(prefix):])): return member.number
        raise ValueError(f"{descriptor.name} {value}: Failed · Not a member")

    def _message_(self, name: str, **fields):
        message = Protobuf.get(name, **fields)
        if self._account_id_ is not None and self._ACCOUNT_ in message.DESCRIPTOR.fields_by_name: setattr(message, self._ACCOUNT_, self._account_id_)
        return message

    def _send_(self, request, timeout: Union[int, None] = None):
        response = blockingCallFromThread(reactor, self._connection_.send, request, responseTimeoutInSeconds=self._timeout_ if timeout is None else timeout)
        if not hasattr(response, "payloadType"): return response
        payload = Protobuf.extract(response)
        if type(payload).__name__ in self._ERRORS_:
            description = getattr(payload, "description", "")
            raise RuntimeError(f"{payload.errorCode} · {description}" if description else payload.errorCode)
        return payload

    def _request_(self, name: str, **fields):
        return self._send_(self._message_(name, **fields))

    def _on_message_(self, client, message) -> None:
        for callback in list(self._subscribers_):
            try: callback(message)
            except Exception as e: self._log_.exception(lambda e=e: f"Message Operation: Failed · {e}")

    def _subscribe_(self, callback: Callable) -> None:
        self._subscribers_.append(callback)

    def _unsubscribe_(self, callback: Callable) -> None:
        try: self._subscribers_.remove(callback)
        except ValueError: pass

    def _listen_(self,
                 subscribe,
                 unsubscribe,
                 decode: Callable,
                 callback: Callable,
                 limit: Union[int, Missing] = MISSING,
                 timeout: Union[float, None] = None) -> int:
        done, lock, count, failure = threading.Event(), threading.Lock(), 0, None
        def _handler_(message) -> None:
            nonlocal count, failure
            with lock:
                if done.is_set(): return
                try:
                    for item in decode(Protobuf.extract(message)):
                        callback(item)
                        count += 1
                        if limit is not MISSING and limit is not None and count >= limit:
                            done.set()
                            return
                except Exception as error:
                    failure = error
                    done.set()
        self.connect()
        self._subscribe_(_handler_)
        try:
            self._send_(subscribe)
            done.wait(timeout=timeout)
            if failure is not None: raise failure
        except KeyboardInterrupt:
            self._log_.info(lambda: f"Stream Operation: Interrupted by User ({count} Updates)")
        except Exception as e:
            self._log_.failure(lambda e=e: f"Stream Operation: Failed · {e}")
            raise
        finally:
            with lock: done.set()
            self._unsubscribe_(_handler_)
            try: self._send_(unsubscribe)
            except Exception as e: self._log_.debug(lambda e=e: f"Unsubscribe Operation: Failed · {e}")
        return count