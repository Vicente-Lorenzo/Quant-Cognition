from __future__ import annotations

from enum import Enum
from typing import Union, Any
from difflib import SequenceMatcher

from Library.Utility.Typing import normalize

class EnumerationAPI(Enum):

    @classmethod
    def names(cls) -> list[str]:
        return [member.name for member in cls]

    @classmethod
    def parse(cls, value: Any) -> Any:
        if value is None: return None
        if isinstance(value, cls): return value
        try: return cls.__members__[value] if isinstance(value, str) else cls(value)
        except (KeyError, ValueError): return value

    @classmethod
    def _missing_(cls, value: object) -> Union[EnumerationAPI, None]:
        if not isinstance(value, str):
            return None
        normalized_value = normalize(value)
        for member in cls:
            if normalize(member.name) == normalized_value:
                return member
        best_match = None
        highest_ratio = 0.0
        for member in cls:
            normalized_name = normalize(member.name)
            ratio = SequenceMatcher(None, normalized_name, normalized_value).ratio()
            if ratio >= 0.9 and ratio > highest_ratio:
                highest_ratio = ratio
                best_match = member
        return best_match