from __future__ import annotations

import threading

from Library.Utility.Service import ServiceAPI
from Library.Spotware.Universe import UniverseAPI
from Library.Spotware.Market import MarketAPI
from Library.Spotware.Streaming import StreamingAPI
from Library.Spotware.Portfolio import PortfolioAPI
from Library.Spotware.Execution import ExecutionAPI

class SpotwareAPI(ServiceAPI):
    """
    Main Spotware Open API interface.
    Provides access to Universe, Market, Streaming, and Portfolio data.
    """

    _HOSTS_ = {"live": "live.ctraderapi.com", "demo": "demo.ctraderapi.com"}

    def __init__(self, *,
                 client_id: str,
                 client_secret: str,
                 access_token: str | None = None,
                 account_id: int | None = None,
                 environment: str = "demo",
                 host: str | None = None,
                 port: int = 5035,
                 timeout: int = 10,
                 legacy: bool = False) -> None:
        """
        Initializes the Spotware Open API session and sub-APIs.
        :param client_id: Application client identifier.
        :param client_secret: Application client secret.
        :param access_token: User access token (required for account operations).
        :param account_id: ctidTraderAccountId of the target account.
        :param environment: Target environment: "live" or "demo".
        :param host: Optional explicit host (overrides environment).
        :param port: Open API SSL port (default 5035).
        :param timeout: Default response timeout in seconds.
        :param legacy: If True, returns Pandas DataFrames instead of Polars.
        """
        super().__init__(legacy=legacy)

        self._client_id_: str = client_id
        self._client_secret_: str = client_secret
        self._access_token_: str | None = access_token
        self._account_id_: int | None = account_id
        self._host_: str = host or self._HOSTS_.get(str(environment).lower(), environment)
        self._port_: int = port
        self._timeout_: int = timeout

        self._reactor_ = None
        self._reactor_thread_ = None
        self._connection_ = None
        self._connected_event_: threading.Event | None = None
        self._disconnected_event_: threading.Event | None = None
        self._app_authed_: bool = False
        self._account_authed_: bool = False
        self._subscribers_: list = []

        self.universe = UniverseAPI(self)
        self.market = MarketAPI(self)
        self.streaming = StreamingAPI(self)
        self.portfolio = PortfolioAPI(self)
        self.execution = ExecutionAPI(self)

    def _connect_(self, **kwargs) -> None:
        """Starts the Spotware Open API session and authenticates."""
        from twisted.internet import reactor
        from twisted.internet.threads import blockingCallFromThread
        from ctrader_open_api import Client, TcpProtocol
        self._reactor_ = reactor
        if not reactor.running:
            self._reactor_thread_ = threading.Thread(
                target=reactor.run,
                kwargs={"installSignalHandlers": False},
                daemon=True
            )
            self._reactor_thread_.start()
        self._connected_event_ = threading.Event()
        self._disconnected_event_ = threading.Event()
        self._connection_ = Client(self._host_, self._port_, TcpProtocol)
        self._connection_.setConnectedCallback(lambda c: self._connected_event_.set())
        self._connection_.setDisconnectedCallback(lambda c, r: self._disconnected_event_.set())
        self._connection_.setMessageReceivedCallback(self._on_message_)
        blockingCallFromThread(reactor, self._connection_.startService)
        if not self._connected_event_.wait(timeout=self._timeout_):
            self._connection_ = None
            raise ConnectionError(f"Failed to connect to Spotware Open API at {self._host_}:{self._port_}")
        self._authenticate_()

    def _authenticate_(self) -> None:
        """Performs application and (optional) account-level authentication."""
        from ctrader_open_api import Protobuf
        if not self._app_authed_:
            req = Protobuf.get("ProtoOAApplicationAuthReq",
                               clientId=self._client_id_,
                               clientSecret=self._client_secret_)
            self._send_(req)
            self._app_authed_ = True
        if self._account_id_ and self._access_token_ and not self._account_authed_:
            req = Protobuf.get("ProtoOAAccountAuthReq",
                               ctidTraderAccountId=self._account_id_,
                               accessToken=self._access_token_)
            self._send_(req)
            self._account_authed_ = True

    def _send_(self, request, timeout: int | None = None):
        """
        Sends a request and returns the extracted response payload.
        :param request: Protobuf request message.
        :param timeout: Response timeout in seconds (defaults to API timeout).
        """
        from twisted.internet.threads import blockingCallFromThread
        from ctrader_open_api import Protobuf
        response = blockingCallFromThread(
            self._reactor_,
            self._connection_.send,
            request,
            responseTimeoutInSeconds=timeout if timeout is not None else self._timeout_
        )
        if not hasattr(response, "payloadType"): return response
        payload = Protobuf.extract(response)
        name = type(payload).__name__
        if name in ("ProtoOAErrorRes", "ProtoErrorRes"):
            code = getattr(payload, "errorCode", "UNKNOWN")
            desc = getattr(payload, "description", "")
            raise RuntimeError(f"Spotware Error [{code}]: {desc}")
        return payload

    def _on_message_(self, client, message) -> None:
        """Dispatches incoming messages to registered subscribers."""
        for cb in list(self._subscribers_):
            try: cb(message)
            except Exception as e:
                self._log_.exception(lambda: str(e))

    def _subscribe_(self, callback) -> None:
        """Registers a message callback for push events."""
        self._subscribers_.append(callback)

    def _unsubscribe_(self, callback) -> None:
        """Unregisters a previously registered message callback."""
        try: self._subscribers_.remove(callback)
        except ValueError: pass

    def connected(self) -> bool:
        """Checks if the Spotware session is active."""
        return self._connection_ is not None and bool(getattr(self._connection_, "isConnected", False))

    def _disconnect_(self) -> None:
        """Stops the Spotware session and clears credentials state."""
        if self._connection_ is None: return
        try:
            from twisted.internet.threads import blockingCallFromThread
            blockingCallFromThread(self._reactor_, self._connection_.stopService)
        except Exception: pass
        self._connection_ = None
        self._app_authed_ = False
        self._account_authed_ = False
        self._subscribers_.clear()

    def disconnected(self) -> bool:
        """Checks if the Spotware session is stopped."""
        return self._connection_ is None
