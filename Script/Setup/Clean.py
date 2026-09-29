import sys
import json
from pathlib import Path
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Utility.Datetime import utc_now
from Library.Utility.Path import inspect_persistent
from Library.Utility.IO import read_json, write_json
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Database import PostgresDatabaseAPI, QueryAPI
from Library.Data.Universe import UniverseServiceAPI
from Library.Market.Download import DownloadAPI
from Library.Market.Tape import TapeAPI
from Library.Universe import CategoryAPI, ContractAPI, ProviderAPI, SecurityAPI, TickerAPI

MARKER = inspect_persistent("Migrations") / "universe-clean.json"
ARCHIVE = inspect_persistent("Archive", "Market.Tick 2026-09-27") / "Manifest.json"
PORTFOLIO = ("Trade", "Position", "Order", "Account", "Session")
UNIVERSE = ("Contract", "Security", "Ticker", "Category", "Provider")

def _old_(db) -> dict:
    tickers = {row["UID"]: row["Category"] for row in db.records(schema="Universe", table="Ticker", columns=["UID", "Category"])}
    categories = {row["UID"]: row for row in db.records(schema="Universe", table="Category")}
    securities = {row["Ticker"]: row["UID"] for row in db.records(schema="Universe", table="Security", columns=["UID", "Ticker"], condition='"Provider" = :provider:', parameters={"provider": "Spotware(cTrader)"})}
    terms = db.records(schema="Universe", table="Contract", condition='"Provider" = :provider: AND "UpdatedBy" = :by:', parameters={"provider": "Spotware(cTrader)", "by": "Autosave"})
    counts = {table: len(db.records(schema="Universe", table=table, columns=["UpdatedAt"])) for table in UNIVERSE}
    return {"Tickers": tickers, "Categories": categories, "Securities": securities, "Terms": {row["Ticker"]: row for row in terms}, "Counts": counts}

def _tape_(db) -> int:
    exists = db.executeone(QueryAPI("SELECT COUNT(*) FROM timescaledb_information.hypertables WHERE hypertable_schema = 'Market' AND hypertable_name = 'Tick'")).fetchall(legacy=False).item()
    if not exists: return 0
    return sum(entry["Rows"] for entry in read_json(ARCHIVE).get("Securities", {}).values()) if ARCHIVE.exists() else -1

def _plan_(old: dict, catalog) -> dict:
    current = catalog.filter(catalog["Status"] != "Archived")
    confirmed = {TickerAPI.normalize(name) for name in current["Ticker"].to_list()}
    kept = {uid: category for uid, category in old["Tickers"].items() if uid in confirmed}
    carried = {ticker: uid for ticker, uid in old["Securities"].items() if ticker in confirmed}
    return {"Symbols": current.height, "Kept Tickers": kept, "Dropped Tickers": len(old["Tickers"]) - len(kept), "Carried Securities": carried,
            "Dropped Securities": old["Counts"]["Security"] - len(carried), "Seeded Terms": sorted(ticker for ticker in old["Terms"] if ticker in carried)}

def _seed_(db, old: dict, plan: dict, broker: str, catalog) -> None:
    provider = UniverseServiceAPI.provider(db, broker)
    used = {category for category in plan["Kept Tickers"].values() if category}
    if used: db.upsert(schema="Universe", table="Category", data=[{key: old["Categories"][uid][key] for key in ("UID", "Primary", "Secondary", "Alternative")} | {"UpdatedAt": utc_now(), "UpdatedBy": "Migration"} for uid in sorted(used)], key=["UID"])
    db.upsert(schema="Universe", table="Ticker", data=[{"UID": uid, "Category": category, "UpdatedAt": utc_now(), "UpdatedBy": "Migration"} for uid, category in plan["Kept Tickers"].items()], key=["UID"])
    rows = {TickerAPI.normalize(row["Ticker"]): row for row in catalog.filter(catalog["Status"] != "Archived").iter_rows(named=True)}
    for ticker, uid in sorted(plan["Carried Securities"].items(), key=lambda item: item[1]):
        row = rows[ticker]
        db.executeone(QueryAPI('''INSERT INTO "Universe"."Security" ("UID", "Provider", "Ticker", "Type", "Symbol", "Status", "Tracked", "UpdatedAt", "UpdatedBy") OVERRIDING SYSTEM VALUE
            VALUES (:uid:, :provider:, :ticker:, :type:, :symbol:, :status:, FALSE, :at:, 'Migration')'''), uid=uid, provider=provider, ticker=ticker, type=row["Type"], symbol=row["Symbol"], status=row["Status"], at=utc_now())
    top = db.executeone(QueryAPI('SELECT COALESCE(MAX("UID"), 0) + 1 FROM "Universe"."Security"')).fetchall(legacy=False).item()
    db.executeone(QueryAPI(f'ALTER TABLE "Universe"."Security" ALTER COLUMN "UID" RESTART WITH {int(top)}'))
    for ticker in plan["Seeded Terms"]:
        terms = old["Terms"][ticker]
        ContractAPI(Security=plan["Carried Securities"][ticker], Timestamp=terms["UpdatedAt"], **{name: terms.get(name) for name in ContractAPI.terms() if name in terms}, db=db).save(by="Autosave")

