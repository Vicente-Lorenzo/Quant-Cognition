from typing_extensions import Self
from dataclasses import dataclass, field

from Library.Database.Dataclass import DataclassAPI

@dataclass(kw_only=True)
class StorageAPI(DataclassAPI):

    index: int = field(default=0, init=True, repr=True)
    counter: int = field(default=0, init=True, repr=True)
    total: int = field(default=0, init=True, repr=True)

    def trigger(self) -> Self:
        self.index += 1
        return self

    def increment(self, value: int = 1) -> Self:
        self.counter += value
        return self

    def progress(self) -> float:
        return self.counter / self.total

    def reset(self) -> Self:
        self.counter = 0
        return self