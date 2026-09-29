import os
import time
import threading

from functools import lru_cache
from typing import Callable, Union
from typing_extensions import Self
from twisted.internet import reactor
from datetime import datetime, timezone
from twisted.internet.threads import blockingCallFromThread

from Library.Database.Dataframe import DataframeAPI, pl
from Library.Spotware.Client import ClientAPI
from Library.Spotware.Execution import ExecutionAPI
from Library.Spotware.Market import MarketAPI
from Library.Spotware.Messages import ERROR_RES, PROTO_OA_ACCOUNT_DISCONNECT_EVENT, PROTO_OA_ACCOUNTS_TOKEN_INVALIDATED_EVENT, PROTO_OA_CLIENT_DISCONNECT_EVENT, PROTO_OA_ERROR_RES
from Library.Spotware.Portfolio import PortfolioAPI
from Library.Spotware.Streaming import StreamingAPI
from Library.Spotware.Token import TokenAPI
from Library.Spotware.Universe import UniverseAPI
from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing, normalize

class SpotwareAPI(ServiceAPI, DataframeAPI):

    _STARTING_ = threading.Lock()

    def __init__(self, *,
                 client_id: str,
                 client_secret: str,
                 access_token: Union[str, None] = None,
                 account_id: Union[int, None] = None,
                 environment: str = "demo",
                 host: Union[str, None] = None,
                 port: int = 5035,
                 timeout: int = 10,
                 historical_timeout: int = 60,
                 renew: Union[Callable[[], str], Missing] = MISSING,
                 legacy: bool = False) -> None:
        super().__init__(legacy=legacy)

        self._client_id_: str = client_id
        self._client_secret_: str = client_secret
        self._access_token_: Union[str, None] = access_token
        self._account_id_: Union[int, None] = account_id
        self._host_: str = host or {"live": "live.ctraderapi.com", "demo": "demo.ctraderapi.com"}.get(str(environment).lower(), environment)
        self._port_: int = port
        self._timeout_: int = timeout
        self._historical_timeout_: int = historical_timeout
        self._renew_: Union[Callable[[], str], Missing] = renew

        self._connection_ = None
        self._connected_event_: Union[threading.Event, None] = None
        self._ready_: threading.Event = threading.Event()
        self._restoring_: threading.Lock = threading.Lock()
        self._established_: bool = False
        self._stopping_: bool = False
        self._app_authed_: bool = False
        self._account_authed_: bool = False
        self._generation_: int = 0
        self._failures_: int = 0
        self._subscribers_: list = []
        self._subscriptions_: dict = {}
        self._listeners_: set = set()

        self.universe = UniverseAPI(self)
        self.market = MarketAPI(self)
        self.streaming = StreamingAPI(self)
        self.portfolio = PortfolioAPI(self)
        self.execution = ExecutionAPI(self)

    @classmethod
    def of(cls, values: dict, *, account: Union[int, Missing] = MISSING, **kwargs) -> Self:
        plain = lambda name: TokenAPI.plain(values.get(name))
        return cls(client_id=plain("Identifier"), client_secret=plain("Secret"), access_token=plain("AccessToken"), account_id=None if account is MISSING else int(account), environment=plain("Environment") or "demo", **kwargs)

    @classmethod
    def test(cls, values: dict) -> str:
        with cls.of(values) as api:
            if not api._access_token_: return "Application authenticated"
            reached = api.portfolio.accounts()
        return f"Application authenticated · Token reaches {len(reached)} account(s)"

    @classmethod
    def _reactor_(cls) -> None:
        with cls._STARTING_:
            if reactor.running: return
            started = threading.Event()
            reactor.callWhenRunning(started.set)
            threading.Thread(target=reactor.run, kwargs={"installSignalHandlers": False}, daemon=True).start()
            started.wait(timeout=10)

    def _connect_(self, **kwargs) -> None:
        self._reactor_()
        self._connected_event_, self._stopping_ = threading.Event(), False
        self._connection_ = ClientAPI(self._host_, self._port_, connected=self._on_connected_, disconnected=self._on_disconnected_, received=self._on_message_)
        blockingCallFromThread(reactor, self._connection_.startService)
        if not self._connected_event_.wait(timeout=self._timeout_):
            self._disconnect_()
            raise ConnectionError(f"Server Unreachable ({self._host_}:{self._port_})")
        try: self._authenticate_()
        except Exception:
            self._disconnect_()
            raise
        self._established_ = True
        self._ready_.set()

    def _renew_token_(self) -> None:
        self._access_token_ = self._renew_()
        self._log_.info("Token Operation: Renewed")

    def _authenticate_(self) -> None:
        if not self._app_authed_:
            self._send_(self._message_("ProtoOAApplicationAuthReq", clientId=self._client_id_, clientSecret=self._client_secret_))
            self._app_authed_ = True
        if self._account_id_ and self._access_token_ and not self._account_authed_:
            try: self._send_(self._message_("ProtoOAAccountAuthReq", accessToken=self._access_token_))
            except RuntimeError:
                if self._renew_ is MISSING: raise
                self._renew_token_()
                self._send_(self._message_("ProtoOAAccountAuthReq", accessToken=self._access_token_))
            self._account_authed_ = True

    def _resubscribe_(self, message) -> None:
        try: self._send_(message)
        except RuntimeError as error:
            if not str(error).startswith("ALREADY_SUBSCRIBED"): raise

    def _restore_(self, renew: bool = False, generation: Union[int, Missing] = MISSING) -> None:
        with self._restoring_:
            if self._stopping_ or not self.connected() or generation is not MISSING and generation != self._generation_: return
            if generation is not MISSING: self._app_authed_ = self._account_authed_ = False
            current = self._generation_
            try:
                if renew and self._renew_ is not MISSING: self._renew_token_()
                self._authenticate_()
                for messages in list(self._subscriptions_.values()):
                    for message in messages: self._resubscribe_(message)
                self._failures_ = 0
                self._ready_.set()
                self._log_.info(lambda: f"Connection Operation: Restored ({len(self._subscriptions_)} Subscriptions)")
            except Exception as error:
                if self._stopping_: return
                self._failures_ += 1
                self._log_.failure(lambda error=error: f"Connection Operation: Failed · {error}")
                time.sleep(min(self._timeout_ * 2 ** (self._failures_ - 1), 300))
                if not self._stopping_ and current == self._generation_ and self._connection_ is not None: blockingCallFromThread(reactor, self._connection_.drop)

    def _on_connected_(self, client) -> None:
        self._generation_ += 1
        self._connected_event_.set()
        if self._established_ and not self._stopping_: threading.Thread(target=self._restore_, kwargs={"generation": self._generation_}, daemon=True).start()

    def connected(self) -> bool:
        return self._connection_ is not None and bool(getattr(self._connection_, "Connected", False))

    def _on_disconnected_(self, client, reason) -> None:
        self._ready_.clear()
        self._app_authed_ = self._account_authed_ = False
        if not self._stopping_: self._log_.warning(lambda reason=reason: f"Connection Operation: Lost · {reason.getErrorMessage()}")

    def _disconnect_(self) -> None:
        if self._connection_ is None: return
        self._stopping_ = True
        self._ready_.clear()
        if reactor.running:
            if self._account_authed_ and self.connected():
                try: self._send_(self._message_("ProtoOAAccountLogoutReq"), timeout=3)
                except Exception as error: self._log_.debug(lambda error=error: f"Logout Operation: Failed · {error}")
            try: blockingCallFromThread(reactor, self._connection_.stopService)
            except Exception as error: self._log_.debug(lambda error=error: f"Disconnect Operation: Failed · {error}")
        self._connection_ = None
        self._app_authed_ = self._account_authed_ = self._established_ = False
        for done in list(self._listeners_): done.set()
        self._subscribers_.clear()
        self._subscriptions_.clear()

    def disconnected(self) -> bool:
        return self._connection_ is None

    @staticmethod
    @lru_cache(maxsize=None)
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

    @staticmethod
    def _price_(relative):
        return relative / 100000

    @staticmethod
    def _prices_(relative: pl.Expr) -> pl.Expr:
        return (relative / 100000).round(5)

    @staticmethod
    def _relative_(price: float) -> int:
        return round(price * 100000)

    @staticmethod
    def _units_(cents: int) -> float:
        return cents / 100

    @staticmethod
    def _cents_(units: float) -> int:
        return round(units * 100)

    @staticmethod
    def _digits_(message) -> int:
        return message.moneyDigits if message.HasField("moneyDigits") else 2

    @classmethod
    def _money_(cls, message) -> int:
        return 10 ** cls._digits_(message)

    @classmethod
    @lru_cache(maxsize=None)
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
        message = ClientAPI.message(name, **fields)
        if self._account_id_ is not None and "ctidTraderAccountId" in message.DESCRIPTOR.fields_by_name: message.ctidTraderAccountId = self._account_id_
        return message

    @staticmethod
    def _transient_(code: str, description: str) -> bool:
        return code == "BLOCKED_PAYLOAD_TYPE" or (code == "UNKNOWN_ERROR" and description == "Can't request tickdata")

    def _send_(self, request, timeout: Union[int, Missing] = MISSING):
        for delay in (1, 2, 4, 8, None):
            response = blockingCallFromThread(reactor, self._connection_.send, request, timeout=self._timeout_ if timeout is MISSING else timeout)
            if not hasattr(response, "payloadType"): return response
            payload = ClientAPI.payload(response)
            if response.payloadType not in (PROTO_OA_ERROR_RES, ERROR_RES): return payload
            description = getattr(payload, "description", "")
            if not self._transient_(payload.errorCode, description) or delay is None: raise RuntimeError(f"{payload.errorCode} · {description}" if description else payload.errorCode)
            self._log_.warning(lambda delay=delay, code=payload.errorCode: f"Request Operation: Throttled ({type(request).__name__}) · {code} · Retrying in {delay}s")
            time.sleep(delay)

    def _await_(self) -> None:
        if not self._ready_.wait(timeout=self._timeout_ * 3): raise ConnectionError(f"Session Operation: Failed · Not restored within {self._timeout_ * 3}s")

    def _request_(self, name: str, **fields):
        message = self._message_(name, **fields)
        self._await_()
        return self._send_(message, timeout=self._historical_timeout_ if ClientAPI.historical(message.payloadType) else MISSING)

    def _react_(self, payload) -> None:
        name = type(payload).__name__
        if name == "ProtoOAClientDisconnectEvent":
            self._log_.warning(lambda: f"Connection Operation: Closed (Server) · {payload.reason}")
            return
        invalidated = name == "ProtoOAAccountsTokenInvalidatedEvent"
        accounts = list(payload.ctidTraderAccountIds) if invalidated else [payload.ctidTraderAccountId]
        if self._stopping_ or self._account_id_ not in accounts: return
        self._ready_.clear()
        self._account_authed_ = False
        self._log_.warning(lambda: f"Account Operation: {'Token Invalidated' if invalidated else 'Disconnected'} (Server)")
        threading.Thread(target=self._restore_, kwargs={"renew": invalidated}, daemon=True).start()

    def _on_message_(self, client, message) -> None:
        if getattr(message, "payloadType", None) in (PROTO_OA_CLIENT_DISCONNECT_EVENT, PROTO_OA_ACCOUNT_DISCONNECT_EVENT, PROTO_OA_ACCOUNTS_TOKEN_INVALIDATED_EVENT): self._react_(ClientAPI.payload(message))
        for callback in list(self._subscribers_):
            try: callback(message)
            except Exception as error: self._log_.exception(lambda error=error: f"Message Operation: Failed · {error}")

    def _subscribe_(self, callback: Callable) -> None:
        self._subscribers_.append(callback)

    def _unsubscribe_(self, callback: Callable) -> None:
        try: self._subscribers_.remove(callback)
        except ValueError: pass

    def _listen_(self,
                 subscribe: list,
                 unsubscribe: list,
                 event: int,
                 decode: Callable,
                 callback: Callable,
                 limit: Union[int, Missing] = MISSING,
                 timeout: Union[float, None] = None) -> int:
        done, lock, count, failure = threading.Event(), threading.Lock(), 0, None
        def _handler_(message) -> None:
            nonlocal count, failure
            if getattr(message, "payloadType", None) != event: return
            with lock:
                if done.is_set(): return
                try:
                    for item in decode(ClientAPI.payload(message)):
                        callback(item)
                        count += 1
                        if limit is not MISSING and count >= limit:
                            done.set()
                            return
                except Exception as error:
                    failure = error
                    done.set()
        self.connect()
        self._subscribe_(_handler_)
        self._listeners_.add(done)
        try:
            self._await_()
            self._subscriptions_[id(subscribe)] = subscribe
            for message in subscribe: self._resubscribe_(message)
            done.wait(timeout=timeout)
            if failure is not None: raise failure
            if self._stopping_ and not (limit is not MISSING and count >= limit): raise ConnectionError("Session Stopped")
        except KeyboardInterrupt:
            self._log_.info(lambda: f"Stream Operation: Interrupted by User ({count} Updates)")
        except Exception as error:
            self._log_.failure(lambda error=error: f"Stream Operation: Failed · {error}")
            raise
        finally:
            with lock: done.set()
            self._listeners_.discard(done)
            self._unsubscribe_(_handler_)
            self._subscriptions_.pop(id(subscribe), None)
            for message in unsubscribe if self._ready_.is_set() else ():
                try: self._send_(message)
                except Exception as error: self._log_.debug(lambda error=error: f"Unsubscribe Operation: Failed · {error}")
        return count