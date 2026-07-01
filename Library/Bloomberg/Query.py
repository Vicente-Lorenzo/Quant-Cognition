"""Bloomberg Query Language (BQL) interface backed by xbbg."""
from xbbg import blp

from Library.Database.Dataframe import pd, pl
from Library.Utility.Service import ServiceAPI
from Library.Utility.Typing import MISSING, Missing

class QueryAPI(ServiceAPI):
    """Bloomberg Query Language (BQL) interface (xbbg blp.bql)."""

    def execute(self,
                query: str,
                legacy: bool | Missing = MISSING) -> pd.DataFrame | pl.DataFrame:
        """
        Executes a BQL query and returns the result as a frame.
        :param query: BQL query string (e.g. "get(px_last) for(['AAPL US Equity'])").
        :param legacy: If True, returns a Pandas DataFrame; if False, Polars. Defaults to the API setting.
        :returns: A frame whose columns follow the BQL query's own output schema.
        """
        def _execute_():
            # VERIFY: xbbg 1.4.1 blp.bql backend support
            return blp.bql(query, backend=self._api_._backend_(legacy))
        timer, df = super()._fetch_(callback=_execute_)
        self._log_.info(lambda: f"Execute Operation: Executed · {len(df)} Rows ({timer.result()})")
        return df