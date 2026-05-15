from __future__ import annotations

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
        first = None
        for m in self._machines_:
            r = m.perform(event, args)
            if r and first is None: first = r
        return first if first is not None else []

__all__ = ["EngineAPI"]