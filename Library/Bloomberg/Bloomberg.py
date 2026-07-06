"""Main Bloomberg interface backed by the xbbg 1.4.1 engine with optional ZMQ remote calls."""
import io
import json

from Library.Database.Dataframe import DataframeAPI, pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Bloomberg.Reference import ReferenceAPI
from Library.Bloomberg.Historical import HistoricalAPI
from Library.Bloomberg.Intraday import IntradayAPI
from Library.Bloomberg.Query import QueryAPI
from Library.Bloomberg.Streaming import StreamingAPI

class BloombergAPI(ServiceAPI, DataframeAPI):
    """
    Main Bloomberg interface.

    Groups the Reference, Historical, Intraday, Query and Streaming sub-APIs and dispatches their
    engine calls through a single mode-aware channel:
    - Local mode (default): calls the xbbg 1.4.1 Rust engine next to a logged-in Bloomberg Terminal.
    - Remote mode (host and port given): ships each call as a JSON envelope to a serve() peer over
      ZMQ REQ/REP and rebuilds the resulting frame from Arrow IPC bytes, so neither xbbg nor the
      Bloomberg runtime is needed on the client machine.
    xbbg opens the underlying Bloomberg session lazily, so local connection is a lightweight state
    flag rather than an explicit session handshake.
    """

    def __init__(self, *,
                 host: str = None,
                 port: int = None,
                 token: str = None,
                 timeout: int = None,
                 legacy: bool = False) -> None:
        """
        Initializes the Bloomberg interface and its sub-APIs.
        :param host: Remote server host - if given (together with port), remote mode is assumed.
        :param port: Remote server port.
        :param token: Optional shared secret expected by the remote server.
        :param timeout: Optional remote receive timeout in seconds (blocking when omitted).
        :param legacy: If True, sub-APIs default to Pandas DataFrames instead of Polars.
        """
        super().__init__(legacy=legacy)
        self._host_ = host
        self._port_ = port
        self._token_ = token
        self._timeout_ = timeout
        self._socket_ = None
        self._connected_ = False
        self.reference = ReferenceAPI(self)
        self.historical = HistoricalAPI(self)
        self.intraday = IntradayAPI(self)
        self.query = QueryAPI(self)
        self.streaming = StreamingAPI(self)

    def remote(self) -> bool:
        """Checks whether the interface targets a remote server instead of the local xbbg engine."""
        return self._host_ is not None

    def connected(self) -> bool:
        """Checks whether the interface has been marked connected."""
        return self._connected_

    def _connect_(self, **kwargs) -> None:
        """Opens the ZMQ request socket (remote) or marks the lazy xbbg session connected (local)."""
        if self.remote():
            import zmq
            self._socket_ = zmq.Context.instance().socket(zmq.REQ)
            self._socket_.setsockopt(zmq.LINGER, 0)
            if self._timeout_ is not None: self._socket_.setsockopt(zmq.RCVTIMEO, self._timeout_ * 1000)
            self._socket_.connect(f"tcp://{self._host_}:{self._port_}")
        self._connected_ = True

    def disconnected(self) -> bool:
        """Checks whether the interface is disconnected."""
        return not self._connected_

    def _disconnect_(self) -> None:
        """Closes the ZMQ request socket (remote) and marks the interface disconnected."""
        if self._socket_ is not None:
            self._socket_.close()
            self._socket_ = None
        self._connected_ = False

    def _backend_(self, legacy: bool | Missing) -> str:
        """Resolves the effective legacy flag to the matching xbbg output backend name."""
        return "pandas" if self.legacy(legacy) else "polars"

    def _call_(self, name: str, *args, legacy: bool | Missing = MISSING, **kwargs) -> pd.DataFrame | pl.DataFrame:
        """
        Dispatches one engine call by name - straight into xbbg locally or as a JSON envelope with
        an Arrow IPC reply when remote - so the wire protocol mirrors the xbbg layout exactly.
        Remote replies always travel as Polars Arrow IPC; the legacy conversion happens client-side.
        :param name: xbbg function name (bdp, bds, bdh, bdib, bdtick, bql).
        :param args: Positional arguments forwarded to the xbbg function.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :param kwargs: Keyword arguments forwarded to the xbbg function.
        :returns: The frame produced by the xbbg function in the requested backend.
        """
        if not self.remote():
            from xbbg import blp
            return getattr(blp, name)(*args, backend=self._backend_(legacy), **kwargs)
        request = json.dumps({"call": name, "args": args, "kwargs": kwargs, "token": self._token_}, default=str).encode()
        try:
            self._socket_.send(request)
            frames = self._socket_.recv_multipart()
        except Exception:
            self.disconnect()
            raise
        header = json.loads(frames[0])
        if header["status"] != "ok": raise RuntimeError(header["error"])
        df = pl.read_ipc(io.BytesIO(frames[1]))
        return df.to_pandas() if self.legacy(legacy) else df

    def _stream_(self, securities: str | list[str], fields: str | list[str], legacy: bool | Missing = MISSING):
        """Opens the live xbbg stream generator (local mode only)."""
        if self.remote(): raise RuntimeError("Streaming is not supported in remote mode")
        from xbbg import blp
        return blp.stream(securities, fields, backend=self._backend_(legacy))

    def serve(self, port: int, token: str = None) -> None:
        """
        Runs the blocking server loop answering remote BloombergAPI clients over ZMQ REQ/REP.
        Each envelope is dispatched to the local xbbg engine and answered with a JSON status header
        plus an Arrow IPC payload so clients rebuild the frame without any Bloomberg dependency.
        :param port: TCP port to bind on all interfaces.
        :param token: Optional shared secret that every request must present.
        """
        if self.remote(): raise RuntimeError("Serving requires a local interface")
        import zmq
        self.connect()
        socket = zmq.Context.instance().socket(zmq.REP)
        socket.bind(f"tcp://*:{port}")
        self._log_.info(lambda: f"Serve Operation: Listening (Port {port})")
        try:
            while True:
                request = socket.recv()
                try:
                    envelope = json.loads(request)
                    if token is not None and envelope.get("token") != token: raise PermissionError("Invalid Token")
                    df = self._call_(envelope["call"], *envelope["args"], legacy=False, **envelope["kwargs"])
                    buffer = io.BytesIO()
                    df.write_ipc(buffer)
                    socket.send_multipart([json.dumps({"status": "ok"}).encode(), buffer.getvalue()])
                    self._log_.debug(lambda: f"Serve Operation: Answered {envelope['call']} ({len(df)} Rows)")
                except Exception as e:
                    socket.send_multipart([json.dumps({"status": "error", "error": f"{e}"}).encode()])
                    self._log_.error(lambda: f"Serve Operation: Failed · {e}")
        except KeyboardInterrupt:
            self._log_.info(lambda: "Serve Operation: Interrupted by User")
        finally:
            socket.close()