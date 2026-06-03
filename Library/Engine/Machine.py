from __future__ import annotations

from typing import Any, Union
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI
from Library.Logging import HandlerLoggingAPI
from Library.Engine.State import StateAPI

@dataclass(slots=True)
class MachineAPI(DataclassAPI):
    Name: Union[str, None]
    Events: int
    At: Union[StateAPI, None] = field(default=None, init=False)

    _states_: dict[str, StateAPI] = field(default_factory=dict, init=False, repr=False)
    _log_: Union[HandlerLoggingAPI, None] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._log_ = HandlerLoggingAPI(Class=type(self).__name__, Subclass=self.Name)

    def state(self, name: str, end: bool = False) -> StateAPI:
        existing = self._states_.get(name)
        if existing is not None: return existing
        new_state = StateAPI(Name=name, End=end, events=self.Events)
        self._states_[name] = new_state
        if self.At is None: self.At = new_state
        return new_state

    def perform(self, event: Any, args: Any) -> list:
        try: index = event.value
        except AttributeError: index = int(event)
        transition = self.At._transitions_[index]
        if transition is None:
            return []
        ret = transition.perform(args)
        if transition.Reason is not None:
            log = self._log_.debug if transition.To is self.At else self._log_.info
            log(lambda: f"[{self.At.Name}] → ({transition.Reason}) → [{transition.To.Name}]")
        self.At = transition.To
        return ret if ret is not None else []

__all__ = ["MachineAPI"]