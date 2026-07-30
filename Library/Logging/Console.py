import sys

from Library.Logging.Level import VerboseLevel
from Library.Logging.Logger import LoggerAPI

class ConsoleAPI(LoggerAPI):
    """
    Standard output sink with level coloring.

    Color is applied only to the level name, which keeps lines readable while still making severity
    scannable, and only when the stream is an interactive terminal. Redirected output therefore
    carries no escape sequences, so captured logs stay clean. On Windows, virtual terminal
    processing is enabled on first open; if that fails the sink falls back to plain text.

    The stream is resolved on every write rather than cached so that a reassigned sys.stdout, as
    used by test capture and by the tray applications, is honored immediately.
    """

    _GREEN_: str = "\033[38;5;46m"
    _BLUE_: str = "\033[38;5;33m"
    _YELLOW_: str = "\033[38;5;226m"
    _ORANGE_: str = "\033[38;5;208m"
    _RED_: str = "\033[38;5;196m"
    _DARKRED_: str = "\033[38;5;197m"
    _RESET_: str = "\033[0m"

    _VIRTUAL_: int = 0x0004
    _OUTPUT_: int = -11

    Name: str = "Console"

    def __init__(self, level: VerboseLevel = VerboseLevel.Debug) -> None:
        super().__init__(level=level)
        self._palette_: dict = {
            VerboseLevel.Debug: f"{self._GREEN_}{VerboseLevel.Debug.name}{self._RESET_}",
            VerboseLevel.Info: f"{self._BLUE_}{VerboseLevel.Info.name}{self._RESET_}",
            VerboseLevel.Alert: f"{self._ORANGE_}{VerboseLevel.Alert.name}{self._RESET_}",
            VerboseLevel.Warning: f"{self._YELLOW_}{VerboseLevel.Warning.name}{self._RESET_}",
            VerboseLevel.Error: f"{self._RED_}{VerboseLevel.Error.name}{self._RESET_}",
            VerboseLevel.Exception: f"{self._DARKRED_}{VerboseLevel.Exception.name}{self._RESET_}"
        }
        self._color_: bool = False
        self._forced_: bool | None = None

    @property
    def Palette(self) -> dict:
        """Returns the precolored level names keyed by level."""
        return self._palette_

    @property
    def Color(self) -> bool:
        """Returns whether color is currently being emitted."""
        return self._color_

    @property
    def Forced(self) -> bool | None:
        """Returns the color override, or None when color is detected from the stream."""
        return self._forced_

    @staticmethod
    def _stream_():
        return sys.stdout

    @staticmethod
    def _virtual_() -> bool:
        try:
            import ctypes
            kernel = ctypes.windll.kernel32
            handle = kernel.GetStdHandle(ConsoleAPI._OUTPUT_)
            mode = ctypes.c_uint32()
            if not kernel.GetConsoleMode(handle, ctypes.byref(mode)): return False
            return bool(kernel.SetConsoleMode(handle, mode.value | ConsoleAPI._VIRTUAL_))
        except Exception:
            return False

    @staticmethod
    def _supports_() -> bool:
        stream = ConsoleAPI._stream_()
        if stream is None: return False
        try:
            if not stream.isatty(): return False
        except Exception:
            return False
        if not sys.platform.startswith("win"): return True
        return ConsoleAPI._virtual_()

    def _open_(self) -> None:
        self._color_ = self._supports_() if self._forced_ is None else self._forced_

    def _flush_(self) -> None:
        stream = self._stream_()
        if stream is not None: stream.flush()

    def set_color(self, color: bool | None) -> None:
        """
        Overrides color handling.
        :param color: True to always color, False to never color, None to detect from the stream.
        """
        if self._locked_: return
        self._forced_ = color
        self._color_ = self._supports_() if color is None else color

    def _format_(self, level: VerboseLevel, moment: str, head: str, tail: str, message: str) -> str:
        name = self._palette_[level] if self._color_ else level.name
        return f"{moment} - {head}{name} - {tail}{message}\n"

    def _write_(self, line: str) -> None:
        stream = self._stream_()
        if stream is None: return
        try:
            stream.write(line)
        except UnicodeEncodeError:
            encoding = getattr(stream, "encoding", None) or "ascii"
            stream.write(line.encode(encoding, "replace").decode(encoding, "replace"))