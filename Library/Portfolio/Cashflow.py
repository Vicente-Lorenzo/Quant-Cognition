from datetime import datetime
from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey, ForeignKey
from Library.Database.Datapoint import DatapointAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Account import AccountAPI

@dataclass
class CashflowAPI(DatapointAPI):

    Schema: ClassVar[str] = PortfolioAPI.Schema
    Table: ClassVar[str] = "Cashflow"

    UID: Union[int, None] = None
    Account: Union[int, None] = None
    Timestamp: Union[datetime, None] = None
    Type: Union[str, None] = None
    Delta: Union[float, None] = None
    Balance: Union[float, None] = None
    Equity: Union[float, None] = None
    Note: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.Int64),
            self.ID.Account: ForeignKey(pl.Int64, reference=AccountAPI.reference("ON DELETE CASCADE")),
            self.ID.Timestamp: pl.Datetime(),
            self.ID.Type: pl.String(),
            self.ID.Delta: pl.Float64(),
            self.ID.Balance: pl.Float64(),
            self.ID.Equity: pl.Float64(),
            self.ID.Note: pl.String(),
            **super().Structure
        }