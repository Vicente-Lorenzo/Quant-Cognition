import os, sys, json, hashlib, subprocess, argparse
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
PAIR = "Library/Parameter/Spotware(cTrader)/Forex(Major)/EURUSD/Hour"
CHAMPION = f"{PAIR}/DDPG THESIS 2026-07-27 [S1000s0 regime67 sharpe0.46]"
REPLICATION = f"{PAIR}/DDPG REPLICATION 2026-07-28 [E15s3 regime62 short-tilted]"
BASELINE = HERE / "baseline.json"

EXPECTED = {"return": 34.02, "regime": 67.0, "long": 66.6, "maxdd": 23.5, "sharpe": 0.275}
TOLERANCE = {"return": 0.05, "regime": 0.1, "long": 0.1, "maxdd": 0.1, "sharpe": 0.005}

GOLDENS = [f"Reports/2026-07-05 16-47-{n} BacktestingAPI" for n in ("18", "19", "27", "28", "36", "39")]
KIT = ["REPRODUCE.md", "sweep_campaign.py", "robust_eval.py", "monitor_campaign.py",
       "Analysis/yearly_decomp.py", "Analysis/curve_analysis.py", "Analysis/rule_ablation.py",
       "Analysis/selection_rules.py", "Analysis/ensemble.py", "Analysis/permutation_test.py",
       "Analysis/regime_ceiling.py", "Analysis/plot_model.py"]
SYMBOLS = {
    "Library/Strategy/Hybrid/DDPG.py": ["DecisionSchedule", "RebalanceThreshold", "AccountFeatures",
                                        "NeutralizeScale", "RewardScale", "SignalSmoothing", "_bucket_"],
    "Library/System/Learning.py": ["mirror_ratio", "_exposure_directions_", "LongBars", "ShortBars"],
    "Library/Strategy/Strategy.py": ["_long_bars_", "_short_bars_"],
    "Library/System/System.py": ["_long_bars_"],
}

failures, warnings = [], []

def ok(label, good, detail=""):
    print(f"  [{'OK' if good else 'FAIL'}]  {label}{('  ' + detail) if detail else ''}")
    if not good: failures.append(label)

def digest(path):
    h = hashlib.sha256()
    for chunk in iter(lambda: path.open("rb").read() if False else None, None): break
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""): h.update(block)
    return h.hexdigest()

def weights_fingerprint(folder):
    out = {}
    base = ROOT / folder / "DDPG"
    if not base.is_dir(): return out
    for f in sorted(base.iterdir()):
        if f.is_file(): out[f.name] = digest(f)
    return out

def section(title):
    print(f"\n=== {title} ===")

parser = argparse.ArgumentParser()
parser.add_argument("--write-baseline", action="store_true")
parser.add_argument("--skip-replay", action="store_true")
parser.add_argument("--skip-tests", action="store_true")
args = parser.parse_args()

print("CAMPAIGN LOCK VERIFICATION — DDPG EURUSD H1")
print(f"repo: {ROOT}")

section("1 · reproduction kit")
for rel in KIT: ok(rel, (HERE / rel).exists())

section("2 · artifacts")
for folder, label in ((CHAMPION, "deliverable"), (REPLICATION, "replication")):
    base = ROOT / folder
    ok(f"{label} weights", (base / "DDPG" / "actor").exists(), folder.split("/")[-1][:52])
ok("deliverable CAMPAIGN.md", (ROOT / CHAMPION / "CAMPAIGN.md").exists(),
   f"{len((ROOT / CHAMPION / 'CAMPAIGN.md').read_text(encoding='utf-8').splitlines())} lines"
   if (ROOT / CHAMPION / "CAMPAIGN.md").exists() else "")
for name in ("README.md", "FRICTIONS.md", "DDPGStrategyAPI Manifest.json"):
    ok(f"deliverable {name}", (ROOT / CHAMPION / name).exists())
for rel in ("Learning.yml", "Backtesting.yml", "Realtime.yml"):
    ok(f"parameter {rel}", (ROOT / PAIR / rel).exists())

