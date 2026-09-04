import re
import flask
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from Library.Scheduler.Executor import ExecutorAPI

@dataclass(kw_only=True)
class ArtifactAPI:

    runs: Path = None
    kept: Path = None
    route: str = "/_artifact"

    _STAMP_ = re.compile(r"^(\d{4}-\d{2}-\d{2}[ _]\d{2}-\d{2}-\d{2})\s*(.*)$")

    @classmethod
    def _parse_(cls, name: str) -> tuple:
        match = cls._STAMP_.match(name)
        if not match: return None, name
        stamp = datetime.strptime(match.group(1).replace("_", " "), "%Y-%m-%d %H-%M-%S")
        return stamp, match.group(2).strip() or name

    @staticmethod
    def _weigh_(path: Path) -> int:
        if not path.is_dir(): return path.stat().st_size
        return sum(entry.stat().st_size for entry in path.rglob("*") if entry.is_file())

    @staticmethod
    def _kind_(path: Path) -> str:
        if path.is_dir(): return "Export"
        if path.name == "Result.json": return "Result"
        if path.suffix == ".html": return "Plot"
        return "Profile" if path.suffix in (".prof", ".pstats") else "File"

    def _folder_(self, run: str) -> Path | None:
        if not run: return None
        for root in (self.kept, self.runs):
            if root is None: continue
            folder = Path(root) / str(run)
            if folder.is_dir(): return folder
        return None

    def produced(self, run: str) -> list[dict]:
        folder = self._folder_(run)
        if folder is None: return []
        output = folder / "Output"
        source = output if output.is_dir() else folder
        rows = []
        for path in sorted(source.iterdir()):
            if path.is_file() and path.suffix == ".log": continue
            kind = self._kind_(path)
            stamp, label = self._parse_(path.name if path.is_dir() else path.stem)
            leaf = path.relative_to(folder).as_posix()
            rows.append({"UID": f"{kind}:{run}/{leaf}", "Kind": kind, "Name": label,
                         "Stamp": stamp, "Size": self._weigh_(path), "Path": path})
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

ARTIFACTS = ArtifactAPI(runs=Path(ExecutorAPI.Runs), kept=Path(ExecutorAPI.Kept))