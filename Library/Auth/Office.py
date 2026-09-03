from __future__ import annotations

from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI

@dataclass
class OfficeAPI(DatapointAPI):

    Schema: ClassVar[str] = "Auth"
    Table: ClassVar[str] = "Office"

    UID: Union[str, None] = None
    Name: Union[str, None] = None
    Address: Union[str, None] = None
    ZipCode: Union[str, None] = None
    City: Union[str, None] = None
    Region: Union[str, None] = None
    Country: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Name: pl.String(),
            self.ID.Address: pl.String(),
            self.ID.ZipCode: pl.String(),
            self.ID.City: pl.String(),
            self.ID.Region: pl.String(),
            self.ID.Country: pl.String(),
            **super().Structure
        }