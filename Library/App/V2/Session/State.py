from typing_extensions import Self
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI

@dataclass(kw_only=True)
class StateAPI(DataclassAPI):

    index: int = field(default=0)
    counter: int = field(default=0)
    total: int = field(default=0)

    def trigger(self) -> Self:
        self.index += 1
        return self

    def increment(self, value: int = 1) -> Self:
        self.counter += value
        return self

    def progress(self) -> float:
        return self.counter / self.total if self.total else 0.0

    def reset(self) -> Self:
        self.counter = 0
        return self