def _apply_(database: str, old: dict, plan: dict, broker: str, catalog, log) -> dict:
    with PostgresDatabaseAPI(database=database) as db:
        db.executeone(QueryAPI('DROP TABLE IF EXISTS "Market"."Download"'))
        db.executeone(QueryAPI('DROP TABLE IF EXISTS "Market"."Tick" CASCADE'))
        for table in PORTFOLIO: db.executeone(QueryAPI(f'DROP TABLE IF EXISTS "Portfolio"."{table}" CASCADE'))
        for table in UNIVERSE: db.executeone(QueryAPI(f'DROP TABLE IF EXISTS "Universe"."{table}" CASCADE'))
        for kind in (CategoryAPI, ProviderAPI, TickerAPI, SecurityAPI, ContractAPI): kind(db=db, migrate=True)
        _seed_(db, old, plan, broker, catalog)
        outcome = UniverseServiceAPI.sync(db, broker, catalog)
        TapeAPI.create(db)
        DownloadAPI(db=db, migrate=True)
        tracked = [row["UID"] for row in db.records(schema="Universe", table="Ticker", columns=["UID", "Category"]) if row["Category"] in ("Forex(Major)", "Forex(Minor)")]
        db.update(schema="Universe", table="Security", data={"Tracked": True, "UpdatedAt": utc_now(), "UpdatedBy": "Migration"}, condition='"Provider" = :provider: AND "Ticker" = ANY(:tickers:)', parameters={"provider": outcome["Provider"], "tickers": tracked})
        log.info(lambda: f"Universe Clean: Synced · {outcome['Symbols']} Symbols · {outcome['Revised']} Contracts · {len(tracked)} Tracked")
        return {**outcome, "Tracked": sorted(tracked)}

def main(database: str = "Quant", apply: bool = False, force: bool = False, vault: str = "Quant") -> int:
    log = LoggingAPI()
    log.console.set_level(VerboseLevel.Info)
    with log:
        applied = read_json(MARKER).get("Applied") if database == "Quant" else None
        if apply and not force and applied:
            log.error(lambda: f"Universe Clean: Refused · Already Applied {applied}")
            return 1
        service = UniverseServiceAPI(database=database, vault=vault)
        account = next((account for account in service.accounts() if account.get("Broker")), None)
        if account is None:
            log.error(lambda: "Universe Clean: Refused · No demo account names its broker")
            return 1
        with service.client(int(account["AccountId"])) as api: catalog = api.universe.catalog(archived=True, legacy=False)
        with PostgresDatabaseAPI(database=database) as db:
            old = _old_(db)
            dumped = _tape_(db)
        if dumped < 0 and database == "Quant":
            log.error(lambda: f"Universe Clean: Refused · Market.Tick exists and no verified dump at {ARCHIVE}")
            return 1
        plan = _plan_(old, catalog)
        log.info(lambda: f"Universe Clean: Plan · {plan['Symbols']} Symbols · {len(plan['Kept Tickers'])} Tickers Kept · {plan['Dropped Tickers']} Dropped · {len(plan['Carried Securities'])} Securities Carried · {plan['Dropped Securities']} Dropped · Terms Seeded {' · '.join(plan['Seeded Terms']) or 'None'} · Tape {dumped:,} Ticks Dumped")
        if not apply:
            log.info(lambda: "Universe Clean: Dry Run · Nothing Changed · Pass --apply")
            return 0
        saved = MARKER.with_name(f"universe-clean-prior {utc_now():%Y-%m-%d %H-%M-%S}.json")
        write_json(saved, json.loads(json.dumps({"Old": old, "Plan": plan}, default=str)), safe=False)
        log.info(lambda: f"Universe Clean: Saved (Prior Rows) · {saved.name}")
        outcome = _apply_(database, old, plan, account["Broker"], catalog, log)
        if database == "Quant": write_json(MARKER, {"Applied": utc_now().isoformat(sep=" ", timespec="seconds"), "Plan": {key: value if not isinstance(value, dict) else len(value) for key, value in plan.items()}, "Outcome": outcome})
        return 0

if __name__ == "__main__":
    parser = ArgumentParser(prog="Clean")
    parser.add_argument("--database", default="Quant")
    parser.add_argument("--vault", default="Quant")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    raise SystemExit(main(args.database, args.apply, args.force, args.vault))