import math
import pytest
from datetime import datetime, timedelta

from Library.Database.Dataframe import np, pl
from Script.Data.Portfolio import PortfolioWorkerAPI
from Library.Market.Download import DownloadAPI, DownloadStatus
from Library.Market.Tape import TapeAPI
from Library.Portfolio.Account import AccountAPI
from Library.Portfolio.Cashflow import CashflowAPI
from Library.Portfolio.Order import OrderAPI
from Library.Portfolio.Position import PositionAPI
from Library.Portfolio.Replay import ReplayAPI
from Library.Portfolio.Trade import TradeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.Datetime import datetime_to_epoch, epoch_to_datetime

DAY = datetime(2026, 3, 10)
ACCOUNT = 7001
DEPOSIT = 10_000.0

def bids(count: int) -> list[int]:
    return [110_000 + round(120 * math.sin(index / 9.0) + 35 * math.sin(index / 2.3)) + (index % 7) * 3 for index in range(count)]

@pytest.fixture
def mirror(tape):
    db, security = tape
    for kind in (AccountAPI, OrderAPI, PositionAPI, TradeAPI, CashflowAPI): kind(db=db, migrate=True, autoload=False)
    for kind in (TradeAPI, PositionAPI, CashflowAPI, AccountAPI): db.remove(schema=kind.Schema, table=kind.Table, condition=f'"{"UID" if kind is AccountAPI else "Account"}" = :account:', parameters={"account": ACCOUNT})
    db.upsert(schema=AccountAPI.Schema, table=AccountAPI.Table, data=[{"UID": ACCOUNT, "Provider": "Pepperstone(cTrader)", "Asset": "USD", "Balance": DEPOSIT, "Tracked": True, "UpdatedBy": "Tester"}], key=["UID"])
    stamps = [datetime_to_epoch(DAY + timedelta(hours=9)) + 7_000 * index for index in range(1200)]
    path = bids(len(stamps))
    frame = pl.DataFrame({"Stamp": stamps, "Ask": [bid + 2 + index % 3 for index, bid in enumerate(path)], "Bid": path}, schema={"Stamp": pl.Int64, "Ask": pl.Int64, "Bid": pl.Int64})
    TapeAPI.write(db, security, frame, DAY, DAY + timedelta(days=1), "Tester")
    DownloadAPI(Security=security, Timestamp=DAY, Ticks=frame.height, Status=DownloadStatus.Complete, Through=DAY + timedelta(days=1), db=db).save(by="Tester")
    CashflowAPI(UID=1, Account=ACCOUNT, Timestamp=DAY + timedelta(hours=8), Type="Deposit", Delta=DEPOSIT, Balance=DEPOSIT, Equity=DEPOSIT, db=db).save(by="Tester")
    yield db, security, frame
    for kind in (TradeAPI, PositionAPI, CashflowAPI, AccountAPI): db.remove(schema=kind.Schema, table=kind.Table, condition=f'"{"UID" if kind is AccountAPI else "Account"}" = :account:', parameters={"account": ACCOUNT})

def moment(frame: pl.DataFrame, index: int) -> datetime:
    return epoch_to_datetime(int(frame["Stamp"][index]))

def price(frame: pl.DataFrame, column: str, index: int) -> float:
    return int(frame[column][index]) / 100_000

def window(frame: pl.DataFrame, column: str, first: int, last: int) -> np.ndarray:
    return frame[column].to_numpy()[first:last + 1] / 100_000

def closed(uid: int, position: int, side: str, volume: float, frame: pl.DataFrame, entry: int, exit: int, balance: float, label: str = "Run") -> dict:
    opened, shut = (price(frame, "Ask", entry), price(frame, "Bid", exit)) if side == "Buy" else (price(frame, "Bid", entry), price(frame, "Ask", exit))
    gross = round((shut - opened if side == "Buy" else opened - shut) * volume, 2)
    return {"UID": uid, "Position": position, "Security": None, "Direction": side, "Volume": volume, "EntryTimestamp": moment(frame, entry), "EntryPrice": opened, "ExitTimestamp": moment(frame, exit),
            "ExitPrice": shut, "GrossPnL": gross, "CommissionPnL": 0.0, "SwapPnL": 0.0, "NetPnL": gross, "ExitBalance": round(balance + gross, 2), "Label": label}

