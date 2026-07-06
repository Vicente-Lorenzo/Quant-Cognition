"""Bloomberg Reference Data interface backed by xbbg BDP / BDS."""
from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class ReferenceAPI(ServiceAPI):
    """Bloomberg Reference Data interface (xbbg BDP for point-in-time fields, BDS for bulk/array fields)."""

    def fetch(self,
              securities: str | list[str],
              fields: str | list[str],
              overrides: dict[str, str] = None,
              legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        """
        Fetches point-in-time reference data (BDP) for one security/field or lists of them.
        :param securities: Security ticker or list of tickers.
        :param fields: Field mnemonic or list of fields.
        :param overrides: Optional {fieldId: value} override mapping.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :returns: Long-format frame with columns "ticker", "field" and "value" (one row per security and field).
        """
        def _fetch_():
            return self._api_._call_("bdp", securities, fields, legacy=legacy, overrides=overrides)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Fetch Operation: Fetched {len(df)} Data Points ({timer.result()})")
        return df

    def bulk(self,
             securities: str | list[str],
             field: str,
             overrides: dict[str, str] = None,
             legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        """
        Fetches bulk reference data (BDS) - array fields that return a whole table per security, such
        as index members (INDX_MEMBERS) or dividend history (DVD_HIST_ALL).
        :param securities: Security ticker or list of tickers.
        :param field: Bulk field mnemonic (e.g. INDX_MEMBERS, DVD_HIST_ALL).
        :param overrides: Optional {fieldId: value} override mapping.
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :returns: One row per bulk record, tagged with "ticker" and "field" columns plus the field's own columns.
        """
        def _fetch_():
            return self._api_._call_("bds", securities, field, legacy=legacy, overrides=overrides)
        timer, df = super()._fetch_(callback=_fetch_)
        self._log_.info(lambda: f"Bulk Operation: Fetched {len(df)} Records ({timer.result()})")
        return df