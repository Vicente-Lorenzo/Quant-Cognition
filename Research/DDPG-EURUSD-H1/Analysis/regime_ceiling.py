import os, sys
sys.path.insert(0, r"C:\Users\Admin\OneDrive\Documents\cAlgo")
os.chdir(r"C:\Users\Admin\OneDrive\Documents\cAlgo")
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")

from datetime import datetime
from Library.Database.Dataframe import np, pd
from Library.Database.Postgres.Postgres import PostgresDatabaseAPI
from Library.Logging import HandlerLoggingAPI, VerboseLevel
from Library.Market.Market import MarketAPI
from Library.Universe.Provider import ProviderAPI
from Library.Universe.Ticker import TickerAPI
from Library.Universe.Security import SecurityAPI
from Library.Universe.Timeframe import TimeframeAPI

HandlerLoggingAPI(Class="Ceiling", Subclass="Regime").set_verbose_level(VerboseLevel.Warning)
with PostgresDatabaseAPI(database="Quant") as db:
    tf = TimeframeAPI(UID="H1", db=db, autoload=True)
    p = ProviderAPI(UID="Spotware(cTrader)", db=db, autoload=True)
    t = TickerAPI(UID="EURUSD", db=db, autoload=True)
    s = SecurityAPI(Provider=p, Ticker=t, db=db, autoload=True)
    frame = MarketAPI.pull_bars(db, s.UID, tf.UID, start=datetime(2014, 1, 1), stop=datetime(2026, 1, 1)).to_pandas()

close = frame["CloseTick.Bid"].astype(float).reset_index(drop=True)
stamp = pd.to_datetime(frame["Timestamp"]).reset_index(drop=True)
inside = stamp >= pd.Timestamp(2015, 1, 1)
year = stamp.dt.year

moves = {}
for y in sorted(year[inside].unique()):
    cc = close[(year == y) & inside]
    if len(cc) > 100: moves[int(y)] = (float(cc.iloc[-1]) / float(cc.iloc[0]) - 1.0) * 100.0

def score(signal, label):
    weighted, total, detail = 0.0, 0.0, []
    for y, move in moves.items():
        sel = (year == y) & inside
        sig = signal[sel]
        sig = sig[~np.isnan(sig)]
        if len(sig) < 100: continue
        longfrac = float((sig > 0).sum()) / float((sig != 0).sum()) if (sig != 0).sum() else 0.0
        aligned = longfrac if move > 0 else 1.0 - longfrac
        weighted += aligned * abs(move); total += abs(move)
        detail.append((y, move, longfrac * 100, aligned * 100))
    value = 100.0 * weighted / total if total else 0.0
    print(f"  {label:<28} REGIME SCORE {value:5.1f}%", flush=True)
    return value, detail

print("=== REGIME-FOLLOWING CEILING · EURUSD H1 · can a trivial slow-trend rule follow regimes? ===", flush=True)
print("  (50% = coin flip / one-sided · >55% = real regime skill · 100% = perfect foresight)", flush=True)
print("", flush=True)
best = None
for window in (480, 1440, 2880, 4320, 8640):
    sma = close.rolling(window).mean()
    sig = np.sign(close - sma).to_numpy()
    value, detail = score(sig, f"SMA-cross L={window} ({window/24:.0f}d)")
    if best is None or value > best[0]: best = (value, f"SMA{window}", detail)
    roc = close - close.shift(window)
    score(np.sign(roc).to_numpy(), f"ROC sign  L={window} ({window/24:.0f}d)")

forward = close.shift(-720) - close
print("", flush=True)
score(np.sign(forward).to_numpy(), "ORACLE fwd-30d (leak)")
print("", flush=True)
print("=== P&L OF THE TRIVIAL REGIME RULE (vol-targeted like the strategy, real spread) ===", flush=True)
logret = np.log(close).diff().to_numpy()
high = frame["HighTick.Bid"].astype(float).reset_index(drop=True)
low = frame["LowTick.Bid"].astype(float).reset_index(drop=True)
prev = close.shift()
true_range = pd.concat([(high - low), (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
atr = true_range.rolling(14).mean().to_numpy()
mask = inside.to_numpy()
for window in (1440, 2880, 4320):
    sma = close.rolling(window).mean()
    sig = np.sign(close - sma).to_numpy()
    lev = np.where(atr > 0, 0.01 / (1.5 * atr / close.to_numpy()), 0.0)
    lev = np.clip(np.nan_to_num(lev), 0.0, 10.0) * 0.05
    position = np.nan_to_num(sig) * lev
    turn = np.abs(np.diff(np.concatenate([[0.0], position])))
    spread = 0.00008 / close.to_numpy()
    net = position[:-1] * logret[1:] - turn[:-1] * spread[:-1]
    net = net[mask[:-1]]
    equity = np.cumprod(1.0 + np.nan_to_num(net))
    peak = np.maximum.accumulate(equity)
    dd = float(((peak - equity) / peak).max() * 100)
    flips = int((np.abs(np.diff(np.nan_to_num(sig[mask]))) > 0).sum())
    longfrac = float((sig[mask] > 0).sum()) / float((sig[mask] != 0).sum()) * 100
    print(f"  SMA{window:<5} ({window/24:3.0f}d) · return {(equity[-1]-1)*100:+7.2f}% · maxDD {dd:5.1f}% · long {longfrac:4.1f}% · direction-changes {flips} · mean lev {lev[mask].mean():.2f}x", flush=True)
print("", flush=True)
print(f"=== BEST TRIVIAL RULE: {best[1]} at {best[0]:.1f}% ===", flush=True)
for y, move, lf, al in best[2]:
    print(f"    {y} market {move:+6.2f}% · long {lf:5.1f}% · aligned {al:5.1f}% {'OK' if al > 50 else 'MISS'}", flush=True)
