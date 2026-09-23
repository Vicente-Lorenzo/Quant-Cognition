from typing import Union

from Library.Auth.Role import RoleAPI
from Library.Utility.Enumeration import EnumerationAPI

class AccessLevel(EnumerationAPI):

    Denied = 0
    View = 1
    Run = 2
    Edit = 3

class AccessAPI:

    @staticmethod
    def roles() -> list[str]:
        return [name for name in RoleAPI.names() if name != RoleAPI.Public.name]

    @staticmethod
    def parse(value) -> Union[RoleAPI, None]:
        if value is None or value == "": return None
        parsed = RoleAPI.parse(value)
        if not isinstance(parsed, RoleAPI): raise ValueError(f"Access Threshold: Failed · Unknown role {value} · Expected one of {' · '.join(RoleAPI.names())}")
        return parsed

    @staticmethod
    def label(value) -> str:
        parsed = RoleAPI.parse(value)
        return parsed.name if isinstance(parsed, RoleAPI) else "Owner only"

    @classmethod
    def validate(cls, lower, upper, *, names: tuple, setter: Union[RoleAPI, None] = None, previous: tuple = (None, None)) -> tuple:
        lower, upper = cls.parse(lower), cls.parse(upper)
        for name, value, kept in zip(names, (lower, upper), previous):
            if value is None: continue
            if value is RoleAPI.Public: raise ValueError(f"Access Threshold: Failed · {name} cannot be Public")
            if setter is not None and value is not RoleAPI.parse(kept) and not setter.grants(value): raise ValueError(f"Access Threshold: Failed · {name} {value.name} is above your own role {setter.name}")
        if lower is None and upper is not None: raise ValueError(f"Access Threshold: Failed · {names[1]} must be owner only when {names[0]} is owner only")
        if lower is not None and upper is not None and upper.value < lower.value: raise ValueError(f"Access Threshold: Failed · {names[1]} {upper.name} is below {names[0]} {lower.name}")
        return lower, upper

    @staticmethod
    def allows(threshold, *, role: RoleAPI, user: Union[str, None], owner: Union[str, None]) -> bool:
        if role is RoleAPI.Administrator: return True
        if user is not None and user == owner: return True
        parsed = RoleAPI.parse(threshold)
        return isinstance(parsed, RoleAPI) and parsed is not RoleAPI.Public and role.grants(parsed)

    @staticmethod
    def claim(owner: Union[str, None], *, role: RoleAPI, user: Union[str, None]) -> None:
        if role is RoleAPI.Administrator or owner is None or owner == user: return
        raise PermissionError(f"Access Owner: Failed · Only an Administrator may assign {owner} as owner · {user or 'Anonymous'} may only own what they create")