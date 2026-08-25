from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Union

import yaml
from typing_extensions import Self

class Parameter:

    def __init__(self, data: dict, path: Union[Path, str], parent: Union[Parameter, None] = None, parent_key: Union[str, None] = None) -> None:
        self.data = data
        self.path = Path(path)
        self.parent = parent
        self.parent_key = parent_key

        self._cache_ = {}
        for k, v in self.data.items():
            if isinstance(v, dict):
                self._cache_[k] = Parameter(v, self.path, parent=self, parent_key=k)

    def __getattr__(self, key: str) -> Any:
        if key in self._cache_:
            return self._cache_[key]
        if key in self.data:
            return self.data[key]
        return None

    def __getitem__(self, key: str) -> Any:
        return self.__getattr__(key)

    def __setattr__(self, key: str, value: Any) -> None:
        if key in ("data", "path", "parent", "parent_key", "_cache_"):
            super().__setattr__(key, value)
        else:
            if isinstance(value, Parameter):
                self.data[key] = value.data
                self._cache_[key] = value
                value.parent = self
                value.parent_key = key
            elif isinstance(value, dict):
                self.data[key] = value
                self._cache_[key] = Parameter(value, self.path, parent=self, parent_key=key)
            else:
                self.data[key] = value
                self._cache_.pop(key, None)
            self._save_()

    def __setitem__(self, key: str, value: Any) -> None:
        self.__setattr__(key, value)

    def __delattr__(self, key: str) -> None:
        if key in self.data:
            del self.data[key]
            self._cache_.pop(key, None)
            self._save_()
        else:
            raise KeyError(f"Key {key} not found.")

    def __delitem__(self, key: str) -> None:
        self.__delattr__(key)

    def _save_(self) -> None:
        if self.parent:
            self.parent.data[self.parent_key] = self.data
            self.parent._save_()
        else:
            with self.path.open("w", encoding="utf-8") as f:
                yaml.safe_dump(self.data, f)

    def keys(self) -> Any:
        return self.data.keys()

    def values(self) -> Any:
        return self.data.values()

    def items(self) -> Any:
        return self.data.items()

    def clone(self) -> Self:
        return Parameter(copy.deepcopy(self.data), self.path, parent=self.parent, parent_key=self.parent_key)

    def __repr__(self) -> str:
        return repr(f"Parameter(path={self.path}, data={self.data})")

SEPARATOR = " · "
SEPARATORS = ("·", ";")
ALTERNATIVE = "|"

def _decode_(text: str):
    part = str(text).strip()
    if part == "": return None
    for cast in (int, float):
        try: return cast(part)
        except ValueError: continue
    return part

def numbered(body) -> bool:
    return isinstance(body, dict) and bool(body) and all(str(key).replace("-", "").strip().isdigit() for key in body)

def format_value(value) -> str:
    if value is None: return ""
    if isinstance(value, (list, tuple)): return ", ".join("" if item is None else str(item) for item in value)
    return str(value)

def parse_value(text: str) -> list:
    return [_decode_(part) for part in str(text).split(",")]

def format_slots(value) -> str:
    if value is None: return ""
    if not isinstance(value, (list, tuple)): return str(value)
    slots = []
    for slot in value:
        options = slot if isinstance(slot, (list, tuple)) else [slot]
        slots.append(ALTERNATIVE.join("" if option is None else str(option) for option in options))
    return SEPARATOR.join(slots)

def parse_slots(text: str) -> list:
    body = str(text).strip()
    if body == "": return []
    for symbol in SEPARATORS[1:]: body = body.replace(symbol, SEPARATORS[0])
    slots = []
    for part in body.split(SEPARATORS[0]):
        options = [_decode_(option) for option in part.split(ALTERNATIVE)]
        slots.append(options if len(options) > 1 else options[0])
    return slots