# TODOS — Quant Trading Framework

The single planning file. `RULES.md` holds conventions and verified state only; nothing here belongs
there. Ordered — item 1 is current.

---

## 1. Logging refactor ← CURRENT

Deep refactor + optimization of `Library/Logging`. Declared by the user 2026-07-14 as "the silent
killer"; picked up now because it is self-contained and fast.

**Measured problems**

- **Buffer-until-exit design.** `FileLoggingAPI`/`BufferLoggingAPI` accumulate into a class-level RAM
  deque drained only at `__exit__`. Patched with an `is_entered()` guard in `FileLoggingAPI.output`
  for the never-exiting daemon, but the architecture stands — a week-long run buffers everything.
- **Class-level state everywhere.** Verbose levels, tags, buffers and enter/exit flags are all
  classmethod/class-attribute (per-subclass singletons), so instances share state. Confusing
  double-negative flags (`enable_entering` sets the flag False). `HandlerLoggingAPI` fans out to four
  handler instances whose calls all hit class state.
- **Hot-path cost ~0.3 s per H1-year** at Debug console verbosity. Every `log()` takes two locks
  (global + class) even when the message is filtered out, and `build()` assembles the string per call.
- **V1 couples to the buffering.** `Library/App/V1/App.py` polls `web.stream()` on an *un-entered*
  `WebLoggingAPI`; any refactor must preserve poll-drain semantics or migrate that consumer.

**Constraints** — preserve the RULES §LOGGING conventions exactly (message format, ` · ` separators,
state-transition arrows, Debug/Info split, tags via `type(self).__name__`, and the symmetric
`log.console` / `log.file` verbose declarations in entry points).

**Approach** — profile first (`cProfile` cumulative + tottime on an H1 year) to confirm the 0.3 s/y
figure and locate the real cost before touching the architecture.

---

## 2. DB-only inputs and outputs

Every input a model consumes and every output it produces moves from scattered files into Postgres.
Today parameters are a YAML tree in `Library/Parameter/`, weights are torch folders under
`~/.cache/cAlgo/models` (plus curated copies in `Library/Parameter/`), and results are CSVs under
`Reports/`. Nothing is queryable, nothing links a run to the exact inputs that produced it, and the
two most valuable series — the timestamped equity curve and the per-bar signal tape — are only
persisted *inside* a plot HTML. Target: **parameters in a `Parameter` schema, results in a `Research`
schema, weights as rows, one `Run` row tying them together**, identical CLI behavior, thin web UI on
top.

⚠ `Library/Research` (this module) is distinct from the top-level `Research/` folder (frozen campaign
method and tooling).

### 2.1 Decisions already made — do not re-litigate

| Decision | Rationale |
|---|---|
| DB-first, no CSV interim | the backend must be touched anyway to capture equity/signals; writing to Postgres instead is barely extra work |
| Weights in the DB (bytea) with a `materialize()` export | self-contained and atomic with results; nets are KBs–MBs. Realtime/cTrader gets a materialize step |
| Full DB-only, Realtime included | one source of truth; the `Library/Parameter` file tree is archived out |
| A dedicated `Library/Research` module, not the Scheduler | Scheduler `Task` carries a bare file path with **no arguments column** (`ExecutorAPI._command_` → `[sys.executable, path]`), so it cannot express `python -m Library.System.Main Backtesting --provider ... --start ...` |
| Runs launch without a daemon | `ManagerAPI.run_task` already proves the pattern; only cron/supervision needs the daemon |

### 2.2 Current state — verified facts to build on

**Inputs.** `Library/Parameter/Parameter.py` has `ParameterAPI` (filesystem navigator —
`__getattr__`/`__getitem__` walk directories, leaf `.yml` → `Parameter`) and `Parameter` (nested dict
whose `_save_` dumps YAML at the root). Consumers use exactly one shape:
`Library/System/Main.py:277` → `parameterize[provider.UID][category.UID][ticker.UID][args.timeframe]`,
then `.Backtesting[strategy]` / `.Learning[strategy]` / `.Realtime[strategy]`. **That is the seam** —
a DB-backed `ParameterAPI` with an identical access surface converts every consumer untouched.
Weights: `DDPGStrategyAPI._DEFAULT_WEIGHTS_ = ~/.cache/cAlgo/models`;
`LearningAPI._weights_directory_()` → `<root>/<Security UID> <Timeframe UID> <Strategy>`; manifest
written as `<Strategy> Manifest.json` beside it; deployed weights referenced from YAML via
`SignalManagement.Weights`.

