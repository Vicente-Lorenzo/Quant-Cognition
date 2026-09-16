import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from waitress import serve

from Library.Logging import LoggingAPI
from Library.Web.App import WebAppAPI
from Library.Web.Service.Tray import TrayAPI

def headless() -> None:
    app = WebAppAPI.build()
    serve(app.app.server, host=app._host_, port=app._port_, threads=8, ident=TrayAPI._NAME_)

def main() -> None:
    TrayAPI.redirect(TrayAPI._LOG_)
    TrayAPI.main(LoggingAPI(), headless)

if __name__ == "__main__":
    main()