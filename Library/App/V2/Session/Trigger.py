from typing_extensions import Self
from dataclasses import dataclass

from Library.App.V2.Session.Storage import StorageAPI

@dataclass(kw_only=True)
class TriggerAPI(StorageAPI):

    def trigger(self) -> Self:
        super().trigger()
        self.increment()
        return self