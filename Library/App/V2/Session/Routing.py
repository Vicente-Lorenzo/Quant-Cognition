from typing_extensions import Self
from dataclasses import dataclass, field

from Library.App.V2.Session.Storage import StorageAPI
from Library.Utility.Typing import MISSING

@dataclass(kw_only=True)
class RoutingAPI(StorageAPI):

    href: str | None = field(default=MISSING, init=True, repr=True)
    refresh: bool = field(default=False, init=True, repr=True)
    external: bool = field(default=False, init=True, repr=True)
    replace: bool = field(default=False, init=True, repr=True)

    def redirect(self, href: str, *, refresh: bool = False, external: bool = False) -> Self:
        self.trigger()
        self.href = href
        self.refresh = refresh
        self.external = external
        return self

    def clear(self) -> Self:
        self.href = MISSING
        self.refresh = False
        self.external = False
        self.replace = False
        return self