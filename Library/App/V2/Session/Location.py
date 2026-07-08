from dataclasses import dataclass, field

from Library.App.V2.Session.Storage import StorageAPI

@dataclass(kw_only=True)
class LocationAPI(StorageAPI):

    history: list[str] = field(default_factory=list, init=True, repr=True)

    def current(self) -> str | None:
        if 0 <= self.index < len(self.history):
            return self.history[self.index]
        return None

    def register(self, *, path: str) -> None:
        if self.index == -1:
            self.history = [path]
            self.index = 0
            return
        if self.current() == path:
            return
        if self.index < len(self.history) - 1:
            self.history = self.history[: self.index + 1]
        self.history.append(path)
        self.index = len(self.history) - 1

    def backward(self, *, step: bool = False) -> str | None:
        if self.index <= 0:
            return None
        if not step:
            return self.history[self.index - 1]
        self.index -= 1
        return self.history[self.index]

    def forward(self, *, step: bool = False) -> str | None:
        if self.index < 0 or self.index >= len(self.history) - 1:
            return None
        if not step:
            return self.history[self.index + 1]
        self.index += 1
        return self.history[self.index]