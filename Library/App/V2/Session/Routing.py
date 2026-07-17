from typing_extensions import Self
from dataclasses import dataclass, field

from Library.App.V2.Session.State import StateAPI
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class RoutingAPI(StateAPI):

    href: str | None = field(default=MISSING)
    refresh: bool = field(default=False)
    external: bool = field(default=False)
    replace: bool = field(default=False)

    def redirect(self, href: str, *, refresh: bool = False, external: bool = False, replace: bool = False) -> Self:
        self.trigger()
        self.href = href
        self.refresh = refresh
        self.external = external
        self.replace = replace
        return self

    def clear(self) -> Self:
        self.href = MISSING
        self.refresh = False
        self.external = False
        self.replace = False
        return self