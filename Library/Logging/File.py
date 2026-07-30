from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from threading import RLock
from typing import TextIO

from Library.Utility.Path import inspect_temporary
from Library.Logging.Level import VerboseLevel
from Library.Logging.Logger import LoggerAPI

class FileAPI(LoggerAPI):
    """
    Rotating file sink, temporary by default and persistent on request.

    With no path configured the sink writes under the system temporary folder, which is fast local
    storage on every platform and is never synchronized to cloud storage. Calling set_path moves it
    to a durable location. The filename follows the conventional program.log form with rotated
    backups as program.log.1 and so on; host, user and origin belong inside the lines as tags rather
    than in the name.

    Neither temporary nor persistent storage is self managing, so the sink bounds itself: it rotates
    once a file exceeds its size budget and prunes files older than its retention horizon each time
    it opens. Files are opened in append mode with explicit UTF-8 encoding and Unix newlines so the
    output is byte identical on Windows and Linux.
    """

    _EXTENSION_: str = "log"
    _FALLBACK_: str = "Python"
    _INVALID_: str = '<>:"/\\|?* '
    _SIZE_: int = 32 * 1024 * 1024
    _COUNT_: int = 5
    _DAYS_: int = 30

    Folder: str = "Logs"
    Name: str = "File"

    def __init__(self, level: VerboseLevel = VerboseLevel.Debug) -> None:
        super().__init__(level=level)
        self._lock_: RLock = RLock()
        self._directory_: Path | None = None
        self._name_: str | None = None
        self._extension_: str = self._EXTENSION_
        self._distinct_: bool = False
        self._size_: int = self._SIZE_
        self._count_: int = self._COUNT_
        self._days_: int = self._DAYS_
        self._path_: Path | None = None
        self._handle_: TextIO | None = None
        self._written_: int = 0

    @property
    def Directory(self) -> Path:
        """Returns the folder in use, temporary unless a path was set."""
        return self._directory_ if self._directory_ is not None else self.folder()

    @property
    def Extension(self) -> str:
        """Returns the file extension without its leading dot."""
        return self._extension_

    @property
    def Distinct(self) -> bool:
        """Returns whether the process identifier is part of the filename."""
        return self._distinct_

    @property
    def Rotation(self) -> tuple:
        """Returns the rotation budget as a size and backup count pair."""
        return self._size_, self._count_

    @property
    def Retention(self) -> int:
        """Returns the retention horizon in days."""
        return self._days_

    @property
    def Filename(self) -> str:
        """Returns the filename in use, derived from the entry point unless a name was set."""
        name = self._name_ if self._name_ else self._origin_()
        return f"{name}.{os.getpid()}.{self._extension_}" if self._distinct_ else f"{name}.{self._extension_}"

    @property
    def Path(self) -> Path:
        """Returns the full path of the file currently open, or the one that would be opened."""
        return self._path_ if self._path_ is not None else self.Directory / self.Filename

    @property
    def Temporary(self) -> bool:
        """Returns whether the sink is writing to the temporary folder rather than a durable one."""
        return self._directory_ is None

    @property
    def Size(self) -> int:
        """Returns the characters written to the current file since it was opened or rotated."""
        return self._written_

    @staticmethod
    def _sanitize_(name: str) -> str:
        return "".join("-" if character in FileAPI._INVALID_ else character for character in name).strip("-")

    @staticmethod
    def _origin_() -> str:
        argument = sys.argv[0] if sys.argv else ""
        if not argument or argument.startswith("-"): return FileAPI._FALLBACK_
        return FileAPI._sanitize_(Path(argument).stem) or FileAPI._FALLBACK_

    @classmethod
    def folder(cls) -> Path:
        """Returns the default temporary folder every sink writes into unless a path is set."""
        return inspect_temporary(cls.Folder)

    def _open_(self) -> None:
        directory = self.Directory
        directory.mkdir(parents=True, exist_ok=True)
        self._prune_(directory)
        self._path_ = directory / self.Filename
        self._handle_ = self._path_.open("a", encoding="utf-8", newline="\n")
        try: self._written_ = self._path_.stat().st_size
        except OSError: self._written_ = 0

    def _close_(self) -> None:
        handle, self._handle_ = self._handle_, None
        if handle is None: return
        try: handle.flush()
        finally: handle.close()

    def _flush_(self) -> None:
        if self._handle_ is not None: self._handle_.flush()

    def _reopen_(self) -> None:
        with self._lock_:
            if not self._opened_: return
            self.close()
            self.open()

    def set_path(self, directory: Path | str | None) -> None:
        """
        Sets the destination folder and reopens if the sink is already open.
        :param directory: A folder to persist into, or None to return to the temporary folder.
        """
        if self._locked_: return
        self._directory_ = Path(directory) if directory is not None else None
        self._reopen_()

    def set_name(self, name: str | None) -> None:
        """
        Sets the base filename, sanitized of characters no filesystem accepts.
        :param name: The base name, or None to derive it from the entry point.
        """
        if self._locked_: return
        self._name_ = self._sanitize_(name) if name else None
        self._reopen_()

    def set_extension(self, extension: str) -> None:
        """Sets the file extension, with or without a leading dot."""
        if self._locked_: return
        self._extension_ = extension.lstrip(".")
        self._reopen_()

    def set_distinct(self, distinct: bool) -> None:
        """
        Adds the process identifier to the filename.

        Enable this where several processes run the same entry point concurrently and should not
        share one file.
        """
        if self._locked_: return
        self._distinct_ = distinct
        self._reopen_()

    def set_rotation(self, size: int = None, count: int = None) -> None:
        """
        Sets the rotation budget.
        :param size: Maximum characters before rotating; zero disables rotation entirely.
        :param count: Number of backups to retain; zero truncates instead of rotating.
        """
        if self._locked_: return
        if size is not None: self._size_ = max(0, size)
        if count is not None: self._count_ = max(0, count)

    def set_retention(self, days: int) -> None:
        """
        Sets how long log files survive in the destination folder.
        :param days: Age in days beyond which files are removed on open; zero disables pruning.
        """
        if self._locked_: return
        self._days_ = max(0, days)

    def _prune_(self, directory: Path) -> None:
        if not self._days_: return
        horizon = time.time() - self._days_ * 86400
        for candidate in directory.glob(f"*.{self._extension_}*"):
            try:
                if candidate.is_file() and candidate.stat().st_mtime < horizon: candidate.unlink()
            except OSError:
                continue

    def _rotate_(self) -> None:
        base = self._path_
        self._handle_.close()
        if self._count_:
            for index in range(self._count_ - 1, 0, -1):
                source, target = Path(f"{base}.{index}"), Path(f"{base}.{index + 1}")
                if not source.exists(): continue
                try: os.replace(source, target)
                except OSError: continue
            try: os.replace(base, Path(f"{base}.1"))
            except OSError: pass
        else:
            try: base.unlink()
            except OSError: pass
        self._handle_ = base.open("a", encoding="utf-8", newline="\n")
        self._written_ = 0

    def _format_(self, level: VerboseLevel, moment: str, head: str, tail: str, message: str) -> str:
        return f"{moment} - {head}{level.name} - {tail}{message}\n"

    def _write_(self, line: str) -> None:
        with self._lock_:
            if self._handle_ is None: return
            if self._size_ and self._written_ >= self._size_: self._rotate_()
            self._handle_.write(line)
            self._written_ += len(line)