import sys
from pathlib import Path
from datetime import datetime, timedelta
from argparse import ArgumentParser

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from Library.Database import PostgresDatabaseAPI
from Library.Database.Dataframe import np, pl
from Library.Market.Tape import TapeAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI
from Library.Utility.IO import mkdir
from Script.Campaign.Campaign import root

INK, MUTED, LONG, SHORT, FOLD, TEST = "#222222", "#8a8a8a", "#2f6fd6", "#d64545", "#eef1f5", "#fdf1dc"
PAGES = {"A": ("AUDUSD", "EURUSD", "GBPUSD"), "B": ("NZDUSD", "USDCAD", "USDCHF"), "C": ("USDJPY",)}

def _style_(axis) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(MUTED)
    axis.tick_params(colors=MUTED, labelsize=9)
    axis.grid(axis="y", color="#e6e6e6", linewidth=0.8)
    axis.set_axisbelow(True)

def _name_(pair: str) -> str:
    return f"{pair[:3]}/{pair[3:]}"

def _read_(folder: Path, name: str) -> pl.DataFrame:
    path = folder / "Output" / "Export" / f"{name}.csv"
    return pl.read_csv(path, try_parse_dates=True, infer_schema_length=None) if path.is_file() else pl.DataFrame()

def _model_(row: dict) -> Path:
    return root() / row["Pair"] / f"Arm {row['Arm']}" / row["Job"] / "Evaluation" / f"Seed {row['Seed']}"

def _benchmark_(start: datetime, stop: datetime) -> pl.DataFrame:
    cache = root() / "Figures" / "US500.csv"
    if cache.is_file(): return pl.read_csv(cache, try_parse_dates=True)
    with PostgresDatabaseAPI(database="Quant") as db:
        security = SecurityAPI(Provider="Spotware(cTrader)", Ticker="US500", db=db, autoload=True)
        tape, bars = TapeAPI.span(db, security.UID, TimeframeAPI(UID="D1", db=db, autoload=True), start, stop)
    frame = pl.DataFrame({"Timestamp": pl.Series(bars["Timestamp"].to_numpy()).cast(pl.Datetime("ms")), "Close": tape.Bids[bars["Close"].to_numpy()]})
    mkdir(cache.parent, safe=False)
    frame.write_csv(cache)
    return frame

def _shade_(axis) -> None:
    for year in range(2018, 2025): axis.axvspan(datetime(year, 1, 1), datetime(year + 1, 1, 1), color=FOLD if year % 2 == 0 else "#f6f8fa", zorder=0, linewidth=0)
    axis.axvspan(datetime(2025, 1, 1), datetime(2026, 1, 1), color=TEST, zorder=0, linewidth=0)

def equity(rows: list, target: Path, benchmark: bool = True) -> None:
    figure, axes = plt.subplots(len(rows), 1, figsize=(12.4, 3.35 * len(rows)), squeeze=False)
    reference = _benchmark_(datetime(2015, 1, 1), datetime(2026, 1, 1)) if benchmark else None
    for axis, row in zip(axes[:, 0], rows):
        full = _model_(row) / "Full"
        prices, curve = _read_(full, "prices"), _read_(full, "equity")
        _shade_(axis)
        axis.plot(curve["Timestamp"], curve["Equity"] / curve["Equity"][0] * 100.0, color=INK, linewidth=1.3, label="Model")
        axis.plot(prices["Timestamp"], prices["Close"] / prices["Close"][0] * 100.0, color=MUTED, linewidth=1.0, linestyle="--", label="Buy and Hold")
        if reference is not None and reference.height:
            window = reference.filter(pl.col("Timestamp") >= reference["Timestamp"][0])
            axis.plot(window["Timestamp"], window["Close"] / window["Close"][0] * 100.0, color="#b8a36a", linewidth=0.9, linestyle=":", label="US 500")
        axis.set_title(_name_(row["Pair"]), fontsize=12, color=INK)
        axis.set_ylabel("Equity (Rebased 100)", fontsize=10)
        axis.set_xlim(datetime(2015, 1, 1), datetime(2026, 1, 1))
        axis.legend(frameon=False, loc="upper left", fontsize=9)
        _style_(axis)
    figure.tight_layout()
    figure.savefig(target)
    plt.close(figure)

def signal(row: dict, target: Path, start: datetime = datetime(2018, 1, 1), stop: datetime = datetime(2026, 1, 1)) -> None:
    full = _model_(row) / "Full"
    prices, signals = _read_(full, "prices"), _read_(full, "signals")
    prices, signals = prices.filter(pl.col("Timestamp").is_between(start, stop)), signals.filter(pl.col("Timestamp").is_between(start, stop))
    figure, (top, middle, bottom) = plt.subplots(3, 1, figsize=(12.4, 7.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1.2, 1.2]})
    for axis in (top, middle, bottom): _shade_(axis)
    top.plot(prices["Timestamp"], prices["Close"], color=INK, linewidth=0.9)
    top.set_ylabel(_name_(row["Pair"]), fontsize=10)
    action = signals["Signal"].to_numpy()
    middle.fill_between(signals["Timestamp"], action, 0.0, where=action > 0, color=LONG, alpha=0.55, linewidth=0, step="post")
    middle.fill_between(signals["Timestamp"], action, 0.0, where=action < 0, color=SHORT, alpha=0.55, linewidth=0, step="post")
    middle.set_ylim(-1.05, 1.05)
    middle.set_ylabel("Direction\n(Action)", fontsize=10)
    exposure = signals["Exposure"].to_numpy() / 1000.0
    bottom.fill_between(signals["Timestamp"], exposure, 0.0, where=exposure > 0, color=LONG, alpha=0.55, linewidth=0, step="post")
    bottom.fill_between(signals["Timestamp"], exposure, 0.0, where=exposure < 0, color=SHORT, alpha=0.55, linewidth=0, step="post")
    bottom.set_ylabel("Net Position\n(000s Units)", fontsize=10)
    for axis in (top, middle, bottom):
        axis.axhline(0.0, color=MUTED, linewidth=0.6) if axis is not top else None
        _style_(axis)
    bottom.set_xlim(start, stop)
    figure.tight_layout()
    figure.savefig(target)
    plt.close(figure)