def replayed(db, security: int, trades: list[dict]) -> dict:
    for row in trades: row["Security"] = security
    item = SecurityAPI(UID=security, db=db, autoload=True)
    opened, closes, _ = ReplayAPI.book(item, trades, [])
    facts = [(DAY + timedelta(hours=8), 0.0, DEPOSIT)] + [(row["ExitTimestamp"], row["ExitBalance"] - row["NetPnL"], row["ExitBalance"]) for row in trades]
    start = min(row["EntryTimestamp"] for row in trades)
    stop = max(row["ExitTimestamp"] for row in trades)
    portfolio = ReplayAPI(db, item, "USD", TimeframeAPI(UID="M1")).replay(AccountAPI(UID=ACCOUNT, Asset="USD", Balance=0.0), list(opened.values()), closes, ReplayAPI.balance(facts), start, stop)
    return {trade.UID: ReplayAPI.derived(trade) for trade in portfolio._trades_}

def test_a_long_trades_excursions_equal_the_bid_extremes_of_its_holding_window(mirror):
    db, security, frame = mirror
    derived = replayed(db, security, [closed(1, 11, "Buy", 10_000.0, frame, 97, 733, DEPOSIT)])[1]
    held = window(frame, "Bid", 97, 733)
    assert derived["MaxEquityDrawdownPrice"] == pytest.approx(held.min(), abs=1e-9)
    assert derived["MaxEquityRunupPrice"] == pytest.approx(held.max(), abs=1e-9)
    assert derived["EntryBalance"] == DEPOSIT

def test_a_short_trades_excursions_equal_the_ask_extremes_of_its_holding_window(mirror):
    db, security, frame = mirror
    derived = replayed(db, security, [closed(2, 12, "Sell", 10_000.0, frame, 211, 1004, DEPOSIT)])[2]
    held = window(frame, "Ask", 211, 1004)
    assert derived["MaxEquityDrawdownPrice"] == pytest.approx(held.max(), abs=1e-9)
    assert derived["MaxEquityRunupPrice"] == pytest.approx(held.min(), abs=1e-9)

def test_each_partial_close_keeps_the_excursions_of_its_own_window(mirror):
    db, security, frame = mirror
    first = closed(3, 13, "Buy", 5_000.0, frame, 150, 402, DEPOSIT)
    second = closed(4, 13, "Buy", 5_000.0, frame, 150, 977, first["ExitBalance"])
    derived = replayed(db, security, [first, second])
    assert derived[3]["MaxEquityDrawdownPrice"] == pytest.approx(window(frame, "Bid", 150, 402).min(), abs=1e-9)
    assert derived[4]["MaxEquityDrawdownPrice"] == pytest.approx(window(frame, "Bid", 150, 977).min(), abs=1e-9)
    assert derived[4]["MaxEquityRunupPrice"] == pytest.approx(window(frame, "Bid", 150, 977).max(), abs=1e-9)

def test_the_book_splits_a_position_into_its_closes_and_what_each_left_open():
    trades = [{"UID": 5, "Position": 9, "Direction": "Buy", "Volume": 3.0, "EntryTimestamp": DAY, "EntryPrice": 1.1, "ExitTimestamp": DAY + timedelta(hours=1), "ExitPrice": 1.2, "GrossPnL": 0.3, "CommissionPnL": 0.0, "SwapPnL": 0.0, "NetPnL": 0.3},
              {"UID": 6, "Position": 9, "Direction": "Buy", "Volume": 2.0, "EntryTimestamp": DAY, "EntryPrice": 1.1, "ExitTimestamp": DAY + timedelta(hours=2), "ExitPrice": 1.3, "GrossPnL": 0.4, "CommissionPnL": 0.0, "SwapPnL": 0.0, "NetPnL": 0.4}]
    opened, closes, _ = ReplayAPI.book(SecurityAPI(UID=1), trades, [{"UID": 9, "Direction": "Buy", "Volume": 1.0, "EntryTimestamp": DAY, "EntryPrice": 1.1, "Status": "Opened", "CommissionPnL": -0.5, "SwapPnL": -0.1}])
    assert opened[9].Volume == 6.0
    assert [(trade.UID, remaining.Volume if remaining else None) for trade, remaining in closes] == [(5, 3.0), (6, 1.0)]

def test_the_balance_at_an_instant_reads_the_last_fact_at_or_before_it():
    at = ReplayAPI.balance([(DAY + timedelta(hours=2), 100.0, 90.0), (DAY + timedelta(hours=1), 0.0, 100.0)])
    assert at(DAY) == 0.0 and at(DAY + timedelta(hours=1)) == 100.0 and at(DAY + timedelta(hours=3)) == 90.0
    assert ReplayAPI.balance([])(DAY) is None

