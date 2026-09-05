# TODOS — Quant Trading Framework

The single planning file. `RULES.md` holds conventions, traps and verified state; `ARCHITECTURE.md`
holds design depth. Nothing here belongs in either.

**Current:** finish the uncommitted-code review, commit, then write the thesis in LaTeX (lead with
the alpha decomposition). The 7-pair campaign is complete — see `Research/CAMPAIGN-7PAIR.md`.

---

## 1. Open engine defects

### 1.1 A backtest contaminates the next one in the same process — mitigated, not fixed

Running any backtest mutates the cached `DatasetAPI` in `BacktestingAPI._PRELOAD_CACHE_`, so a later
run in the same process reads corrupted state. Same candidate, same window, same fresh system object:

| evaluated | Sharpe |
|---|---|
| alone in a fresh process | **0.08825151393019111** |
| after another candidate, same process | **-0.03230736384293977** |
| after another candidate, with `_PRELOAD_CACHE_.clear()` between | **0.08825151393019111** |

The tape's visible fields are identical before and after (bar/tick counts, sums, shapes, indicator
presence), so the mutation is **inside the `BarAPI` objects**, not the frames. `copy.deepcopy` of the
tape raises, so copy-on-reuse is unavailable without first making the dataset copyable.

**Mitigation in place:** `OptimizationAPI._evaluate_` clears the cache before every candidate. Serial
and 6-worker parallel agree 0 mismatches of 24; 1/8/16 workers give identical selections. Cost is
real — 192 candidates × 2 folds went 40s → 267s serial because every candidate re-loads the tape;
8 workers bring it to 34s (7.9×), 16 saturates at 33s.

**Scope is wider than the optimizer.** Any process running more than one backtest is affected. The
goldens are safe (each runs in its own process). Learning injects its own tapes via `_tapes_` so it
is probably unaffected — **not verified**. Finding the mutation inside `BarAPI` would let the cache
be shared again and make the optimizer several times faster.

### 1.2 Currency handling in Portfolio / Sizing / Backtesting

Evidence: `Research/CAMPAIGN-7PAIR.md` §31-33.

**Verified correct — do not "fix" these:** P&L quote→account conversion is correct for every
base/quote combination under an EUR account, validated against the goldens (`account == base` uses
`1/price`: EURUSD `30.27/1.0743 = 28.1765` vs recorded `28.1760`; `account == third` uses the tick's
`QuoteConversion`, and the implied rate **varies per trade** - USDJPY 0.00707514 / 0.00707354 /
0.00698959 / 0.00704379 - proving a per-tick read rather than a constant). The tick
conversion data is accurate, EUR-denominated, zero nulls; `QuoteConv / BaseConv` equals `1/price` to
4 decimals on all seven majors.

**(a) Risk sizing ignores the quote→account conversion.** `calculate_fixed_amount_volume` computes
`amount / (sl_pips * PipSize)` — `amount` in **account** currency, the stop in **quote** currency, no
conversion. `PipSize` cancels, so contract tick metadata is not the lever. Effective risk becomes
`RiskPercentage / price`:

| pair | intended | actual |
|---|---|---|
| EURUSD | 1.0% | 0.909% |
| USDJPY | 1.0% | **0.0067%** |

On USDJPY the raw volume (133 units at 10 000 balance) falls under `VolumeMin`, which is why DDPG
could never open a position. **Raising the balance does not help** — risk stays `1/price` because
volume and balance scale together.

**(b) The USDJPY goldens cannot validate sizing — they are degenerate.** All **781** USDJPY golden
trades sit at exactly `VolumeMin` (1 distinct volume, 100% at floor) because
`calculate_normalized_volume` clamps *up*. The byte-identical match proves both engines clamp, not
that raw sizing agrees. EURUSD spans 2 000-82 000 across 61 distinct volumes and does validate it.
⇒ **Before regenerating USDJPY goldens, run the same backtest in cTrader with a much larger account
(e.g. 1 000 000 EUR) so raw volume clears the floor.** If cTrader's volumes stay tiny our engine is
faithful and must not change; if they come out ~150× larger, the fix is warranted. Re-baselining
without this test risks anchoring to the wrong reference.

**(c) Account currency must become generic.** Stored rates convert to EUR only. `quote → account` is
derivable as `1.0` when `account == quote` and `QuoteConv / BaseConv` when `account == base`, but a
fourth currency unrelated to the pair (a CHF account trading GBPJPY) needs a cross rate the tick does
not carry. Needs a designed rate source, not a bolt-on.

