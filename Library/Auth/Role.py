from __future__ import annotations

from Library.Utility.Enumeration import EnumerationAPI

class RoleAPI(EnumerationAPI):

    Public = 0
    Viewer = 1
    Member = 2
    Moderator = 3
    Administrator = 4

    def grants(self, required: str | int | RoleAPI) -> bool:
        required = RoleAPI.parse(required)
        return isinstance(required, RoleAPI) and self.value >= required.value