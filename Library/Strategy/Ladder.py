from copy import deepcopy
from pathlib import Path
from typing import Union

from Library.Logging import LoggingAPI
from Library.Strategy.Strategy import StrategyAPI
from Library.Utility.IO import read_yaml, write_yaml
from Library.Strategy.Syntax import SyntaxAPI
from Library.Utility.Parameter import Parameter
from Library.Utility.Path import inspect_persistent

class LadderAPI:

    Folder: str = "Overrides"
    RUNGS: tuple = ("Provider", "Category", "Ticker", "Timeframe")
    _ORIGIN_: str = "Defaults"

    def __init__(self, root: Union[str, Path, None] = None) -> None:
        self._root_: Path = Path(root) if root else inspect_persistent(self.Folder)
        self._log_ = LoggingAPI("Parameter Management")

    @property
    def root(self) -> Path:
        return self._root_

    @staticmethod
    def merge(base: Union[dict, None], override: Union[dict, None]) -> dict:
        merged = deepcopy(base) if base else {}
        for key, value in (override or {}).items():
            current = merged.get(key)
            blended = isinstance(value, dict) and isinstance(current, dict) and SyntaxAPI.numbered(value) == SyntaxAPI.numbered(current)
            merged[key] = LadderAPI.merge(current, value) if blended else deepcopy(value)
        return merged

    @staticmethod
    def scopes(*rungs: str) -> tuple:
        return tuple(tuple(rungs[:depth]) for depth in range(len(rungs) + 1))

    def _load_(self, path: Path) -> dict:
        if not path.is_file(): return {}
        try: return read_yaml(path, safe=False)
        except Exception as error:
            self._log_.warning(lambda path=path, error=error: f"Override Load: Failed · {path} · {error}")
            return {}

    def override(self, kind: str, *rungs: str) -> Path:
        return self._root_.joinpath(*rungs, f"{kind}.yml")

    def sparse(self, strategy: type[StrategyAPI], kind: str, *rungs: str) -> dict:
        return deepcopy(self._load_(self.override(kind, *rungs)).get(strategy.key()) or {})

    def resolve(self, strategy: type[StrategyAPI], kind: str, *rungs: str) -> tuple[dict, list]:
        merged, trail = strategy.defaults(kind), [self._ORIGIN_]
        for scope in self.scopes(*rungs):
            for ancestor in strategy.lineage(kind):
                path = self.override(ancestor, *scope)
                section = self._load_(path).get(strategy.key())
                if section is None: continue
                merged = self.merge(merged, section)
                trail.append(str(path))
        return merged, trail

    def parameterize(self, strategy: type[StrategyAPI], kind: str, *rungs: str) -> tuple[Parameter, list]:
        sections, trail = self.resolve(strategy, kind, *rungs)
        return Parameter(sections, self.override(kind, *rungs)), trail

    def pin(self, strategy: type[StrategyAPI], kind: str, source: Union[str, Path], target: Union[str, Path]) -> tuple[Parameter, list]:
        source = Path(source)
        return Parameter(self.merge(strategy.defaults(kind), read_yaml(source, safe=False)), Path(target)), [self._ORIGIN_, str(source)]

    def sources(self, strategy: type[StrategyAPI], kind: str, *rungs: str) -> dict:
        found = {}
        for scope in self.scopes(*rungs):
            for ancestor in strategy.lineage(kind):
                sections = self._load_(self.override(ancestor, *scope)).get(strategy.key()) or {}
                for section, body in sections.items():
                    if not isinstance(body, dict):
                        found[(section, None)] = (scope, ancestor)
                        continue
                    for name in body: found[(section, name)] = (scope, ancestor)
        return found

    def promote(self, strategy: type[StrategyAPI], kind: str, sections: dict, *rungs: str, origin: Union[str, None] = None) -> Path:
        path = self.override(kind, *rungs)
        document = self._load_(path)
        document[strategy.key()] = sections
        if origin: document.setdefault("Provenance", {})[strategy.key()] = origin
        write_yaml(path, document, safe=False)
        self._log_.info(lambda: f"Override Promote: Saved · {strategy.key()} · {kind} · {path}")
        return path

    def provenance(self, strategy: type[StrategyAPI], kind: str, *rungs: str) -> str:
        for scope in reversed(self.scopes(*rungs)):
            for ancestor in reversed(strategy.lineage(kind)):
                document = self._load_(self.override(ancestor, *scope))
                if strategy.key() not in document: continue
                origin = (document.get("Provenance") or {}).get(strategy.key())
                where = Path(*scope).as_posix() if scope else "Global"
                return origin or f"Override · {where}" + ("" if ancestor == kind else f" · via {ancestor}")
        return self._ORIGIN_

__all__ = ["LadderAPI"]