**Outputs.** `SystemAPI._report_` (`System.py:346`) builds `{Orders, Positions, Trades, Deals,
Net(+Benchmark)}`, then optionally `_plot_` and `_export_` (CSVs in
`Reports/<YYYY-MM-DD HH-MM-SS> <ident>/`). `net.csv` = 85 metric rows × 6 value columns, label column
`Statistical Metrics`; historical files drift (`Annualised` vs `Annualized`) so **key by normalized
label, never row index**. `Library/Portfolio/Statistic.py` also exposes
`generate_realized_report`/`generate_unrealized_report`; only Net is exported today.

**The two series that matter.** `PortfolioAPI.EquityTrack` (`Portfolio.py:544`) returns
`list[(datetime, float)]` — timestamped, public, **never persisted** (balance is reconstructible from
`trades.csv`, equity is not). `StrategyAPI._emit_` appends `(timestamp, signal, delta, exposure,
volume delta)` to `self.Signals`, but **only when `--plot` is passed** (`System.deploy()` line 684
sets `Recording = self._plotting_`), only **two** strategies call it (`Rule/Trend.py:68`,
`Hybrid/DDPG.py:431`), and `Signals` resets per `deploy()`.

**Bars** are already in the `Market` schema — do not persist per run.

### 2.3 Target design

**`Parameter` schema.** Table `Parameter.Parameter`, composite PK
(`Provider`, `Category`, `Ticker`, `Timeframe`, `File`) + `Content` (JSON of the YAML dict) +
`UpdatedAt`/`UpdatedBy`; `File` ∈ {Backtesting, Realtime, Learning, Optimization}. Refactor
`Parameter._save_` to delegate to an injected saver; `ParameterAPI(database="Quant")` becomes the
default navigator with the **same** walk, keeping `ParameterAPI(path=...)` for migration and tests.
`Setup/Parameter.py` creates the schema then upserts every `Library/Parameter/**/*.yml` idempotently,
registered in the `Setup` workflow after `Setup.Scheduler`. **A parity test is mandatory** —
identical structure for every YAML, and write-back must preserve nested-update semantics.

**`Research` schema — `Library/Research`**

| File | Contents |
|---|---|
| `Run.py` | `ResearchStatus` (Waiting/Running/Success/Failure/Cancelled) · `ResearchRunAPI` — `UID` PK, `System`, `Status`, `Arguments` (JSON CLI flags), `Command`, `Strategy`/`Provider`/`Ticker`/`Timeframe`/`Start`/`Stop`, `Parameters` (JSON snapshot of resolved parameters at launch ⇒ full reproducibility), `Owner` FK→Auth.User, `PID`, `ExitCode`, `Log`, `StartedAt`/`StoppedAt`/`Duration`, headline metrics (`Trades`, `NetPnL`, `NetReturn`, `AnnualizedReturn`, `WinRate`, `ProfitFactor`, `Sharpe`, `MaxDrawdown`) |
| `Result.py` | all `RID` FK→Run **ON DELETE CASCADE**: `TradeResultAPI`, `DealResultAPI`, `PositionResultAPI`, `OrderResultAPI`, `StatisticResultAPI` (long form: RID · Report ∈ {Net, Realized, Unrealized} · Metric · 6 values), `EquityResultAPI` (RID, Timestamp, Equity, Balance), `SignalResultAPI` (RID, Timestamp, Signal, Delta, Exposure, VolumeDelta), `EpisodeResultAPI` (RID, Seed, Fold, Episode, Train, Selection), `BenchmarkResultAPI`, `WeightResultAPI` (RID, Path, Content `pl.Binary`), plus **`ResultAPI`** the writer/reader facade |
| `Model.py` | `ModelAPI` — named deployable weights registry (`UID` name PK, `RID` FK, Strategy/Provider/Ticker/Timeframe, Description). Parameter `Weights:` keys hold a Model UID instead of a folder path |
| `Research.py` | `ResearchAPI` manager shaped like `Library/Scheduler/Manager.py`: `command()`, `launch()`, `run()`/`runs()`, `reap()` (PID liveness + `create_time()` guard), `cancel()` (tree-kill), `delete()`, `promote()`, `materialize()`, `fingerprint()` |
| `Runner.py` | `python -m Library.Research.Runner <uid>` — Popen the CLI with stdout→log, persist Running+PID+StartedAt, wait, **reload the row (a Cancelled status must win)**, write terminal state |

