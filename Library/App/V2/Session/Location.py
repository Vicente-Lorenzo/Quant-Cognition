from dataclasses import dataclass, field

from Library.App.V2.Session.State import StateAPI

@dataclass(kw_only=True)
class LocationAPI(StateAPI):

    history: list[str] = field(default_factory=list)
    cursor: int = field(default=-1)

    def current(self) -> str | None:
        if 0 <= self.cursor < len(self.history):
            return self.history[self.cursor]
        return None

    def register(self, *, path: str) -> None:
        if self.cursor == -1:
            self.history = [path]
            self.cursor = 0
            return
        if self.current() == path:
            return
        if self.cursor < len(self.history) - 1:
            self.history = self.history[: self.cursor + 1]
        self.history.append(path)
        self.cursor = len(self.history) - 1

    def backward(self, *, step: bool = False) -> str | None:
        if self.cursor <= 0:
            return None
        if not step:
            return self.history[self.cursor - 1]
        self.cursor -= 1
        return self.history[self.cursor]

    def forward(self, *, step: bool = False) -> str | None:
        if self.cursor < 0 or self.cursor >= len(self.history) - 1:
            return None
        if not step:
            return self.history[self.cursor + 1]
        self.cursor += 1
        return self.history[self.cursor]