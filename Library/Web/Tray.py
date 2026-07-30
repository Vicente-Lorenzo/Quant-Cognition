import sys
import threading
import webbrowser

from waitress import create_server

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Logging.File import FileAPI
from Library.Utility.Runtime import tail_terminal
from Library.Web.Serve import build, main as headless

class TrayAPI:

    _URL_ = "https://quantcognition.com"
    _LOG_ = FileAPI.folder() / "Web.log"

    def __init__(self) -> None:
        import pystray
        self._log_ = LoggingAPI()
        self._debug_ = False
        self._verbose_ = True
        self._running_ = False
        self._server_ = None
        self._thread_ = None
        self._icon_ = pystray.Icon("Quant Cognition", self._image_(), "Quant Cognition", menu=pystray.Menu(
            pystray.MenuItem("Open in Browser", self._browser_, default=True),
            pystray.MenuItem("Open in Terminal", self._terminal_),
            pystray.MenuItem("Debug Mode", self._mode_, checked=lambda item: self._debug_),
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
        draw.rounded_rectangle((4, 4, 60, 60), radius=14, fill=(13, 110, 253, 255))
        draw.line((15, 45, 27, 29, 37, 37, 50, 17), fill=(255, 255, 255, 255), width=5, joint="curve")
        return image

    def _update_(self) -> None:
        try: self._icon_.update_menu()
        except Exception: pass

    def _browser_(self, icon=None, item=None) -> None:
        webbrowser.open(self._URL_)

    def _terminal_(self, icon=None, item=None) -> None:
        tail_terminal(self._LOG_)

    def _toggle_(self, icon=None, item=None) -> None:
        self._verbose_ = not self._verbose_
        self._log_.console.set_level(VerboseLevel.Debug if self._verbose_ else VerboseLevel.Info)

    def _mode_(self, icon=None, item=None) -> None:
        self._debug_ = not self._debug_
        if self._running_:
            self._shutdown_()
            self._launch_()
        self._update_()

    def _launch_(self, icon=None, item=None) -> None:
        app = build()
        if self._debug_: app.app.enable_dev_tools(debug=True)
        self._server_ = create_server(app.app.server, host=app._host_, port=app._port_, threads=8, ident="Quant Cognition")
        self._thread_ = threading.Thread(target=self._server_.run, name="Server", daemon=True)
        self._thread_.start()
        self._running_ = True
        self._log_.info(lambda app=app: f"Server Launch: Running ({app._host_}:{app._port_}) · {'Debug' if self._debug_ else 'Production'} Mode")
        self._update_()

    def _shutdown_(self, icon=None, item=None) -> None:
        try: self._server_.close()
        except Exception: pass
        self._running_ = False
        self._log_.info(lambda: "Server Shutdown: Halted")
        self._update_()

    def _restart_(self, icon=None, item=None) -> None:
        self._shutdown_()
        self._icon_.stop()

    def _quit_(self, icon, item) -> None:
        if self._running_: self._shutdown_()
        icon.stop()

    def run(self) -> None:
        self._launch_()
        self._icon_.run()

def main() -> None:
    TrayAPI._LOG_.parent.mkdir(parents=True, exist_ok=True)
    handle = TrayAPI._LOG_.open("w", buffering=1, encoding="utf-8-sig")
    sys.stdout = handle
    sys.stderr = handle
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Debug)
    log.file.set_level(VerboseLevel.Debug)
    try:
        tray = TrayAPI()
    except Exception as error:
        log.error(lambda error=error: f"Tray Start: Failed · Due to {error} · Running Headless")
        headless()
        return
    tray.run()

if __name__ == "__main__":
    main()