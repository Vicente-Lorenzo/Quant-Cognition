# Plan

The single planning file for the framework. Written 2026-09-10, replacing `TODOS.md`,
`Research/THESIS-NOTES.md` and the project memory set, all of which were folded in here or into
`RULES.md` and then deleted. Reordered 2026-09-17, rewritten 2026-09-18 and renumbered 2026-09-26 — Appendices C and D map every
earlier item number to its current one.

**What belongs here:** work not yet done, in the order it will be done, with the evidence that
justifies it and the condition that closes it. **What does not:** conventions, current state and traps
(those are `RULES.md`), architecture (`ARCHITECTURE.md`), delivered results
(`CAMPAIGNS.md`) and anything git history
already records. **A finished phase is reduced to one row of the Done log** — what it was, when it
closed, where its facts now live — and every detail of it is deleted from this file; a finished item
inside a live phase keeps one line in that phase's **Done** list until the phase itself closes.

**The thesis is delivered, and its numbers bind nothing below — decided 2026-09-24.** Once every phase
is done, a fresh campaign runs on the new tape and the corrected engine (Phase 7); nothing is kept only to
replay the old one. Nothing below is a quick fix applied to make a result look better; every phase is a
structural change that leaves the framework permanently correct.

---

## Done

A finished phase keeps one line here; its facts live where the last column says, and its details are
gone from this file.

| Phase | What it delivered | Done | Facts in |
|---|---|---|---|
| **0** | Safety net — the online and offline goldens, the DDPG self-consistency golden, the `Contract.yml` pin | 2026-09-17 | `RULES.md` ("Goldens", "Contract terms"), `Tests/Golden/RESIDUALS.md` |
| **1** | Credential manager — `Library/Credential`, owner and threshold access on credentials, workflows and tasks, the credential page and CLI, the stored session key | 2026-09-23 | `RULES.md` ("`Library/Credential`", "Two thresholds"), `ARCHITECTURE.md` |
| **3** | The market database — `Market.Tick` in UTC, the only market table: **1 663 014 876 ticks in 7.0 GB** (the database went from 365 GB to 7.2 GB); the two-sided `BarAPI` → `PointAPI` → `TickAPI`; every timeframe built on demand on the 17:00 New York clock and **equal to the platform's trendbars** (labels on every bar, OHLC exact M1 to D1, 2020-2025); conversions rebuilt at run time for any account currency; one binary blob per chunk read in parallel, no cache anywhere (run 5 cold 568 s → 17 s); Postgres tuned; the engine switched, the old tables and the Parquet cache dropped; the goldens' movement explained — runs 1 and 3 now within 6 and 11 EUR of cTrader, from 104 and 882 — and 6.0's gate made exact | 2026-09-25 | `RULES.md` ("The tick tape", "Bars", "Market data", "Currency conversion"), `ARCHITECTURE.md`, `Tests/Golden/RESIDUALS.md` ("The switch") |
| **2** | The Spotware module — a verified TLS connection; one sign-in and refresh through the vault; every public method verified live, five defects fixed; **the Open API proven to serve exactly the cBot's tape, and the stored tape found in London time**; what a tick is, decided; the allowance measured without asking Spotware (per connection, spaced sends, eight connections ≈ two hours for the whole history); a session that survives drops, silence and token loss (a 30-minute soak: 88 of 88 fetch cycles, both forced socket drops restored in 2-2.5 s with the live stream resumed); the demo-only live suite and 96 % offline coverage | 2026-09-24 | `RULES.md` ("`Library/Spotware`", "Market data", "Exclusions"), Appendix B |
| **4** | Database and engine optimization, and an environment always on its latest libraries — workers share tapes, warmup history and the bar index through shared memory with one pool per fold (eleven years of D1 at 16 workers 85.2 → 51.0 s, every score identical); generic `DatabaseAPI.binary`; `Research/` distilled into `CAMPAIGNS.md`; every dependency declared and nothing pinned but Python; the vendor package replaced by the module's own client, verified live (tape equality, throughput, backoff, resilience, 61 methods, a 30-minute soak; three defects fixed); upgrades built and tested as `Quant.next` and applied by a base-Python launcher at logon, never in place; workflows split into `Environment` · `Web Application` · `Data Intelligence`, with workflow dependencies, `Waiting` cycles and services that wait only for their own ancestors | 2026-09-27 | `RULES.md` (`Library/System`, "The tick tape", "The warmup window", `Quant.yml`, "Never upgrade the `Quant` environment in place", `Library/Spotware`, `Library/Scheduler`, `Script/`), `CAMPAIGNS.md`, README ("Rebuilding This Machine From Scratch") |
| **5** | The data workflow — one writer per schema under the `Data` workflow: the Universe from the Open API (830 symbols, dated terms, the 28 pairs of the eight majors tracked); the Market service, a worker per security, the 28 pairs refilled from 2014 (130 284 pair-days) and kept current, a tick reaching its row in about 2 s at the median (the tail is 9.12); the Portfolio mirror of every demo account with every derived field through `PortfolioAPI` and equal to the tick truth; the economic calendar in Monday weeks read across both Forex Factory pages; the database pages; a cBot that stores nothing; the tape repaired (`Script/Setup/Boundary.py`: 95 days rewritten, 38 last-millisecond ticks restored) and diffed against the cBot tape over every year — every old tick present, the only value differences 3 205 same-millisecond pairs in 2014-2017 — after which the 5.97 GB archive was deleted; the Spotware module verified live on six demo accounts in five currencies (72 tests, netting and hedging), its netting defects fixed | 2026-09-28 | `RULES.md` (`Script/Data`, "Market data", "The tick tape", `Library/Spotware`, `Library/Scheduler`), `ARCHITECTURE.md`, the diff reports in `inspect_persistent("Archive")`; its open items moved to 9.12, 11.1 and Phase 12 |
| **6** | Backtesting engine accuracy — the engine reverse-engineers cTrader's and extends it: intrabar segmentation (every excursion equal to the tick truth), costs inside the excursions, the open position settled at the stop, swap charged at each roll from every contract term (`SwapTime` in UTC, each night rounded), `SpreadPnL`, risk sizing through the conversions for any account currency, bridging through a third currency, hedging and netting, closes by oldest fills with an exact average entry, commission rounded like the broker with its minimum and the conversion fee; `PriceMode.Mid` and the nine-tick wire bar; the `Test` strategy; the goldens re-based in one cTrader session — five backtests (every position opens identically, 93-99.6 % close identically) and two live demo runs equal to the broker to the cent (15 of 15 deals netted, 12 of 12 hedged); offline 6.7-35× faster than cTrader end to end | 2026-09-29 | `RULES.md` ("The goldens", "Swap", "Commission", "A close takes the position's oldest fills", "A stop fires", "Risk", "An intrabar event", "The position open at the stop", "Currency conversion", `Library/Portfolio`, `Library/System`, `Library/Strategy`), `Tests/Golden/RESIDUALS.md` ("The `Test` goldens", "Phase 6"), `ARCHITECTURE.md`; what it measured and did not take is in 9.8 and 9.13 |

---

## Order of work

| Phase | Scope | Gate | Can start |
|---|---|---|---|
| **7** | Optimization and Learning — thesis iteration two | Phase 6 (done) | **now** |
| **8** | Web app, opened by the Research schema (8.0) | none | any time |
| **9** | Remaining | none | any time |
| **10** | Indicator connector — Python indicators on cTrader charts | Phase 6 (done) | now |
| **11** | Live trading panel at `/trading` | Phases 5, 6 and 8 complete | after 8 |
| **12** | Interactive Brokers provider | Phase 11 complete | after 11 |
| **13** | Option strategy pricer and backtester | Phase 12 complete (chain data) | last |
| **14** | Free-threaded Python — investigate | none | any time |

**Five rules bind the order.**

