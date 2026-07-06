"""Main Bloomberg interface backed by the xbbg 1.4.1 engine with optional ZMQ remote calls."""
from Library.Database.Dataframe import DataframeAPI, pd, pl
from Library.Utility.Remote import RemoteAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Bloomberg.Reference import ReferenceAPI
from Library.Bloomberg.Historical import HistoricalAPI
from Library.Bloomberg.Intraday import IntradayAPI
from Library.Bloomberg.Query import QueryAPI
from Library.Bloomberg.Streaming import StreamingAPI

class BloombergAPI(RemoteAPI, DataframeAPI):
    """
    Main Bloomberg interface.

    Groups the Reference, Historical, Intraday, Query and Streaming sub-APIs and dispatches their
    engine calls through a single mode-aware channel provided by RemoteAPI:
    - Local mode (default): calls the xbbg 1.4.1 Rust engine next to a logged-in Bloomberg Terminal.
    - Remote mode (host and port given): ships each call as a JSON envelope to a serve() peer over
      ZMQ REQ/REP and rebuilds the resulting frame from Arrow IPC bytes, so neither xbbg nor the
      Bloomberg runtime is needed on the client machine.
    serve(port, token, whitelist, blacklist) turns a local interface into the server side, with
    optional shared-secret and client-address filtering (inherited from RemoteAPI).
    xbbg opens the underlying Bloomberg session lazily, so local connection is a lightweight state
    flag rather than an explicit session handshake.
    """

    def __init__(self, *,
                 host: str | Missing = MISSING,
                 port: int | Missing = MISSING,
                 token: str | Missing = MISSING,
                 timeout: int | Missing = MISSING,
                 legacy: bool = False) -> None:
        """
        Initializes the Bloomberg interface and its sub-APIs.
        :param host: Remote server host - if given (together with port), remote mode is assumed.
        :param port: Remote server port.
        :param token: Optional shared secret expected by the remote server.
        :param timeout: Optional remote receive timeout in seconds (blocking when omitted).
        :param legacy: If True, sub-APIs default to Pandas DataFrames instead of Polars.
        """
        super().__init__(host=host, port=port, token=token, timeout=timeout, legacy=legacy)
        self.reference = ReferenceAPI(self)
        self.historical = HistoricalAPI(self)
        self.intraday = IntradayAPI(self)
        self.query = QueryAPI(self)
        self.streaming = StreamingAPI(self)

    def _backend_(self, legacy: bool | Missing) -> str:
        """Resolves the effective legacy flag to the matching xbbg output backend name."""
        return "pandas" if self.legacy(legacy) else "polars"

    def _call_(self, name: str, *args, legacy: bool | Missing = MISSING, **kwargs) -> pd.DataFrame | pl.DataFrame:
        """
        Dispatches one engine call by name - straight into xbbg locally or through RemoteAPI's JSON
        envelope with an Arrow IPC reply when remote - so the wire protocol mirrors the xbbg layout.
        Remote replies always travel as Polars Arrow IPC; the legacy conversion happens client-side.
        :param name: xbbg function name (bdp, bds, bdh, bdib, bdtick, bql).
        :param args: Positional arguments forwarded to the xbbg function.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :param kwargs: Keyword arguments forwarded to the xbbg function.
        :returns: The frame produced by the xbbg function in the requested backend.
        """
        kwargs = {key: value for key, value in kwargs.items() if value is not MISSING}
        if not self.remote():
            from xbbg import blp
            return getattr(blp, name)(*args, backend=self._backend_(legacy), **kwargs)
        return self.deserialize(self._request_(name, *args, **kwargs), legacy=legacy)

    def _dispatch_(self, name: str, args: list, kwargs: dict) -> bytes:
        """Serves one remote envelope by running the local engine call and encoding the frame as Arrow IPC."""
        return self.serialize(self._call_(name, *args, legacy=False, **kwargs))

    def _stream_(self, securities: str | list[str], fields: str | list[str], legacy: bool | Missing = MISSING):
        """Opens the live xbbg stream generator (local mode only)."""
        if self.remote(): raise RuntimeError("Streaming is not supported in remote mode")
        from xbbg import blp
        return blp.stream(securities, fields, backend=self._backend_(legacy))