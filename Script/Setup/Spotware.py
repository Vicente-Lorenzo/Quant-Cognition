import sys
from argparse import ArgumentParser, Namespace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Credential import CredentialAPI, CredentialType, VaultAPI
from Library.Spotware import SpotwareAPI
from Library.Spotware.Token import TokenAPI
from Library.Utility.Command import CommandAPI
from Library.Utility.Runtime import open_browser
from Library.Utility.Typing import MISSING

class CallbackAPI(BaseHTTPRequestHandler):

    def do_GET(self) -> None:
        self.server.address = self.path
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Spotware access received · you can close this window".encode("utf-8"))

    def log_message(self, *args) -> None:
        return None

class SignInCommandAPI(CommandAPI):

    def __init__(self) -> None:
        super().__init__(name="Spotware")

    @staticmethod
    def _code_(address: str) -> str:
        query = parse_qs(urlparse(address.strip()).query)
        if query.get("error"): raise PermissionError(f"Spotware Consent: Failed · {query['error'][0]}")
        if not query.get("code"): raise ValueError("Spotware Consent: Failed · The address carries no code")
        return query["code"][0]

    @classmethod
    def _listen_(cls, redirect: str, timeout: float) -> str:
        target = urlparse(redirect)
        with HTTPServer((target.hostname, target.port or 80), CallbackAPI) as server:
            server.timeout, server.address = timeout, None
            server.handle_request()
            address = server.address
        if address is None: raise TimeoutError(f"Spotware Consent: Failed · No redirect within {timeout:.0f}s")
        return cls._code_(address)

    @staticmethod
    def _accounts_(values: dict) -> list[dict]:
        with SpotwareAPI.of(values) as api: listed = api.portfolio.accounts(legacy=False).to_dicts()
        accounts = []
        for entry in listed:
            account = {"AccountId": entry["AccountID"], "Live": bool(entry["IsLive"]), "Login": entry["TraderLogin"]}
            if account["Live"] == (values["Environment"] == "live"):
                with SpotwareAPI.of(values, account=entry["AccountID"]) as api:
                    trader = api.portfolio.account(legacy=False).to_dicts()[0]
                    assets = {row["AssetId"]: row["Name"] for row in api.universe.assets(legacy=False).to_dicts()}
                account.update({"Broker": trader["BrokerName"], "Currency": assets.get(trader["DepositAssetID"])})
            accounts.append(account)
        return accounts

    def arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--database", default="Quant", choices=["Quant", "Tests"])
        parser.add_argument("--user", default=MISSING)
        parser.add_argument("--application", default="Application")
        parser.add_argument("--name", default="cTrader ID")
        parser.add_argument("--environment", default="demo", choices=["demo", "live"])
        parser.add_argument("--timeout", type=float, default=300.0)

    def run(self, args: Namespace) -> int:
        vault = VaultAPI(database=args.database)
        user = args.user or vault.administrator()
        rows = {row["Name"]: row for row in vault.credentials(by=user, service="Spotware")}
        if args.application not in rows: raise LookupError(f"Spotware Sign In: Failed · Store Spotware · {args.application} first")
        application = vault.resolve(uid=rows[args.application]["UID"], by=user)
        redirect = TokenAPI.plain(application.get("RedirectUri"))
        if not redirect: raise ValueError(f"Spotware Sign In: Failed · Spotware · {args.application} carries no RedirectUri in its Fields")
        consent = TokenAPI.consent(application["Identifier"], redirect)
        print(f"Grant access in the browser · {consent}")
        open_browser(consent)
        loopback = urlparse(redirect).hostname in ("127.0.0.1", "localhost")
        code = self._listen_(redirect, args.timeout) if loopback else self._code_(input("Paste the address the browser landed on: "))
        tokens, expires = TokenAPI.exchange(code, client_id=application["Identifier"], client_secret=application["Secret"], redirect_uri=redirect)
        accounts = self._accounts_({**application, "AccessToken": tokens["AccessToken"], "Environment": args.environment})
        secret = CredentialAPI.pack(tokens)
        fields = CredentialAPI.pack({"Environment": args.environment, "Accounts": accounts})
        if args.name in rows: vault.update(rows[args.name]["UID"], by=user, Secret=secret, ExpiresAt=expires, Fields=fields)
        else: vault.store(by=user, Service="Spotware", Name=args.name, Kind=CredentialType.OAuth2.name, Parent=rows[args.application]["UID"], Secret=secret, ExpiresAt=expires, Fields=fields)
        self.table([{key: account.get(key) for key in ("AccountId", "Live", "Login", "Broker", "Currency")} for account in accounts])
        print(f"Spotware · {args.name} signed in · {len(accounts)} account(s) · token expires {expires:%Y-%m-%d}")
        return 0

if __name__ == "__main__":
    raise SystemExit(SignInCommandAPI().main())