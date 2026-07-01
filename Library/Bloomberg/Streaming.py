"""Bloomberg Streaming Data interface backed by xbbg live subscriptions."""
from typing import Callable
from xbbg import blp

from Library.Utility.Service import ServiceAPI

class StreamingAPI(ServiceAPI):
    """Bloomberg Streaming Data interface (xbbg live stream generator)."""

    def subscribe(self,
                  securities: str | list[str],
                  fields: str | list[str],
                  callback: Callable,
                  frame: bool = True,
                  limit: int = None) -> None:
        """
        Subscribes to real-time market data updates and dispatches them to a callback.

        xbbg's blp.stream is a synchronous generator (it runs the async subscription on a background
        thread), so a plain loop keeps the public interface callback-based like the rest of the module.
        :param securities: Security ticker or list of tickers.
        :param fields: Field mnemonic or list of fields.
        :param callback: Function receiving each update (a DataFrame if frame, else the raw record).
        :param frame: If True, each update is wrapped in a single-row DataFrame.
        :param limit: Optional number of updates to receive before stopping.
        """
        securities = [securities] if isinstance(securities, str) else securities
        fields = [fields] if isinstance(fields, str) else fields
        try:
            self.connect()
            count = 0
            for update in blp.stream(securities, fields):
                callback(self._api_.frame([update]) if frame else update)
                count += 1
                if limit is not None and count >= limit: break
        except KeyboardInterrupt:
            self._log_.info(lambda: "Streaming Operation: Interrupted by User")
        except Exception as e:
            self._log_.error(lambda: f"Streaming Operation: Failed · {e}")
            self._log_.exception(lambda: f"Streaming Operation: Failed · {e}")
            raise