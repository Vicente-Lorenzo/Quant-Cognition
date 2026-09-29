import sys
import time
from pathlib import Path
from typing import Union
from argparse import ArgumentParser
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Library.Database import PostgresDatabaseAPI
from Library.Database.Dataframe import pl
from Library.Logging import LoggingAPI, VerboseLevel
from Library.Market.Download import DownloadAPI
from Library.Market.Price import Direction
from Library.Portfolio.Account import AccountAPI, Environment, MarginMode
from Library.Portfolio.Cashflow import CashflowAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI, PositionStatus, PositionType
from Library.Portfolio.Replay import ReplayAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import utc_now
from Library.Utility.Typing import MISSING, Missing
from Script.Data.Horizon import HORIZON
from Script.Data.Service import DataServiceAPI, SupervisorAPI
from Script.Data.Universe import UniverseServiceAPI

class PortfolioWorkerAPI(DataServiceAPI):

    def __init__(self, *, account: int, horizon: datetime, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING, poll: float = 5.0, overlap: float = 60.0, refresh: float = 300.0) -> None:
        super().__init__(database=database, credential=credential, vault=vault)
        self._account_ = account
        self._horizon_ = horizon
        self._poll_ = poll
        self._overlap_ = timedelta(seconds=overlap)
        self._refresh_ = refresh
        self._frontier_: Union[datetime, None] = None
        self._securities_: dict = {}
        self._provider_: Union[str, None] = None
        self._asset_: Union[str, None] = None
        self._failed_: dict = {}

    @staticmethod
    def by() -> str:
        return "Portfolio"

    @staticmethod
    def _columns_(kind: type) -> set:
        return {str(name) for name in kind(db=None).Structure}

    def _write_(self, db: PostgresDatabaseAPI, kind: type, rows: list[dict]) -> int:
        if not rows: return 0
        columns, stamp = self._columns_(kind), utc_now()
        groups = {}
        for row in rows:
            data = {**{key: value for key, value in row.items() if key in columns}, "UpdatedAt": stamp, "UpdatedBy": self.by()}
            groups.setdefault(tuple(data), []).append(data)
        for group in groups.values(): db.upsert(schema=kind.Schema, table=kind.Table, data=pl.DataFrame(group, strict=False, infer_schema_length=None), key=["UID"])
        return len(rows)

    def _security_(self, symbol: Union[int, None]) -> Union[int, None]:
        return self._securities_.get(symbol)

    @staticmethod
    def _margin_(positions: pl.DataFrame, mode: Union[str, None]) -> Union[float, None]:
        if not positions.height: return 0.0
        if mode == MarginMode.Sum.name: return float(positions["UsedMargin"].sum())
        if mode != MarginMode.Max.name: return None
        sides = positions.group_by("Symbol", "Direction").agg(pl.col("UsedMargin").sum())
        return float(sides.group_by("Symbol").agg(pl.col("UsedMargin").max())["UsedMargin"].sum())

    def _account_row_(self, api, values: dict, positions: pl.DataFrame, unrealized: dict) -> dict:
        frame = api.portfolio.account(legacy=False).row(0, named=True)
        equity = frame["Balance"] + sum(net or 0.0 for _, net in unrealized.values())
        used = self._margin_(positions, frame["MarginMode"])
        return {"UID": self._account_, "Provider": self._provider_, "Number": frame["TraderLogin"], "Environment": (Environment.Live if values.get("Live") else Environment.Demo).name,
                "AccountType": frame["AccountType"], "MarginMode": frame["MarginMode"], "Asset": self._asset_, "Leverage": frame["Leverage"], "Balance": frame["Balance"], "Equity": equity,
                "MarginUsed": used, "MarginFree": equity - used if used is not None else None, "MarginLevel": equity / used * 100.0 if used else None}

    def _order_rows_(self, frame: pl.DataFrame) -> list[dict]:
        rows = []
        for order in frame.iter_rows(named=True):
            rows.append({**order, "UID": order["OrderID"], "Account": self._account_, "Position": order["PositionID"], "Security": self._security_(order["Symbol"])})
        return rows

    def _position_rows_(self, frame: pl.DataFrame, unrealized: dict) -> list[dict]:
        rows = []
        for position in frame.iter_rows(named=True):
            gross = unrealized.get(position["PositionID"], (None, None))
            rows.append({**position, "UID": position["PositionID"], "Account": self._account_, "Security": self._security_(position["Symbol"]), "Type": PositionType.Normal.name,
                         "Status": PositionStatus.Opened.name, "GrossPnL": gross[0], "NetPnL": gross[1]})
        return rows

    def _entries_(self, db: PostgresDatabaseAPI) -> dict:
        entries = {row["Position"]: row["EntryTimestamp"] for row in db.records(schema=TradeAPI.Schema, table=TradeAPI.Table, columns=["Position", "EntryTimestamp"], condition='"Account" = :account: AND "EntryTimestamp" IS NOT NULL', parameters={"account": self._account_})}
        entries.update({row["UID"]: row["EntryTimestamp"] for row in db.records(schema=PositionAPI.Schema, table=PositionAPI.Table, columns=["UID", "EntryTimestamp"], condition='"Account" = :account: AND "EntryTimestamp" IS NOT NULL', parameters={"account": self._account_})})
        return entries

    def _trade_rows_(self, deals: pl.DataFrame, labels: dict, entries: dict) -> list[dict]:
        entries = dict(entries)
        for deal in deals.filter(~pl.col("Closing")).sort("ExecutionTimestamp").iter_rows(named=True): entries.setdefault(deal["PositionID"], deal["ExecutionTimestamp"])
        rows = []
        for deal in deals.filter(pl.col("Closing")).iter_rows(named=True):
            side = Direction.Sell.name if deal["Direction"] == Direction.Buy.name else Direction.Buy.name
            net = (deal["GrossPnL"] or 0.0) + (deal["ClosingCommission"] or 0.0) + (deal["SwapPnL"] or 0.0)
            rows.append({"UID": deal["DealID"], "Account": self._account_, "Position": deal["PositionID"], "Security": self._security_(deal["Symbol"]), "Type": PositionType.Normal.name,
                         "Status": PositionStatus.Closed.name, "Direction": side, "Volume": deal["ClosedVolume"] or deal["Volume"], "EntryTimestamp": entries.get(deal["PositionID"]),
                         "EntryPrice": deal["EntryPrice"], "ExitTimestamp": deal["ExecutionTimestamp"], "ExitPrice": deal["ExecutionPrice"], "GrossPnL": deal["GrossPnL"],
                         "CommissionPnL": deal["ClosingCommission"], "SwapPnL": deal["SwapPnL"], "NetPnL": net, "ExitBalance": deal["Balance"], "Label": labels.get(deal["PositionID"]), "_Order_": deal["OrderID"]})
            if rows[-1]["EntryTimestamp"] is None: del rows[-1]["EntryTimestamp"]
        return rows

    def _cashflow_rows_(self, frame: pl.DataFrame) -> list[dict]:
        return [{"UID": row["BalanceHistoryId"], "Account": self._account_, "Timestamp": row["ChangeBalanceTimestamp"], "Type": row["OperationType"], "Delta": row["Delta"],
                 "Balance": row["Balance"], "Equity": row["Equity"], "Note": row["ExternalNote"]} for row in frame.iter_rows(named=True)]

    def _sync_(self, api, db: PostgresDatabaseAPI, values: dict) -> dict:
        start = self._frontier_ - self._overlap_ if self._frontier_ else self._horizon_
        now = utc_now()
        unrealized = {row["PositionID"]: (row["GrossPnL"], row["NetPnL"]) for row in api.portfolio.pnl(legacy=False).iter_rows(named=True)}
        positions = api.portfolio.positions(legacy=False)
        self._write_(db, AccountAPI, [self._account_row_(api, values, positions, unrealized)])
        orders = api.portfolio.orders(start, now, legacy=False)
        opened = api.portfolio.orders(legacy=False)
        written = self._write_(db, OrderAPI, self._order_rows_(pl.concat([orders, opened], how="diagonal_relaxed")) if orders.height or opened.height else [])
        known = {row["UID"] for row in db.records(schema=OrderAPI.Schema, table=OrderAPI.Table, columns=["UID"], condition='"Account" = :account:', parameters={"account": self._account_})}
        labels = {row["Position"]: row["Label"] for row in db.records(schema=OrderAPI.Schema, table=OrderAPI.Table, columns=["Position", "Label"], condition='"Account" = :account: AND "Label" IS NOT NULL', parameters={"account": self._account_})}
        deals = api.portfolio.deals(start, now, legacy=False)
        trades = [{**row, "Order": row["_Order_"] if row["_Order_"] in known else None} for row in self._trade_rows_(deals, labels, self._entries_(db))] if deals.height else []
        self._write_(db, TradeAPI, trades)
        self._write_(db, PositionAPI, self._position_rows_(positions, unrealized))
        live = set(positions["PositionID"].to_list()) if positions.height else set()
        stored = {row["UID"] for row in db.records(schema=PositionAPI.Schema, table=PositionAPI.Table, columns=["UID"], condition='"Account" = :account:', parameters={"account": self._account_})}
        for closed in stored - live: db.remove(schema=PositionAPI.Schema, table=PositionAPI.Table, condition='"UID" = :uid:', parameters={"uid": closed})
        flows = api.portfolio.cashflow(start, now, legacy=False)
        self._write_(db, CashflowAPI, self._cashflow_rows_(flows) if flows.height else [])
        db.update(schema=AccountAPI.Schema, table=AccountAPI.Table, data={"Timestamp": now}, condition='"UID" = :uid:', parameters={"uid": self._account_})
        self._frontier_ = now
        return {"Orders": written, "Trades": len(trades), "Positions": len(live), "Cashflows": flows.height}

    def _derive_(self, db: PostgresDatabaseAPI, security_uid: int, trades: list[dict], positions: list[dict], facts: list[tuple]) -> int:
        through = DownloadAPI.through(db, security_uid)
        if through is None: return 0
        security = SecurityAPI(UID=security_uid, db=db, autoload=True)
        opened, closes, changes = ReplayAPI.book(security, trades, positions, ReplayAPI.orders(db, self._account_, {row["Position"] for row in trades} | {row["UID"] for row in positions}))
        if not opened: return 0
        start = min(position.EntryTimestamp.DateTime for position in opened.values())
        exits = [trade.ExitTimestamp.DateTime for trade, _ in closes]
        stop = max(exits + ([min(utc_now(), through)] if positions else []), default=start)
        if through < max(exits, default=start) or not DownloadAPI.covers(db, security_uid, start, stop): return 0
        portfolio = ReplayAPI(db, security, self._asset_, TimeframeAPI(UID="M1")).replay(AccountAPI(UID=self._account_, Asset=self._asset_, Balance=0.0), list(opened.values()), closes, ReplayAPI.balance(facts), start, stop, changes=changes)
        derived = [{"UID": trade.UID, **ReplayAPI.derived(trade)} for trade in portfolio.closed()]
        current = [{"UID": row["UID"], **ReplayAPI.derived(portfolio.position(row["UID"]))} for row in positions if portfolio.position(row["UID"]) is not None]
        self._write_(db, TradeAPI, derived)
        self._write_(db, PositionAPI, current)
        return len(derived) + len(current)

    def _pending_(self, db: PostgresDatabaseAPI, everything: bool) -> set:
        account = {"account": self._account_}
        waiting = db.records(schema=TradeAPI.Schema, table=TradeAPI.Table, columns=["Position"], condition='"Account" = :account: AND "Security" IS NOT NULL AND "MaxEquityDrawdownPrice" IS NULL', parameters=account)
        opened = db.records(schema=PositionAPI.Schema, table=PositionAPI.Table, columns=["UID"], condition='"Account" = :account: AND "Security" IS NOT NULL', parameters=account) if everything else []
        return {row["Position"] for row in waiting} | {row["UID"] for row in opened}

    def _derivations_(self, db: PostgresDatabaseAPI, everything: bool) -> int:
        pending = self._pending_(db, everything)
        if not pending: return 0
        scope = {"account": self._account_, "pending": sorted(pending)}
        trades = db.records(schema=TradeAPI.Schema, table=TradeAPI.Table, condition='"Account" = :account: AND "Security" IS NOT NULL AND "Position" = ANY(:pending:)', parameters=scope)
        positions = db.records(schema=PositionAPI.Schema, table=PositionAPI.Table, condition='"Account" = :account: AND "Security" IS NOT NULL AND "UID" = ANY(:pending:)', parameters=scope)
        facts, derived = ReplayAPI.facts(db, self._account_), 0
        for security in sorted({row["Security"] for row in trades + positions}):
            if security in self._failed_ and time.monotonic() - self._failed_[security] < self._refresh_: continue
            try:
                derived += self._derive_(db, security, [row for row in trades if row["Security"] == security], [row for row in positions if row["Security"] == security], facts)
                self._failed_.pop(security, None)
            except Exception as error:
                self._failed_[security] = time.monotonic()
                self._log_.warning(lambda security=security, error=error: f"Portfolio Derivation: Failed ({self._account_} · Security {security}) · {error}")
        return derived

    def work(self) -> None:
        values = next((account for account in self.accounts() if int(account["AccountId"]) == self._account_), None)
        if values is None: raise LookupError(f"Portfolio Worker: Failed · Account {self._account_} is not reachable by the stored token")
        with PostgresDatabaseAPI(database=self._database_) as db:
            self._provider_ = UniverseServiceAPI.provider(db, values.get("Broker") or "Spotware")
            self._asset_ = values.get("Currency")
            synced = db.first(schema=AccountAPI.Schema, table=AccountAPI.Table, columns=["Timestamp"], condition='"UID" = :uid:', parameters={"uid": self._account_})
            self._frontier_ = synced["Timestamp"] if synced else None
            self._securities_ = {row["Symbol"]: row["UID"] for row in db.records(schema=SecurityAPI.Schema, table=SecurityAPI.Table, columns=["UID", "Symbol"], condition='"Provider" = :provider:', parameters={"provider": self._provider_})}
            with self.client(self._account_) as api:
                registration = api.portfolio.account(legacy=False)["Registration"][0]
                if registration is not None: self._horizon_ = max(self._horizon_, registration)
                outcome = self._sync_(api, db, values)
                derived = self._derivations_(db, True)
                self.ready(f"{self._account_} · {outcome['Trades']} Trades · {outcome['Positions']} Open · {derived} Derived")
                refreshed = time.monotonic()
                while not self.stopped(self._poll_):
                    try:
                        self._sync_(api, db, values)
                        everything = time.monotonic() - refreshed >= self._refresh_
                        self._derivations_(db, everything)
                        if everything: refreshed = time.monotonic()
                    except Exception as error:
                        if self.stopped(): break
                        self._log_.warning(lambda error=error: f"Portfolio Sync: Failed ({self._account_}) · {error}")

