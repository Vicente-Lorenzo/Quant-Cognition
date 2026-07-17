from typing_extensions import Self
from dataclasses import dataclass

from Library.App.V2.Session.State import StateAPI

@dataclass(kw_only=True)
class TriggerAPI(StateAPI):

    def trigger(self) -> Self:
        super().trigger()
        self.increment()
        return self