from typing import Union
from pathlib import Path

def is_readable(path: Path) -> bool:
    try:
        if path.is_dir():
            next(path.iterdir(), None)
            return True
        if path.is_file() or path.is_symlink():
            with path.open("rb"):
                return True
        return False
    except:
        return False

def is_writable(path: Path) -> bool:
    try:
        base = path if path.is_dir() else path.parent
        if not base.exists():
            return False
        tmp = base / ".write_test.tmp"
        tmp.write_text("x", encoding="utf-8")
        tmp.unlink(missing_ok=True)
        return True
    except:
        return False

def mkdir(path: Path, *, safe: bool = True) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except:
        if safe:
            return False
        raise

def remove(path: Path, *, safe: bool = True) -> bool:
    import shutil
    try:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        return True
    except:
        if safe:
            return False
        raise

def read_text(path: Path, *, safe: bool = True, encoding: str = "utf-8") -> str:
    try:
        return path.read_text(encoding=encoding)
    except:
        if safe:
            return ""
        raise

def write_text(path: Path, text: str, *, safe: bool = True, encoding: str = "utf-8") -> bool:
    try:
        mkdir(path.parent, safe=True)
        path.write_text(text, encoding=encoding)
        return True
    except:
        if safe:
            return False
        raise

def read_json(path: Path, *, safe: bool = True, encoding: str = "utf-8") -> dict:
    import json
    try:
        data = json.loads(path.read_text(encoding=encoding))
        return data if isinstance(data, dict) else {}
    except:
        if safe:
            return {}
        raise

def write_json(path: Path, data: dict, *, safe: bool = True, encoding: str = "utf-8") -> bool:
    import json
    try:
        mkdir(path.parent, safe=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding=encoding)
        return True
    except:
        if safe:
            return False
        raise

def symlink(dst: Path, src: Path, *, safe: bool = True) -> bool:
    import os
    try:
        mkdir(dst.parent, safe=True)
        if dst.exists() or dst.is_symlink():
            remove(dst, safe=True)
        os.symlink(str(src), str(dst))
        return True
    except:
        if safe:
            return False
        raise

def hardlink(dst: Path, src: Path, *, safe: bool = True) -> bool:
    import os
    try:
        if src.is_dir():
            raise IsADirectoryError(str(src))
        mkdir(dst.parent, safe=True)
        if dst.exists() or dst.is_symlink():
            remove(dst, safe=True)
        os.link(str(src), str(dst))
        return True
    except:
        if safe:
            return False
        raise

def copy(dst: Path, src: Path, *, safe: bool = True) -> bool:
    import shutil
    try:
        mkdir(dst.parent, safe=True)
        if dst.exists() or dst.is_symlink():
            remove(dst, safe=True)
        shutil.copy2(str(src), str(dst))
        return True
    except:
        if safe:
            return False
        raise

def smartlink(dst: Path, src: Path, *, safe: bool = True) -> Union[str, None]:
    if symlink(dst, src, safe=True):
        return "symlink"
    if hardlink(dst, src, safe=True):
        return "hardlink"
    if copy(dst, src, safe=True):
        return "copy"
    if safe:
        return None
    raise RuntimeError(f"Failed to link/copy {src} to {dst}")