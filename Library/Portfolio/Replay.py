from __future__ import annotations

from bisect import bisect_right
from datetime import datetime
from typing import Union

from Library.Database.Dataframe import np
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Market.Bar import BarAPI
from Library.Market.Download import DownloadAPI
from Library.Market.Price import Direction
from Library.Market.Tape import TapeAPI
from Library.Market.Tick import TickAPI
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Cashflow import CashflowAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Portfolio import PortfolioAPI
from Library.Portfolio.Position import PositionAPI, PositionType
from Library.Portfolio.Trade import TradeAPI
from Library.Statistic.Curve import CurveAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime, utc_now
from Library.Utility.Typing import MISSING, Missing

class ReplayAPI:

    def __init__(self, db: PostgresDatabaseAPI, security: SecurityAPI, asset: str, timeframe: TimeframeAPI, readers: int = 8) -> None:
        self._db_ = db
        self._security_ = security
        self._asset_ = asset
        self._timeframe_ = timeframe
        self._readers_ = readers
        self._tape_ = None
        self._sources_ = (None, None)

    def _load_(self, start: datetime, stop: datetime) -> tuple[list[BarAPI], list[tuple[int, int]]]:
        tape, frame = TapeAPI.span(self._db_, self._security_.UID, self._timeframe_, start, stop, workers=self._readers_)
        if not tape.Stamps.size or not frame.height: return [], []
        quote = TapeAPI.source(self._db_, self._security_, self._security_.Ticker.QuoteAsset, self._asset_, tape, workers=self._readers_)
        self._tape_, self._sources_ = tape, (None, quote)
        bars = [BarAPI.row(row, self._security_, self._timeframe_) for row in tape.materialize(frame, self._timeframe_, None, quote).to_dicts()]
        return bars, list(zip(frame["Open"].to_list(), frame["Close"].to_list()))

    def _ticks_(self, first: int, last: int) -> list[TickAPI]:
        if last <= first: return []
        tape = self._tape_
        asks, bids = tape.Asks[first:last], tape.Bids[first:last]
        index = np.unique(first + np.array([0, int(np.argmax(asks)), int(np.argmax(bids)), int(np.argmin(asks)), int(np.argmin(bids)), last - first - 1]))
        stamps = tape.Stamps[index]
        base, quote = TapeAPI.rates(stamps, self._sources_[0]), TapeAPI.rates(stamps, self._sources_[1])
        return [TickAPI(Security=self._security_, Timestamp=epoch_to_datetime(int(stamps[k])), Ask=float(tape.Asks[i]), Bid=float(tape.Bids[i]),
                        AskBaseConversion=float(base[0][k]), BidBaseConversion=float(base[1][k]), AskQuoteConversion=float(quote[0][k]), BidQuoteConversion=float(quote[1][k]))
                for k, i in enumerate(index)]

    def _quote_(self, moment: int) -> tuple[float, float, float]:
        tape = self._tape_
        index = max(int(np.searchsorted(tape.Stamps, moment, side="right")) - 1, 0)
        rate = float(TapeAPI.rates(np.array([moment], dtype=np.int64), self._sources_[1])[1][0])
        return float(tape.Asks[index]), float(tape.Bids[index]), rate if rate == rate else 1.0

    def _spread_(self, moment: datetime, volume: float) -> float:
        ask, bid, rate = self._quote_(datetime_to_epoch(moment))
        return (bid - ask) * volume * rate

    def _open_(self, portfolio: PortfolioAPI, position: PositionAPI) -> None:
        position.SpreadPnL = self._spread_(position.EntryTimestamp.DateTime, position.Volume)
        portfolio.open_position(None, position)

    def _change_(self, portfolio: PortfolioAPI, moment: datetime, position: PositionAPI) -> None:
        held = portfolio.position(position.UID)
        if held is None: return self._open_(portfolio, position)
        added = position.Volume - held.Volume
        position.SpreadPnL = (held.SpreadPnL.PnL if held.SpreadPnL else 0.0) + self._spread_(moment, added)
        position.SwapPnL = held.SwapPnL.PnL if held.SwapPnL else 0.0
        portfolio.modify_position(position)

    @staticmethod
    def _share_(value, volume: float, total: float) -> float:
        return (value.PnL if value else 0.0) * volume / total if total else 0.0

    def _close_(self, portfolio: PortfolioAPI, trade: TradeAPI, remaining: Union[PositionAPI, None]) -> None:
        held = portfolio.position(trade.Position.UID)
        trade.SpreadPnL = self._share_(held.SpreadPnL, trade.Volume, held.Volume)
        if remaining is not None:
            for name in ("CommissionPnL", "SpreadPnL", "SwapPnL"): setattr(remaining, name, self._share_(getattr(held, name), remaining.Volume, held.Volume))
        portfolio.close_position(trade.Position.UID, remaining, trade)

    def _roll_(self, portfolio: PortfolioAPI, moment: int, days: int) -> None:
        contract = self._security_.Contract
        if contract is None: return
        _, bid, rate = self._quote_(moment)
        skip = int(contract.SwapSkip or 0)
        for position in portfolio.BuyPositions + portfolio.SellPositions:
            if skip and len(contract.rolls(position.EntryTimestamp.DateTime, epoch_to_datetime(moment))) < skip: continue
            if datetime_to_epoch(position.EntryTimestamp.DateTime) < moment: portfolio.charge(position, swap=contract.swap(position.IsLong, position.Volume, bid, days) * rate)

    @staticmethod
    def facts(db: PostgresDatabaseAPI, account: int) -> list[tuple[datetime, float, float]]:
        flows = db.records(schema=CashflowAPI.Schema, table=CashflowAPI.Table, condition='"Account" = :account:', parameters={"account": account})
        closes = db.records(schema=TradeAPI.Schema, table=TradeAPI.Table, condition='"Account" = :account: AND "ExitBalance" IS NOT NULL AND "NetPnL" IS NOT NULL', parameters={"account": account})
        return [(row["Timestamp"], row["Balance"] - row["Delta"], row["Balance"]) for row in flows] + [(row["ExitTimestamp"], row["ExitBalance"] - row["NetPnL"], row["ExitBalance"]) for row in closes]

    @staticmethod
    def balance(facts: list[tuple[datetime, float, float]]):
        ordered = sorted(facts, key=lambda fact: fact[0])
        stamps = [fact[0] for fact in ordered]
        def at(moment: datetime) -> Union[float, None]:
            if not ordered: return None
            index = bisect_right(stamps, moment)
            return ordered[index - 1][2] if index else ordered[0][1]
        return at

    @staticmethod
    def orders(db: PostgresDatabaseAPI, account: int, positions: list) -> list[dict]:
        return db.records(schema=OrderAPI.Schema, table=OrderAPI.Table, condition='"Account" = :account: AND "Position" = ANY(:positions:)', parameters={"account": account, "positions": sorted(positions)}) if positions else []

    @staticmethod
    def _position_(uid: int, security: SecurityAPI, side: str, volume: float, entry: datetime, price: float, commission: float = 0.0, stop: Union[float, None] = None, take: Union[float, None] = None, label: Union[str, None] = None) -> PositionAPI:
        return PositionAPI(UID=uid, Security=security, Type=PositionType.Normal, Direction=Direction[side], Volume=volume, EntryTimestamp=entry, EntryPrice=price, StopLossPrice=stop, TakeProfitPrice=take,
                           GrossPnL=0.0, CommissionPnL=commission, SwapPnL=0.0, NetPnL=commission, Label=label)

    @staticmethod
    def _trade_(row: dict, security: SecurityAPI) -> TradeAPI:
        return TradeAPI(UID=row["UID"], Position=row["Position"], Security=security, Type=PositionType.Normal, Direction=Direction[row["Direction"]], Volume=row["Volume"], EntryTimestamp=row["EntryTimestamp"],
                        EntryPrice=row["EntryPrice"], ExitTimestamp=row["ExitTimestamp"], ExitPrice=row["ExitPrice"], GrossPnL=row["GrossPnL"], CommissionPnL=row["CommissionPnL"], SwapPnL=row["SwapPnL"], NetPnL=row["NetPnL"])

    @staticmethod
    def _rate_(trades: list[dict], live: Union[dict, None]) -> float:
        closed = sum(row["Volume"] for row in trades)
        if closed: return sum(row["CommissionPnL"] or 0.0 for row in trades) / closed / 2.0
        return (live.get("CommissionPnL") or 0.0) / live["Volume"] if live and live.get("Volume") else 0.0

    @staticmethod
    def _fills_(orders: list[dict]) -> dict[int, list[dict]]:
        fills = {}
        for row in sorted(orders, key=lambda row: (row.get("LastUpdateTimestamp") or row["EntryTimestamp"], row["UID"])):
            if row.get("Position") is not None and row.get("ExecutedVolume") and row.get("ExecutionPrice") is not None: fills.setdefault(row["Position"], []).append(row)
        return fills

    @staticmethod
    def _netted_(fills: list[dict]) -> bool:
        side, volume = None, 0.0
        for fill in fills:
            if side is not None and (fill["Direction"] == side or fill["ExecutedVolume"] > volume + 1e-9): return True
            side, volume = (fill["Direction"], fill["ExecutedVolume"]) if side is None else (side, volume - fill["ExecutedVolume"])
            if volume <= 1e-9: side, volume = None, 0.0
        return False

    @classmethod
    def _net_(cls, uid: int, security: SecurityAPI, fills: list[dict], trades: list[dict], rate: float, label: Union[str, None], opened: dict, closes: list, changes: list) -> None:
        pending, side, volume, entry, start = list(trades), None, 0.0, 0.0, None
        for fill in fills:
            moment, quantity, direction, price = fill.get("LastUpdateTimestamp") or fill["EntryTimestamp"], fill["ExecutedVolume"], fill["Direction"], fill["ExecutionPrice"]
            if side is None or direction == side:
                entry, start = (entry * volume + price * quantity) / (volume + quantity), start if side is not None else moment
                side, volume = direction, volume + quantity
                position = cls._position_(uid, security, side, volume, start, entry, commission=rate * volume, label=label)
                if uid in opened: changes.append((moment, position))
                else: opened[uid] = position
                continue
            matched = [row for row in pending if row.get("Order") == fill["UID"]] or [row for row in pending if abs((row["ExitTimestamp"] - moment).total_seconds()) < 5.0]
            closed = sum(row["Volume"] for row in matched) if matched else min(quantity, volume)
            for row in matched:
                pending.remove(row)
                volume -= row["Volume"]
                closes.append((cls._trade_(row, security), cls._position_(uid, security, side, volume, start, entry, label=label) if volume > 1e-9 else None))
            if not matched: volume -= closed
            if volume > 1e-9: continue
            if quantity - closed > 1e-9:
                side, volume, entry, start = direction, quantity - closed, price, moment
                changes.append((moment, cls._position_(uid, security, side, volume, start, entry, commission=rate * volume, label=label)))
            else: side, volume, entry, start = None, 0.0, 0.0, None

    @classmethod
    def book(cls, security: SecurityAPI, trades: list[dict], positions: list[dict], orders: list[dict] = ()) -> tuple[dict, list[tuple[TradeAPI, Union[PositionAPI, None]]], list[tuple[datetime, PositionAPI]]]:
        rows = sorted(trades, key=lambda row: (row["ExitTimestamp"], row["UID"]))
        live = {row["UID"]: row for row in positions}
        fills = cls._fills_(orders)
        netted = {uid for uid, own in fills.items() if cls._netted_(own)}
        opened, closes, changes = {}, [], []
        for uid in sorted(netted):
            own = [row for row in rows if row["Position"] == uid]
            label = next((row.get("Label") for row in own + ([live[uid]] if uid in live else []) if row.get("Label")), None)
            cls._net_(uid, security, fills[uid], own, cls._rate_(own, live.get(uid)), label, opened, closes, changes)
        rows = [row for row in rows if row["Position"] not in netted]
        volumes = {}
        for row in rows: volumes[row["Position"]] = volumes.get(row["Position"], 0.0) + row["Volume"]
        for row in positions:
            if row["UID"] not in netted: volumes[row["UID"]] = volumes.get(row["UID"], 0.0) + row["Volume"]
        first = {}
        for row in rows + [{**row, "Position": row["UID"]} for row in positions if row["UID"] not in netted]: first.setdefault(row["Position"], row)
        for uid, row in first.items():
            if row["EntryTimestamp"] is None: continue
            rate = cls._rate_([other for other in rows if other["Position"] == uid], live.get(uid))
            opened[uid] = cls._position_(uid, security, row["Direction"], volumes[uid], row["EntryTimestamp"], row["EntryPrice"], commission=rate * volumes[uid], stop=row.get("StopLossPrice"), take=row.get("TakeProfitPrice"), label=row.get("Label"))
        left = dict(volumes)
        for row in rows:
            if row["Position"] not in opened: continue
            left[row["Position"]] -= row["Volume"]
            remaining = cls._position_(row["Position"], security, row["Direction"], left[row["Position"]], row["EntryTimestamp"], row["EntryPrice"]) if left[row["Position"]] > 1e-9 else None
            closes.append((cls._trade_(row, security), remaining))
        return opened, closes, changes

    @staticmethod
    def _events_(positions: list[PositionAPI], closes: list[tuple[TradeAPI, Union[PositionAPI, None]]], changes: list[tuple[datetime, PositionAPI]], rolls: list[tuple[datetime, int]]) -> list[tuple]:
        opens = [(datetime_to_epoch(position.EntryTimestamp.DateTime), 0, position.UID, position, None) for position in positions]
        shuts = [(datetime_to_epoch(trade.ExitTimestamp.DateTime), 1, trade.UID, trade, remaining) for trade, remaining in closes]
        moves = [(datetime_to_epoch(moment), 2, position.UID, position, moment) for moment, position in changes]
        charges = [(datetime_to_epoch(moment), 3, 0, days, None) for moment, days in rolls]
        return sorted(opens + shuts + moves + charges, key=lambda event: event[:3])

    def replay(self, account: AccountAPI, positions: list[PositionAPI], closes: list[tuple[TradeAPI, Union[PositionAPI, None]]], balance, start: datetime, stop: datetime, marks: Union[list, None] = None, changes: list = ()) -> PortfolioAPI:
        portfolio = PortfolioAPI()
        portfolio.Security = self._security_
        portfolio.init_data(account)
        bars, spans = self._load_(start, stop)
        rolls = self._security_.Contract.rolls(start, stop) if self._security_.Contract is not None else []
        events, cursor = self._events_(positions, closes, changes, rolls), 0
        stamps = self._tape_.Stamps if self._tape_ is not None else np.empty(0, dtype=np.int64)
        for index, bar in enumerate(bars):
            first, last = spans[index][0], spans[index][1] + 1
            if cursor >= len(events) or events[cursor][0] > int(stamps[last - 1]): portfolio.update_data(bar)
            else:
                position = first
                while cursor < len(events) and events[cursor][0] <= int(stamps[last - 1]):
                    moment, kind, _, item, extra = events[cursor]
                    cursor += 1
                    cut = int(np.searchsorted(stamps, moment, side="right" if kind == 1 else "left"))
                    for tick in self._ticks_(position, max(position, cut)): portfolio.update_data(tick)
                    position = max(position, cut)
                    known = balance(epoch_to_datetime(moment))
                    if known is not None: account.Balance = known
                    if kind == 0: self._open_(portfolio, item)
                    elif kind == 1:
                        if item.Position is not None and portfolio.position(item.Position.UID) is not None: self._close_(portfolio, item, extra)
                    elif kind == 2: self._change_(portfolio, extra, item)
                    else: self._roll_(portfolio, moment, item)
                for tick in self._ticks_(position, last): portfolio.update_data(tick)
            if marks is not None: marks.append((bar.Timestamp.DateTime, epoch_to_datetime(int(stamps[last - 1])), portfolio.UnrealizedPnL))
        return portfolio

    @staticmethod
    def derived(item: Union[PositionAPI, TradeAPI]) -> dict:
        price = lambda value: value.Price if value is not None else None
        pnl = lambda value: value.PnL if value is not None else None
        unmarked = isinstance(item, TradeAPI) and item.MaxEquityDrawdownPrice is None
        exit, net = (price(item.ExitPrice), pnl(item.NetPnL)) if unmarked else (None, None)
        return {"EntryBalance": item.EntryBalance, "MidBalance": item.MidBalance, "StopLossPnL": pnl(item.StopLossPnL), "TakeProfitPnL": pnl(item.TakeProfitPnL), "SpreadPnL": pnl(item.SpreadPnL),
                "MaxEquityDrawdownPrice": exit if unmarked else price(item.MaxEquityDrawdownPrice), "MaxEquityRunupPrice": exit if unmarked else price(item.MaxEquityRunupPrice),
                "MaxEquityDrawdownPnL": net if unmarked else pnl(item.MaxEquityDrawdownPnL), "MaxEquityRunupPnL": net if unmarked else pnl(item.MaxEquityRunupPnL)}

    @staticmethod
    def _unrealized_(marks: list[tuple], grid: list[datetime]) -> list[float]:
        stamps, values, window = [mark[0] for mark in marks], [mark[2] for mark in marks], (marks[0][0], marks[-1][0])
        return [values[bisect_right(stamps, stamp) - 1] if window[0] <= stamp <= window[1] else 0.0 for stamp in grid]

    @classmethod
    def curves(cls, db: PostgresDatabaseAPI, account: int, asset: str, timeframe: TimeframeAPI, label: Union[str, Missing] = MISSING, readers: int = 8) -> tuple[list, list, list, CurveAPI, list]:
        condition, parameters = '"Account" = :account: AND "Security" IS NOT NULL', {"account": account}
        if label is not MISSING: condition, parameters = f'{condition} AND "Label" = :label:', {**parameters, "label": label}
        trades = db.records(schema=TradeAPI.Schema, table=TradeAPI.Table, condition=condition, parameters=parameters)
        positions = db.records(schema=PositionAPI.Schema, table=PositionAPI.Table, condition=condition, parameters=parameters)
        orders = cls.orders(db, account, {row["Position"] for row in trades} | {row["UID"] for row in positions})
        ledger = cls.balance(cls.facts(db, account))
        if label is not MISSING:
            entries = [row["EntryTimestamp"] for row in trades + positions if row["EntryTimestamp"] is not None]
            origin = (ledger(min(entries)) if entries else None) or 0.0
            exits = sorted((row["ExitTimestamp"], row["NetPnL"] or 0.0) for row in trades)
            stamps, sums = [stamp for stamp, _ in exits], list(np.cumsum([net for _, net in exits])) if exits else []
            ledger = lambda moment: origin + (float(sums[bisect_right(stamps, moment) - 1]) if bisect_right(stamps, moment) else 0.0)
        marks, skipped = [], []
        for uid in sorted({row["Security"] for row in trades + positions}):
            security = SecurityAPI(UID=uid, db=db, autoload=True)
            opened, closes, changes = cls.book(security, [row for row in trades if row["Security"] == uid], [row for row in positions if row["Security"] == uid], [row for row in orders if row["Security"] == uid])
            if not opened: continue
            through = DownloadAPI.through(db, uid)
            if through is None:
                skipped.append(f"{security.Ticker.UID} (Not tracked)")
                continue
            start = min(position.EntryTimestamp.DateTime for position in opened.values())
            stop = max([trade.ExitTimestamp.DateTime for trade, _ in closes] + ([min(utc_now(), through)] if any(row["Security"] == uid for row in positions) else []), default=start)
            own = []
            try: cls(db, security, asset, timeframe, readers=readers).replay(AccountAPI(UID=account, Asset=asset, Balance=0.0), list(opened.values()), closes, lambda moment: None, start, stop, marks=own, changes=changes)
            except ValueError as error:
                skipped.append(f"{security.Ticker.UID} ({error})")
                continue
            if own: marks.append(own)
        grid = sorted({mark[0] for own in marks for mark in own})
        ends = {}
        for own in marks:
            for stamp, end, _ in own: ends[stamp] = max(ends.get(stamp, end), end)
        unrealized = [cls._unrealized_(own, grid) for own in marks]
        balances = [ledger(ends[stamp]) or 0.0 for stamp in grid]
        equities = [balances[index] + sum(values[index] for values in unrealized) for index in range(len(grid))]
        curve = CurveAPI()
        for stamp, equity in zip(grid, equities):
            curve.record(stamp, equity)
            curve.observe(equity)
        return grid, balances, equities, curve, skipped