1. **Nothing touches the engine without the goldens.** `Tests/Golden/Offline` and `Tests/Golden/Online`
   (runs 1-5, the `Test` strategy's, re-based in the cTrader session of 2026-09-29) and
   `Tests/Golden/Consistency/DDPG`. `pytest Tests/Golden --golden` replays the six offline-engine goldens byte
   for byte, each with its own `Parameters.yml` and `Contract.yml` pinned.
2. **A cTrader re-baseline is a versioned event, never part of a refactor.** The last one, the `Test` session
   of 2026-09-29, re-based the goldens for the UTC tape (Phase 3) and every Phase 6 change; each move is
   explained in `Tests/Golden/RESIDUALS.md` ("The switch", "Phase 6", "The `Test` goldens"). An engine change
   that moves output deliberately needs its own session and its own section there. **Declared exception,
   2026-09-15:** the offline half was re-baselined once outside a session, when `shrink_dtype()` was removed from `DataframeAPI.frame` — every
   database read and preload tape had been downcasting `Float64` prices to `Float32`. That corrected an
   input, not engine logic; the pre-fix exports stay in commit `578c9a5`, and the before/after is in
   `Tests/Golden/RESIDUALS.md`, "Re-baselined 2026-09-15".
3. **Phase 7 retrains once, at the end.** Every engine change invalidates trained weights. Retraining
   between phases burns the longest-running job in the framework for a result the next phase throws
   away.
4. **No secret lives anywhere but the credential store, and it travels by reference.** Not in code,
   git, a log line, a command line, a run artifact, an environment variable or a file in the repository —
   the store is a plain database table, so the discipline is what protects it. Every phase that talks to
   an external API — Spotware (4), the live panel (10), Interactive Brokers (11) — starts from the
   store instead of retrofitting it.
5. **One tape, one writer at a time.** The London-local tape was converted once into `Market.Tick`, in
   UTC — proven identical to what the Open API serves — and the old tables are gone (2026-09-25). From
   now on the market service is its only writer: the market data is dropped and refilled from `HORIZON`
   through the Market service (Phase 5). Two sources writing one table would move every engine number
   without raising a single error.

**Why this order, 2026-09-24.** Measured that day: the Open API serves exactly the tape the Download cBot stored,
and found that tape in London time. That settles the direction: **one writer for market data** — a
service on `Library/Spotware` — **a calendar service** beside it, and **a cBot that only executes actions
and receives updates**, never storing. The end state is a fast database, and two services keeping the
tick tape and the economic calendar current around the clock, in UTC. The database comes first and is
proven on the whole tape — 1.66 billion ticks, not a sample — so every speed and size claim is measured
where it matters (3); the engine and environment are made fast and current on it (4); the services come next (5);
the engine work that reads the new tape follows (6).
The Research schema left Phase 3 for 8.0, and parity with the cBot left Phase 2 for 11.0, so neither
gates the services.

---

## Phase 7 — Optimization and Learning

Goal: out-of-sample strength that survives scrutiny, and a walk-forward protocol that is what it claims to
be. Thesis iteration two.

**Done.** Record the observation order with the weights (2026-09-17) — every `DDPGStrategyAPI.save()`
writes `Observation.json` and `load()` refuses a different layout; the champion and the DDPG golden are
backfilled (`RULES.md`, "Parameter key order is an input"). Optimization and Learning verified end to end and
eight defects fixed (2026-09-29, `RULES.md`, "Optimization and Learning are verified end to end").

### 7.0 The thesis campaign — decided 2026-09-29

The final campaign, `Script/Campaign/` (`NAME` "DDPG 2026-09"). One model per major, trained and selected so that
2025 stays out of sample; results are read test ≫ validation ≫ full range.

| Item | Decided |
|---|---|
| Split | 2015-01-01 → 2026-01-01; rolling 36-month training, 12-month validation (75/25) → seven folds validating 2018-2024; test 2025; `--continuous`, election `Last` |
| Account | USD for all seven, 10 000, 1 % risk, leverage 30, netting |
| Recipe | the DDPG `Defaults` (`RULES.md`); 20 episodes a fold; mirror 0.50; gates activity 10 · balance 300 · ratio 0.30; fitness annualised Calmar; `--threads 1` |
| Costs | real tick spread; commission 3.5 USD a lot a side (`Lots`); swap-free, with a swap sensitivity table |
| Training costs | a canary A/B on GBPUSD and EURUSD, paired seeds: A trains on the spread with hysteresis 0 (the recipe), B on the full costs with hysteresis 0.20; the arm is chosen on validation |
| Seed selection | the seven validation years only, under the full costs: gates (profitable, beats the pair, weaker side ≥ 10 % of active time, mean hold ≥ 24 bars, regime above its own null), then a money · safety · behaviour composite preferring low beta; 2025 is opened once per pair |
| Reproducibility | the commit and packages in every `Run.json`; the nightly environment upgrade paused; one winning seed per pair retrained byte for byte at the end |
| Hardware | one job at a time, about 20 workers (1.2 GB each plus 5 GB a run), a 6 GB free-memory floor |
| Deliverables | the draft's figures and tables regenerated as PDF for `Papers/2026-MEIC-DDPG-FX-Majors`, plus the walk-forward table, the validation stitch, 2025 against the pair and US500, the signal chart and the deal map; the equal-weight basket computed afterwards by script (9.14 is the engine feature) |

### Rules that bind every item in this phase

Each of these cost a wasted campaign or a wrong conclusion. Apply before believing any result.

- **Never rank arms on a single promoted model.** Training is bit-exactly reproducible only at
  `threads=1` and `worker_threads=1`; multi-threaded it is not — the same config and seed gave -3.1 and
  -26.3. Thread reduction order is the confirmed cause. A manifest's `FullRange`, `BuyTrades` and
  `SellTrades` describe **one checkpoint**, not the arm. Compare per-seed distributions.
- **Arms sharing a seed set are paired.** Never compare them with independent-sample tests. An invalid
  Welch comparison on exactly this data produced a "significant variance collapse" finding that had to be
  retracted.
- **Power: seed sigma is 20 to 25 points.** Detecting a 10-point mean difference needs about 100 seeds an
  arm. Two to four seeds resolve only seed variance ratios, structural outcomes such as trade counts and
  direction collapse, and catastrophes such as divergence or NaN. **Pre-register which of those decides
  the arm before launching it.** A previous campaign's +4.80% headline died at n=10, t=0.79.
- **The frictionless cost decomposition is the decisive diagnostic.** Replay the same trained model with
  zero spread, commission and swap against normal costs. It separates "no edge" from "edge destroyed by
  costs" in about ten minutes. Run it **before** building any turnover-reduction, deadband or
  slower-timeframe fix. The 2026-07-21 result: gross Sharpe about 0.05 across three models with all costs
  removed, so no edge existed and costs were real but not binding.
- **Beta before alpha on any positive result.** A one-sided policy earns leverage times instrument drift,
  which looks like alpha. EURUSD H1 2015 to 2026 drifted -2.92%; the best-returning model, +31.54% gross,
  was a permanent short at about 10x, and 10 times 2.92% is about +29% — fully explained, with a Sharpe
  of 0.11. Rank by Sharpe and buy/sell
  balance, never by raw return.
- **`balance=N` does not enforce two-sidedness.** The gate is `min(buys, sells) >= N`, so a 41-buy,
  1891-sell model at 2.1% buys passes `balance=3` trivially. Judge by ratio.
- **Silent-zero traps.** Any `x or fallback` on a config value turns a legitimate 0 into a fallback —
  `SizingATRScale` falls back to `StopLossScale`, so a no-risk arm that zeroes it yields zero volume
  silently under `SizingMode: Risk`. Always verify an arm actually traded before interpreting its return.
- **Config travels as a Parameter, never a class attribute.** Spawn workers rebuild the strategy from the
  payload, so a class attribute set in the parent process silently does not propagate. Read new knobs via
  `getattr(self.SignalManagement, "X", None)` with a class-attribute fallback.
- **`DifferentialSortino` and `DifferentialSharpe` are exactly scale-invariant** — numerator and
  denominator both scale with k cubed — so leverage cannot act through the reward, only through the
  observation. Sizing tuning is legitimately replay-only, but replaying at a different size is **not** a
  pure scaling: different account features give different actions. Measure, never extrapolate.
- **Reward clipping is occupancy-driven, and diagnosis is not cure.** The clip rate tracks market
  occupancy; relieving it did not improve learning.
- **Record the netting knobs yourself.** The manifest records none of `SignalMode`, `TurnoverCost`,
  `PositionMode` or the sizing settings, so arms become indistinguishable unless the sweep results carry
  them.

### 7.1 Purging and embargo at fold boundaries

`--purge` and `--embargo` exist (days trimmed from each training window's end, days skipped after each
validation window), and in this engine a fold cannot leak through a position: every training and validation
window is its own backtest, started flat and settled at its stop, so no position crosses a boundary (checked
2026-09-29). What is left is to state that in the thesis and to report the purge used.

### 7.2 Probability of backtest overfitting and a deflated Sharpe

**The overfitting budget compounds; it does not reset per stage.** Staging turns a product into a sum —
6, 2, 2, 1 is 24 combinations flat but 11 staged — and coarse-to-fine turns a sweep into a funnel, so both
genuinely cut trials. But stage three is conditioned on winners already fitted to the same data, so the
effective trial count is the **accumulated total across every stage, round and fold**. A run already
records that number, so the deflated metric can be computed against the real one.

### 7.3 True walk-forward with `--continuous`, reported honestly

Continuity makes folds path-dependent — every fold starts near the previous winner — so `Frequency`
election becomes near-tautological. With `--continuous`, `Last` or `Mean` is the honest choice, and the
run must record which it used. `SplitAPI.walk_forward_folds` takes the single-split branch when
`training <= 0` rather than entering the rolling loop. A fold's model is scored on its **validation**
window, never its training window, and the held-out `--testing` pass is the only unbiased number.

### 7.4 One untouched holdout, used exactly once

Structural discipline rather than code. Decide the window now, write it down here, and do not look at it
until the campaign is otherwise finished.

### 7.5 A real risk-free rate curve

`--risk-free` is a single constant applied across every ratio and Jensen's alpha — and since 2026-09-17 it
reaches Learning and its workers too. A constant is wrong over 2014 to 2026 — it flatters every ratio in
the ZIRP years and penalises them after 2022. Backfill the **ECB deposit facility rate** from 2014: the
right reference for a EUR account, published daily, free. Store it as a dated series beside the market
data and have the statistics read the rate in force at each period. Keep the flag as an override for
reproducibility.

### 7.6 Search beyond three free parameters

TPE or random search once the space exceeds three free dimensions; the grid stops being the right tool
there. **The trap that would silently corrupt every sweep:** `DatasetAPI` carries `IndicatorResults`.
Learning caches them safely because its indicators never change between episodes. **Optimization varies
indicator parameters**, so reusing a cached tape wholesale evaluates every candidate with the *first*
candidate's indicators — the sweep completes, produces plausible numbers, and is meaningless. Rule: reuse
the market-data tape, always `inject(replace(tape, IndicatorResults=None))`. Do **not** warm every
candidate to the grid's worst-case window (`RULES.md`).

### 7.7 Re-run the seven-pair campaign on the corrected engine

The output of Phases 3 and 6, and the input to thesis iteration two. Single-threaded so it is exactly
reproducible. Compare against `CAMPAIGNS.md` (section 1.2) pair by pair and write down what moved and why;
rebuild the evaluation methods it specifies (section 8) in `Library` first, since the campaign's own
harnesses were deleted with `Research/`.
**State the tape's sampling eras** (Appendix A): the eleven years span four of them, with tick density
differing roughly thirty-fold, which a reader of a tick-derived result needs to know.

Then decide, on evidence, whether iteration two replaces iteration one. If the corrected engine produces
weaker numbers, that is a finding worth stating, not a result worth hiding.

**Three claims iteration one could not make. Items 7.1 through 7.4 exist to earn them.**

1. **It was not walk-forward and not continuous.** The invocation was `--training 0 --validation 12
   --testing 12`, which takes the `training <= 0` branch and produces **one** split: train 2015-01 to
   2024-01, validate 2024-01 to 2025-01, test 2025-01 to 2026-01. Iteration two must pass `training > 0`
   and `--continuous`, and 7.3 says how to elect honestly once it does.
2. **There was no genuinely held-out evaluation.** The campaign's evaluator scored over the full 2015-01-01 to
   2026-01-01, which contains the nine training years. Iteration one states this as a limitation and must
   never sell it as train/validate/test rigour. 7.4 is what fixes it.
3. **"Ten-plus years of data" is not a differentiator.** Across the 18 surveyed articles, 12 already use
   ten years or more, at a median span of 11. What *is* distinctive is resolution over that span: only
   Carapuço and co-authors use tick data, over seven years. Claim tick-derived data across 11 years and
   seven pairs; never span alone.

**Numbers from iteration one that must not drift when they are recomputed.** The five-balance
path-robustness protocol is 9 900 / 10 000 / 10 050 / 10 100 / 10 200, and every pair came back
robust-positive five times out of five. Alpha leads, not return, because in every pair the highest-return
candidate failed the permutation test. USD/JPY is a documented negative — beta +1.012, alpha -1.07% a year
— and since Phase 6 fixed its sizing it is the pair most likely to move. The regime null is per-model, not a constant.

**Two facts about the delivered agent that were each got wrong at least once — read the source, do not
restate these from memory.** Gradient clipping at norm 1.0 on both critic and actor is **not** an
anti-collapse mechanism; it bounds update norm against exploding gradients. Collapse is prevented by the
scale-*sensitive* reward, since a scale-invariant one collapses the actor to about 3% of available size,
and by `ActorRegularization` at 0.001.

**The feature bank lives in the run manifest.** `<Data>/Runs/<id>/Input/Parameters.yml` holds the 16
indicators actually used, in order — the ten fast ones of the campaign's base file plus the six slow ones its
override appended (`CAMPAIGNS.md` section 4). Always read the manifest.

---

## Phase 8 — Web app

Opened by 8.0, which is where the data comes from. The credential page already exists (Phase 1).

### 8.0 Research schema — DB-only inputs and outputs

**Moved from Phase 3 on 2026-09-24:** it stores research results, not market data, so it no longer
gates the market-data service; the pages of this phase are its first consumer.

Every input a model consumes and every output it produces moves from scattered files into Postgres.
Today the two most valuable series — the timestamped equity curve and the per-bar signal tape — are
persisted only *inside* a plot or result artifact. Nothing is queryable and nothing links a run to the
exact inputs that produced it.

Target: results in a `Research` schema, weights as rows, one `Run` row tying them together, identical
CLI behaviour, a thin web UI on top. Parameters are already done — `Library/Strategy/Ladder.py` replaced
the YAML tree — and the contract snapshot (`Input/Contract.yml`) belongs in the run row beside them.

**Layout**

| File | Contents |
|---|---|
| `Run.py` | `ResearchStatus`, `ResearchRunAPI` — `UID` primary key, `System`, `Status`, `Arguments`, `Command`, scope columns, `Parameters` and `Contract` as JSON snapshots at launch (what makes a run reproducible), `Owner` foreign key to `Auth.User`, `PID`, `ExitCode`, `Log`, timing, headline metrics |
| `Result.py` | all with `RID` foreign key to Run **ON DELETE CASCADE**: `TradeResultAPI`, `DealResultAPI`, `PositionResultAPI`, `OrderResultAPI`, `StatisticResultAPI` (long form: RID, Report in Net / Realized / Unrealized, Metric, six values), `EquityResultAPI`, `SignalResultAPI`, `EpisodeResultAPI`, `BenchmarkResultAPI`, `WeightResultAPI`, plus `ResultAPI` as the writer and reader facade |
| `Model.py` | `ModelAPI` — a named deployable weights registry. The `Weights:` parameter holds a Model UID instead of a folder path |
| `Research.py` | `ResearchAPI`, shaped like `Library/Scheduler/Manager.py`: `command()`, `launch()`, `run()` and `runs()`, `reap()`, `cancel()`, `delete()`, `promote()`, `materialize()`, `fingerprint()` |
| `Runner.py` | `python -m Library.Research.Runner <uid>` — Popen the CLI, persist Running and the PID, wait, **reload the row so a Cancelled status wins**, write the terminal state |

`Script/Setup/Research.py` provisions after `setup_auth` for the foreign keys, with indexes on
`Run(Status)`, `Run(System, StartedAt)` and `(RID, Timestamp)` on the series tables.

**Backend contract**

1. `--rid <uid>` on the shared base parser, threaded into `SystemAPI` like `iid`. Absent means the writer
   auto-creates its own Run row, so console runs still enter history.
2. At `_report_` time call `ResultAPI`. The import direction is one-way — `System` may import `Research`,
   `Research` must never import `System`. Write `.trades`, `.deals`, `.positions`, `.orders`,
   `.statistics(rid, report, df)` for **all three** reports, `.equity(rid, df)` **keeping the
   timestamps** (the three `CurveAPI` tracks), `.benchmarks` and `.headline`.
3. **Ungate the signal tape** so it records independently of `--plot`, then flush via `.signals`. Today
   `StrategyAPI._emit_` appends only when recording, only two strategies call it, and `Signals` resets per
   `deploy()`.
4. Learning: `.episode(...)` per episode, replacing log parsing; `.manifest`; `.weights` at completion.
   Parallel seed workers need the rid in their payload. Weight loading moves to a Model UID plus
   `materialize()` into the local cache.
5. Retire the CSV export once the DB path is verified (8.6).

**Measured gotchas**

- **Payload size binds.** A full 11-year H1 run is roughly 34 MB of JSON across about ten series, some
  68k points each. Thin to about 2k points a series, roughly 4 MB, before shipping to a browser; over
  8 MB wedges the Dash dev server. **Decimation must use one shared time grid** or cross-pane crosshair
  lookups break.
- `net.csv` is 90 metric rows by 6 value columns with the label column `Statistical Metrics`, and
  historical files drift — `Annualised` against `Annualized`. **Key by normalised label, never by row
  index.**
- Cancel and finish race: the Runner must reload before writing terminal state.
- PID reuse: guard reaping with `psutil.Process(pid).create_time() <= StartedAt + grace`. Never kill on a
  reap, only mark.
- Bars stay in the `Market` schema. Do not persist them per run.
- DB parameters plus materialized weights change the deployed path. Verify on a Simulation run **before**
  archiving anything.

**Reading list, in order:** `Library/System/System.py` for `_report_`, `_export_`, `_plot_`, `_curves_`,
`_bars_` and `deploy`; `Library/Portfolio/Portfolio.py` for `EquityCurve` (a `CurveAPI`, whose `Track` is the stamped series) and
`_record_equity_`;
`Library/Strategy/Strategy.py` for `_emit_`, `Recording` and `Signals`; `Library/Scheduler/Run.py` with
`Manager.py` and `Executor.py`; `Script/Setup/Scheduler.py` with `Script/Install.py`;
`Library/App/V2/Lightweight/Lightweight.py` for the consumer contract.

**Done when:** `python -m Script.Setup.Research` provisions cleanly; a console run goes Waiting to Running
to Success with result rows and non-null headline metrics; a second run cancelled mid-flight lands
Cancelled with its process tree dead; a real short backtest produces equity and signal row counts
matching bar counts; a one-seed one-episode Learning run records episodes, stores its manifest, and
`promote()` plus `materialize()` round-trips byte-identically in torch; the full suite is green; and the
DDPG consistency golden still replays.

### 8.1 Move the pages onto the Research schema

`Library/Web/Research/` reads run rows and result series instead of parsing artifacts. A result detail page
renders an immutable artifact and therefore **does not poll** — polling re-mounted the grid and discarded
sheet tabs and chart zoom.

### 8.2 Profit, risk and ratio columns on `/backtesting` rows

Build as a DB read once 8.0 lands, never by re-parsing each run's stored artifacts.

### 8.3 Signal and plot refactor

Direction and Volume signal on the Strategy **base** class; thresholds default **off** and one-sided
capable; eight toggleable lines; `Parameter` returns None for a missing key; a `--plot` hardcode audit;
optional markers and a deal map. **Land it as a no-op first, prove the suite and the goldens, then tune
the bounds.**

### 8.4 Payload thinning on one shared time grid

See the measured note in 8.0. This is what makes an 11-year H1 run openable in a browser at all.

### 8.5 iPad pass

`Library/Web` is used from a Windows desktop browser **and an iPad 12.9 inch**; both are first-class.

- **Charts must not capture touch gestures** (`RULES.md` has the exact Plotly settings, and why never
  `staticPlot: True`).
- **Prefer fits-without-interaction.** The workflow DAG should render every task and edge visible at once;
  the only interaction wanted is tapping a node to open that task's page.
- Touch targets, sticky headers and virtualized grids all need checking at iPad width. `LightweightTableAPI`
  is virtualized, so verify momentum scrolling behaves. Playwright emulates the viewport at 1024 by 1366
  CSS pixels.

### 8.6 Retire the CSV export

Once 8.0 is verified end to end.

### 8.7 Known and unfixed

- An ordinal pane with very few points does not fill the width — a three-fold generalization chart leaves
  space at the right edge. Lightweight clamps bar spacing and setting it explicitly is overridden.
  Cosmetic and legible.
- Multi-tab `Open` depends on the browser, not the code. Browsers permit one popup per gesture. The button
  opens the first in place, attempts the rest, and reports how many were blocked. No code-only fix.

---

## Phase 9 — Remaining

### 9.1 Logging

`StorageAPI` is unit-tested against a fake record but has never been exercised against a live Postgres run
end to end, and the Scheduler still writes durable rows through `ExecutorAPI._open_log_`. Close both.
Measured dead end, do not retry: a drain thread for the console and file sinks. Async is a per-sink
property — console and file synchronous, `StorageAPI` not.

### 9.2 Realtime hardening

Audited 2026-07-02, needs a cTrader session: transport hardening; the watchdog is armed only on `Init`;
no hung-peer timeout. The three buffer defects of that audit — warmup bars double-added to the market
buffer, `BufferAPI._worker_` deadlocking on a flush when connect fails, an unused universe buffer — go
with `BufferAPI` in 5.6.

### 9.3 Strategy state recovery

Persist Signal and Risk machine state across a Live restart — `SessionAPI.State` bytes, loaded at
`deploy()`, saved on `Shutdown`.

### 9.4 Test coverage gaps

`Statistic` 1 file for 1889 lines; `Scheduler` 1 for 1700; `Model` 2 for 1654; `Web` 3 for 3449; `Auth` 1
for 460; `Indicator` 4 files for 43 modules.

**A race in `Tests/Scheduler/test_Access.py::test_a_runner_whose_run_was_closed_elsewhere_stands_down`** — it
failed once under a full-suite load on 2026-09-28 and passed alone three times: the test closes the run as soon
as the child has written its marker, and under load that close can land before the runner's own row exists.
Wait for the row, not the marker.

### 9.5 Dead surface

Zero callers outside the package `__init__`. Delete, or keep deliberately as a library offering.

`Utility/Path.py` 28 of the 36 `traceback_*` and `inspect_*` grid, about 120 lines; `Utility/Datetime.py`
`datetime_to_iso`, `iso_to_datetime`, `weekday_shift_datetime` and seven `<day>_shift_datetime`;
`Utility/Runtime.py` `is_local`, `is_service`, `is_python`, `is_ipython`, `is_terminal`, `is_console`,
`match_env_vars`; `Utility/IO.py` `is_readable`, `is_writable`, `smartlink`, `symlink`, `hardlink`;
`Utility/Typing.py` `findvariable` and `getvariable`; `Utility/HTML.py` entirely. **Not dead, despite an
earlier listing here:** `string_to_datetime` (`Web/Core/Artifact.py` parses run stamps with it) and
`find_user` (`StorageAPI.attach`).

Called only by their own tests (rechecked 2026-09-17 across `.py`, `.js`, `.sql`, `.yml`, `.cs`):
`Typing` `hasmember`, `hasmethod`, `getmethod`, `hasproperty`, `getproperty`; `Runtime`
`find_caller_module`, `find_caller_class`, `find_caller_package`; `DataclassAPI.tuple` and `list`.
`DataclassAPI.fields` and `json` have no caller at all — deleting those four also settles 9.6's note that
they forward seven keyword arguments.

`Portfolio.py` the five statics that remain of the original 16: `pull_accounts` and `push_accounts`,
`push_orders`, `push_positions`, `push_trades` — plus `calculate_statistics`, `BuyOrders` and `SellOrders`;
`Portfolio/Statistic.py` `generate_realized_report` and `generate_unrealized_report`; `Market.py`
`load_ticks`, `save_ticks`, `count_ticks`, `load_bars`, `save_bars`; `Universe.py` all 12 `save_` and
`load_` plus `pull_timeframes`.

Convenience properties never read and not emitted by `dict()`: `Account` IsDemo, IsHedged, IsNetted,
UnrealizedReturn, MarginRatio, FreeMarginRatio, CreditRatio; `Order` IsAccepted, IsFilled, IsRejected,
IsExpired, IsCancelled, ExecutionRatio, UnfilledVolume; `PnL.LogPnL`; `Position.MarginUtilization`;
`Trade` DurationDays and IsClosed; `Bar.RangeTick`; `Price.LogPrice`; `Tick.InvertedMid`; `Timestamp` Sin,
Cos, Epoch, Yearday, Millisecond; `Contract` IsSpot, IsDerivative, IsLinear, IsNonLinear; `Ticker` Dashed,
Slashed, Underscored; `Timeframe.Hours`. Plus about 25 `@overridefield` Position columns computed by every
`dict()` and dropped by `reporting_view`.

`IndicatorAPI.init_data` and `update_data` (the one instance is read only for its three members);
`App/V2/Assets/Scripts/Paginate.js`, which targets the retired `.dash-table-container` yet keeps a
`MutationObserver` on the whole body of every page, and the 11 `app.css` rules still styling
`.dash-table-container`, `.dash-spreadsheet` and `.cell-markdown`.

`Database.structured`, `ManagerAPI.delete_run`, `ManagerAPI.retained`, `OptimizationAPI.trials`,
`BrownianNoiseAPI`, `GeometricBrownianNoiseAPI` (no factory; DDPG hardcodes OU), the empty
`Sources/Plugins/Plugin`, and `Requirements.txt` at 0 bytes. `Sources/Indicators/Connector/Connector.cs` is
still the cTrader hello-world template — Phase 10 either makes it real or it goes.

`Library/Formulas/` stays — an xlwings Excel UDF feature with zero callers that you intend to renovate.
The `xlwings` pin stays with it.

### 9.6 Simplifications

Behaviour-preserving, provable by AST body hash plus the suite and the goldens.

- `Position.py`: about 40 `@overridefield` properties are four body shapes — `pnl/(Volume*unit)`, a signed
  price difference over unit, `min`/`max(0, x)`, and `_max_equity_*_pnl_.<attr> or 0` — so one helper each.
  `Order` and `Position` share `_unwrap_price_`, `_make_price_` and `_assign_price_`, timestamp assignment
  and the Session and Account property pairs, which is a Portfolio mixin with two hooks.
- Indicators: a `BaselineAPI(TechnicalAPI)` carrying the four `filter_` and `signal_` rules plus `batch` —
  9 classes times 4 identical methods, 6 identical `batch`, about 125 lines; `MAC`, `DMAC` and `TMAC`
  collapse to one `_AVERAGE_` class attribute; ROC, ATR and RV have identical rules; `FundamentalAPI`
  equals `SentimentalAPI` equals `TechnicalAPI`'s composite half; `MA.py` builds the six-way `match` twice.
- `SystemAPI._process_updates_` is about 190 lines of `match` arms rebuilding the same seven-key context.
  `RULES.md` keeps one `case` per `UpdateID` deliberately, so the lever is the shared `context()`, not a
  dispatch table. `_fitness_()` is byte-identical in `LearningAPI` and `OptimizationAPI`, so it belongs on
  `BacktestingAPI`. `Realtime._binary_*_` are `_lower_` class constants.
- `Strategy.py` `strategy_management`: `update_closed`, `stop_loss`, `take_profit`, `margin_call`, the
  `update_modified_*` family and `update_closed_order`, `filled` and `expired` differ only in the log line —
  but `RULES.md` prefers explicit named handlers, so only a shared log helper is in scope. `Hybrid/DDPG.py`:
  `Defaults["Realtime"]` equals `Defaults["Learning"]` for 35 lines, the 12-field state block appears in
  both `__init__` and `_initialize_`, the optional-parameter idiom repeats ten times, and
  `_hedge_(update, close)` never uses `update`.
- `Model`: the `memorize`, `remember`, `_soft_update_` and `decide` scaffold is copied into the DDPG, SAC
  and TD3 agents and belongs on `AgentAPI`; SAC and TD3 `Critic.forward` are byte-identical; the whole
  module uses `_name` privates where `RULES.md` says `_name_`; `remember()` annotates a tuple literal instead
  of `tuple[np.ndarray, ...]`.
- `Market.py`: `init_data`, `update_data` and `update_offset` list the same series three times; `Series.py` `last()` and `tail()`
  share a 500-character row-to-`TickAPI` expression, and `over`, `under`, `crossover` and `crossunder`
  share a five-line prelude; `Tick.py` has seven same-shape setters. `Universe.py` has 11 live `pull_` and
  `push_` of one shape; `Timeframe.py` has five comparison dunders that are `total_ordering`.
- `Database.py`: the seven-line target-validation block is copied into `exists`, `diff`, `create`,
  `delete` and `migrate`; `executeone` and `executemany` share a 12-line prelude; `search` repeats an
  empty-catalog literal three times; `executemany` logs a failure via `.error` then `.exception`, the same
  double-log as `Service`, `Bloomberg.Streaming` and `Remote`. `Dataclass.py` `tuple`, `list`, `dict` and
  `json` forward seven kwargs explicitly. In `Auth`, Cloudflare `_verify_` and OIDC `authenticate` share
  the JWKS and `jwt.decode` block, which is a `_claims_()`.
- `Runner.load` and `SchedulerAPI._task_` both build a detached `TaskAPI`, which is a
  `TaskAPI.fetch(db, uid)`; `Logging.File.FileAPI` and `Utility.File.FileAPI` share a name, so consider
  renaming the sink `FileSinkAPI`.
- Tests: `Tests/Strategy/test_Strategy.py` imports `MagicMock` inside six tests and `test_Workspace.py`
  imports `json` inside three; comments appear in seven test files; the `test_Sizing.py` derivations could
  move into the assertions; `Tests/Benchmark/IPC.py` is a benchmark script living under `Tests/`.

### 9.7 Blocked

- **Huge pages for Postgres — yours.** They need the Windows privilege *Lock pages in memory* for
  `NT AUTHORITY\NetworkService` (`secpol.msc` → Local Policies → User Rights Assignment), then a restart
  of `postgresql-x64-18`; `huge_pages = try` picks them up, and 16 GB of `shared_buffers` is worth
  measuring again (8 GB today: 16 GB gained nothing without them, the whole tape being 7 GB).
- **`Script/Install.py` and `Script/Task.py` both define `provision()`** — different modules, different
  jobs, no collision today. Rename one if it ever confuses.

### 9.8 Measured but not taken — the hard passes of 2026-09-17 and 2026-09-28

Each was measured, each left the goldens byte-identical in a throwaway process, and each was left out for
the reason given. Take them with the golden gate in hand.

| Opportunity | Measured | Why not yet |
|---|---|---|
| `_build_intra_arrays_` gathers 18 arrays from the tape per candidate | 6-11ms per 369k M1 rows before Phase 3 | A scope-keyed memo is wrong for Learning's mirrored tapes, which share the scope but not the prices |
| Whole-table polling fingerprint (`n_tup_*` on `Scheduler.Run`) | Service heartbeats every 15s make every open page rebuild: research pages ~every 15s, Scheduler pages ~every 20s | A narrower token (0.4-2.9ms, filtered `COUNT(*)` + `MAX`) must still catch Progress and Status without catching service beats |
| 78 KB of the 135 KB index page is duplicate inline JS (87 inline scripts, 33 distinct) | first load only | The fix is `dash.Dash._inline_scripts`, a private attribute Dash drains at index time. Not worth coupling the composition root to it |
| The "admin connect → create `Tests` → disconnect" block is copied in 5 test modules | — | One session fixture in `Tests/conftest.py` |
| The three drivers repeat `__init__`, `_driver_`'s name resolution, `_quote_` and the description mapping | ~100 lines | Only Postgres is proven against a live server. 1.6 touches the same `__init__`s — do both together |
| `_commission_`/`_swap_` carry a second conversion path (1/mid) that only tests reach | — | Production always passes `_conversions_(tick)`; making them required arguments deletes the fallback and the test that exercises it |
| `None` where `RULES.md` wants `MISSING` | — | `LoggingAPI.install(logger)`, `StorageAPI.attach(source, path)`, `BufferAPI(db)`, `find_caller_frame(skip)`, `MarketAPI.pull_bars(start, stop)`, `System._transition_(start)`, `_label_(suffix)`, `Strategy._emit_(raw)`, `Backtesting._stitch_(equity)`. Each needs its body read, not a blind swap |
| `Library/Statistic/Composition.py` wraps 21 calls across lines with several arguments each | — | `RULES.md` says one line or one name per line; mechanical but large |

### 9.9 Move the `Data` tier under OneDrive

**Moved from Phase 3 on 2026-09-24** — a storage-tier question, not the market database.

The seven thesis winners' weights (639 KB, 28 files) exist **only** in `<Data>/Models` on one machine's
local AppData. Verified safe from pruning, but not pruned is not backed up.

| tier | files | size | pruned by | verdict |
|---|---|---|---|---|
| `Temp` | 843 | 3.49 GB | retention, by age | **no** — sync locks make deletion unreliable |
| `Data` | 15 645 | 3.15 GB | never | **yes** — write-once, the only copy of every model |
| `Cache` | 180 | 6.61 GB | retention, by last use | **no** — Files On-Demand can dehydrate a preload tape to a placeholder |

**Resolve first:** does anything assume `Data` and `Temp` share a volume? Save and Release move a run
folder between tiers as a rename; across volumes that becomes copy-and-delete — slower, and no longer
atomic. Also open: whether `inspect_root()` stays derived with only `Data` redirected; a retention policy
for `Data/Models`, since roughly 1 100 wave-archive models (about 110 MB) are search byproduct; and a
per-machine namespace if two machines ever sync the same `Data`.

### 9.10 Exercise the authorization-code sign-in once

From Phase 2: `Script/Setup/Spotware.py` signs a cTrader ID in through the browser, and has never run
end to end — the playground's tokens made it unnecessary, and the refresh grant has kept the token alive
since. It is the only way back if the refresh chain ever breaks. With the https redirect it runs in paste
mode; a `/openapi/callback` page on the web app would make it one click.

### 9.11 Replace the WSGI bridge before Starlette drops it

Found 2026-09-26, the suite's one third-party warning: Starlette deprecated `starlette.middleware.wsgi`,
which `fastapi.middleware.wsgi` re-exports and both `App/V1/App.py` and `App/V2/App.py` mount the Dash
server through. Nothing is pinned, so the release that removes it fails every web import — the updater's
suite catches it on the candidate and keeps the live environment, but every upgrade after it is blocked
until the bridge moves to `a2wsgi`, the named replacement.

### 9.12 Data workflow follow-ups

Moved from Phase 5 when it closed, 2026-09-28; each needs a date or an event that has not come yet.

- **The calendar's Sunday evening.** A Monday week reads both Forex Factory pages it spans since
  2026-09-28; confirm on the first Sunday evening after (2026-10-04) that the NZD, AUD and JPY actuals land
  within a minute or two of release.
- **`SwapTime` at the clock changes** (2026-10-25 Europe, 2026-11-01 US). The engine reads Spotware's 1259 as
  minutes after 00:00 UTC, fixed all year — the winter positions of the `Test` goldens proved cTrader rolls at
  20:59 UTC in winter as in summer (2026-09-29). Confirm the row does not move at either change; if it does,
  the Universe service records a dated row and `ContractAPI.rolls` follows it.
- **A 24/7 security and the repeated hour.** `TapeAPI.bars` buckets on New York time, so the hour New York
  repeats when its clocks go back is one bucket and an H1 bar there holds two hours; the first weekend-trading
  security tracked (a crypto pair, an index CFD) must choose between one long bar and two bars sharing a label.
- **The live tape's tail latency.** Measured 2026-09-28 17:55 UTC on a quiet database, five minutes on EURUSD,
  GBPUSD and USDJPY with every Phase 5 fix live: a tick reaches its row in 2.0-2.5 s at the median, but 11-13 s at
  p90 and up to 22 s, with none missing — the median is near the one-second gate, the tail is not. The causes
  found so far (whole-hypertable deletes, generic plans, compression stalls) are fixed; find the periodic 10-20 s
  stall (a worker's poll cycle, a refusal backoff, a background job) with a per-worker timeline, then re-measure.
- **The mirror after a week offline.** With the PC off for a week and demo trades placed meanwhile, the next
  logon backfills the tape first and then the mirror with correct derived fields. Verified over a nine-hour
  outage (the crash of 2026-09-28 05:17 UTC): the tape resumed, and every derived trade equals the tick truth.

### 9.13 Indicator streaming

Profiled on the DDPG golden, 2026-09-29: the engine's own Phase 6 code is not a hotspot; the largest cost is
`Technical.update_data`, whose `_scalar_` builds a one-row Polars frame per indicator per bar — about 39 of 90 s
under cProfile (its overhead included). Update each indicator on numpy scalars instead, keeping its
frame-building path for the warmup. Gate: every golden byte-identical, the DDPG golden included. Not Appendix
A's ring buffer, which replaced `SeriesAPI`'s storage and was measured slower.

### 9.14 Several securities and timeframes in one backtest

Requested 2026-09-29. Today a backtest trades one security on one timeframe, and a portfolio of models is
built afterwards from their separate equity curves (the thesis basket). Let one run hold several securities,
each on its own timeframe, on one account: one clock across the tapes, one balance and margin, and the
portfolio statistics computed by the engine instead of by a script.

---

## Phase 10 — Indicator connector

`Sources/Indicators/Connector` is the untouched cTrader indicator template today. This is what it becomes:
**a bridge that plots a Python-implemented indicator directly onto a cTrader chart, so it can be compared
against cTrader's own built-in by eye and by value.**

That makes it a **validation instrument, not a feature.** `Library/Indicator/Technical` is the input half
of every strategy in the framework — the DDPG feature bank alone is 16 indicators — and nothing has ever
proven those implementations agree with the platform's. A silent disagreement in, say, `ATR` or `ER` does
not crash anything; it quietly changes every observation the agent ever sees.

### 10.1 The bridge

Mirror the Robots connector rather than inventing a second mechanism: shared memory, single-slot
request/response lockstep, the same `Protocol` vocabulary. An indicator needs bars in and a series out,
with no orders, positions or account state, so the subscription is minimal. **`Script/Setup/Enum.py`
must emit into both projects** once this starts; `OUTPUT_PATH` is a single hardcoded path into the Robots
project today. The two `.algo` artefacts must always be generated from the same enum source, or the wire
mis-decodes exactly as it would between mismatched robot builds.

### 10.2 The comparison harness

The point of the phase, and worth designing before the bridge:

- Plot the Python series and cTrader's native equivalent on the same chart, and a **difference series**
  beneath. Eyeballing two overlapping lines hides small persistent offsets; a difference pane does not.
- Report the maximum absolute difference, and the bar index where it occurs, over the loaded range.
- **Warmup is where these will actually disagree.** A rolling indicator's first N bars depend on how the
  seed is chosen; a difference that vanishes after N bars is a warmup convention mismatch rather than a
  formula error. Report the two regimes separately or the diagnosis is wrong.
- Where the framework has no native counterpart, the comparison is against a hand-computed fixture
  instead, not skipped.

### 10.3 Coverage

Start with the DDPG feature bank, since those are the implementations carrying published results:
`ATR 14`, `ER 120`, `RV 16/480`, the `SMA` family and the `ROC` family. Then the rest of
`Library/Indicator/Technical`. Record each verdict — agrees, agrees after warmup, or disagrees with the
measured magnitude. **A disagreement is a finding, not a bug to rush.** Decide per indicator whether to
match the platform or document the difference — do not reflexively change an implementation the
published results depend on.

**Done when:** the connector plots any registered Python indicator on a cTrader chart beside its native
counterpart with a difference pane, and the feature-bank indicators each carry a recorded verdict.

---

## Phase 11 — Live trading panel at `/trading`

`Library/Web/Trading/Trading.py` is a 910-byte placeholder today. This phase replaces it with the console
the framework is actually for. It consumes almost everything above it: broker sessions and tokens come
from the credential store (1); per-tick updates need the Spotware session (done, Phase 2) and the market service (done, Phase 5);
order actions, any account currency and both position modes are done (Phase 6); surviving a restart needs 9.3; and the run and
result surfaces it links into come from 8.0.

### 11.0 Parity with the cBot — `Live` over the Open API

**Requested 2026-09-24.** Everything the Connector cBot and `RealtimeAPI` do in `Live` must be doable
through `Library/Spotware`: market data (ticks and bars, historical and live), every Protocol action
(market, limit, stop and stop-limit orders; volume, price and SL/TP changes; closes; subscriptions) and
every Protocol update. `Simulation` and `Testing` run inside cTrader's backtester and have no Open API
equivalent, so parity is **`Live` only**. The design keeps `RealtimeAPI` untouched: a second transport
behind the same seam as the shared-memory one turns Protocol actions into Open API requests and Open API
events into Protocol updates, so a strategy cannot tell which one it runs on.

Mapped 2026-09-24, every `ActionID` and `UpdateID` against its Open API message: every action has a
request and every update can be derived, but five pieces are missing, most important first.

1. **A persistent event router.** A new order returns only its `ORDER_ACCEPTED` event and `_on_message_`
   feeds only blocking listeners, so fills, closes, SL/TP hits and amendments are dropped today. The
   router turns `ProtoOAExecutionEvent` (accepted · filled · partial fill · replaced · cancelled · expired
   · rejected) into Order, Position and Trade updates from a cache of the last state, close reason
   included (manual · stop loss · take profit · stop-out).
2. **Reconcile after a reconnect.** The lifecycle itself is done (`RULES.md`, `Library/Spotware`); on top of it, a live session replays
   `ProtoOAReconcileReq` plus the deals since the last one seen, so no fill is lost across a drop.
3. **The market-data half of a cBot bar.** A cBot bar is five complete ticks (gap · open · high · low ·
   close), each with ask, bid and four conversion rates; a trendbar is bid OHLC only. Build bars locally
   from the spot feed and emit BarOpened and BarClosed, fetch the conversion chain
   (`ProtoOASymbolsForConversionReq`), and evaluate the ask and bid price targets on every tick as the
   cBot does.
4. **The action translator.** Pips to a relative price; a target volume to the delta to open or close
   (an increase is a new order carrying `positionId`, unverified on a hedged account); a stop-limit's
   limit price to `slippageInPoints`; removing an SL or TP (how the Open API clears one is unverified);
   full-state SL/TP amends; and `clientOrderId`, so a refusal becomes a `Denied` update tied to its action.
5. **Account and contract updates.** Equity and margin computed, since the Open API trader carries no
   equity, credit, margin or stop-out field; gross and net P&L per position; one Security builder joining
   the symbol, symbol-list and asset requests (tick and pip size derived, commission types mapped to
   `CommissionMode`); and `ProtoOASymbolChangedEvent` re-snapshotting `Contract.yml`, which makes the
   contract-terms rule of `RULES.md` observable live.

Excluded by design: the `Init`, `Execution`, `Complete` and `Batch` messages, the shared-memory framing,
delay mode and the PID watchdog. The Open API also offers what the Protocol lacks — real rejections for
`Denied`, `Expired`, partial fills, balance events mid-run (the cBot sends Account once), margin-call
warnings, native trailing and guaranteed stops — and each is added to the Protocol deliberately, never
slipped in.

**Done when:** one strategy runs `Live` on the demo account through the cBot and through Spotware side by
side, and the two update streams agree event by event — order, position, trade and bar — with every
difference named.

### 11.1 The transport seam

Every other page either polls on a timer or renders an immutable artifact. **A live panel is neither.**
It needs push, and it needs to stay correct when push drops.

- Build on the Scheduler's existing listen, notify and wait seam rather than inventing a second one.
- **Connection count is a correctness budget, not a tuning knob.** A per-viewer subscription needs a hard
  ceiling and a return path — verify with a soak where `pg_stat_activity` plateaus.
- Degrade explicitly. If the push channel drops, the panel says so in the header and falls back to a slow
  poll — never silently shows stale prices as though they were live.
- **Share a subscription between streams** before two consumers need one symbol: `SpotwareAPI._listen_`
  subscribes and unsubscribes per stream, so the first one's exit removes the server's subscription for both.
  Count listeners per symbol and unsubscribe on the last (found 2026-09-25, moved from Phase 5).

### 11.2 Account header

Balance, equity, margin used, free margin, margin level, unrealized P&L, and open exposure broken out by
currency. Equity and margin level update per tick; balance only on a closed deal. Margin level gets a
status treatment — good, warning, serious, critical — with an icon and a label, never colour alone.

### 11.3 Position and order blotters

Two virtualized `LightweightTableAPI` grids. **Positions:** symbol, side, volume, entry price, current
price, stop loss, take profit, swap, commission, spread paid (`SpreadPnL`), gross and net unrealized P&L,
duration, and the strategy that owns it; row actions modify stop and target, close partially, close
fully. **Orders:** symbol, side, type, volume, limit or stop price, expiry, state; row actions modify,
cancel. Both need a totals row computed server-side, not summed in the browser from a thinned payload.

### 11.4 Order ticket

Market, limit and stop, with the volume field driven by the **same** sizing path the engine uses — since
Phase 6 there is exactly one correct sizing formula and this ticket must call it. Show the derived
risk in account currency and as a percentage of balance before the button is armed. Stops and targets
accept pips or price, and convert visibly.

### 11.5 Strategy control and the kill switch

Which strategies are deployed, on which securities and timeframes, what state each Signal and Risk machine
is in, and how long since the last update. Per-strategy start, stop and flatten.

**The kill switch must work when everything else is degraded.** Flatten-all and disconnect must not depend
on the chart layer, the push channel, a payload having loaded — or the credential store being reachable at
that moment: the live session already holds its resolved token in memory, and the kill switch uses that
session. Confirm destructively, and log the outcome where `Run.log` will capture it even if the process
dies immediately after. Mutations are `Editor` and above through the existing router gate.

### 11.6 Live chart

One Lightweight chart per watched security: price, the open position with its entry, stop and target as
price lines, and fill markers as they arrive, with the live signal tape from 8.0 as its own pane. Reuse
`Library/Statistic/Workspace.py` for the spec, so the same definition serves the panel and the backtest
view.

### 11.7 Connection health

Connector state, last heartbeat, tick latency, ticks a second, reconnect count, the current subscription
per strategy, and the token's expiry from the credential store. The panel that answers "is it actually
running".

### 11.8 iPad

The whole panel is subject to 8.5, and more strictly: blotter rows need touch-sized targets, the order
ticket must be usable one-handed, and the kill switch must be reachable without a precise tap.

**Done when:** a Simulation deployment drives the full panel end to end — positions open and close, orders
fill and cancel, the account header tracks, the kill switch flattens — and then the same against a live
demo account, with the push channel deliberately severed mid-session to prove the degrade path.

---

## Phase 12 — Interactive Brokers provider

**Requested 2026-09-15.** A second broker adapter in the shape of Spotware, standalone, with no provider
base class (Appendix B). Its login lives in the credential store from the first line (rule 4). What it
changes, to be verified against its current documentation before design:

- **Transport.** Its API talks to a running Trader Workstation or IB Gateway process over a local socket,
  not a cloud endpoint. A provider that needs a desktop application alive is a different lifecycle, and the
  Scheduler service must supervise that dependency.
- **Multi-asset.** Stocks, futures, options and FX under one account. A security is a contract
  description, not a numeric id.
- **Historical pacing.** It documents strict limits on historical data requests — a poor bulk tick-history
  source and a good live-and-reference source.
- **Options chains and greeks.** One of the few retail-accessible sources for listed option chains, which
  is what makes this phase the data gate for Phase 13.

**Cross-provider tickers.** Brokers name one instrument differently (`GERMANY 40`, `GER40`); a second
provider needs a mapping onto one ticker before its securities can share the framework's `Ticker` rows
(moved from Phase 5).

**Done when:** the provider fetches reference data, historical bars and a live stream for at least one
security per asset class it supports, with its own suite green.

---

## Phase 13 — Option strategy pricer and backtester

**Requested 2026-09-15.** A new asset class for the framework. **The data gate comes first:** cTrader lists
no vanilla options, so chains come from Bloomberg — already integrated — or from Interactive Brokers.
`Universe.Contract` already carries `Variant`, `Payoff`, `Strike`, `Maturity` and `Exercise`; the contract
model needs populating, not redesigning.

1. **The pricer.** Closed form where it exists (Black-Scholes for European equity-style, Black-76 on
   futures and forwards), lattices for early exercise (binomial or trinomial for American and Bermudan),
   an implied-volatility solver, the greeks, and a volatility surface built from observed chains. A
   multi-leg strategy is priced as the sum of its legs. Validate every model against a published reference
   value, not against itself.
2. **The backtester.** Very likely a **third engine**, a sibling of `RealtimeAPI` and `BacktestingAPI`. Its
   state is a chain and a surface evolving through time; its fills are per leg and per strike; and it must
   handle expiry, exercise and assignment. It should still reuse `Library/Portfolio`, `Library/Statistic`
   and `Workspace`.

A new top-level package when it starts, likely `Library/Derivative` or `Library/Option`, named and added
to `RULES.md` at that point.

**Done when:** the pricer reproduces reference values for European and American vanillas and their greeks,
and a multi-leg strategy backtests across at least one expiry cycle with exercise handled.

---

## Phase 14 — Free-threaded Python

**Requested 2026-09-26:** investigate whether the framework can move to a free-threaded (no-GIL) CPython.
The motivation is measured here: every row-wise path stalls near 1.3 M rows a second on the GIL, the tape
decode and the bar build use threads only where numpy releases it, a CPU-bound Python thread starved a
concurrent log writer 253×, and Optimization and Learning pay for processes — spawn, imports, shared memory —
to get parallelism at all. `Future.yml` already maintains a Python 3.14 free-threading environment to try it
in.

Answer, with measurements: which dependencies ship free-threaded wheels (numpy, polars, torch, psycopg,
Twisted, Dash …); how much single-thread speed the free-threaded build costs on the engine's hot path;
whether the tape decode, the bar build and the engine scale with threads once the GIL is gone; and whether
Optimization and Learning could run their candidates and seeds on threads instead of processes.

**Done when:** a written verdict with those measurements, and a migration plan or a stated reason not to.

---

## Appendix A — Measured, do not re-derive

- **The stored tick tape is sampled by era — measured 2026-09-18 on `Market.TickReload`.** The minimum
  spacing between consecutive ticks, identical on all seven pairs:

  | Period | Minimum spacing | Ticks a month (EURUSD) |
  |---|---|---|
  | 2014-01 → 2016-02 | none — 1 ms gaps occur | ~60 000 |
  | 2016-03 → 2017-06 | **150 ms** | ~1.8 M |
  | 2017-07 → 2017-08 | none — 1 ms gaps occur | ~2.1 M |
  | 2017-09 → 2024-08 | **150 ms** | ~1.75 M |
  | 2024-09 → today | **300 ms** | ~1.35 M |

  One busy day (USDJPY, 192 258 ticks) has its 1st percentile gap at 150 ms and not one pair of ticks
  closer. Half the ticks change one side only; none repeats both sides; `Volume` is 1.0 on every tick; and
  every row reads `UpdatedBy = 'Autosave'`. The eras change on the same dates for every pair, which points
  at how cTrader's own tick store holds history — the store its backtester replays — rather than at the
  download. Confirmed 2026-09-24: the Open API serves exactly these sampled ticks. It is the reason for rule 5.
- **Performance.** Warm NNFX H1 year about 1.5 s; D1 ten years about 3.2 s; H1 ten years about 25 s.
  Learning frozen-tape replay about 3.12x a pass. **No cold path since Phase 3:** run 5 (EURUSD D1, eleven
  years) 17 s at `Auto` and 12 s at `Tick` against 568 s cold before; EURUSD's 221 M ticks read and built
  into D1 bars in 7.6 s, H1 and M1 intrabar bars in 4.4 s; a dense day 10 ms.
- **Dead ends, do not retry.** A numpy ring buffer for `SeriesAPI`; mypyc and Cython; a drain thread for
  the console and file sinks (a CPU-bound Python thread starves a concurrent writer 253 times over).
- **Logging cost.** Suppressed record 128 ns, emitted 1188 ns, timestamp 234 ns — down from 271, 4961 and
  1990.
- **The warmup window is read per run; the tape is not.** `BacktestingAPI._tape_` memoises the execution
  tape, its bars and conversions on a window-free key, and each window reads only its own warmup
  (`TapeAPI.before`, 0.2-1 s), so six windows read the tape once.
  `OptimizationAPI._ordered_` keeps the cheap per-window rebuild consecutive — 192 EURUSD D1 candidates
  went 26.96 s to 19.09 s with identical scores.
- **Market data, audited 2026-08-25.** Seven majors — AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF,
  USDJPY — carry D1, H1, M1 and MN1 from 2014-01 to 2026-08, about 78k H1 and 4.6M M1 each. EURJPY and
  US500 have `Security` rows but no data; 1000 defined, 7 populated. Security ids: EURUSD 1, USDJPY 6,
  GBPUSD 11, USDCHF 16, AUDUSD 21, USDCAD 26, NZDUSD 31.
- **2016-01-11 to 2016-01-25 is absent in all seven pairs, ticks and bars, and is not repairable** through
  the cBot — proven 2026-08-25 by a re-download that visited the month and wrote zero rows — nor through the
  Open API, whose tick endpoint returned nothing for it on 2026-09-24 (its trendbars do cover it). Do not
  spend another download on it.
- **Stored conversions are accurate across the whole history.** Implied cross rates track the real rate to
  within -0.001% to -0.009%, consistently bid-side, with zero static stretches. The cTrader "download
  historical data for additional symbols to convert profit/margin" option must stay **on** — with it off,
  the live cBot path freezes the cross-pair spot and the conversion goes stale.
- **Fee flags cannot reproduce broker terms — which is why every run pins `Contract.yml`.** `CommissionType.Amount` is
  a **flat** charge per trade, not per million, and `SwapType.Points` multiplies by `PointSize` where
  `Accurate` with `SwapMode.Pips` multiplies by `PipSize`, ten times apart on all seven majors.
- **Line endings are not mixed.** The working tree looks mixed, but `.gitattributes` carries
  `* text=auto eol=lf`, so the repository is uniform and the CRLF warnings on `git add` are checkout
  artifacts. `Sources/` builds warning-free in Debug and Release; the old `CA1416`/`CS0618` backlog is
  stale.
- **Postgres.** PostgreSQL 18 on Windows, service `postgresql-x64-18`, data directory
  `C:/Program Files/PostgreSQL/18/data`. `synchronous_commit = on` globally (never lose a committed
  trade). `shared_buffers` is deliberately 8 GB rather than the Linux 25% rule — on Windows large
  shared-memory segments are less effective and the OS file cache does the heavy lifting. For heavy
  connection scale use PgBouncer rather than raising `max_connections` further.

## Appendix B — Decided, do not re-litigate

| Decision | Rationale |
|---|---|
| Credentials are their own module, built on `Auth` | `Auth` authenticates people; the store decides what a person or a process acting for them may use. One-way dependency, like `Scheduler` on `Logging` |
| Credentials are stored in plain text, with `ViewRole`/`EditRole` thresholds | decided 2026-09-21. Database access already reads everything, so encryption and a master key buy nothing and cost a key to lose; the thresholds are a UI and bookkeeping control. Keeping secrets in the Windows Credential Manager instead would lose the page, the roles and the stamps |
| A run uses its task owner's credentials | permission to run is not permission to read. The starter is recorded as `Run.Auditor`, and a task's `EditRole` is a statement about who you trust with those credentials |
| The database logins stay in the drivers | the store lives in Postgres, so the Postgres login cannot come from it |
| `timestamptz`, with the server and every session pinned to `UTC`, converted at the driver | the column declares an absolute instant; the driver loads it back as naive UTC, so `RULES.md`'s one in-memory convention stands and every export stays byte-identical. Emitting aware datetimes framework-wide would touch every `utc_now()` caller, Polars dtype and CSV stamp for nothing the column type does not already give |
| The tick hypertable is partitioned on `UID` | keeps the primary key and the existing `UID`-range reads; one chunk per security-month |
| No shared provider base class until many providers pull genuinely different data | decided 2026-09-15; an attempt (`Library/Provider`, `ResultAPI`, `ServiceAPI._listen_`) was built and stripped because none of it had a production caller |
| A block-extremes index over the tape for long-bar segments | About 5 % of a warm D1 decade (0.73 s), 2026-09-28 | New machinery for a small share; a D1 bar holds about 70 000 ticks and the scan already reads only the sides the open positions need |
| `_row_to_bar_` built lazily | Eager today | The dataset is memoised across candidates, so an eager build is paid once per scope |
| `Auto` stays the default resolution and must equal `Tick` byte for byte | a lossless optimization; since 2026-09-25 equal by construction, the gate asking the tick filter's own question of the bar's extremes (Phase 6) |
| DB-first for 8.0, no CSV interim | the backend must be touched anyway to capture equity and signals |
| Weights in the DB as bytea, with `materialize()` | self-contained and atomic with results; nets are kilobytes to megabytes |
| Reuse the Scheduler executor, plus a `Task.Arguments` column | `ExecutorAPI` and `Runner` already own spawn, heartbeat leases, PID tracking, tree-kill, retry, peak RSS, reaping and log capture. `Research.Run` **references** a `Scheduler.Run` rather than reimplementing it, exactly as `Scheduler.Run` references `Logging.Log` |
| `Library/Research` owns the domain | parameter snapshots, result series, headline metrics and `KeptAt` are research concepts the Scheduler must not learn |
| Retention as a nullable `KeptAt` on the Run row | null means eligible for the 30-day sweep, set means retained with its full series |
| `UpdatedAt` and `UpdatedBy` stay on every datapoint | part of the `DatapointAPI` contract; removing them would have to be a `Library/Database` capability |
| Conversions rebuilt from full tick streams, not H1 bars | accuracy over convenience — by cTrader's direct-pair rule at run time, validated against the cBot's stored columns on 2026-09-24 (`RULES.md`, "Currency conversion") |
| Market data comes from the Open API historical endpoint — bid and ask requested separately, merged on the millisecond, each side carried forward — fetched by one service | decided 2026-09-24: identical to the cBot's tape on thirteen windows, 2014-2025 (`RULES.md`, "Market data"). Live spots never enter the tape; they drive the live panel and 11.0 |
| A tick is time, bid and ask, in UTC, keyed `security << 42 \| epoch_ms`, with its source named | no conversion columns (rebuilt at run time), no `Mid` (derivable); `Volume` null unless a provider reports sizes, the reader counting the sides that moved; no millisecond is shared in either source, so the key holds |
| Bars are labelled by their own open, in UTC, every timeframe on the 17:00 New York clock | the platform's convention, verified against its trendbars at the switch (2026-09-25); the old tape's one-bar-early London label went with it |
| The Spotware allowance is found by measurement, not by asking | decided 2026-09-24: spaced sends, per-connection limits and a stop at the first refusal on demo (`RULES.md`, "`Library/Spotware`") |
| `Library/Formulas` stays | the xlwings Excel UDF surface is to be renovated, not deleted |
| Paper-mapping docstrings stay | `Library/Model/Method/DDPG`, `SAC`, `TD3`, `Model/Core/Noise`, `Strategy/Model`, `Strategy/Hybrid/DDPG.py` including the reward-clipping comment in `Strategy/Model/Reward.py` |
| The search space lives in a sibling `Optimization.yml` | it cannot live in `Backtesting.yml`, whose list arity is **structural** — `RiskPercentage: [1.0]` unpacks with `self._risk_percentage_, = ...` |

## Appendix C — Renumbering, 2026-09-18

Numbers on the right are the 2026-09-18 scheme; Appendix D maps them to today's.

References written before this date resolve here. Phases 0 and 1 are done and live in the Done log; Phase 0's
session checklist and five runs (0.0, 0.1) moved into 5.13 on 2026-09-23.

| Before | Now | | Before | Now |
|---|---|---|---|---|
| 1.1 extension | Phase 3, done | | 2.13 | 5.11 |
| 1.1.1 index | closed (Phase 3, done) | | 2.14 | 5.12 |
| 1.1.2 | 3.1 | | 3.0, 3.0.1, 3.0.2 | done; the `.algo` check is 5.13 |
| 1.10 reload | built (Phase 3, done); swap 3.3 | | 3.1 | 2.4 |
| 1.2, 1.4 | done with the reload | | 3.2 | 2.3; its TLS point is 2.1 (renumbered 2026-09-24) |
| 1.3 | 3.2 | | 3.3 | Appendix B |
| 1.5 | 3.5 | | 3.4 | 4.2 |
| 1.6 | 3.6 | | 3.5 | 4.1 |
| 1.7 | 3.8 | | 4.1 – 4.7 | 6.1 – 6.7 |
| 1.8 | 3.7 | | 4.8 | done (Phase 6) |
| 1.9 | 3.4 | | 5.1 – 5.7 | 7.1 – 7.7 |
| 2.0 | 5.0 | | 6.1 – 6.8 | 8.1 – 8.8 |
| 2.1 – 2.5 | 5.1 – 5.5 | | 7.1 – 7.3 | 9.1 – 9.3 |
| 2.6, 2.6.1, 2.6.3, 2.8 | done (Phase 5) | | 8.1 – 8.8 | 10.1 – 10.8 |
| 2.6.2 | 5.6 | | Phase 9 | Phase 11 |
| 2.7 | 5.7 | | Phase 10 | Phase 12 |
| 2.9 | 5.13 | | — | Phase 1 (new) |
| 2.10 | 5.9 | | | |
| 2.11 | 5.8 | | | |
| 2.12 | 5.10 | | | |

**Moved 2026-09-24**, when storage became the service's job and the cBot's writers were retired:

| Before | Now |
|---|---|
| 2.5 decision checkpoint | decided, in Phase 2's Done list |
| 2.7 parity with the cBot | 10.0; its lifecycle half became the new 2.7 |
| 3.3 swap the reloaded table | void — the tape is refilled instead (4.2-4.3) |
| 3.7 Research schema | 7.0 |
| 3.8 `Data` tier | 8.9 |
| 4.1 bulk writes | 3.3 |
| 4.2 capture service | 4.1 |
| 4.3 close the tail | 4.2 — the whole history is refilled, not only the tail |
| (new) | 3.7 the switch · 4.3 the calendar service |

## Appendix D — Renumbering, 2026-09-26

A phase was inserted for the database and engine optimization that followed Phase 3, and one appended.

| Before | After |
|---|---|
| 4.0-4.6 the market services | 5.0-5.6 |
| 4.7 drop the vendor package | 4.2 |
| Phase 5 (5.0-5.14) | Phase 6 (6.0-6.14) |
| Phases 6 to 12 and their items | Phases 7 to 13, the same item numbers under the new phase |
| — | 4.1, 4.3 and Phase 14, new |