**(d) The exposure feature and the order sizer use different formulas.**
`DDPGObservationAPI._position_features_` normalizes exposure by `ActionAPI.maximum_volume`
(`SizingMode.Balance`), while orders are sized by `_reference_volume_` (risk-based). They disagree by
9× on EURUSD/GBPUSD and **238× on USDJPY**, so the feature clips to ±1 above `abs(action)` 0.109 /
0.112 / **0.004**. On USDJPY the agent is effectively blind to its own position and can only trade
all-in or flat. Present on every pair; tolerable at 9×, fatal at 238×. **Unify the two formulas.**

**The campaign is unaffected** — every published winner runs with active risk sizing (26-124 distinct
volumes, 0.0-4.1% of trades at the floor). USDJPY alone used a research-only compensation
(`RiskPercentage` scaled by 119.1994) restoring ~1% risk per trade, exact at window start and
drifting to ~0.8% by the end. Remove it once (a) is fixed properly.

---

## 2. DB-only inputs and outputs

Every input a model consumes and every output it produces moves from scattered files into Postgres.
Today results are CSVs under `Reports/` and the two most valuable series — the timestamped equity
curve and the per-bar signal tape — are persisted only *inside* a plot HTML. Nothing is queryable and
nothing links a run to the exact inputs that produced it. Target: **results in a `Research` schema,
weights as rows, one `Run` row tying them together**, identical CLI behavior, thin web UI on top.

⚠ `Library/Research` (this module) is distinct from the top-level `Research/` folder.

Parameters are already done — `Library/Strategy/Ladder.py` replaced the YAML tree (defaults →
provider → category → ticker → timeframe, sparse overrides in the persisted tier).

### 2.1 Decisions made — do not re-litigate

| Decision | Rationale |
|---|---|
| DB-first, no CSV interim | the backend must be touched anyway to capture equity/signals |
| Weights in the DB (bytea) with `materialize()` | self-contained and atomic with results; nets are KBs-MBs |
| Reuse the Scheduler executor; `Task.Arguments` column | `ExecutorAPI`/`Runner` already own spawn, heartbeat leases, PID tracking, tree-kill, retry, peak-RSS, reaping and log capture. `Research.Run` **references** a `Scheduler.Run` rather than reimplementing it, exactly as `Scheduler.Run` references `Logging.Log` |
| `Library/Research` owns the domain | parameter snapshots, result series, headline metrics and `KeptAt` are research concepts the Scheduler must not learn |
| Retention: a nullable `KeptAt` on the Run row | null ⇒ eligible for the 30-day sweep, set ⇒ retained with its full series. One column, one index; no second table, no status enum to keep in sync |

### 2.2 Current state to build on

`SystemAPI._report_` builds `{Orders, Positions, Trades, Deals, Net(+Benchmark)}`, then optionally
`_plot_`/`_export_`. `net.csv` = 85 metric rows × 6 value columns, label column `Statistical Metrics`; historical files drift
(`Annualised` vs `Annualized`) so **key by normalized label, never row index**.

**The two series that matter.** `PortfolioAPI.EquityTrack` returns `list[(datetime, float)]` —
timestamped, public, **never persisted** (balance is reconstructible from `trades.csv`, equity is
not). `StrategyAPI._emit_` appends `(timestamp, signal, delta, exposure, volume delta)` to
`self.Signals` but **only when `--plot` is passed**, only two strategies call it, and `Signals` resets
per `deploy()`.

**Bars** are already in the `Market` schema — do not persist per run.

### 2.3 Target design

**`Research` schema — `Library/Research`**

| File | Contents |
|---|---|
| `Run.py` | `ResearchStatus` · `ResearchRunAPI` — `UID` PK, `System`, `Status`, `Arguments`, `Command`, scope columns, `Parameters` (JSON snapshot at launch ⇒ reproducibility), `Owner` FK→Auth.User, `PID`, `ExitCode`, `Log`, timing, headline metrics |
| `Result.py` | all `RID` FK→Run **ON DELETE CASCADE**: `TradeResultAPI`, `DealResultAPI`, `PositionResultAPI`, `OrderResultAPI`, `StatisticResultAPI` (long form: RID · Report ∈ {Net, Realized, Unrealized} · Metric · 6 values), `EquityResultAPI`, `SignalResultAPI`, `EpisodeResultAPI`, `BenchmarkResultAPI`, `WeightResultAPI`, plus `ResultAPI` the writer/reader facade |
| `Model.py` | `ModelAPI` — named deployable weights registry. Parameter `Weights:` keys hold a Model UID instead of a folder path |
| `Research.py` | `ResearchAPI` manager shaped like `Library/Scheduler/Manager.py`: `command()`, `launch()`, `run()`/`runs()`, `reap()` (PID liveness + `create_time()` guard), `cancel()` (tree-kill), `delete()`, `promote()`, `materialize()`, `fingerprint()` |
| `Runner.py` | `python -m Library.Research.Runner <uid>` — Popen the CLI, persist Running+PID, wait, **reload the row (a Cancelled status must win)**, write terminal state |