`Setup/Research.py` provisions after `setup_auth` (FKs), with indexes on `Run(Status)`,
`Run(System, StartedAt)` and `(RID, Timestamp)` on the series tables. Datapoint recipe to copy:
`Library/Scheduler/Run.py`.

### 2.4 Backend contract

1. **`--rid <uid>`** on the shared base parser in `Library/System/Main.py`, threaded into `SystemAPI`
   like `iid`. Absent (console runs) ⇒ the writer auto-creates its own `Run` row so console runs
   still enter history.
2. `ParameterAPI()` construction flips to DB mode (automatic once 2.3 lands).
3. **At `_report_` time** call `Library.Research.ResultAPI` — import direction is one-way
   (`System` → `Research`; `Research` must never import `System`): `.trades/.deals/.positions/.orders`,
   `.statistics(rid, report, df)` for **all three** reports, `.equity(rid, df)` from `EquityTrack`
   **keeping timestamps**, `.benchmarks(rid, series)`, `.headline(rid, metrics)`.
4. **Ungate the signal tape** (`System.deploy()` line 684) so it records independently of `--plot`,
   flush via `.signals(rid, df)`. Consider emitting from `NNFX`/`Netting` so every strategy has one.
5. **Learning**: `.episode(...)` per episode (replaces log parsing), `.manifest(rid, dict)`,
   `.weights(rid, dir)` at completion. Parallel seed workers need the rid in their payload. Weight
   loading moves to Model UID → `materialize()` into the local cache (touches
   `DDPGStrategyAPI._weights_path_`).
6. **Retire the CSV export** (and optionally the fat plot HTML) once the DB path is verified.
7. **Optimization** returns `None` from `_system_` and exits 0 silently; a warning + nonzero exit
   would help the UI until `OptimizationAPI` lands.

### 2.5 Gotchas (measured)

- **Payload size binds.** A full 11-year H1 run is ~34 MB of JSON across ~10 series (~68k points
  each). Thin to ~2k points/series (≈4 MB) before shipping to a browser; >8 MB wedges the Dash dev
  server. **Decimation must use one shared time grid** across all series or cross-pane crosshair
  lookups break (series start at different times because candles include warmup bars).
- `PlotAPI` emits the **full marker set twice** (candle + close series), doubling the largest part of
  the payload — fix at the source.
- **Series volume:** 11y H1 ≈ 68k equity + 68k signal rows per run. Fine with `(RID, Timestamp)`.
- **Cancel/finish race:** the Runner must reload before writing terminal state.
- **PID reuse:** guard reaping with `psutil.Process(pid).create_time() <= StartedAt + grace`; never
  kill on a reap, only mark.
- **Realtime cutover risk:** DB parameters + materialized weights change the deployed path. Verify on
  a Simulation run *before* archiving the YAML tree.

### 2.6 Verification plan

1. `python -m Setup.Parameter` → DB navigator structurally identical to every YAML; write-back parity passes.
2. `python -m Setup.Research` → schema, tables, indexes exist.
3. Console smoke: `ResearchAPI.launch("Backtesting", {...EURUSD Daily Trend 2023...})` →
   Waiting→Running→Success with results rows and non-null headline metrics; cancel a second run
   mid-flight → Cancelled and the process tree dead.
4. A real short backtest end to end: CLI reads DB parameters, writes DB results; equity and signal row
   counts match bar counts.
5. Learning 1-seed/1-episode: episodes recorded, manifest stored, `promote()` + `materialize()`
   round-trips byte-identically in torch.
6. Full suite green, **then** archive the YAML tree and weight folders out of `Library/Parameter`.
7. **Re-run `Research/DDPG-EURUSD-H1/verify_lock.py` — the campaign must still reproduce.**

### 2.7 Reading list (in order)

