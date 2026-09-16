import sys
from pathlib import Path
from typing import Callable, Union

from Library.Utility.IO import mkdir
from Library.Utility.Runtime import tail_terminal
from Library.Utility.Typing import MISSING

class TrayAPI:

    _NAME_: str = "Tray"
    _LOG_: Union[Path, None] = None

    def __init__(self, log=MISSING) -> None:
        import pystray
        self._log_ = log
        self._verbose_ = True
        self._running_ = False
        self._thread_ = None
        self._icon_ = pystray.Icon(self._NAME_, self._image_(), self._NAME_, menu=pystray.Menu(
            *self._items_(pystray.MenuItem),
            pystray.MenuItem("Verbose Logging", self._toggle_, checked=lambda item: self._verbose_),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Launch", self._launch_, enabled=lambda item: not self._running_),
            pystray.MenuItem("Restart", self._restart_, enabled=lambda item: self._running_),
            pystray.MenuItem("Shutdown", self._shutdown_, enabled=lambda item: self._running_),
            pystray.MenuItem("Quit", self._quit_)))

    def _items_(self, item: Callable) -> tuple:
        return (item("Open in Terminal", self._terminal_, default=True),)

    def _draw_(self, draw) -> None:
        pass

    def _start_(self) -> None:
        pass

    def _stop_(self) -> None:
        pass

    def _relaunch_(self) -> None:
        pass

    def _image_(self):
        from PIL import Image, ImageDraw
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        self._draw_(ImageDraw.Draw(image))
        return image

    def _update_(self) -> None:
        try: self._icon_.update_menu()
        except Exception: pass

    def _terminal_(self, icon=MISSING, item=MISSING) -> None:
        tail_terminal(self._LOG_)

    def _toggle_(self, icon=MISSING, item=MISSING) -> None:
        from Library.Logging import VerboseLevel
        self._verbose_ = not self._verbose_
        self._log_.console.set_level(VerboseLevel.Debug if self._verbose_ else VerboseLevel.Info)

    def _launch_(self, icon=MISSING, item=MISSING) -> None:
        self._start_()
        self._running_ = True
        self._update_()

    def _shutdown_(self, icon=MISSING, item=MISSING) -> None:
        self._stop_()
        self._running_ = False
        self._update_()

    def _restart_(self, icon=MISSING, item=MISSING) -> None:
        self._shutdown_()
        self._relaunch_()
        self._icon_.stop()

    def _quit_(self, icon, item) -> None:
        if self._running_: self._shutdown_()
        icon.stop()

    def run(self) -> None:
        self._launch_()
        self._icon_.run()

    @staticmethod
    def redirect(path: Path) -> None:
        mkdir(path.parent, safe=False)
        handle = path.open("w", buffering=1, encoding="utf-8-sig")
        sys.stdout = handle
        sys.stderr = handle

    @classmethod
    def main(cls, log, headless: Callable) -> None:
        from Library.Logging import VerboseLevel
        log.console.set_level(VerboseLevel.Debug)
        log.file.set_level(VerboseLevel.Debug)
        try:
            tray = cls()
        except Exception as error:
            log.error(lambda error=error: f"Tray Start: Failed · Due to {error} · Running Headless")
            headless()
            return
        if tray._log_ is MISSING: tray._log_ = log
        tray.run()