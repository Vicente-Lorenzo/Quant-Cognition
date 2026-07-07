from typing import Union
from threading import RLock
from collections import deque

from Library.Logging import VerboseLevel
from Library.App.V1.Component import Component, NotificationAPI
from Library.Utility.Typing import MISSING

class NotifierAPI:

    _COLORS_ = {
        VerboseLevel.Debug: "level-debug",
        VerboseLevel.Info: "level-info",
        VerboseLevel.Alert: "level-alert",
        VerboseLevel.Warning: "level-warning",
        VerboseLevel.Error: "level-error",
        VerboseLevel.Exception: "level-exception"
    }

    _ICONS_ = {
        VerboseLevel.Debug: "bi bi-gear-fill",
        VerboseLevel.Info: "bi bi-info-circle-fill",
        VerboseLevel.Alert: "bi bi-bell-fill",
        VerboseLevel.Warning: "bi bi-exclamation-triangle-fill",
        VerboseLevel.Error: "bi bi-x-circle-fill",
        VerboseLevel.Exception: "bi bi-exclamation-octagon-fill"
    }

    def __init__(self, duration: Union[int, None], dismissable: bool, persistence: Union[bool, str]) -> None:
        self._buffer_: deque[Component] = deque()
        self._lock_: RLock = RLock()
        self._duration_: Union[int, None] = duration
        self._dismissable_: bool = dismissable
        self._persistence_: Union[bool, str] = persistence

    def _push_(self, verbose: VerboseLevel, message: str, duration: int, dismissable: bool, persistence: Union[bool, str]) -> None:
        toast = NotificationAPI(
            element=message,
            header=verbose.name,
            icon=self._ICONS_.get(verbose, "bi bi-info-circle-fill"),
            background=self._COLORS_.get(verbose, "primary"),
            duration=duration if duration is not MISSING else self._duration_,
            dismissable=dismissable if dismissable is not MISSING else self._dismissable_,
            persistence=persistence if persistence is not MISSING else self._persistence_
        ).build()
        with self._lock_:
            self._buffer_.extend(toast)

    def stream(self) -> list[Component]:
        with self._lock_:
            items = list(self._buffer_)
            self._buffer_.clear()
            return items

    def debug(self, message: str, duration: int = MISSING, dismissable: bool = MISSING, persistence: Union[bool, str] = MISSING) -> None:
        self._push_(verbose=VerboseLevel.Debug, message=message, duration=duration, dismissable=dismissable, persistence=persistence)

    def info(self, message: str, duration: int = MISSING, dismissable: bool = MISSING, persistence: Union[bool, str] = MISSING) -> None:
        self._push_(verbose=VerboseLevel.Info, message=message, duration=duration, dismissable=dismissable, persistence=persistence)

    def alert(self, message: str, duration: int = MISSING, dismissable: bool = MISSING, persistence: Union[bool, str] = MISSING) -> None:
        self._push_(verbose=VerboseLevel.Alert, message=message, duration=duration, dismissable=dismissable, persistence=persistence)

    def warning(self, message: str, duration: int = MISSING, dismissable: bool = MISSING, persistence: Union[bool, str] = MISSING) -> None:
        self._push_(verbose=VerboseLevel.Warning, message=message, duration=duration, dismissable=dismissable, persistence=persistence)

    def error(self, message: str, duration: int = MISSING, dismissable: bool = MISSING, persistence: Union[bool, str] = MISSING) -> None:
        self._push_(verbose=VerboseLevel.Error, message=message, duration=duration, dismissable=dismissable, persistence=persistence)

    def exception(self, message: str, duration: int = MISSING, dismissable: bool = MISSING, persistence: Union[bool, str] = MISSING) -> None:
        self._push_(verbose=VerboseLevel.Exception, message=message, duration=duration, dismissable=dismissable, persistence=persistence)