`Setup/Research.py` provisions after `setup_auth` (FKs), with indexes on `Run(Status)`,
`Run(System, StartedAt)` and `(RID, Timestamp)` on the series tables. Recipe to copy:
`Library/Scheduler/Run.py`.

### 2.4 Backend contract

1. **`--rid <uid>`** on the shared base parser, threaded into `SystemAPI` like `iid`. Absent ⇒ the
   writer auto-creates its own `Run` row so console runs still enter history.
2. **At `_report_` time** call `ResultAPI` — import direction is one-way (`System` → `Research`;
   `Research` must never import `System`): `.trades/.deals/.positions/.orders`,
   `.statistics(rid, report, df)` for **all three** reports, `.equity(rid, df)` **keeping timestamps**,
   `.benchmarks`, `.headline`.
3. **Ungate the signal tape** so it records independently of `--plot`; flush via `.signals(rid, df)`.
4. **Learning**: `.episode(...)` per episode (replaces log parsing), `.manifest`, `.weights` at
   completion. Parallel seed workers need the rid in their payload. Weight loading moves to
   Model UID → `materialize()` into the local cache.
5. **Retire the CSV export** once the DB path is verified.

### 2.5 Gotchas (measured)

- **Payload size binds.** A full 11-year H1 run is ~34 MB of JSON across ~10 series (~68k points
  each). Thin to ~2k points/series (≈4 MB) before shipping to a browser; >8 MB wedges the Dash dev
  server. **Decimation must use one shared time grid** or cross-pane crosshair lookups break.
- **Series volume:** 11y H1 ≈ 68k equity + 68k signal rows per run. Fine with `(RID, Timestamp)`.
- **Cancel/finish race:** the Runner must reload before writing terminal state.
- **PID reuse:** guard reaping with `psutil.Process(pid).create_time() <= StartedAt + grace`; never
  kill on a reap, only mark.
- **Realtime cutover risk:** DB parameters + materialized weights change the deployed path. Verify on
  a Simulation run *before* archiving anything.

### 2.6 Verification plan

1. `python -m Setup.Research` → schema, tables, indexes exist.
2. Console smoke: launch → Waiting→Running→Success with result rows and non-null headline metrics;
   cancel a second run mid-flight → Cancelled and the process tree dead.
3. A real short backtest end to end: equity and signal row counts match bar counts.
4. Learning 1-seed/1-episode: episodes recorded, manifest stored, `promote()` + `materialize()`
   round-trips byte-identically in torch.
5. Full suite green.
6. **Re-run `Research/DDPG-EURUSD-H1/verify_lock.py` — the campaign must still reproduce.**

### 2.7 Reading list (in order)

1. `Library/System/System.py` - `_report_`, `_export_`, `_plot_`, `_curves_`, `_bars_`, `deploy`
2. `Library/Portfolio/Portfolio.py` - `EquityTrack` / `EquityCurve` / `_record_equity_`
3. `Library/Strategy/Strategy.py` - `_emit_`, `Recording`, `Signals`
4. `Library/Scheduler/Run.py` + `Manager.py` + `Executor.py` - datapoint, manager, spawn patterns
5. `Setup/Scheduler.py` + `Setup/Install.py` - provisioning + workflow registration
6. `Library/App/V2/Lightweight/Lightweight.py` - the consumer contract (what the UI reads)

---

## 3. Live connector + tick-only storage + generic currency

**Goals.** Backtesting, optimization and learning correct for **any** account, base and quote
currency, in netting **and** hedging. Minimise the database footprint so it scales to many more
tickers and providers. Keep Ask/Bid/Volume per tick and OHLC ticks — not just prices — for intrabar
accuracy, possibly High/Low **Ask and Bid** rather than bid-only pillars. Remove per-tick conversion
rates without losing engine speed or accuracy. Continuous live capture replacing the per-ticker
Download-strategy cBot workflow. A connector abstraction: Spotware first (one instance per broker),
later Bloomberg, Yahoo. Permanently fix P&L and sizing conversions across every offline engine, and
enable a live trading panel updating per tick.

**Measured.** `Market.Tick` is **295 GB** (244 heap + 51 index) over 1 663 564 416 rows — **157
bytes/row actual against 104 declared**, the difference being header, alignment and varchar. Ranked
levers:

| Lever | Saving | Note |
|---|---|---|
| **TimescaleDB compression** | **~250 GB** | measured **90.7%** on 1 203 593 real ticks (173 MB -> 16 MB, compress 1 s, one-day read-back of 367 389 rows in 0.03 s). Reads got *faster*. No schema change |
| drop the 4 conversion columns | 53 GB | 100% redundant — reconstructible from the pair's own price plus EURUSD, worst error **0.036%**, and the same change that makes account currency generic |
| `Tick_pkey` | 51 GB | the only index, and the sole reason `UID` exists |
| narrow types | ~23 GB | price -> int32 scaled by PipSize, Security -> int16 |
| drop `Mid` | 13 GB | derivable from Ask/Bid |

