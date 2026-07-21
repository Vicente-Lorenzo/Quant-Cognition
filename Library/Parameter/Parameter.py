from __future__ import annotations

from typing import Union, Any
import copy
import yaml

from pathlib import Path
from typing_extensions import Self

class ParameterAPI:

    PATH = Path("Library") / Path("Parameter")
    
    def __init__(self, path: Union[Path, None] = None) -> None:
        self.path = ParameterAPI.PATH if not path else path
        if not path: self.path.mkdir(parents=True, exist_ok=True)
        self._cache_ = {}

    def _resolve_path_(self, *args) -> Path:
        return self.path.joinpath(*args)

    def _get_file_path_(self, name: str) -> Path:
        return self._resolve_path_(name).with_suffix(".yml")

    @staticmethod
    def _safe_load_(file_path: Path) -> dict:
        with file_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _safe_dump_(file_path: Path, data: dict) -> None:
        with file_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    def _get_item_(self, name: str) -> Union[ParameterAPI, Parameter, None]:
        item_path = self._resolve_path_(name)
        file_path = self._get_file_path_(name)

        if file_path.is_file():
            mtime = file_path.stat().st_mtime
            if name in self._cache_:
                cached_mtime, cached_param = self._cache_[name]
                if cached_mtime == mtime:
                    return cached_param
            data = self._safe_load_(file_path)
            param = Parameter(data, file_path)
            self._cache_[name] = (mtime, param)
            return param
        if item_path.is_dir():
            return ParameterAPI(item_path)
        return None

    def _set_item_(self, name: str, value: Union[dict, ParameterAPI, Parameter]) -> None:
        item_path = self._resolve_path_(name)
        file_path = self._get_file_path_(name)

        if isinstance(value, ParameterAPI):
            item_path.mkdir(parents=True, exist_ok=True)
        elif isinstance(value, (dict, Parameter)):
            file_path.parent.mkdir(parents=True, exist_ok=True)
            data_to_dump = value.data if isinstance(value, Parameter) else value
            self._safe_dump_(file_path, data_to_dump)
            mtime = file_path.stat().st_mtime
            if isinstance(value, Parameter):
                self._cache_[name] = (mtime, value)
            else:
                self._cache_[name] = (mtime, Parameter(data_to_dump, file_path))
        else:
            raise ValueError("Only dictionaries, ParameterAPI, or Parameter instances can be set directly.")

    def _delete_item_(self, name: str) -> None:
        item_path = self._resolve_path_(name)
        file_path = self._get_file_path_(name)

        if item_path.is_dir():
            import shutil
            shutil.rmtree(item_path)
            self._cache_.pop(name, None)
        elif file_path.is_file():
            file_path.unlink()
            self._cache_.pop(name, None)
        else:
            raise KeyError(f"{name} does not exist.")

    def __getattr__(self, name: str) -> Union[ParameterAPI, Parameter, None]:
        return self._get_item_(name)

    def __getitem__(self, name: str) -> Union[ParameterAPI, Parameter, None]:
        return self._get_item_(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("path", "_cache_"):
            super().__setattr__(name, value)
        else:
            self._set_item_(name, value)

    def __setitem__(self, name: str, value: Any) -> None:
        self._set_item_(name, value)

    def __delattr__(self, name: str) -> None:
        self._delete_item_(name)

    def __delitem__(self, name: str) -> None:
        self._delete_item_(name)

    def __repr__(self) -> str:
        return repr(f"ParameterAPI(path={self.path})")

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