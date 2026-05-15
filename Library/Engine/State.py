from __future__ import annotations

from typing import Any, Callable, Union
from typing_extensions import Self
from dataclasses import dataclass, field, InitVar

from Library.Database.Dataclass import DataclassAPI
from Library.Engine.Transition import TransitionAPI

@dataclass(slots=True)
class StateAPI(DataclassAPI):
    Name: Union[str, None]
    End: bool

    events: InitVar[int]
    _transitions_: list = field(init=False, repr=False)

    def __post_init__(self, events: int) -> None:
        self._transitions_ = [None] * events

    def on(self, event: Any, to: Self, action: Union[Callable[[Any], Union[list, None]], None], reason: Union[str, None]) -> None:
        try: index = event.value
        except AttributeError: index = int(event)
        self._transitions_[index] = TransitionAPI(To=to, Action=action, Reason=reason)

__all__ = ["StateAPI"]