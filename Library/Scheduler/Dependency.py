from dataclasses import dataclass
from typing import Union, ClassVar

from Library.Scheduler.Task import TaskAPI
from Library.Scheduler.Workflow import WorkflowAPI
from Library.Database.Dataframe import pl
from Library.Database.Datapoint import DatapointAPI
from Library.Database.Database import ForeignKey

@dataclass
class DependencyAPI(DatapointAPI):

    Schema: ClassVar[str] = WorkflowAPI.Schema
    Table: ClassVar[str] = "Dependency"

    WID: Union[str, None] = None
    Predecessor: Union[str, None] = None
    Successor: Union[str, None] = None

    @property
    def Structure(self) -> dict:
        return {
            self.ID.WID: ForeignKey(pl.String, reference=f'"{WorkflowAPI.Schema}"."{WorkflowAPI.Table}"("{WorkflowAPI.ID.UID}")', primary=True),
            self.ID.Predecessor: ForeignKey(pl.String, reference=f'"{TaskAPI.Schema}"."{TaskAPI.Table}"("{TaskAPI.ID.UID}")', primary=True),
            self.ID.Successor: ForeignKey(pl.String, reference=f'"{TaskAPI.Schema}"."{TaskAPI.Table}"("{TaskAPI.ID.UID}")', primary=True),
            **super().Structure
        }