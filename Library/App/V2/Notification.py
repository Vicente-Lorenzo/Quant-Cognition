import dash
import dash_bootstrap_components as dbc
from dash import Patch
from dash.development.base_component import Component

from Library.Utility.Typing import MISSING

class NotifierAPI:

    _COLORS_ = {"info": "info", "success": "success", "warning": "warning", "error": "danger"}

    def __init__(self, container: str | dict, *, duration: int | None = 5000) -> None:
        self._container_ = container
        self._duration_ = duration

    def _toast_(self, level: str, message: str, header: str, duration: int) -> Component:
        return dbc.Toast(
            message,
            header=header if header is not MISSING else level.title(),
            icon=self._COLORS_.get(level, "info"),
            duration=duration if duration is not MISSING else self._duration_,
            is_open=True,
            dismissable=True,
            className=f"app-toast app-toast-{level}"
        )

    def _push_(self, level: str, message: str, header: str, duration: int) -> None:
        patch = Patch()
        patch.append(self._toast_(level, message, header, duration))
        dash.set_props(self._container_, {"children": patch})

    def info(self, message: str, *, header: str = MISSING, duration: int = MISSING) -> None:
        self._push_("info", message, header, duration)

    def success(self, message: str, *, header: str = MISSING, duration: int = MISSING) -> None:
        self._push_("success", message, header, duration)

    def warning(self, message: str, *, header: str = MISSING, duration: int = MISSING) -> None:
        self._push_("warning", message, header, duration)

    def error(self, message: str, *, header: str = MISSING, duration: int = MISSING) -> None:
        self._push_("error", message, header, duration)