class PortfolioServiceAPI(SupervisorAPI):

    def __init__(self, *, script: Path, database: str = "Quant", credential: str = "cTrader ID", vault: Union[str, Missing] = MISSING, interval: float = 30.0, backoff: float = 60.0) -> None:
        super().__init__(script=script, flag="--account", name="Portfolio", database=database, credential=credential, vault=vault, interval=interval, backoff=backoff)

    def _discover_(self, db: PostgresDatabaseAPI) -> None:
        stored = {row["UID"] for row in db.records(schema=AccountAPI.Schema, table=AccountAPI.Table, columns=["UID"])}
        fresh = [{"UID": int(account["AccountId"]), "Provider": UniverseServiceAPI.provider(db, account["Broker"]), "Environment": Environment.Demo.name, "Asset": account.get("Currency"), "Tracked": True,
                  "UpdatedAt": utc_now(), "UpdatedBy": "Portfolio"} for account in self.accounts() if account.get("Broker") and int(account["AccountId"]) not in stored]
        if fresh: db.upsert(schema=AccountAPI.Schema, table=AccountAPI.Table, data=fresh, key=["UID"])

    def tracked(self) -> dict:
        with PostgresDatabaseAPI(database=self._database_) as db:
            self._discover_(db)
            rows = db.records(schema=AccountAPI.Schema, table=AccountAPI.Table, columns=["UID", "Asset"], condition='"Tracked" = :tracked: AND "Environment" = :demo:', parameters={"tracked": True, "demo": Environment.Demo.name})
        return {row["UID"]: f"{row['UID']} {row['Asset'] or ''}".strip() for row in rows}

def main() -> int:
    parser = ArgumentParser(prog="Portfolio")
    parser.add_argument("--account", type=int, default=None)
    parser.add_argument("--database", default="Quant")
    args = parser.parse_args()
    worker, log = args.account is not None, LoggingAPI()
    log.console.set_level(VerboseLevel.Warning if worker else VerboseLevel.Info)
    log.file.set_level(VerboseLevel.Warning if worker else VerboseLevel.Info)
    with log:
        if worker: return PortfolioWorkerAPI(account=args.account, horizon=HORIZON, database=args.database).serve()
        return PortfolioServiceAPI(script=Path(__file__).resolve(), database=args.database).serve()

if __name__ == "__main__":
    raise SystemExit(main())