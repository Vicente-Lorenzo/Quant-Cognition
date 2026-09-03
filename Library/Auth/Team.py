from __future__ import annotations

from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Database.Dataframe import pl
from Library.Database.Database import PrimaryKey
from Library.Database.Datapoint import DatapointAPI

@dataclass
class TeamAPI(DatapointAPI):

    Schema: ClassVar[str] = "Auth"
    Table: ClassVar[str] = "Team"

    UID: Union[str, None] = None
    Name: Union[str, None] = None
    Abbreviation: Union[str, None] = None
    Email: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.UID: PrimaryKey(pl.String),
            self.ID.Name: pl.String(),
            self.ID.Abbreviation: pl.String(),
            self.ID.Email: pl.String(),
            **super().Structure
        }