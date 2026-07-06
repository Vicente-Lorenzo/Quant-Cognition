"""Bloomberg Historical Data interface backed by xbbg BDH."""
from datetime import date, datetime
from xbbg import blp

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
        period = self._PERIODICITY_[str(timeframe).upper()]
        def _fetch_():
            return blp.bdh(securities, fields, start, stop or "today", Per=period, backend=self._api_._backend_(legacy), overrides=overrides)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Fetch Operation: Fetched {len(df)} Data Points ({timer.result()})")
        return df