def _candles_(axis, frame: pl.DataFrame) -> None:
    rising = frame["Close"] >= frame["Open"]
    for color, mask in ((LONG, rising), (SHORT, ~rising)):
        part = frame.filter(mask)
        axis.vlines(part["Timestamp"], part["Low"], part["High"], color=color, linewidth=0.8)
        axis.bar(part["Timestamp"], (part["Close"] - part["Open"]).abs().clip(lower_bound=1e-6), bottom=part.select(pl.min_horizontal("Open", "Close")).to_series(), width=0.6, color=color, linewidth=0)

def trades(row: dict, target: Path, margin: int = 20) -> None:
    full = _model_(row) / "Full"
    deals, prices, signals = _read_(full, "deals"), _read_(full, "prices"), _read_(full, "signals")
    deals = deals.with_columns(((pl.col("ExitTimestamp") - pl.col("EntryTimestamp")).dt.total_hours() / 24.0).alias("Days"))
    best = deals.filter(pl.col("Days") >= 5).sort("NetPnL", descending=True).head(1)
    if not best.height: return
    trade = best.row(0, named=True)
    start, stop = trade["EntryTimestamp"] - timedelta(days=margin), trade["ExitTimestamp"] + timedelta(days=margin)
    daily = prices.filter(pl.col("Timestamp").is_between(start, stop)).group_by_dynamic("Timestamp", every="1d").agg(pl.col("Open").first(), pl.col("High").max(), pl.col("Low").min(), pl.col("Close").last())
    held = signals.filter(pl.col("Timestamp").is_between(start, stop))
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(12.4, 6.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    exposure = held["Exposure"].to_numpy()
    for axis in (top, bottom):
        axis.fill_between(held["Timestamp"], 0, 1, where=exposure > 0, transform=axis.get_xaxis_transform(), color=LONG, alpha=0.06, linewidth=0, step="post")
        axis.fill_between(held["Timestamp"], 0, 1, where=exposure < 0, transform=axis.get_xaxis_transform(), color=SHORT, alpha=0.06, linewidth=0, step="post")
    _candles_(top, daily)
    side = "long" if trade["Direction"] == "Buy" else "short"
    top.annotate(f"open {side}  {trade['EntryPrice']:.5g}", xy=(trade["EntryTimestamp"], trade["EntryPrice"]), xytext=(0, 40), textcoords="offset points", ha="center", fontsize=10, arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.6})
    top.plot([trade["EntryTimestamp"], trade["ExitTimestamp"]], [trade["EntryPrice"], trade["ExitPrice"]], color=INK, linestyle=":", linewidth=1.2)
    top.scatter([trade["ExitTimestamp"]], [trade["ExitPrice"]], marker="X", s=110, color=INK, zorder=5)
    top.annotate(f"close  {trade['ExitPrice']:.5g}\n{trade['Days']:.0f} days,  {trade['NetPnL']:+,.0f} USD", xy=(trade["ExitTimestamp"], trade["ExitPrice"]), xytext=(-60, 40), textcoords="offset points", ha="center", fontsize=10, arrowprops={"arrowstyle": "-", "color": MUTED})
    top.set_ylabel(_name_(row["Pair"]), fontsize=11)
    bottom.fill_between(held["Timestamp"], exposure / 1000.0, 0.0, where=exposure > 0, color=LONG, alpha=0.55, linewidth=0, step="post")
    bottom.fill_between(held["Timestamp"], exposure / 1000.0, 0.0, where=exposure < 0, color=SHORT, alpha=0.55, linewidth=0, step="post")
    bottom.axhline(0.0, color=MUTED, linewidth=0.6)
    bottom.set_ylabel("Net Position\n(000s Units)", fontsize=10)
    for axis in (top, bottom): _style_(axis)
    bottom.set_xlim(start, stop)
    figure.tight_layout()
    figure.savefig(target)
    plt.close(figure)

def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()
    summary = root() / "Summary.csv"
    if not summary.is_file(): return 0
    rows, folder = pl.read_csv(summary, infer_schema_length=None).to_dicts(), root() / "Figures"
    mkdir(folder, safe=False)
    by = {row["Pair"]: row for row in rows}
    for page, pairs in PAGES.items():
        chosen = [by[pair] for pair in pairs if pair in by]
        if chosen: equity(chosen, folder / f"PairEquity{page}.pdf", args.benchmark)
    for row in rows:
        signal(row, folder / f"Signal{row['Pair']}.pdf")
        trades(row, folder / f"TrendRide{row['Pair']}.pdf")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())