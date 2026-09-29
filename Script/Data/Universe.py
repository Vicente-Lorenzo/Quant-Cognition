import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Union

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database import PostgresDatabaseAPI
from Library.Database.Dataframe import pl
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Universe.Category import CategoryAPI
from Library.Universe.Contract import ContractAPI
from Library.Universe.Provider import ProviderAPI, Platform
from Library.Universe.Security import SecurityAPI, SecurityStatus
from Library.Universe.Ticker import TickerAPI
from Library.Utility.Datetime import utc_now
from Library.Utility.Typing import MISSING, Missing
from Script.Data.Service import DataServiceAPI

class UniverseServiceAPI(DataServiceAPI):

    def __init__(self, *, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING, interval: float = 86_400.0, pause: float = 60.0) -> None:
        super().__init__(database=database, credential=credential, vault=vault)
        self._interval_ = interval
        self._pause_ = pause
        self._changed_ = threading.Event()

    @staticmethod
    def by() -> str:
        return "Universe"

    @staticmethod
    def provider(db: PostgresDatabaseAPI, broker: str) -> str:
        abbreviation = ProviderAPI.normalize(broker)
        uid = f"{abbreviation}({Platform.cTrader.name})"
        if db.first(schema=ProviderAPI.Schema, table=ProviderAPI.Table, condition='"UID" = :uid:', parameters={"uid": uid}) is None:
            db.upsert(schema=ProviderAPI.Schema, table=ProviderAPI.Table, data=[{"UID": uid, "Name": broker, "Abbreviation": abbreviation, "Platform": Platform.cTrader.name, "UpdatedAt": utc_now(), "UpdatedBy": UniverseServiceAPI.by()}], key=["UID"])
        return uid

    @staticmethod
    def _categories_(db: PostgresDatabaseAPI, frame: pl.DataFrame, tickers: dict, at: datetime, by: str) -> dict:
        known = {row["UID"] for row in db.records(schema=CategoryAPI.Schema, table=CategoryAPI.Table, columns=["UID"])}
        assigned, fresh = {}, {}
        for row in frame.iter_rows(named=True):
            uid = TickerAPI.normalize(row["Ticker"])
            if tickers.get(uid): continue
            category = CategoryAPI.classify(row["Primary"], base=row["BaseName"], quote=row["QuoteName"], country=row["Country"]) if row["Primary"] else None
            if category is None: continue
            assigned[uid] = category.UID
            if category.UID not in known: fresh[category.UID] = {"UID": category.UID, "Primary": category.Primary, "Secondary": category.Secondary, "Alternative": category.Alternative, "UpdatedAt": at, "UpdatedBy": by}
        if fresh: db.upsert(schema=CategoryAPI.Schema, table=CategoryAPI.Table, data=list(fresh.values()), key=["UID"])
        return assigned

    @staticmethod
    def _tickers_(db: PostgresDatabaseAPI, frame: pl.DataFrame, tickers: dict, assigned: dict, at: datetime, by: str) -> None:
        described, created = {}, {}
        for row in frame.iter_rows(named=True):
            uid = TickerAPI.normalize(row["Ticker"])
            values = {"UID": uid, "BaseAsset": row["BaseAsset"], "BaseName": row["BaseName"], "QuoteAsset": row["QuoteAsset"], "QuoteName": row["QuoteName"], "Description": row["Description"], "UpdatedAt": at, "UpdatedBy": by}
            if tickers.get(uid): described[uid] = values
            else: created[uid] = {**values, "Category": assigned.get(uid)}
        if described: db.upsert(schema=TickerAPI.Schema, table=TickerAPI.Table, data=list(described.values()), key=["UID"])
        if created: db.upsert(schema=TickerAPI.Schema, table=TickerAPI.Table, data=list(created.values()), key=["UID"])

    @staticmethod
    def _securities_(db: PostgresDatabaseAPI, provider: str, frame: pl.DataFrame, at: datetime, by: str) -> dict:
        stored = {(row["Ticker"], row["Type"]): row for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition='"Provider" = :provider:', parameters={"provider": provider})}
        updated, created = [], []
        for row in frame.iter_rows(named=True):
            key = (TickerAPI.normalize(row["Ticker"]), row["Type"])
            values = {"Provider": provider, "Ticker": key[0], "Type": key[1], "Symbol": row["Symbol"], "Status": row["Status"], "UpdatedAt": at, "UpdatedBy": by}
            if key in stored:
                if stored[key]["Symbol"] != row["Symbol"] or stored[key]["Status"] != row["Status"]: updated.append(values)
            else: created.append({**values, "Tracked": False})
        if updated: db.upsert(schema=SecurityAPI.Schema, table=SecurityAPI.Table, data=updated, key=["Provider", "Ticker", "Type"])
        if created: db.upsert(schema=SecurityAPI.Schema, table=SecurityAPI.Table, data=created, key=["Provider", "Ticker", "Type"])
        return {row["Symbol"]: row["UID"] for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Symbol"], condition='"Provider" = :provider:', parameters={"provider": provider})}

    @staticmethod
    def _archive_(db: PostgresDatabaseAPI, provider: str, frame: pl.DataFrame, at: datetime, by: str) -> int:
        symbols = frame.filter(pl.col("Status") == SecurityStatus.Archived.name)["Symbol"].to_list()
        if not symbols: return 0
        stored = db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, condition='"Provider" = :provider:', parameters={"provider": provider})
        archived = [{"Provider": row["Provider"], "Ticker": row["Ticker"], "Type": row["Type"], "Status": SecurityStatus.Archived.name, "UpdatedAt": at, "UpdatedBy": by} for row in stored if row["Symbol"] in set(symbols) and row["Status"] != SecurityStatus.Archived.name]
        if archived: db.upsert(schema=SecurityAPI.Schema, table=SecurityAPI.Table, data=archived, key=["Provider", "Ticker", "Type"])
        return len(archived)

    @staticmethod
    def _contracts_(db: PostgresDatabaseAPI, frame: pl.DataFrame, securities: dict, at: datetime, by: str) -> int:
        revised = 0
        for row in frame.iter_rows(named=True):
            security = securities.get(row["Symbol"])
            if security is not None and ContractAPI.revise(db, security, row, at, by) is not None: revised += 1
        return revised

    @classmethod
    def sync(cls, db: PostgresDatabaseAPI, broker: str, catalog: pl.DataFrame, at: Union[datetime, Missing] = MISSING) -> dict:
        at, by = utc_now() if at is MISSING else at, cls.by()
        provider = cls.provider(db, broker)
        current = catalog.filter(pl.col("Status") != SecurityStatus.Archived.name)
        tickers = {row["UID"]: row["Category"] for row in db.records(schema=TickerAPI.Schema, table=TickerAPI.Table, columns=["UID", "Category"])}
        assigned = cls._categories_(db, current, tickers, at, by)
        cls._tickers_(db, current, tickers, assigned, at, by)
        securities = cls._securities_(db, provider, current, at, by)
        archived = cls._archive_(db, provider, catalog, at, by)
        revised = cls._contracts_(db, current, securities, at, by)
        return {"Provider": provider, "Symbols": current.height, "Created": sum(1 for uid in assigned if uid not in tickers), "Revised": revised, "Archived": archived}

    def _refresh_(self, api, broker: str) -> dict:
        catalog = api.universe.catalog(archived=True, legacy=False)
        with PostgresDatabaseAPI(database=self._database_) as db: outcome = self.sync(db, broker, catalog)
        self._log_.info(lambda: f"Universe Sync: Completed ({outcome['Provider']}) · {outcome['Symbols']} Symbols · {outcome['Created']} New Tickers · {outcome['Revised']} Revised Contracts · {outcome['Archived']} Archived")
        return outcome

    def work(self) -> None:
        account = next((account for account in self.accounts() if account.get("Broker")), None)
        if account is None: raise LookupError("Universe Service: Failed · No demo account names its broker")
        broker = account["Broker"]
        with self.client(int(account["AccountId"])) as api:
            self._refresh_(api, broker)
            self.ready(broker)
            release = api.universe.changes(lambda symbols: self._changed_.set())
            try:
                last = time.monotonic()
                while not self.stopped(self._pause_):
                    due = time.monotonic() - last >= self._interval_
                    if not (due or self._changed_.is_set()): continue
                    self._changed_.clear()
                    try: self._refresh_(api, broker)
                    except Exception as error: self._log_.failure(lambda error=error: f"Universe Sync: Failed · {error}")
                    last = time.monotonic()
            finally: release()

def main(database="Quant") -> int:
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Info)
    with log:
        return UniverseServiceAPI(database=database).serve()

if __name__ == "__main__":
    raise SystemExit(main())