TimescaleDB 2.24.0 is available and `shared_preload_libraries` already contains `timescaledb`, but
**`CREATE EXTENSION` has never been run in `Quant`** — it is enabled in `Tests` only. Tick-only
storage then lets continuous aggregates derive every timeframe on demand, retiring the `Bar` tables
(5.9 GB) and unlocking H4/D2/W1 and arbitrary intervals.

**Decided.** `UpdatedAt`/`UpdatedBy` stay — they are part of the `DatapointAPI` contract, and
dropping them would have to be a `Library/Database` opt-out capability, not a one-off. Conversions
must be rebuilt from **full tick streams, not H1 bars** — accuracy over convenience.

**Sequence**, ordered so nothing in flight breaks: compress as-is -> continuous aggregates for bars
-> the feed-equivalence test -> live connector for capture only -> **then** the v2 schema plus the
generic currency engine. Doing the last one first is the dangerous path: it touches P&L, sizing and
the goldens simultaneously.

**Risks to what already works.**

- Reconstructed conversions will **not** be bit-identical to stored ones (float ordering), so the six
  golden reports break. Not a blocker, but it must be a **versioned** change with the goldens
  deliberately re-baselined against cTrader — never absorbed into an ordinary refactor.
- **A new cross-stream dependency**: backtesting GBPUSD would require EURUSD ticks loaded. Cache
  keys, preload sizing and the memory ceiling all need revisiting — the campaign already hit a hard
  wall here, a cold multi-worker start on an uncached pair exceeding 51 GB.
- **Hedging is unproven, not merely untested.** It is a stated goal, but everything to date ran
  `PositionMode.Netting`.

**Blocking unknown:** whether the Spotware Open API and the Download cBot deliver identical ticks.
Same broker backend, but different transport — untested, and it gates everything downstream. Needs
an app `clientId`/`clientSecret`, an OAuth `accessToken` and a `ctidTraderAccountId`; the test is to
capture one symbol for one session through both paths and compare tick counts, timestamps and
prices. Historical backfill via Open API is not viable (weeks) — keep the existing history and
capture forward.

**Before any code**, the currency algebra needs its own written design: `account`, `base`, `quote`,
and the bridge-pair graph for cases where no direct rate exists (a CHF account trading GBPJPY),
including what happens when a required bridge pair has no data for part of the window.

## 4. Persistence tiers vs OneDrive backup (brainstorm, 2026-09-03)

**The idea.** Relocate the persistence tiers under OneDrive so results and models are backed up, and
git stays free of binaries.

**Why it came up.** The seven thesis winners' weights (639 KB, 28 files) live *only* in
`<Data>/Models`, on one machine's local AppData. Verified safe from pruning — `Setup/Retention.py`
imports only `inspect_cached`/`inspect_temporary` — but "not pruned" is not "backed up".

| tier | files | size | pruned by | OneDrive verdict |
|---|---|---|---|---|
| `Temp` | 843 | 3.49 GB | retention, by age | **no** |
| `Data` | 15 645 | 3.15 GB | **never** | **yes — the good candidate** |
| `Cache` | 180 | 6.61 GB | retention, by last use | **no** |

- **`Data` — move it.** Write-once, never pruned, holds the only copy of every model and override.
- **`Temp` — do not move.** Retention deletes from it constantly and OneDrive sync locks make
  deletion unreliable — purging legacy models on 2026-09-03 raised `PermissionError [WinError 5]` on
  `rmdir` and needed readonly-clearing plus a 6-attempt backoff; one directory still could not be
  removed.
- **`Cache` — do not move.** 6.61 GB of preload tapes on the hot path, and **Files On-Demand can
  dehydrate a cached tape to a placeholder**, so a backtest's first read would block on a network
  fetch or fail — a silent, intermittent failure in the worst possible place.

**Blocking design question:** does anything assume `Data` and `Temp` share a volume? Save/Release
moves a run folder between tiers as a **rename**. Crossing volumes turns that into copy+delete —
slower and no longer atomic. Resolve this before moving anything.

Also open: whether `inspect_root()` stays derived with only `Data` redirected (a per-tier root is the
cleaner shape); a `Data/Models` retention policy of its own, since ~1 100 wave-archive models
(~110 MB) are search byproduct rather than deliverables; and a per-machine namespace if two machines
ever sync the same `Data`.

---

## 5. Queued

