import os, sys, math
from pathlib import Path
from datetime import datetime

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import numpy as np

CSV = Path(sys.argv[1])
BALANCE = 10000.0
rows = [line.split(",") for line in CSV.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
stamps = [datetime.fromisoformat(r[0]) for r in rows]
equity = np.array([float(r[1]) for r in rows])
exposure = np.array([float(r[2]) for r in rows])
closes = np.array([float(r[3]) for r in rows])
years = np.array([s.year for s in stamps])
n = len(rows)

def simulate(expo, cost):
    account = np.empty(n); account[0] = BALANCE
    held = 0.0
    for i in range(1, n):
        pnl = held * (closes[i] - closes[i - 1]) / closes[i]
        target = expo[i]
        fee = abs(target - held) * cost / closes[i]
        account[i] = account[i - 1] + pnl - fee
        held = target
    return account

print("=== 0 · CALIBRATING THE SIMULATOR AGAINST GROUND TRUTH ===", flush=True)
truth = (equity[-1] / BALANCE - 1.0) * 100.0
print(f"  actual backtest total      : {truth:+.2f}%", flush=True)
best = None
for cost in (0.0, 0.000035, 0.00007, 0.0001, 0.00014, 0.0002, 0.00028, 0.0004):
    got = (simulate(exposure, cost)[-1] / BALANCE - 1.0) * 100.0
    if best is None or abs(got - truth) < abs(best[1] - truth): best = (cost, got)
    print(f"  cost {cost:.5f} per unit    : {got:+.2f}%", flush=True)
COST = best[0]
print(f"  ⇒ calibrated round-trip cost {COST:.5f} reproduces {best[1]:+.2f}% vs actual {truth:+.2f}%", flush=True)
print(f"  ⇒ simulator error {abs(best[1] - truth):.2f}pp — counterfactuals below use this accounting", flush=True)
print("", flush=True)

def summarize(label, account, expo):
    total = (account[-1] / BALANCE - 1.0) * 100.0
    step = np.diff(account) / np.where(account[:-1] > 0, account[:-1], 1.0)
    sharpe = float(step.mean() / step.std() * math.sqrt(24 * 252)) if step.std() > 0 else 0.0
    peak = np.maximum.accumulate(account)
    dd = float(((peak - account) / np.where(peak > 0, peak, 1.0)).max() * 100.0)
    active = int((expo != 0).sum())
    frac = 100.0 * float((expo > 0).sum()) / active if active else float("nan")
    weighted = held = 0.0
    for y in sorted(set(int(v) for v in years)):
        sel = years == y
        if sel.sum() < 100: continue
        cl = closes[sel]; ex = expo[sel]
        move = cl[-1] / cl[0] - 1.0
        act = int((ex != 0).sum())
        if act < 100: continue
        share = float((ex > 0).sum()) / act
        weighted += (share if move > 0 else 1.0 - share) * abs(move); held += abs(move)
    regime = 100.0 * weighted / held if held else 0.0
    print(f"  {label:<34}{total:>+9.2f}%{sharpe:>9.3f}{dd:>8.1f}%{frac:>8.1f}%{regime:>9.1f}%", flush=True)
    return total

window = 120 * 24
cumulative = np.concatenate(([0.0], np.cumsum(closes)))
sma = np.full(n, np.nan)
sma[window - 1:] = (cumulative[window:] - cumulative[:-window]) / window
rule = np.where(np.isnan(sma), 0.0, np.sign(closes - sma))

magnitude = np.abs(exposure)
model_side = np.sign(exposure)
rule_expo = magnitude * rule
flip_expo = magnitude * np.where(rule != 0, rule, model_side)

print("=== 1 · SIGN-SWAP ABLATION — is the model more than a 120-day trend rule? ===", flush=True)
print("  identical sizing in every arm; only the DIRECTION differs", flush=True)
print(f"  {'arm':<34}{'total':>10}{'Sharpe':>9}{'maxDD':>9}{'long%':>8}{'regime':>9}", flush=True)
print(f"  {'-' * 79}", flush=True)
a = summarize("model direction (champion)", simulate(exposure, COST), exposure)
b = summarize("SMA120 rule direction", simulate(rule_expo, COST), rule_expo)
c = summarize("model magnitude, rule sign", simulate(flip_expo, COST), flip_expo)
d = summarize("always long, model magnitude", simulate(magnitude, COST), magnitude)
e = summarize("always short, model magnitude", simulate(-magnitude, COST), -magnitude)
print("", flush=True)
print(f"  ⇒ model minus SMA120 rule : {a - b:+.2f}pp", flush=True)
print(f"  ⇒ model minus always-long : {a - d:+.2f}pp", flush=True)
print("", flush=True)

print("=== 2 · WHERE THE MODEL DISAGREES WITH THE RULE ===", flush=True)
print("  P&L at bar i comes from the position held at bar i-1 — buckets aligned accordingly", flush=True)
model_step = exposure[:-1] * (closes[1:] - closes[:-1]) / closes[1:]
rule_step = rule_expo[:-1] * (closes[1:] - closes[:-1]) / closes[1:]
mask = (model_side[:-1] != 0) & (rule[:-1] != 0)
agree = model_side[:-1] == rule[:-1]
total_gross = float(model_step.sum())
print(f"  {'bucket':<26}{'bars':>8}{'share':>8}{'model P&L':>14}{'rule P&L':>14}", flush=True)
print(f"  {'-' * 70}", flush=True)
for label, sel in (("agrees with SMA120", mask & agree), ("disagrees with SMA120", mask & ~agree)):
    share = 100.0 * float(sel.sum()) / float(mask.sum())
    print(f"  {label:<26}{int(sel.sum()):>8,}{share:>7.1f}%{float(model_step[sel].sum()):>+13,.0f}{float(rule_step[sel].sum()):>+14,.0f}", flush=True)
print(f"  {'-' * 70}", flush=True)
disagree_pnl = float(model_step[mask & ~agree].sum())
print(f"  model gross (all bars)    : {total_gross:>+13,.0f} EUR", flush=True)
print(f"  disagreement contributes  : {100.0 * disagree_pnl / total_gross:>13.1f}% of gross profit from {100.0 * float((mask & ~agree).sum()) / float(mask.sum()):.1f}% of bars", flush=True)
print(f"  swing versus the rule     : {2.0 * disagree_pnl:>+13,.0f} EUR — the model's entire edge over SMA120", flush=True)
print("", flush=True)
print("=== 3 · TURNOVER (the rule is not even cheaper) ===", flush=True)
for label, expo in (("model", exposure), ("SMA120 rule", rule_expo)):
    print(f"  {label:<14} turnover {float(np.abs(np.diff(expo)).sum()):>16,.0f} units", flush=True)
