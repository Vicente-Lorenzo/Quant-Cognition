from dataclasses import dataclass, InitVar, field
from typing import Optional
def overridefield(func):
    func._overridefield_ = True
    return func
@dataclass
class Test:
    Ask: InitVar[Optional[float]] = field(default=None, init=True, repr=False)
    @property
    @overridefield
    def Ask(self) -> Optional[float]:
        return getattr(self, '_ask', None)
    def __post_init__(self, Ask):
        self._ask = Ask
t = Test()
print(t.Ask)