- **A real risk-free rate curve.** `--risk-free` is a single constant applied across Sharpe, Sortino,
  Calmar, Sterling and Jensen's alpha. A constant is wrong over 2014-2026 — it flatters every ratio in
  the ZIRP years and penalizes them after 2022. Backfill the **ECB deposit facility rate** from 2014
  (right reference for a EUR account, published daily, free), store it as a dated series beside the
  market data, and have the statistics read the rate in force at each period. Keep the flag as an
  override for reproducibility.
- **`Nr Total of Trades` disagrees with the Trades table by one, in 3 of 6 goldens.** Statistics say
  113 · 1026 · 710 where `trades.csv` has 112 · 1025 · 709 (goldens 19 · 27 · 36); the other three
  agree. The `+1` runs hold an open position at the stop date, but the open trade **is** present in
  the Trades sheet (a `Sell` with empty `ExitPrice`), so "stats count it, the table drops it" does not
  explain it. Pre-existing — the 2026-07-05 files carry the same numbers. Goldens 19 · 27 · 36 have
  Aggregated == Individual while 18 has 25 vs 37; explain both in one pass. Moves statistics
  semantics, so it needs its own focused change.
- **Profit/risk/ratio columns on `/backtesting` rows** — build as a DB read once §2 lands, not by
  re-parsing each run's stored plot HTML (user decision 2026-08-20).
- **An ordinal pane with very few points does not fill the width.** A 3-fold generalization chart leaves
  space at the right edge — Lightweight clamps bar spacing and setting it explicitly is overridden.
  Cosmetic, legible, unfixed.
- **Multi-tab `Open` depends on the browser, not the code.** Browsers permit one popup per gesture;
  Playwright's Chrome only worked with `--disable-popup-blocking`. The button opens the first in
  place, attempts the rest, and reports how many were blocked. No code-only fix.
- **Re-measure emergence at the champion's own ratios.** Phases 14-17 measured ~12.5% at
  `mirror_ratio 0.65 / ratio 0.35`; the champion is **0.50 / 0.30**.
- **UID encoding Phase 6** — DROP + repopulate Tick/Bar with the encoded scheme; gated on no
  in-flight downloads.
