from __future__ import annotations

from Library.Utility.Enumeration import EnumerationAPI

class RoleAPI(EnumerationAPI):

    Public = 0
    Viewer = 1
    Editor = 2
    Moderator = 3
    Administrator = 4

    @classmethod
    def coerce(cls, value: str | int | RoleAPI | None, default: RoleAPI | None = None) -> RoleAPI:
        parsed = cls.parse(value)
        if isinstance(parsed, cls): return parsed
        return default if isinstance(default, cls) else cls.Public

    def grants(self, required: str | int | RoleAPI) -> bool:
        required = RoleAPI.parse(required)
        return isinstance(required, RoleAPI) and self.value >= required.value