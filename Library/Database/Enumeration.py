from __future__ import annotations

from enum import Enum
from typing import Union, Any
from difflib import SequenceMatcher

class Enumeration(Enum):
    
    @classmethod
    def parse(cls, value: Any) -> Any:
        if value is None: return None
        if isinstance(value, cls): return value
        try: return cls.__members__[value] if isinstance(value, str) else cls(value)
        except (KeyError, ValueError): return value
        
    @classmethod
    def _missing_(cls, value: object) -> Union[Enumeration, None]:
        if not isinstance(value, str):
            return None
        normalized_value = "".join(c for c in value if c.isalnum()).lower()
        for member in cls:
            if "".join(c for c in member.name if c.isalnum()).lower() == normalized_value:
                return member
        best_match = None
        highest_ratio = 0.0
        for member in cls:
            normalized_name = "".join(c for c in member.name if c.isalnum()).lower()
            ratio = SequenceMatcher(None, normalized_name, normalized_value).ratio()
            if ratio >= 0.9 and ratio > highest_ratio:
                highest_ratio = ratio
                best_match = member
        return best_match