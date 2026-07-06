"""Bloomberg Streaming Data interface backed by xbbg live subscriptions."""
from typing import Callable

from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class StreamingAPI(ServiceAPI):
    """Bloomberg Streaming Data interface (xbbg live stream generator · local mode only)."""

    def subscribe(self,
                  securities: str | list[str],
                  fields: str | list[str],
                  callback: Callable,
                  limit: int = None,
                  legacy: bool | Missing = MISSING) -> None:
        """
        Subscribes to real-time market data updates and dispatches them to a callback.

        xbbg's blp.stream is a synchronous generator (it runs the async subscription on a background
        thread) that yields each update batch already converted to the requested backend, so a plain
        loop keeps the public interface callback-based like the rest of the module. Streaming needs
        the local xbbg engine and raises in remote mode.
        :param securities: Security ticker or list of tickers.
        :param fields: Field mnemonic or list of fields.
        :param callback: Function receiving each update batch as a DataFrame.
        :param limit: Optional number of updates to receive before stopping.
        :param legacy: If True, updates are Pandas DataFrames; if False, Polars. Defaults to the API setting.
        """
        try:
            self.connect()
            count = 0
            for update in self._api_._stream_(securities, fields, legacy):
                callback(update)
                count += 1
                if limit is not None and count >= limit: break
        except KeyboardInterrupt:
            self._log_.info(lambda: "Streaming Operation: Interrupted by User")
        except Exception as e:
            self._log_.error(lambda: f"Streaming Operation: Failed · {e}")
            self._log_.exception(lambda: f"Streaming Operation: Failed · {e}")
            raise