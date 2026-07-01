"""Bloomberg Historical Data interface backed by xbbg BDH."""
from datetime import date, datetime
from xbbg import blp, ovr

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class HistoricalAPI(ServiceAPI):
    """Bloomberg Historical Data interface (xbbg BDH end-of-day time series)."""

    _PERIODICITY_ = {"DAILY": "D", "WEEKLY": "W", "MONTHLY": "M", "QUARTERLY": "Q", "YEARLY": "Y"}

    def fetch(self,
              securities: str | list[str],
              fields: str | list[str],
              start: str | date | datetime,
              stop: str | date | datetime = None,
              timeframe: str = "DAILY",
              overrides: dict[str, str] = None,
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        """
        Fetches historical time series (BDH) for one security/field or lists of them.
        :param securities: Security ticker or list of tickers.
        :param fields: Field mnemonic or list of fields.
        :param start: Start date/datetime (or 'YYYY-MM-DD' string).
        :param stop: End date/datetime (defaults to xbbg's today).
        :param timeframe: Periodicity - DAILY, WEEKLY, MONTHLY, QUARTERLY or YEARLY.
        :param overrides: Optional {fieldId: value} override mapping.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :returns: Long-format frame with columns "ticker", "date", "field" and "value" (one row per security, date and field).
        """
        if isinstance(start, (date, datetime)): start = start.strftime("%Y-%m-%d")
        if isinstance(stop, (date, datetime)): stop = stop.strftime("%Y-%m-%d")
        period = self._PERIODICITY_.get(str(timeframe).upper(), "D")
        def _fetch_():
            backend = self._api_._backend_(legacy)
            overrides_ = ovr(**overrides) if overrides else None
            # VERIFY: xbbg 1.4.1 bdh periodicity option name (classic xbbg used Per='D'/'W'/'M')
            if stop:
                return blp.bdh(securities, fields, start, stop, Per=period, backend=backend, overrides=overrides_)
            return blp.bdh(securities, fields, start, Per=period, backend=backend, overrides=overrides_)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Fetch Operation: Fetched {len(df)} historical data points ({timer.result()})")
        return df