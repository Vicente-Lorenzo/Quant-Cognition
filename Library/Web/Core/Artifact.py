import os
import re
import flask
import functools
from dataclasses import dataclass
from pathlib import Path
from typing_extensions import Self

from Library.Scheduler.Executor import ExecutorAPI
from Library.System.System import SystemAPI
from Library.Utility.Datetime import STAMP, string_to_datetime
from Library.Utility.Profiler import PROFILE

@dataclass(kw_only=True)
class ArtifactAPI:

    route: str = "/_artifact"

    _STAMP_ = re.compile(r"^(\d{4}-\d{2}-\d{2}[ _]\d{2}-\d{2}-\d{2})\s*(.*)$")

    @classmethod
    def _parse_(cls, name: str) -> tuple:
        match = cls._STAMP_.match(name)
        if not match: return None, name
        stamp = string_to_datetime(match.group(1).replace("_", " "), STAMP)
        return stamp, match.group(2).strip() or name

    @staticmethod
    def _kind_(path: Path, folder: bool) -> str:
        if folder: return "Export"
        if path.name == SystemAPI.RESULT: return "Result"
        if path.suffix == ".html": return "Plot"
        return "Profile" if path.suffix in (".prof", PROFILE) else "File"

    @staticmethod
    def _folder_(run: str) -> Path | None:
        if not run: return None
        folder = ExecutorAPI.settle(run)
        return folder if folder.is_dir() else None

    def produced(self, run: str) -> list[dict]:
        folder = self._folder_(run)
        if folder is None: return []
        output = folder / SystemAPI.OUTPUT
        source, prefix = (output, f"{SystemAPI.OUTPUT}/") if output.is_dir() else (folder, "")
        rows = []
        for entry in sorted(os.scandir(source), key=lambda entry: os.path.normcase(entry.name)):
            path, directory = Path(entry.path), entry.is_dir()
            if not directory and path.suffix == ".log": continue
            kind = self._kind_(path, directory)
            stamp, label = self._parse_(path.name if directory else path.stem)
            rows.append({"UID": f"{kind}:{run}/{prefix}{entry.name}", "Kind": kind, "Name": label, "Stamp": stamp, "Path": path})
        return rows

    @staticmethod
    def _contained_(root: Path, candidate: Path) -> Path | None:
        try: resolved = candidate.resolve()
        except OSError: return None
        if resolved != root and root not in resolved.parents: return None
        return resolved if resolved.exists() else None

    def locate(self, uid: str) -> Path | None:
        if not uid or ":" not in str(uid): return None
        kind, name = str(uid).split(":", 1)
        if "/" not in name: return None
        run, leaf = name.split("/", 1)
        folder = self._folder_(run)
        if folder is None: return None
        try: root = folder.resolve()
        except OSError: return None
        return self._contained_(root, root / leaf)

    def href(self, uid: str) -> str:
        return f"{self.route}/{uid}"

    def install(self, server) -> None:
        def _view_(uid: str):
            path = self.locate(uid)
            if path is None or not path.is_file(): flask.abort(404)
            return flask.send_file(path, mimetype="text/html" if path.suffix == ".html" else None)
        server.add_url_rule(f"{self.route}/<path:uid>", endpoint=f"artifact_{id(self)}", view_func=_view_)

    @classmethod
    @functools.cache
    def shared(cls) -> Self:
        return cls()