- **Protocol symmetry** — add 4 target-volume actions (`Increase`/`Decrease`/`Modify`) in logical
  order. Renumbering is safe because `Setup/Enum.py` regenerates the C# side; run `python -m
  Setup.Enum`, rebuild, reinstall the `.algo`, then verify a live round-trip.
- **Signal + plot refactor** — Direction+Volume signal on the Strategy base class, thresholds default
  OFF and one-sided-capable, 8 toggleable lines. Land as a no-op first, prove tests + goldens, then
  tune.
- **Report folder seconds-collision** — two exports in the same second overwrite; needs a uniqueness
  suffix.
- **Strategy state recovery** — persist Signal/Risk machine state across a Live restart
  (`SessionAPI.State` bytes, load at `deploy()`, save on `Shutdown`).
- **Realtime hardening** (audited 2026-07-02, needs a cTrader session): warmup bars double-added to
  the market buffer · `BufferAPI._worker_` flush deadlock on connect failure · transport hardening ·
  unused universe buffer · watchdog armed only on `Init` · hung-peer timeout.
- **`receive_update_security`** — parse the C# security payload to enrich `SecurityAPI`.
- **Dataframe dtype preservation + FK-aware `reorder`** — blocked: `reorder` must become FK-aware
  before the per-fetch `shrink_dtype` can go, which would remove the latent Float64→Float32 price
  downcast.
- **C# warnings** (non-breaking): 2× `CA1416`, 3× `CS0618` deprecated order APIs.
- **`Setup/Install.py` and `Setup/Task.py` both define `provision()`** — different modules, different
  jobs, no collision today. Rename one if it ever confuses.

### 5.1 Review pass 2026-09-05 — flagged, not applied

Findings from the full-codebase pass (every `Library`/`Setup`/`Script`/`Tests`/`Sources` file read). Mechanical, provably inert
cleanups were applied and staged; everything below is behavioral, design-level or golden-adjacent and waits for a decision.

**Bugs**

- **`Library/Spotware` is drift-broken — future work, leave it broken for now (user decision 2026-09-05).** `Market.py`, `Streaming.py`, `Portfolio.py` construct datapoints with pre-rename
  keyword names (`TickAPI(SecurityUID=, DateTime=, AskPrice=, BidPrice=)`, `BarAPI(SecurityUID=, TimeframeUID=, DateTime=,
  OpenBidPrice=…, TickVolume=)`, `OrderAPI(OrderID=, PositionID=…)`, `TradeAPI(TradeID=…)`, `PositionAPI(PositionID=…)`); the
  `kw_only` datapoints raise `TypeError`. `Tests/Spotware/test_Market.py:52` and `test_Portfolio.py:100-268` assert the stale
  names too. Fix = rename the kwargs to `Security/Timestamp/Ask/Bid/Volume`, `Timeframe/GapTick..CloseTick`, `UID/Position/…`
  and update both test files; prove with a live-broker session. Also there: `Execution.py` has 8 pure pass-through buy/sell
  wrappers (side unused → `partialmethod` or drop), `Streaming.py` imports inside per-message closures, 5 unused imports, and
  `Spotware.py` carries 12 docstrings outside the exemption list.

**Dead surface (0 callers outside the package `__init__`)** — delete, or keep deliberately as library offering

- `Library/Formulas/` (an xlwings Excel-UDF feature, 0 callers) **stays** — the user intends to renovate it (2026-09-05); the
  `xlwings` pin stays with it.
- `Utility/Path.py`: 28 of the 36 `traceback_*`/`inspect_*` grid (≈120 lines); `Utility/Datetime.py`: `string_to_datetime`,
  `datetime_to_iso`, `iso_to_datetime`, `weekday_shift_datetime` + 7 `<day>_shift_datetime`; `Utility/Runtime.py`: `is_local`,
  `is_service`, `find_user`, `is_python`, `is_ipython`, `is_terminal`, `is_console`, `match_env_vars`; `Utility/IO.py`:
  `is_readable`, `is_writable`, `smartlink`/`symlink`/`hardlink`; `Utility/Typing.py`: `findvariable`/`getvariable`;
  `Utility/HTML.py` (`HtmlAPI`, `htmlize`, `stylize` — only `Tests/Utility/test_HTML.py` uses them).
- `Portfolio.py`: all 16 `load_/save_/pull_/push_{accounts,orders,positions,trades}` statics (≈150 lines incl. a 25-column
  Contract JOIN repeated 3×), `calculate_statistics`, `BuyOrders`, `SellOrders`; `Portfolio/Statistic.py`
  `generate_realized_report`/`generate_unrealized_report`; `Market.py` `load_ticks`/`save_ticks`/`count_ticks`/`load_bars`/`save_bars`;
  `Universe.py` all 12 `save_*/load_*` + `pull_timeframes`.
- Convenience properties never read and not emitted by `dict()`: `Account` {IsDemo, IsHedged, IsNetted, UnrealizedReturn,
  MarginRatio, FreeMarginRatio, CreditRatio}; `Order` {IsAccepted, IsFilled, IsRejected, IsExpired, IsCancelled, ExecutionRatio,
  UnfilledVolume}; `PnL.LogPnL`; `Position.MarginUtilization`; `Trade` {DurationDays, IsClosed}; `Bar.RangeTick`; `Price.LogPrice`;
  `Tick.InvertedMid`; `Timestamp` {Sin, Cos, Epoch, Yearday, Millisecond}; `Contract` {IsSpot, IsDerivative, IsLinear,
  IsNonLinear}; `Ticker` {Dashed, Slashed, Underscored}; `Timeframe.Hours`. Plus ~25 `@overridefield` Position columns computed by
  every `dict()` and dropped by `reporting_view`.
- `Database.structured`, `ManagerAPI.delete_run`, `OptimizationAPI.trials`, `BrownianNoiseAPI`, `GeometricBrownianNoiseAPI`
  (no factory; DDPG hardcodes OU), `Sources/Indicators/Connector/Connector.cs` (the cTrader "Hello world" template) and the
  empty `Sources/Plugins/Plugin`, `Requirements.txt` (0 bytes).

**Simplifications (behavior-preserving, provable by AST body hash + suite; golden-adjacent ones need the goldens back first)**

- `Position.py`: ~40 `@overridefield` properties are four body shapes (`pnl/(Volume*unit)`, signed price-diff/unit,
  `min/max(0, x)`, `_max_equity_*_pnl_.<attr> or 0`) → one helper each. `Order`/`Position` share `_unwrap_price_`,
  `_make_price_`/`_assign_price_`, timestamp assignment and the `Session`/`Account` property pairs → a Portfolio mixin with two hooks.
- Indicators: a `BaselineAPI(TechnicalAPI)` carrying the four `filter_*/signal_*` rules + `batch` (9 classes × 4 identical
  methods, 6 identical `batch`, ≈125 lines); `MAC`/`DMAC`/`TMAC` → one `_AVERAGE_` class attribute; ROC/ATR/RV identical
  `True/True/False/False` rules; `FundamentalAPI` == `SentimentalAPI` == `TechnicalAPI`'s composite half; `MA.py` builds the
  6-way `match` twice.
- `SystemAPI._process_updates_` (190 lines, ~70 `match` arms rebuilding the same 7-key context) → `(UpdateID → (class, reader))`
  table + one `context()`; `_fitness_()` byte-identical in `LearningAPI`/`OptimizationAPI` → `BacktestingAPI`;
  `Realtime._binary_*_` are `_lower_` class constants (`Tests/System/test_Realtime.py:201` reads `_binary_security_`).
- `Strategy.py` `strategy_management`: `update_closed/stop_loss/take_profit/margin_call`, `update_modified_*`,
  `update_closed_order/filled/expired` differ only in the log line → closures. `Hybrid/DDPG.py`: `Defaults["Realtime"]` ==
  `Defaults["Learning"]` (35 lines), the 12-field state block appears in `__init__` and `_initialize_`, the optional-parameter idiom
  repeats 10×, `_hedge_(update, close)` never uses `update`.
- `Model`: `memorize`/`remember`/`_soft_update_`/`decide` scaffold copied into DDPG/SAC/TD3 agents → `AgentAPI`; SAC/TD3
  `Critic.forward` byte-identical; the whole module uses `_name` privates (RULES 3 says `_name_`); `remember()` annotates a tuple
  literal instead of `tuple[np.ndarray, ...]`.
- `Market.py`: `pull_bars` repeats an 11-column tick join 5× (provable by comparing the built SQL); `init_data`/`update_data`/
  `update_offset` list the same series 3×; `Series.py` `last()`/`tail()` share a 500-char row→`TickAPI` expression and
  `over/under/crossover/crossunder` a 5-line prelude; `Tick.py` 7 same-shape setters. `Universe.py` 11 live `pull_*/push_*` are one
  shape; `Timeframe.py` 5 comparison dunders → `total_ordering`.
- `Database.py`: the 7-line target-validation block is copied into `exists/diff/create/delete/migrate`, `executeone`/`executemany`
  share a 12-line prelude, `search` repeats an empty-catalog literal 3×, `executemany` logs a failure via `.error` then `.exception`
  (same double-log in `Service`, `Bloomberg.Streaming`, `Remote`); `Dataclass.py` `tuple/list/dict/json` forward 7 kwargs
  explicitly. `Auth`: Cloudflare `_verify_` and OIDC `authenticate` share the JWKS + `jwt.decode` block → `_claims_()`.
- Two near-identical `TrayAPI` classes (`Scheduler/Tray.py`, `Web/Service/Tray.py`); `Runner.load` and
  `SchedulerAPI._task_` both build a detached `TaskAPI` → `TaskAPI.fetch(db, uid)`; `Logging.File.FileAPI` and
  `Utility.File.FileAPI` share a name (rename the sink `FileSinkAPI`?).
- `Sources/Robots/.../Logging.cs` private consts are lower-case; `Tests/Strategy/test_Strategy.py` imports `MagicMock` inside 6
  tests, `test_Workspace.py` `json` inside 3; comments in 7 test files (`test_Sizing.py` derivations could move into the
  assertions); `Tests/Benchmark/IPC.py` is a benchmark script living under `Tests/`.

**Rules**

- Test-coverage gaps stand: `Statistic` 1 file / 1889 lines · `Scheduler` 1 / 1700 · `Model` 2 / 1654 · `Web` 3 / 3449 · `Auth`
  1 / 460 · `Indicator` 4 files / 43 modules.

---

## 6. Delivered

Kept for the findings that live nowhere else. Full detail is in git history.

**Module review — 2026-09-04.** Pre-commit pass over `Setup` · `Script` · `Scheduler` · `System` ·
`App/V2` · `Statistic` · `Web`. The findings worth keeping:
- **A star import binds `__all__` too.** `Statistic/Label.py`'s own `__all__` listed the string
  `"__all__"` — a generator had collected its own previous output as if it were a label constant. So
  `from Library.Statistic.Label import *` handed `Portfolio/Statistic.py` an `__all__` of 119 label
  names, hiding all 31 of that module's real public names. Nothing failed; the export surface was
  simply wrong.
- **A package `__init__` nobody imports through is dead weight.** App/V2's four subpackage `__init__`
  files re-exported 93 names while the parent reached past them into leaf modules. Routing the parent
  through the packages exposed a genuine cycle (`Core/Callback` ↔ `Component/Field`) that had only
  ever worked by accident of leaf-import order. `Component` was used in annotations only, so
  `TYPE_CHECKING` erased the edge. 30 of 30 nested packages elsewhere already did this correctly.
- **A per-app asset override must not repoint Dash's `assets_folder`.** Doing so silently drops the
  eight auto-injected `Scripts/*.js` and the favicon, because only stylesheets were re-added. The
  overlay — library folder stays Dash's, application folder consulted first by `asset()` and served
  at `/_application` — deletes the re-injection hack instead of extending it.
- **`Setup/Install.py` registers task paths as strings into live Scheduler rows, so moving a file is
  a database migration.** The `Scripts/`→`Script/` rename had left the `Quant Scheduler` logon task
  pointing at a path that no longer existed; it would have failed silently at the next logon. Re-run
  `python -m Setup.Install --boot` after moving anything a task points at, and check
  `Scheduler.Task.Path` resolves for all 18 rows.
- **`Tests/Web` created (26 tests) where there were none.** The layout itself is guarded: every page
  must live in the folder matching its father route, the parent may not import past its packages,
  and no Quant Cognition vocabulary may appear under `App/V2/Assets`.

**Logging refactor — 2026-07-30.** 12 files / 1031 lines → 7 modules; 0 tests → 274. Suppressed
record 271 → **128 ns**, emitted 4961 → **1188 ns**, timestamp 1990 → **234 ns**.
- **Threads lose to the GIL for local sinks.** A CPU-bound Python thread starves a concurrent writer
  253×, and a drain thread fell 93k records behind. Making the *formatter* cheap (cached-second
  timestamp, 5.5×) beat making the write asynchronous, with no queue and no backlog. Async is
  therefore a per-sink property: console and file synchronous, `StorageAPI` not.
- **stdlib cannot be the hot path.** `LogRecord.__init__` alone costs 2097 ns with every knob off, and
  `QueueHandler.prepare()` formats on the calling thread. Subclassing `logging.Logger` while bypassing
  `_log`/`makeRecord`/`handle` gives interoperation at 247 ns.
- Two real bugs fixed on the way: `with log:` returned truthy from `__exit__` and was **swallowing
  exceptions**; timestamps truncated instead of rounding (`.123` rendered as `.122`).
- **Remaining:** `StorageAPI` is unit-tested against a fake record but never exercised against a live
  Postgres run end to end; the Scheduler still writes durable rows through `ExecutorAPI._open_log_`.

**Strategy inputs and `/strategies` — 2026-08-25.** The YAML tree was retired by `Ladder.py`;
`/strategies` rebuilt as the scopes-as-columns pivot grid with editing and diff-on-apply review.

**Optimization engine — 2026-08-25.** `Library/System/Optimization.py`: DOF staging, coarse-to-fine
rounds, walk-forward selection/election, the `/optimization` surface. Search space lives in a sibling
`Optimization.yml` — it cannot live in `Backtesting.yml` because that file's list arity is
**structural** (`RiskPercentage: [1.0]` unpacks with `self._risk_percentage_, = ...`;
`BaselineMode: [Signal, Off, Signal]` unpacks as three positions). The optimization format keeps the
shape and turns each **slot** into a list of options; a slot absent from the file is not searched.
- **The trap that would silently corrupt every sweep:** `DatasetAPI` carries `IndicatorResults`.
  Learning caches them safely because *its* indicators never change between episodes. **Optimization
  varies indicator parameters**, so reusing a cached tape wholesale evaluates every candidate with the
  *first* candidate's indicators — the sweep completes, produces plausible numbers, and is
  meaningless. Rule: reuse the market-data tape, always
  `inject(replace(tape, IndicatorResults=None))`.
- Still worth adding: purging + embargo around train/test boundaries (golden 19 has an average hold of
  **537 days**, so a naive boundary leaks badly); probability of backtest overfitting / deflated
  Sharpe; one untouched holdout used exactly once; TPE or random search beyond three free parameters.

**G7 majors extension — complete.** All seven pairs trained, evaluated and published; results in
`Research/CAMPAIGN-7PAIR.md`, robustness in `Research/THESIS-ROBUSTNESS.json`. Each pair is its own
campaign folder (`Research/DDPG-<TICKER>-<TIMEFRAME>/`), so the delivered EURUSD campaign is
untouched. `robust_eval.py` reads `Security`/`Timeframe` from the model's own manifest, so a model is
always scored on the pair it was trained on.

**Environment permissions — resolved 2026-08-20.** `icacls C:\ProgramData\miniforge3 /grant
"Admin:(OI)(CI)M"` applied; `Environment.Update` has succeeded on every run since. The daemon stays
Limited, as intended.

**Groundwork landed 2026-07-31.** Output flags take an optional path; `Library/Utility/Plot.py`
deleted in favour of `Workspace.py`; the `PlotAPI` oracle frozen to literals before deletion so the
V2-port guarantee survived; dead code removed; the `Netting` *strategy* removed (⚠ `PositionMode.Netting`
is a different thing — the core position model DDPG depends on — and was kept); `Script/Cache.py`
rewritten with a 30-day horizon and honest counts (the old `ignore_errors=True` silently failed on
OneDrive and left 70 empty `__pycache__` dirs while reporting success).
⚠ Goldens regenerate with `--export`, which now defaults to temp — rebuilding them needs
`--export "Reports"` explicitly.