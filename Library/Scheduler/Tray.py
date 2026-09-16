import sys
import threading
import subprocess

from Library.Logging import LoggingAPI
from Library.Logging.File import FileAPI
from Library.Utility.Path import traceback_root
from Library.Utility.Runtime import windowless
from Library.Utility.Tray import TrayAPI as BaseTrayAPI
from Library.Scheduler.Serve import build

class TrayAPI(BaseTrayAPI):

    _NAME_ = "Scheduler"
    _LOG_ = FileAPI.folder() / "Scheduler.log"
    _LAUNCHER_ = traceback_root() / "Script" / "Scheduler.py"

    def __init__(self) -> None:
        self._scheduler_ = None
        super().__init__(LoggingAPI())

    def _draw_(self, draw) -> None:
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(45, 51, 59, 255))
        draw.ellipse((14, 14, 50, 50), outline=(255, 255, 255, 255), width=5)
        draw.line((32, 32, 32, 21), fill=(255, 255, 255, 255), width=4)
        draw.line((32, 32, 40, 37), fill=(13, 110, 253, 255), width=4)

    def _start_(self) -> None:
        self._scheduler_ = build()
        self._thread_ = threading.Thread(target=self._scheduler_.start, name="Scheduler", daemon=True)
        self._thread_.start()

    def _stop_(self) -> None:
        self._scheduler_.stop()

    def _relaunch_(self) -> None:
        subprocess.Popen([sys.executable, str(self._LAUNCHER_)], cwd=str(traceback_root()), **windowless())

    @classmethod
    def serve(cls) -> None:
        cls.main(LoggingAPI(), lambda: build().start())

if __name__ == "__main__":
    TrayAPI.serve()