from __future__ import annotations

from typing import Any, Callable, Union, TYPE_CHECKING
from dataclasses import dataclass

from Library.Database.Dataclass import DataclassAPI

if TYPE_CHECKING:
    from Library.Engine.State import StateAPI

@dataclass(slots=True)
class TransitionAPI(DataclassAPI):
    To: StateAPI
    Action: Union[Callable[[Any], Union[list, None]], None]
    Reason: Union[str, None]

    def perform(self, args: Any) -> Union[list, None]:
        return self.Action(args) if self.Action is not None else None

__all__ = ["TransitionAPI"]