1. `Library/System/System.py` — `_report_`, `_export_`, `_plot_`, `_curves_`, `_bars_`, `_markers_`, `deploy`
2. `Library/Portfolio/Portfolio.py` — `EquityTrack` / `EquityCurve` / `_record_equity_`
3. `Library/Strategy/Strategy.py` — `_emit_`, `Recording`, `Signals`
4. `Library/Parameter/Parameter.py` — the navigator seam to preserve
5. `Library/Scheduler/Run.py` + `Manager.py` + `Executor.py` — datapoint, manager, spawn patterns
6. `Setup/Scheduler.py` + `Setup/Install.py` — provisioning + workflow registration
7. `Library/App/V2/Lightweight.py` — the consumer contract (what the UI reads)

**Phase A is already delivered** (`Library/App/V2/Lightweight.py` + assets): TradingView-backed charts
and a virtualized grid, verified live against a real DDPG payload. Its data shapes are the target
shapes for 2.3 — matching them makes the UI a thin read layer. Phase C afterwards is three page
families (Backtesting · Optimization · Learning), each Launch → Runs → Analysis.

---

## 3. G7 majors extension

Retrain the locked method on all seven Forex majors (professor's ask, no deadline).
Method: `Research/DDPG-EURUSD-H1/REPRODUCE.md`.

**Blocked on data — only 2 of 7 are ready.**

| pair | H1 bars | status |
|---|---|---|
| EURUSD | 84 332 (2012-11-11 → 2026-06-25) | ready |
| USDJPY | 84 188 (2012-11-11 → 2026-06-25) | ready |
| GBPUSD · AUDUSD · USDCAD · USDCHF · NZDUSD | none | **download required** |

Steps per new pair: Universe ticker/security/contract rows → `Download` ticks + H1 bars →
parameter tree (`<PAIR>/Hour/Learning.yml`, friendly key `Hour` never `H1`) → re-check commission and
swap (JPY pip scaling differs) → train ~30 min/pair at the locked protocol.

---

## 4. Blocked on the user (one command)

```
icacls C:\ProgramData\miniforge3 /grant "Admin:(OI)(CI)M"
```

`C:\ProgramData\miniforge3` grants Users RX only and the `Quant Scheduler` logon task runs
**Limited**, so daemon-spawned conda/mamba env updates cannot write — this is why
`Environment.Update` fails nightly. Keep the task Limited; never elevate the daemon tree. Claude is
classifier-blocked from running `icacls`.

---

## 5. Queued

- **Re-measure emergence at the champion's own ratios.** Phases 14-17 measured ~12.5% at
  `mirror_ratio 0.65 / ratio 0.35`; the champion is **0.50 / 0.30**.
- **UID encoding Phase 6** — DROP + repopulate Tick/Bar with the encoded scheme; gated on no
  in-flight downloads. Everything else shipped green.
- **Protocol symmetry** — add 4 target-volume actions (`Increase`/`Decrease`/`Modify`) in logical
  order. Renumbering is safe because `Setup/Enum.py` regenerates the C# side; run `python -m
  Setup.Enum` after ANY enum edit, rebuild, reinstall the `.algo`, then verify a live round-trip —
  wire-ID mismatches mis-decode silently.
- **Signal + plot refactor** — Direction+Volume signal on the Strategy base class, thresholds default
  OFF and one-sided-capable, 8 toggleable lines. Land as a no-op first, prove 651 + goldens, then tune.
- **Optimization refactor** — rebuild `OptimizationAPI` on the tape seam (`extract()` once →
  `inject()` across N parameter runs/workers).
- **Report folder seconds-collision** — two exports in the same second overwrite; needs a uniqueness
  suffix.
- **Strategy state recovery** — persist Signal/Risk machine state across a Live restart
  (`SessionAPI.State` bytes, load at `deploy()`, save on `Shutdown`).
- **Realtime hardening** (audited 2026-07-02, needs a cTrader session): warmup bars double-added to
  the market buffer · `BufferAPI._worker_` flush deadlock on connect failure · transport hardening
  (handle validation, length bounds, batch offset guards) · unused universe buffer · watchdog armed
  only on `Init` · hung-peer timeout (the current watchdog only detects peer death by PID).
- **`receive_update_security`** — parse the C# security payload to enrich `SecurityAPI` (pip size,
  commission).
- **Dataframe dtype preservation + FK-aware `reorder`** — blocked: `reorder` must become FK-aware
  before the per-fetch `shrink_dtype` can go, which would remove the latent Float64→Float32 price
  downcast.
- **C# warnings** (non-breaking): 2× `CA1416`, 3× `CS0618` deprecated order APIs. `--profile` wraps
  only the Python side.
