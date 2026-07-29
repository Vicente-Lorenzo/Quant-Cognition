import os, sys, math, glob
from pathlib import Path
from datetime import datetime

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np

S = Path(r"C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-OneDrive-Documents-cAlgo\dfaf0be2-e579-4eb0-9df6-25a2c66ff13f\scratchpad")
BALANCE = 10000.0
COST = 0.000035

files = sorted(glob.glob(str(S / "curves" / "seed*.csv")), key=lambda p: int(Path(p).stem.replace("seed", "")))
if not files:
    print("no curves yet"); sys.exit(0)

curves, stamps, closes = {}, None, None
for path in files:
    seed = int(Path(path).stem.replace("seed", ""))
    rows = [l.split(",") for l in Path(path).read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    if not rows: continue
    ts = [datetime.fromisoformat(r[0]) for r in rows]
    if stamps is None:
        stamps = ts; closes = np.array([float(r[3]) for r in rows])
    if len(ts) != len(stamps): print(f"  seed {seed}: length mismatch, skipped"); continue
    curves[seed] = np.array([float(r[2]) for r in rows])

print(f"=== ENSEMBLE OVER {len(curves)} SEEDS · {len(stamps):,} bars ===")
years = np.array([s.year for s in stamps])
n = len(stamps)

def simulate(expo):
    account = np.empty(n); account[0] = BALANCE; held = 0.0
    for i in range(1, n):
        account[i] = account[i - 1] + held * (closes[i] - closes[i - 1]) / closes[i] - abs(expo[i] - held) * COST / closes[i]
        held = expo[i]
    return account

def regime_of(expo):
    weighted = total = 0.0
    for y in sorted(set(int(v) for v in years)):
        sel = years == y
        if sel.sum() < 100: continue
        cl = closes[sel]; ex = expo[sel]
        move = cl[-1] / cl[0] - 1.0
        active = int((ex != 0).sum())
        if active < 100: continue
        frac = float((ex > 0).sum()) / active
        weighted += (frac if move > 0 else 1.0 - frac) * abs(move); total += abs(move)
    return 100.0 * weighted / total if total else 0.0

def report(label, expo):
    account = simulate(expo)
    total = (account[-1] / BALANCE - 1.0) * 100.0
    step = np.diff(account) / np.where(account[:-1] > 0, account[:-1], 1.0)
    sharpe = float(step.mean() / step.std() * math.sqrt(24 * 252)) if step.std() > 0 else 0.0
    peak = np.maximum.accumulate(account)
    dd = float(((peak - account) / np.where(peak > 0, peak, 1.0)).max() * 100.0)
    active = int((expo != 0).sum())
    frac = 100.0 * float((expo > 0).sum()) / active if active else float("nan")
    print(f"  {label:<34}{total:>+10.2f}%{sharpe:>9.3f}{dd:>8.1f}%{frac:>8.1f}%{regime_of(expo):>9.1f}%{100.0*active/n:>9.1f}%")
    return total

matrix = np.vstack([curves[k] for k in sorted(curves)])
print(f"  {'arm':<34}{'return':>11}{'Sharpe':>9}{'maxDD':>8}{'long%':>8}{'regime':>9}{'active':>9}")
print(f"  {'-' * 88}")

singles = [report(f"seed {k} (individual)", curves[k]) for k in sorted(curves)]
print(f"  {'-' * 88}")
mean_single = sum(singles) / len(singles)

mean_expo = matrix.mean(axis=0)
report("ENSEMBLE mean exposure", mean_expo)
report("ENSEMBLE median exposure", np.median(matrix, axis=0))
signs = np.sign(matrix)
vote = np.sign(signs.sum(axis=0))
magnitude = np.abs(matrix).mean(axis=0)
report("ENSEMBLE majority vote x mean size", vote * magnitude)
strong = np.where(np.abs(signs.sum(axis=0)) >= max(2, len(curves) // 3), vote, 0.0)
report("ENSEMBLE vote, >=1/3 agreement", strong * magnitude)

print(f"  {'-' * 88}")
print(f"  mean of individual seeds        : {mean_single:+.2f}%")
print(f"  best individual seed            : {max(singles):+.2f}%")
print(f"  worst individual seed           : {min(singles):+.2f}%")
print(f"  positive seeds                  : {sum(1 for v in singles if v > 0)}/{len(singles)}")
agree = np.abs(signs.sum(axis=0)) / max(1, len(curves))
print(f"  mean cross-seed sign agreement  : {100.0 * agree.mean():.1f}%  (0 = total disagreement · 100 = unanimous)")
print(f"  bars with unanimous sign        : {100.0 * float((agree == 1.0).sum()) / n:.1f}%")
