import time
from typing import Callable, Union
from pathlib import Path

from Library.Utility.IO import remove
from Library.Utility.Path import PathAPI
from Library.Utility.Typing import MISSING, Missing, format

class FileAPI:

    def __init__(self, data: Union[str, Path, PathAPI], *, encoding: str = "utf-8"):
        if isinstance(data, PathAPI):
            self._data_: str = data.file.read_text(encoding=encoding)
        elif isinstance(data, Path):
            self._data_: str = data.read_text(encoding=encoding)
        else:
            self._data_: str = data

    def __call__(self, *args, **kwargs) -> str:
        return format(self._data_, *args, **kwargs)

    def __str__(self) -> str:
        return self._data_

    def __repr__(self) -> str:
        return repr(self._data_)

class PruneAPI:

    DAYS: int = 30

    @staticmethod
    def horizon(days: int = DAYS) -> float:
        return time.time() - days * 86400

    @staticmethod
    def newest(folder: Path) -> float:
        stamps = [entry.stat().st_mtime for entry in folder.rglob("*") if entry.is_file()]
        return max(stamps) if stamps else 0.0

    @classmethod
    def stale(cls, path: Path, horizon: float) -> bool:
        try: return (cls.newest(path) if path.is_dir() else path.stat().st_mtime) < horizon
        except OSError: return False

    @staticmethod
    def weight(path: Path) -> int:
        try:
            if path.is_file(): return path.stat().st_size
            return sum(entry.stat().st_size for entry in path.rglob("*") if entry.is_file())
        except OSError:
            return 0

    @classmethod
    def discard(cls, path: Path) -> int:
        size = cls.weight(path)
        return size if remove(path) else 0

    @classmethod
    def sweep(cls, candidates, horizon: float, spare: Union[Callable, Missing] = MISSING) -> tuple:
        removed, reclaimed = 0, 0
        for candidate in candidates:
            candidate = Path(candidate)
            if not cls.stale(candidate, horizon): continue
            if spare is not MISSING and spare(candidate): continue
            size = cls.discard(candidate)
            if not size and candidate.exists(): continue
            removed += 1
            reclaimed += size
        return removed, reclaimed

    @classmethod
    def prune(cls, folders, days: int = DAYS, patterns=("*",), recursive: bool = False, spare: Union[Callable, Missing] = MISSING) -> tuple:
        candidates = {}
        for folder in folders:
            folder = Path(folder)
            if not folder.is_dir(): continue
            for pattern in patterns:
                for candidate in (folder.rglob(pattern) if recursive else folder.glob(pattern)): candidates.setdefault(candidate, None)
        return cls.sweep(candidates, cls.horizon(days), spare)