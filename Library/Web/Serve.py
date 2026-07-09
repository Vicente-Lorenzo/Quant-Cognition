import os

from waitress import serve

from Library.Web.App import WebAppAPI

def build() -> WebAppAPI:
    host = os.environ.get("QUANT_HOST", "127.0.0.1")
    port = int(os.environ.get("QUANT_PORT", "8050"))
    return WebAppAPI(name="Quant Cognition", title="Quant Cognition", team="Vicente Lorenzo", contact="vicente.aser.lorenzo@gmail.com", host=host, port=port)

def main() -> None:
    app = build()
    serve(app.app.server, host=app._host_, port=app._port_, threads=8, ident="Quant Cognition")

if __name__ == "__main__":
    main()