def test_the_account_curve_is_the_balance_plus_the_open_pnl_at_each_bar_close(mirror):
    db, security, frame = mirror
    trade = closed(8, 18, "Buy", 10_000.0, frame, 97, 733, DEPOSIT)
    trade["Account"] = ACCOUNT
    trade["Security"] = security
    db.upsert(schema=TradeAPI.Schema, table=TradeAPI.Table, data=[{**trade, "UpdatedBy": "Tester"}], key=["UID"])
    grid, balances, equities, curve, skipped = ReplayAPI.curves(db, ACCOUNT, "USD", TimeframeAPI(UID="M1"))
    assert not skipped and grid and len(grid) == len(balances) == len(equities)
    assert curve.Values == pytest.approx(equities) and curve.Stamps == grid
    stamps = frame["Stamp"].to_numpy()
    for stamp, balance, equity in zip(grid, balances, equities):
        close = int(np.searchsorted(stamps, datetime_to_epoch(stamp + timedelta(minutes=1)), side="left")) - 1
        exited = close >= 733
        assert balance == pytest.approx(trade["ExitBalance"] if exited else DEPOSIT)
        expected = balance if exited else DEPOSIT + (price(frame, "Bid", close) - trade["EntryPrice"]) * trade["Volume"]
        assert equity == pytest.approx(expected, abs=1e-6)
    labelled = ReplayAPI.curves(db, ACCOUNT, "USD", TimeframeAPI(UID="M1"), label="Run")
    assert labelled[0] == grid and labelled[2] == pytest.approx(equities)
    assert ReplayAPI.curves(db, ACCOUNT, "USD", TimeframeAPI(UID="M1"), label="Nobody")[0] == []

def test_the_margin_follows_the_accounts_calculation_mode():
    positions = pl.DataFrame({"Symbol": [1, 1, 2], "Direction": ["Buy", "Sell", "Buy"], "UsedMargin": [100.0, 40.0, 25.0]})
    assert PortfolioWorkerAPI._margin_(positions, "Sum") == 165.0
    assert PortfolioWorkerAPI._margin_(positions, "Max") == 125.0
    assert PortfolioWorkerAPI._margin_(positions, "Net") is None
    assert PortfolioWorkerAPI._margin_(pl.DataFrame(), "Max") == 0.0

def test_a_closing_deal_becomes_a_trade_on_its_positions_side_with_its_net():
    service = PortfolioWorkerAPI(account=ACCOUNT, horizon=DAY, database="Tests", vault="Tests")
    service._securities_ = {1: 42}
    deals = pl.DataFrame([{"DealID": 70, "OrderID": 60, "PositionID": 50, "Symbol": 1, "Direction": "Buy", "Volume": 1000.0, "ClosedVolume": None, "ExecutionTimestamp": DAY, "ExecutionPrice": 1.1,
                           "EntryPrice": None, "GrossPnL": None, "ClosingCommission": None, "SwapPnL": None, "Balance": None, "Closing": False},
                          {"DealID": 71, "OrderID": 61, "PositionID": 50, "Symbol": 1, "Direction": "Sell", "Volume": 1000.0, "ClosedVolume": 1000.0, "ExecutionTimestamp": DAY + timedelta(hours=1), "ExecutionPrice": 1.2,
                           "EntryPrice": 1.1, "GrossPnL": 100.0, "ClosingCommission": -3.0, "SwapPnL": -1.5, "Balance": 10_095.5, "Closing": True}])
    rows = service._trade_rows_(deals, {50: "Run"}, {})
    assert len(rows) == 1
    row = rows[0]
    assert (row["UID"], row["Position"], row["Security"], row["Direction"], row["NetPnL"], row["Label"]) == (71, 50, 42, "Buy", 95.5, "Run")
    assert row["EntryTimestamp"] == DAY and row["ExitBalance"] == 10_095.5
    orphan = service._trade_rows_(deals.filter(pl.col("Closing")), {}, {})[0]
    assert "EntryTimestamp" not in orphan
def test_a_trade_no_tick_saw_open_takes_its_exit_as_both_excursions(mirror):
    db, security, frame = mirror
    trade = closed(9, 19, "Buy", 10_000.0, frame, 100, 100, DEPOSIT)
    trade["EntryTimestamp"], trade["ExitTimestamp"] = moment(frame, 100) + timedelta(milliseconds=1), moment(frame, 100) + timedelta(milliseconds=3)
    derived = replayed(db, security, [trade])[9]
    assert derived["MaxEquityDrawdownPrice"] == derived["MaxEquityRunupPrice"] == trade["ExitPrice"]
    assert derived["MaxEquityDrawdownPnL"] == derived["MaxEquityRunupPnL"] == trade["NetPnL"]

def test_an_open_position_on_a_security_without_a_tape_is_left_for_later(tape):
    db, security = tape
    service = PortfolioWorkerAPI(account=ACCOUNT, horizon=DAY, database="Tests", vault="Tests")
    position = {"UID": 31, "Security": security, "Direction": "Buy", "Volume": 1000.0, "EntryTimestamp": DAY, "EntryPrice": 1.1, "Status": "Opened", "CommissionPnL": 0.0, "SwapPnL": 0.0}
    assert service._derive_(db, security, [], [position], []) == 0