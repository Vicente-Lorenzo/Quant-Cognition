import re, sys, json, math
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")

S = Path(r"C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-OneDrive-Documents-cAlgo\dfaf0be2-e579-4eb0-9df6-25a2c66ff13f\scratchpad")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
text = ANSI.sub("", (S / "_seedscan.log").read_text(encoding="utf-8", errors="replace"))

seeds = {}
for line in text.splitlines():
    hit = re.match(r"ROBUST seed(\d+) · === mean ([-+0-9.]+)% .* longfrac ([0-9.]+)% · maxDD ([0-9.]+)% · Sharpe ([-+0-9.]+) · Sortino ([-+0-9.]+)", line)
    if hit:
        i = int(hit.group(1))
        seeds.setdefault(i, {}).update(ret=float(hit.group(2)), longfrac=float(hit.group(3)),
                                       maxdd=float(hit.group(4)), sharpe=float(hit.group(5)))
    hit = re.match(r"ROBUST seed(\d+) · === REGIME SCORE ([0-9.]+)%", line)
    if hit: seeds.setdefault(int(hit.group(1)), {}).update(regime=float(hit.group(2)))
    hit = re.match(r"ROBUST seed(\d+) · === SPLIT regime: train-era \S+ ([0-9.]+)% · recent \S+ ([0-9.]+)%", line)
    if hit: seeds.setdefault(int(hit.group(1)), {}).update(train_regime=float(hit.group(2)), recent_regime=float(hit.group(3)))

test = json.loads((S / "_r_E15.json").read_text(encoding="utf-8"))[0]["test_returns"]
for i, value in enumerate(test):
    if i in seeds: seeds[i]["test"] = value

rows = [dict(seed=i, **v) for i, v in sorted(seeds.items()) if "ret" in v and "regime" in v]
if not rows:
    print("no complete rows yet"); sys.exit(0)

print(f"=== PER-SEED SCAN · {len(rows)} seeds · 15-episode arm · D1 · 3.5pt · swap-free ===")
print(f"  {'seed':<6}{'full-range':>12}{'regime':>9}{'long%':>8}{'maxDD':>8}{'Sharpe':>8}{'test fold':>11}")
print(f"  {'-' * 62}")
for r in sorted(rows, key=lambda x: -x["ret"]):
    print(f"  {r['seed']:<6}{r['ret']:>+11.2f}%{r['regime']:>8.1f}%{r['longfrac']:>7.1f}%{r['maxdd']:>7.1f}%{r['sharpe']:>8.3f}{r.get('test', float('nan')):>+10.2f}%")

def pearson(xs, ys):
    n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
    num = sum((a-mx)*(b-my) for a, b in zip(xs, ys))
    den = math.sqrt(sum((a-mx)**2 for a in xs)) * math.sqrt(sum((b-my)**2 for b in ys))
    return num/den if den else float("nan")

def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0]*len(v)
        for pos, i in enumerate(order): out[i] = pos
        return out
    return pearson(rank(xs), rank(ys))

print()
print("=== DO ANY AVAILABLE SIGNALS PREDICT THE FULL-RANGE RETURN? ===")
target = [r["ret"] for r in rows]
for label, key in (("regime score", "regime"), ("train-era regime", "train_regime"),
                   ("Sharpe", "sharpe"), ("maxDD", "maxdd"), ("long fraction", "longfrac"),
                   ("test-fold return", "test")):
    xs = [r.get(key) for r in rows]
    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in xs): continue
    print(f"  {label:<20} pearson {pearson(xs, target):+.3f} · spearman {spearman(xs, target):+.3f}")

print()
print("=== WOULD A SELECTION RULE HAVE FOUND A GOOD SEED? ===")
best = max(rows, key=lambda r: r["ret"])
print(f"  best available seed        : seed {best['seed']} · {best['ret']:+.2f}% · regime {best['regime']:.1f}%")
for label, key, reverse in (("highest regime score", "regime", True),
                            ("highest train-era regime", "train_regime", True),
                            ("highest Sharpe", "sharpe", True),
                            ("lowest maxDD", "maxdd", False),
                            ("most two-sided (long% near 50)", None, None)):
    if key is None:
        pick = min(rows, key=lambda r: abs(r["longfrac"] - 50.0))
    else:
        usable = [r for r in rows if r.get(key) is not None]
        if not usable: continue
        pick = sorted(usable, key=lambda r: r[key], reverse=reverse)[0]
    rank = sorted(rows, key=lambda r: -r["ret"]).index(pick) + 1
    print(f"  {label:<32} -> seed {pick['seed']:<3} {pick['ret']:>+7.2f}%  (rank {rank}/{len(rows)} by return)")
print(f"  {'random seed (expected)':<32} -> {sum(target)/len(target):>+13.2f}%  (mean)")