section("3 · goldens")
for g in GOLDENS:
    p = ROOT / g
    good = p.is_dir() and all((p / f).exists() for f in ("trades.csv", "positions.csv", "orders.csv", "deals.csv"))
    ok(g.split("/")[-1], good)

section("4 · framework symbols carrying the method")
for rel, symbols in SYMBOLS.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    missing = [s for s in symbols if s not in text]
    ok(rel, not missing, "" if not missing else f"MISSING {missing}")

section("5 · weight fingerprints")
current = {"champion": weights_fingerprint(CHAMPION), "replication": weights_fingerprint(REPLICATION)}
if args.write_baseline or not BASELINE.exists():
    BASELINE.write_text(json.dumps({"weights": current, "expected": EXPECTED}, indent=2), encoding="utf-8")
    print(f"  [WROTE] baseline.json ({sum(len(v) for v in current.values())} files fingerprinted)")
else:
    saved = json.loads(BASELINE.read_text(encoding="utf-8"))["weights"]
    for label in ("champion", "replication"):
        same = saved.get(label) == current.get(label)
        ok(f"{label} weights unchanged", same,
           "" if same else "SHA256 DRIFT — weights differ from the locked baseline")

section("6 · champion replay (the decisive check)")
if args.skip_replay:
    print("  [SKIP] --skip-replay")
else:
    env = dict(os.environ, ROBUST_FAST="1", ROBUST_SCHEDULE="D1", ROBUST_REBALANCE="0.20",
               PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, str(HERE / "robust_eval.py"), str(ROOT / CHAMPION),
                           "verify", "64x32", "0.0", "0.0", "0", "3.5", "2", "1", "1.0"],
                          capture_output=True, text=True, cwd=ROOT, env=env, encoding="utf-8", errors="replace")
    line = next((l for l in (proc.stdout or "").splitlines() if "=== mean" in l), "")
    regime = next((l for l in (proc.stdout or "").splitlines() if "REGIME SCORE" in l), "")
    import re
    got = {}
    m = re.search(r"mean ([-+0-9.]+)%", line);            got["return"] = float(m.group(1)) if m else None
    m = re.search(r"longfrac ([0-9.]+)%", line);          got["long"] = float(m.group(1)) if m else None
    m = re.search(r"maxDD ([0-9.]+)%", line);             got["maxdd"] = float(m.group(1)) if m else None
    m = re.search(r"Sharpe ([-+0-9.]+)", line);           got["sharpe"] = float(m.group(1)) if m else None
    m = re.search(r"REGIME SCORE ([0-9.]+)%", regime);    got["regime"] = float(m.group(1)) if m else None
    if got.get("return") is None:
        ok("champion replay produced a result", False, (proc.stderr or "")[-200:])
    else:
        for key, want in EXPECTED.items():
            have = got.get(key)
            good = have is not None and abs(have - want) <= TOLERANCE[key]
            ok(f"{key:<7} = {want}", good, f"got {have}")

section("7 · test suite")
if args.skip_tests:
    print("  [SKIP] --skip-tests")
else:
    proc = subprocess.run([sys.executable, "-m", "pytest", "Tests/", "--ignore=Tests/Spotware",
                           "--ignore=Tests/Bloomberg", "-q"], capture_output=True, text=True,
                          cwd=ROOT, encoding="utf-8", errors="replace")
    tail = [l for l in (proc.stdout or "").splitlines() if "passed" in l or "failed" in l]
    summary = tail[-1].strip() if tail else "no summary"
    ok("pytest 651 passed / 0 failed", "651 passed" in summary and "failed" not in summary, summary)

print("\n" + "=" * 62)
if failures:
    print(f"RESULT: {len(failures)} CHECK(S) FAILED")
    for f in failures: print(f"  - {f}")
    sys.exit(1)
print("RESULT: LOCK INTACT — the campaign is fully reproducible from this state")
sys.exit(0)
