import sys, math
from pathlib import Path
from datetime import datetime

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")

import os
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
import numpy as np

def pearson(x, y):
    dx = x - x.mean(); dy = y - y.mean()
    den = math.sqrt(float((dx * dx).sum())) * math.sqrt(float((dy * dy).sum()))
    return float((dx * dy).sum()) / den if den else float('nan')

CSV = Path(sys.argv[1])
rows = [line.split(",") for line in CSV.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
stamps = [datetime.fromisoformat(r[0]) for r in rows]
equity = np.array([float(r[1]) for r in rows])
exposure = np.array([float(r[2]) for r in rows])
closes = np.array([float(r[3]) for r in rows])
deltas = np.array([float(r[4]) for r in rows])
years = np.array([s.year for s in stamps])
months = np.array([s.month for s in stamps])
side = np.sign(exposure)

print(f"=== CURVE ANALYSIS · {len(rows):,} bars · {stamps[0].date()} → {stamps[-1].date()} ===", flush=True)
print("", flush=True)

print("=== 1 · THE 2024 MISREAD, MONTH BY MONTH ===", flush=True)
print(f"  {'month':<8}{'EURUSD':>9}{'model':>9}{'long%':>8}{'exposure':>11}", flush=True)
print(f"  {'-' * 45}", flush=True)
for m in range(1, 13):
    sel = (years == 2024) & (months == m)
    if sel.sum() < 20: continue
    eq = equity[sel]; cl = closes[sel]; ex = exposure[sel]
    ret = (eq[-1] / eq[0] - 1.0) * 100.0
    move = (cl[-1] / cl[0] - 1.0) * 100.0
    active = int((ex != 0).sum())
    frac = 100.0 * float((ex > 0).sum()) / active if active else float("nan")
    print(f"  2024-{m:02d} {move:>+8.2f}%{ret:>+8.2f}%{frac:>7.1f}%{ex.mean():>11.2f}", flush=True)
print("", flush=True)

print("=== 2 · HOLD DURATION (does it actually hold a side?) ===", flush=True)
runs = []
current, length = side[0], 1
for value in side[1:]:
    if value == current: length += 1
    else:
        if current != 0: runs.append((current, length))
        current, length = value, 1
if current != 0: runs.append((current, length))
lengths = np.array([r[1] for r in runs]) / 24.0
longs = np.array([r[1] for r in runs if r[0] > 0]) / 24.0
shorts = np.array([r[1] for r in runs if r[0] < 0]) / 24.0
print(f"  directional runs        : {len(runs)}  ({len(longs)} long · {len(shorts)} short)", flush=True)
print(f"  median hold             : {np.median(lengths):.1f} days   mean {lengths.mean():.1f} days", flush=True)
print(f"  longest long / short    : {longs.max():.0f} d / {shorts.max():.0f} d", flush=True)
for cut in (1, 7, 30, 90):
    share = 100.0 * float((lengths >= cut).sum()) / len(lengths)
    weight = 100.0 * float(lengths[lengths >= cut].sum()) / lengths.sum()
    print(f"  runs >= {cut:>3}d            : {share:5.1f}% of runs · {weight:5.1f}% of time held", flush=True)
print("", flush=True)

print("=== 3 · LEVERAGE AND TURNOVER ===", flush=True)
notional = np.abs(exposure) * closes
gross = notional / np.where(equity > 0, equity, 1.0)
print(f"  mean gross leverage     : {gross.mean():.2f}x   median {np.median(gross):.2f}x   p95 {np.percentile(gross, 95):.2f}x   max {gross.max():.2f}x", flush=True)
print(f"  flat (zero exposure)    : {100.0 * float((exposure == 0).sum()) / len(exposure):.1f}% of bars", flush=True)
print(f"  long / short bars       : {100.0 * float((exposure > 0).sum()) / len(exposure):.1f}% / {100.0 * float((exposure < 0).sum()) / len(exposure):.1f}%", flush=True)
turnover = float(np.abs(deltas).sum() * closes.mean())
print(f"  rebalances              : {int((deltas > 0).sum()):,}  ({int((deltas > 0).sum()) / 11.0:.0f}/year)", flush=True)
print("", flush=True)

print("=== 4 · WHAT LOOKBACK DID THE POLICY LEARN? ===", flush=True)
print("  correlation of net exposure with the trailing return over N days", flush=True)
print(f"  {'lookback':<12}{'corr':>9}", flush=True)
print(f"  {'-' * 21}", flush=True)
best = None
for days in (1, 3, 5, 10, 20, 30, 45, 60, 90, 120, 180, 250):
    lag = days * 24
    if lag >= len(closes): continue
    trailing = np.full(len(closes), np.nan)
    trailing[lag:] = closes[lag:] / closes[:-lag] - 1.0
    mask = ~np.isnan(trailing) & (exposure != 0)
    if mask.sum() < 500: continue
    corr = pearson(exposure[mask], trailing[mask])
    if best is None or abs(corr) > abs(best[1]): best = (days, corr)
    print(f"  {days:>4} days   {corr:>+9.3f}", flush=True)
print(f"  ⇒ strongest alignment at {best[0]} days (corr {best[1]:+.3f})", flush=True)
print("", flush=True)

print("=== 5 · IS IT JUST A MOVING-AVERAGE RULE? ===", flush=True)
print("  agreement between the policy's side and a simple SMA-cross rule", flush=True)
for days in (20, 30, 60, 90, 120):
    window = days * 24
    if window >= len(closes): continue
    cumulative = np.concatenate(([0.0], np.cumsum(closes)))
    sma = (cumulative[window:] - cumulative[:-window]) / window
    aligned = closes[window - 1:]
    rule = np.sign(aligned - sma)
    policy = side[window - 1:]
    mask = (policy != 0) & (rule != 0)
    agree = 100.0 * float((policy[mask] == rule[mask]).sum()) / mask.sum()
    print(f"  price vs SMA{days:>4}d       : {agree:5.1f}% agreement", flush=True)
print("  (50% = independent · 100% = the policy IS that rule)", flush=True)
