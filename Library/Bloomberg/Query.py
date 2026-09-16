"""Bloomberg Query Language (BQL) interface backed by xbbg."""
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
        return self._api_._engine_(self, "Execute Operation: Executed", "Rows", "bql", query, legacy=legacy)