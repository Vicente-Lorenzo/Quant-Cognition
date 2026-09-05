from typing import Any
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataclass import DataclassAPI
from Library.Engine.Machine import MachineAPI

@dataclass(slots=True)
class EngineAPI(DataclassAPI):

    machines: InitVar[list[MachineAPI]]
    _machines_: list[MachineAPI] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self, machines: list[MachineAPI]) -> None:
        self._machines_ = machines

    @property
    def IsTerminated(self) -> bool:
        return all(m.At.End for m in self._machines_)

    def perform(self, event: Any, args: Any) -> list:
        actions = []
        for m in self._machines_:
            r = m.perform(event, args)
            if r: actions.extend(r)
        return actions

__all__ = ["EngineAPI"]