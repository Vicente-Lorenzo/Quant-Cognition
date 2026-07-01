"""Bloomberg Intraday Data interface backed by xbbg BDIB / BDTICK."""
from datetime import date, datetime
from xbbg import blp

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class IntradayAPI(ServiceAPI):
    """Bloomberg Intraday Data interface (xbbg BDIB single-date bars and BDTICK datetime-range ticks)."""

    def bars(self,
             security: str,
             dt: str | date | datetime,
             interval: int = 1,
             session: str = "allday",
             typ: str = "TRADE",
             legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        """
        Fetches intraday bars (BDIB) for a security on a single date (mirrors xbbg's bdib layout).
        :param security: Security ticker.
        :param dt: The date to fetch (date/datetime or 'YYYY-MM-DD' string).
        :param interval: Bar interval in minutes.
        :param session: Trading session - 'allday', 'day', 'am', 'pm', etc.
        :param typ: Event type - TRADE, BID, ASK, etc.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :returns: One row per bar with its timestamp and open, high, low, close and volume.
        """
        if isinstance(dt, (date, datetime)): dt = dt.strftime("%Y-%m-%d")
        def _fetch_():
            return blp.bdib(security, dt=dt, interval=interval, session=session, typ=typ,
                            backend=self._api_._backend_(legacy))
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Bars Operation: Fetched {len(df)} bars ({timer.result()})")
        return df

    def ticks(self,
              security: str,
              start: str | date | datetime,
              stop: str | date | datetime,
              event_types: str | list[str] = "TRADE",
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        """
        Fetches intraday ticks (BDTICK) for a security over a datetime range (mirrors xbbg's bdtick layout).
        :param security: Security ticker.
        :param start: Start datetime (datetime or 'YYYY-MM-DD HH:MM:SS' string).
        :param stop: End datetime (datetime or 'YYYY-MM-DD HH:MM:SS' string).
        :param event_types: Event type or list of event types - TRADE, BID, ASK, etc.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :returns: One row per tick with its timestamp, value, size and event type.
        """
        def _fetch_():
            return blp.bdtick(security, start, stop, event_types=event_types,
                              backend=self._api_._backend_(legacy))
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Ticks Operation: Fetched {len(df)} ticks ({timer.result()})")
        return df