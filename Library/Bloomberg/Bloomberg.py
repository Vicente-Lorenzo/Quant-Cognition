"""Main Bloomberg interface backed by the xbbg 1.4.1 engine."""
from xbbg import Backend

from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing
from Library.Bloomberg.Reference import ReferenceAPI
from Library.Bloomberg.Historical import HistoricalAPI
from Library.Bloomberg.Intraday import IntradayAPI
from Library.Bloomberg.Query import QueryAPI
from Library.Bloomberg.Streaming import StreamingAPI

class BloombergAPI(ServiceAPI):
    """
    Main Bloomberg interface.

    Groups the Reference, Historical, Intraday, Query and Streaming sub-APIs, all backed by the
    xbbg 1.4.1 Rust engine. xbbg opens the underlying Bloomberg session lazily, so connection here
    is a lightweight state flag rather than an explicit session handshake.
    """

    def __init__(self, *, legacy: bool = False) -> None:
        """
        Initializes the Bloomberg interface and its sub-APIs.
        :param legacy: If True, sub-APIs default to Pandas DataFrames instead of Polars.
        """
        super().__init__(legacy=legacy)
        self._connected_ = False
        self.reference = ReferenceAPI(self)
        self.historical = HistoricalAPI(self)
        self.intraday = IntradayAPI(self)
        self.query = QueryAPI(self)
        self.streaming = StreamingAPI(self)

    def connected(self) -> bool:
        """Checks whether the interface has been marked connected."""
        return self._connected_

    def _connect_(self, **kwargs) -> None:
        """Marks the interface connected (xbbg opens the Bloomberg session lazily on first call)."""
        self._connected_ = True

    def disconnected(self) -> bool:
        """Checks whether the interface is disconnected."""
        return not self._connected_

    def _disconnect_(self) -> None:
        """Marks the interface disconnected."""
        self._connected_ = False

    def _backend_(self, legacy: bool | Missing) -> Backend:
        """Resolves the effective legacy flag to the matching xbbg output backend (Pandas or Polars)."""
        legacy = self._legacy_ if legacy is MISSING else legacy
        return Backend.PANDAS if legacy else Backend.POLARS