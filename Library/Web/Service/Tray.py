import threading
from typing import Callable

from waitress import create_server

from Library.Logging import LoggingAPI
from Library.Logging.File import FileAPI
from Library.Utility.Typing import MISSING
from Library.Utility.Runtime import open_browser
from Library.Utility.Tray import TrayAPI as BaseTrayAPI
from Library.Web.Service.Serve import build, main as headless

class TrayAPI(BaseTrayAPI):

    _URL_ = "https://quantcognition.com"
    _NAME_ = "Quant Cognition"
    _LOG_ = FileAPI.folder() / "Web.log"

    def __init__(self) -> None:
        self._debug_ = False
        self._server_ = None
        super().__init__(LoggingAPI())

    def _items_(self, item: Callable) -> tuple:
        return (
            item("Open in Browser", self._browser_, default=True),
            item("Open in Terminal", self._terminal_),
            item("Debug Mode", self._mode_, checked=lambda entry: self._debug_)
        )

    def _draw_(self, draw) -> None:
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(13, 110, 253, 255))
        draw.line((15, 45, 27, 29, 37, 37, 50, 17), fill=(255, 255, 255, 255), width=5, joint="curve")

    def _browser_(self, icon=MISSING, item=MISSING) -> None:
        open_browser(self._URL_)

    def _mode_(self, icon=MISSING, item=MISSING) -> None:
        self._debug_ = not self._debug_
        if self._running_:
            self._shutdown_()
            self._launch_()
        self._update_()

    def _start_(self) -> None:
        app = build()
        if self._debug_: app.app.enable_dev_tools(debug=True)
        self._server_ = create_server(app.app.server, host=app._host_, port=app._port_, threads=8, ident=self._NAME_)
        self._thread_ = threading.Thread(target=self._server_.run, name="Server", daemon=True)
        self._thread_.start()
        self._log_.info(lambda app=app: f"Server Launch: Running ({app._host_}:{app._port_}) · {'Debug' if self._debug_ else 'Production'} Mode")

    def _stop_(self) -> None:
        try: self._server_.close()
        except Exception: pass
        self._log_.info(lambda: "Server Shutdown: Halted")

    @classmethod
    def serve(cls) -> None:
        cls.redirect(cls._LOG_)
        cls.main(LoggingAPI(), headless)

if __name__ == "__main__":
    TrayAPI.serve()