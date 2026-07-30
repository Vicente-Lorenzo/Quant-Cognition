from waitress import serve

from Library.Logging import LoggingAPI, VerboseLevel
from Library.Web.App import WebAppAPI

def build() -> WebAppAPI:
    return WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Vicente Lorenzo", contact="vicente.aser.lorenzo@gmail.com", host="127.0.0.1", port=8050)

def main() -> None:
    log = LoggingAPI(Class=WebAppAPI.__name__, Subclass="Serve")
    log.console.set_level(VerboseLevel.Debug)
    log.file.set_level(VerboseLevel.Debug)
    app = build()
    serve(app.app.server, host=app._host_, port=app._port_, threads=8, ident="Quant Cognition")

if __name__ == "__main__":
    main()