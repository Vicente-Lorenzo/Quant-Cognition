import sys
import threading
import subprocess

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Logging.File import FileAPI
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import tail_terminal
from Library.Scheduler.Serve import build

class TrayAPI:

    _LOG_ = FileAPI.folder() / "Scheduler.log"
    _LAUNCHER_ = traceback_root() / "Scripts" / "Scheduler.py"

    def __init__(self) -> None:
        import pystray
        self._log_ = LoggingAPI()
        self._verbose_ = True
        self._running_ = False
        self._scheduler_ = None
        self._thread_ = None
        self._icon_ = pystray.Icon("Scheduler", self._image_(), "Scheduler", menu=pystray.Menu(
            pystray.MenuItem("Open in Terminal", self._terminal_, default=True),
            pystray.MenuItem("Verbose Logging", self._toggle_, checked=lambda item: self._verbose_),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Launch", self._launch_, enabled=lambda item: not self._running_),
            pystray.MenuItem("Restart", self._restart_, enabled=lambda item: self._running_),
            pystray.MenuItem("Shutdown", self._shutdown_, enabled=lambda item: self._running_),
            pystray.MenuItem("Quit", self._quit_)))

    @staticmethod
    def _image_():
        from PIL import Image, ImageDraw
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(45, 51, 59, 255))
        draw.ellipse((14, 14, 50, 50), outline=(255, 255, 255, 255), width=5)
        draw.line((32, 32, 32, 21), fill=(255, 255, 255, 255), width=4)
        draw.line((32, 32, 40, 37), fill=(13, 110, 253, 255), width=4)
        return image

    def _update_(self) -> None:
        try: self._icon_.update_menu()
        except Exception: pass

    def _terminal_(self, icon=None, item=None) -> None:
        tail_terminal(self._LOG_)

    def _toggle_(self, icon=None, item=None) -> None:
        self._verbose_ = not self._verbose_
        self._log_.console.set_level(VerboseLevel.Debug if self._verbose_ else VerboseLevel.Info)

    def _launch_(self, icon=None, item=None) -> None:
        self._scheduler_ = build()
        self._thread_ = threading.Thread(target=self._scheduler_.start, name="Scheduler", daemon=True)
        self._thread_.start()
        self._running_ = True
        self._update_()

    def _shutdown_(self, icon=None, item=None) -> None:
        self._scheduler_.stop()
        self._running_ = False
        self._update_()

    def _restart_(self, icon=None, item=None) -> None:
        self._shutdown_()
        subprocess.Popen([sys.executable, str(self._LAUNCHER_)], cwd=str(traceback_root()))
        self._icon_.stop()

    def _quit_(self, icon, item) -> None:
        if self._running_: self._shutdown_()
        icon.stop()

    def run(self) -> None:
        self._launch_()
        self._icon_.run()

def main() -> None:
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Debug)
    log.file.set_level(VerboseLevel.Debug)
    try:
        tray = TrayAPI()
    except Exception as error:
        log.error(lambda error=error: f"Tray Start: Failed · Due to {error} · Running Headless")
        build().start()
        return
    tray.run()

if __name__ == "__main__":
    main()