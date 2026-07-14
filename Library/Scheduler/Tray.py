import subprocess
import threading
import webbrowser

from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Utility.Path import traceback_root
from Library.Scheduler.Serve import build

LOG = traceback_root() / "Logs" / "Scheduler.log"
URL = "https://quantcognition.com"

def _terminal_(icon=None, item=None) -> None:
    subprocess.Popen(["powershell", "-NoExit", "-Command", f"Get-Content -LiteralPath '{LOG}' -Wait -Tail 200"], creationflags=subprocess.CREATE_NEW_CONSOLE)

def _dashboard_(icon=None, item=None) -> None:
    webbrowser.open(URL)

class TrayAPI:

    def __init__(self, scheduler) -> None:
        import pystray
        self._scheduler_ = scheduler
        self._icon_ = pystray.Icon("QuantScheduler", self._image_(), "Quant Scheduler", menu=pystray.Menu(
            pystray.MenuItem("Terminal", _terminal_, default=True),
            pystray.MenuItem("Open Dashboard", _dashboard_),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit_)))

    @staticmethod
    def _image_():
        from PIL import Image, ImageDraw
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        tone = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(tone)
        draw.rectangle((0, 0, 64, 32), fill=(48, 105, 152, 255))
        draw.rectangle((0, 32, 64, 64), fill=(255, 212, 59, 255))
        mask = Image.new("L", (64, 64), 0)
        ImageDraw.Draw(mask).rounded_rectangle((4, 4, 60, 60), radius=14, fill=255)
        image.paste(tone, (0, 0), mask)
        draw = ImageDraw.Draw(image)
        draw.ellipse((17, 17, 47, 47), outline=(255, 255, 255, 255), width=5)
        draw.line((32, 32, 32, 23), fill=(255, 255, 255, 255), width=4)
        draw.line((32, 32, 39, 36), fill=(255, 255, 255, 255), width=4)
        return image

    def _quit_(self, icon, item) -> None:
        self._scheduler_.stop()
        icon.stop()

    def run(self) -> None:
        self._icon_.run()

def main() -> None:
    log = HandlerLoggingAPI(Class=TrayAPI.__name__)
    log.console.set_verbose_level(VerboseLevel.Info)
    log.file.set_verbose_level(VerboseLevel.Debug)
    scheduler = build()
    thread = threading.Thread(target=scheduler.start, name="Scheduler", daemon=True)
    thread.start()
    try:
        TrayAPI(scheduler).run()
    except Exception as error:
        log.error(lambda error=error: f"Tray Start: Failed · Due to {error} · Running Headless")
        thread.join()

if __name__ == "__main__":
    main()