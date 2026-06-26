# Quant Trading Framework — Handoff

Single source of truth for the `cAlgo` repo: orientation, current state, and the active roadmap. Read this first, then `RULES.md` for conventions. (Old `plans/master-plan.md` and `SCHEDULE.md` were merged in here and removed.)

---

## 1. Orientation

- **Root:** `C:\Users\Admin\OneDrive\Documents\cAlgo`
- **`Library/`** Python core (engine, persistence, AI, Dash UI).
- **`Sources/`** C# cTrader Robots/Indicators/Plugins. The Connector cBot bridges to Python via Shared Memory (Windows named `mmap` + auto-reset Event signaling, single-slot request/response lockstep) + a binary protocol.
- **`Tests/`** pytest, mirrors `Library/` layout. Exclude `Tests/Spotware`. Suite is green (355+; the buffer suite including the new FK-race regression is green).
- **`Setup/`** unified workspace + DB setup. `conda run -n Quant python -m Setup.Main --all`. `Setup.Main --enums` regenerates `Connector/Enum.cs` (protocol/common enums) from their Python sources. `Connector/Parameter.cs` enums (stream/buffer modes…) are hand-authored cBot config, NOT generated.
- **Env:** `conda run --no-capture-output -n Quant ...` (`--no-capture-output` avoids a charmap crash on log `·`/`→` glyphs; also `PYTHONIOENCODING=utf-8`).
- **Test:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware`.
- **Build C#:** `dotnet build Sources/Robots/Connector/Connector.sln` (**the user builds/runs the Connector — the agent cannot**).
- **Git:** stage with `git add`, **never commit** (the user commits).

Both the **realtime path** (Live/Simulation/Testing, `RealtimeAPI`) and the **offline backtesting engine** (`BacktestingAPI`) are built and validated. The cBot streams updates over shared memory; Python runs the strategy through the shared `SystemAPI.deploy()` lifecycle and produces reports that reconcile with cTrader. Strategy / engine / indicators / portfolio / reporting code is byte-for-byte shared between the two paths — which is why a cTrader online report is a valid oracle for the offline engine.

---

## 2. Where we are now (2026-06-26)

The **download + realtime optimization track is DONE**; focus moves to the **offline backtesting engine** (§4) for the Optimization/Learning tracks.

**Landed this arc (all validated):**
- **Download throughput** — batch/delay protocol (sliding-FIFO + `UpdateID.Batch` + enlarged slot), Full buffering, Subscription trimming. Download is no longer the gate.
- **NNFX online streaming fix** — `NNFXStrategyAPI.Subscription = Stream.All & ~Stream.Tick` (=62). NNFX reactivity is 100% target-driven (armed `Ask/Bid Above/Below` targets + native SL/TP), so dropping the raw tick stream is bit-exact on trades while collapsing ~21.3M per-tick round-trips → daily bar closes + a few target crossings (≈55 min → ~1.5 min for a D1 year). **DDPG `Subscription` NOT yet reviewed** — an RL agent may genuinely need `Stream.Tick`; decide deliberately, don't copy NNFX.
- **Buffer FK-race fix** — the async market buffer (`Library/Database/Buffer.py`) drained bars before their anchor ticks under a fresh (truncated) table → `Bar_GapTick_fkey` violations + silently dropped bars. Fixed by snapshotting all types up front in reverse dependency order then writing forward (`_consume_`/`_dispatch_`), so ticks are always committed before any referencing bar. Regression test `Tests/Database/test_BufferIntegration.py::test_buffer_fk_race_bar_not_drained_before_its_ticks` reproduces the exact error on old code, passes on the fix.
- **Conversion policy = cTrader option ON, always.** The cTrader backtest option "Download historical data for additional symbols…" is the single source of conversion accuracy (required for the live online path; redundant under ON elsewhere). `FindConversions` (`Robot.cs`) was reverted to a clean targeted 2-candidate lookup (no `GetBars`/`GetTicks` force-load, no `StrategyType` special-case). The offline engine reads the 4 stored per-tick conversion fields, so it is option-independent and accurate.

**Data state:** `Market.Tick`/`Market.Bar` were truncated and fully re-downloaded with the option ON. Validated complete 2012-11 → 2026-06 for the two essential symbols:

| Symbol | MN1 | D1 | H1 | M1 | Ticks |
|---|---:|---:|---:|---:|---:|
| EURUSD (sec 1) | 162 | 3,638 | 84,332 | 5,003,724 | 259,137,457 |
| USDJPY (sec 6) | 162 | 3,632 | 84,188 | 4,998,555 | 300,184,910 |

- EURJPY (sec 41) Ticks still finishing (only needed as a denser conversion-validation reference; the engine reads stored USDJPY conversions).
- **Known minor gap:** MN1 (Monthly) stops at 2026-03 (missing Apr/May closed bars) — Monthly isn't used by the D1/H1/Tick goldens, non-blocking.
- **Preload disk cache** (`~/.cache/cAlgo/preload`) was **cleared** after the re-download (was 4 files / 139 MB) — backtests will cold-rebuild it from fresh DB data.

---

## 3. Offline Backtesting Engine — BUILT & VALIDATED

`Library/System/Backtesting.py` → `BacktestingAPI(SystemAPI)`: an in-process broker simulator that emits the **same `UpdateID` protocol** into the **same `deploy()` loop** as realtime, driven by DB market data instead of cTrader. Wired in `Main.py` (`_system_`); exported in `Library/System/__init__.py`; `Tests/System/test_Backtesting.py` = 41 mocked unit tests (data-independent, ~0.1s).

### 3.1 What's implemented
- **Fidelity / resolution (`--resolution`):** omit → **auto-resolution** (builds an intrabar tick ladder, descending H1→M1→Tick only on bars that can touch an armed level — `_should_descend_`/`_descend_`); or pin a finer bar/tick resolution. `_intrabar_source_` dispatches: same-tf bar extremes, tick-stream, N-tick bars, or finer bars.
- **Preload + cache:** `_load_bars_` pulls warmup+execution bars; `_preload_`/`_acquire_frames_` build the numpy tick arrays (`_tick_ts_/ask/bid` int64-µs + `float64`), conversion arrays, rung/finer frames. Two-level cache: class-level in-memory `_PRELOAD_CACHE_` **and** on-disk Parquet (`_read_cache_`/`_write_cache_` at `~/.cache/cAlgo/preload`), keyed by `_cache_signature_` with a `_data_token_` = `MarketAPI.last_tick_uid` (MAX(UID) over the bar span, O(log n) PK-index lookup) so re-downloads invalidate.
- **Feed (`_generate_`):** per boundary emits `BarClosed → Tick(open)`; intrabar path reconstructed by `_intrabar_source_`/`_descend_`/`_walk_` running SL/TP + ask/bid-target checks. Vectorized leaf event-search (`_ticks_`/`_candidate_mask_`) with `_arm_version_` gating; deque queues; NumPy/Polars only (no Pandas).
- **Fees:** `Accurate` spread/commission/swap, contract-driven (matches cTrader). Swap uses the contract's current values (no reliable historical swap-rate source — see §3.4).
- **No look-ahead** is structural (strategy only sees a bar's indicators at its `BarClosed`; fills happen on the next open tick).

### 3.2 Conversion — the 4-rate bid-side rule (validated)
Each tick stores 4 rates: `AskBaseConversion`, `BidBaseConversion`, `AskQuoteConversion`, `BidQuoteConversion`, computed at download time by the cBot's `FindConversions` and snapshotted into `CurrentTick()`.
- **Rule (proven):** cTrader expresses any foreign amount (gross/commission/swap) in the deposit currency at the **BID side** of the foreign→deposit conversion (you sell foreign / buy deposit). Engine `_conversions_`/`_tick_conversions_`/`_conversion_at_` carry all 4 rates on synth ticks.
- **`_needs_conversion_ = account ∉ {base, quote}`** gates IO: account-related symbols (e.g. EURUSD/EUR) compute from the tick's raw ask/bid (zero array IO); the **"neither" case** (e.g. USDJPY/EUR) loads the 4 stored per-tick arrays and `np.searchsorted`es them (`_conversion_at_`).
- **Symbol test matrix (EUR account)** — each needs its conversion pairs in the universe + a fresh cTrader golden:

  | Symbol | Account vs pair | base→EUR | quote→EUR | Validates |
  |---|---|---|---|---|
  | EURUSD ✅ | base | 1.0 | 1/Ask (own) | baseline (golden) |
  | USDJPY | **neither** | EURUSD | EURJPY | USD + JPY legs (data now present) |
  | EURJPY | base | 1.0 | 1/Ask (own, JPY) | JPY pip scaling |
  | GBPJPY | **neither** (purest) | EURGBP | EURJPY | no EUR-direct leg |

  The "neither" path is **implemented but not yet golden-validated** — USDJPY data is now downloaded, so a USDJPY golden (§5) is the next validation.

### 3.3 Performance — current numbers
Profiled with logging silenced (`LoggingAPI.set_verbose_level(Silent)`; default class level is `Silent`). After the `last_tick_uid` token (warm-run DB token check 1.9s → O(log n)): **warm engine ~1.09s** for a D1 year; FINAL TIMINGS D1-2023 Auto ~0.142s exec. Extrapolation: 10y Daily ≈ 1–2 s exec, 10y Hourly ≈ 1.5–3 min exec (data local); cold preload ~7–10 min one-time, warm Parquet ~10–25 s. Whole-process wall-clock for a 1y run is ~3 s dominated by conda+Python startup (negligible at 10y).

### 3.4 Accuracy floor (documented, data-bound — NOT engine bugs)
- **Sub-pip intrabar exit residual:** bar/target data can't recover ms-precise SL/TP exit prices; tick-resolution mode closes it. D1-2023 Gross ≈195.68 vs golden 195.56 (+0.12) is this, not a conversion error.
- **Swap residual (~0.5% on 1y):** per-deal diagnosis showed overnight counts/DST correct; the gap is time-varying historical swap **rates** (we apply the contract's current SwapLong/SwapShort). Closing it needs a cTrader historical swap-rate schedule (a data capture).

### 3.5 Engine mechanics reference (mirror `Robot.cs`)
- **Event order:** `OnBarClosed → OnTick(open) → OnBarOpened`. cBot keeps one accumulating `xBar`; on `OnBarClosed` sets volume, sends `BarClosed`, then `GapTick = CloseTick`, `Timestamp = lastBar.OpenTime`.
- **Pop order:** `SystemAPI._process_updates_` pops sub-objects in a fixed order (e.g. `OpenedBuyPosition` pops bar then position; closes pop a position+trade pair). `receive_update_*` must match exactly. Bars carry 5 anchor ticks (Gap/Open/High/Low/Close); `System._receive_update_bar_` queues the 5 ticks then the bar.
- **UID collisions:** simulated `_pids_`/`_tids_` use negative space (`count(start=-1, step=-1)`).
- **Reference files:** `Realtime.py` (sibling SystemAPI), `System.py` (`deploy`/`_process_updates_`), `Robot.cs` (broker behavior), `Market/Series.py`+`Market/Market.py` (`init_data`/`update_data`, no-look-ahead), `Market/Bar.py`+`Tick.py`, `Portfolio/*`, `Universe/*`.

---

## 4. CURRENT FOCUS — Offline engine optimization (prioritized)

Goal: drive down per-run cost for the Optimization/Learning tracks (many runs over the same data) while staying byte-identical to the goldens. **Every item MUST be golden-validated before commit.** Profile first (cProfile cumulative+tottime, targeted micro-benchmarks) — measure, don't guess.

**Tier 1 — biggest engine wins (per-bar hot path):**
- **A · Numpy-ize the per-bar feed + indicators.** Dominant remaining cost is per-bar **Polars churn**: every bar builds 1-row `pl.DataFrame`s for the feed and for each indicator (`ATR`/`KAMA`/`MACD`/`HMA`/`SMA` wrap a *scalar* in a 1-row frame and `vstack`). Replace `SeriesAPI` per-bar storage + indicators' `stream()` with numpy/scalar incremental; keep Polars for warmup/IO/batch. Expected **2–4× walk** + fixes the chunk-accumulation pathology at 10y-Hourly (per-bar `vstack`/`extend` accrues ~60k Polars chunks). Risk: touches accuracy-critical math → validate bit-for-bit. **Biggest win; do early.**
- **Bar/Tick construction at load (`_row_to_bar_`).** `_load_bars_` builds a `BarAPI` + 5 `TickAPI` dataclasses per execution bar — ~500k object builds for 10y-Hourly (the "construction machinery is the real target" from prior profiling). Move the feed onto array-backed bar access (the walk mostly needs prices+timestamps, not full dataclasses); keep dataclasses only where the protocol/reporting needs them.

**Tier 2 — multi-run / scale enabler:**
- **B · Pull-once shared injectable dataset.** Freeze everything `_load_bars_`+`_preload_` produce into a `BacktestDataset` (`bars`/`warmup_frame`/`tick_ts/ask/bid`/`tick_conversions`/`rung_frames`/`ladder`/`finer_frame`). Add optional `dataset=` to `BacktestingAPI`; in `_connect_`, if injected → assign + skip the DB load, else load as today and expose `.Dataset`. Optimization loads once, injects across N runs (and once per `ProcessPoolExecutor` worker). Default (no-dataset) path stays byte-identical → golden-safe by construction. Market data is read-only during a run (only `_bars_.pop(0)` mutates, at load — moves into dataset construction). The class-level `_PRELOAD_CACHE_` already caches the FRAMES across runs; B extends this to the `BarAPI` list + warmup frame and makes it explicitly injectable + cross-process.

**Tier 3 — startup / smaller / fallback:**
- **DB connection startup (~0.6 s).** `_connect_` + universe/contract/market loads open ~10 PG connections at startup. Pool/reuse one connection; subsumes `_load_bars_` re-pulling per run for multi-run.
- **Conversion `_conversion_at_` per-tick `searchsorted` ("neither" path only, e.g. USDJPY).** Batch/vectorize conversions over a bar's tick slice instead of per-synth-tick searchsorted.
- **C · Targeted Polars de-churn (fallback if A is too risky).** Periodic `rechunk` to bound chunk growth + avoid the worst 1-row frames in `_sub_rows_`/`_finer_bars_` `iter_rows`. Partial walk win + scaling fix.

**Accuracy (optional, data-bound):** tick-resolution exact exits (closes the sub-pip residual); historical swap-rate schedule capture (closes the swap residual). See §3.4.

---

## 5. Fresh golden reports to produce (user runs these)

The old goldens are stale — swap rates drifted during the download work. Re-run NNFX as **online cTrader Backtests** (Simulation through the Connector cBot) to mint fresh ground-truth fingerprints, then the offline engine is brute-forced apples-to-apples against them.

**Common settings for every run:** Strategy **NNFX** · Account **EUR**, balance **10,000** · cTrader conversion option **ON (ticked)** · cBot **Report = ON** and **Export = ON** · cTrader data = **Tick data from server (most accurate)** so the golden is ground truth. Each run writes `Reports/<timestamp> <iid>/` (`report.html` + deals/net/orders/positions/trades.csv).

**EURUSD — essential (re-pins the 3 existing oracles):**

| # | Symbol | Timeframe | Window | Validates |
|---|---|---|---|---|
| 1 | EURUSD | Daily (D1) | 2023-01-01 → 2024-01-01 | primary golden (1y) |
| 2 | EURUSD | Daily (D1) | 2022-01-01 → 2025-01-01 | 3y (swap-DST + gap exits) |
| 3 | EURUSD | Hour (H1) | 2023-01-01 → 2024-01-01 | intraday density |

**USDJPY — recommended (first validation of the "neither" cross-pair conversion path):**

| # | Symbol | Timeframe | Window | Validates |
|---|---|---|---|---|
| 4 | USDJPY | Daily (D1) | 2023-01-01 → 2024-01-01 | JPY + USD legs, JPY pip scaling |
| 5 | USDJPY | Hour (H1) | 2023-01-01 → 2024-01-01 | intraday "neither" path |
| 6 | USDJPY | Daily (D1) | 2022-01-01 → 2025-01-01 | 3y cross-account |

Minimum to proceed: #1–#3 (EURUSD) + #4 (USDJPY). Once the reports exist, hand over the folder names and the new fingerprints become the pinned goldens (replacing the 2026-06-07/08 set); the engine validation must reproduce all of them.

---

## 6. Backlog
- **Optimization** — uncomment `OptimizationAPI` in `Main.py` + export; depends on §4-B (shared dataset) for throughput.
- **Learning** — uncomment `LearningAPI` in `Main.py` + export; depends on `BacktestingAPI` + §4-B. Review DDPG `Subscription` (may need `Stream.Tick`).
- **Phase G — Strategy state recovery:** persist Signal/Risk machine state on Live restart. *Sketch:* `State: Union[bytes, None]` on `SessionAPI` (`pl.Binary()`); `EngineAPI.State` maps machine→state name as JSON bytes; loaded at `deploy()` start, saved on `UpdateID.Shutdown`.
- **Wire up `receive_update_security`** — parse C# security data to enrich `SecurityAPI` (pip size, commission). Sent but codec not consumed.
- **Timeout watchdog** — configurable hung-peer timeout (e.g. 30 s → teardown). Current watchdog only detects peer-death via PID.
- **`Schedule` orchestrator (future project, was `SCHEDULE.md`):** a Prefect-style task orchestrator integrated into the framework. New `Schedule` DB schema — `Workflow`, `Task` (Python script + cron), `Run` (status: Resting→Waiting→Approving→Running→Reviewing→Success/Failure, with duration/memory/message), plus `WorkflowTask` (sequence + auto-approve), `Dependency` (Finish-to-Start / Success-to-Start task graph), `Parameter` (per-run JSONB payload). Phases: (1) `Schedule` schema + `ScheduleDatabaseAPI`; (2) `SchedulerService` (cron monitor) + `WorkerService` (subprocess runner); (3) dependency-tree transition engine; (4) Dash dashboard with manual Approve/Review gates.
- **Completed refactors (was `plans/master-plan.md`):** Market (DB-aligned `TickAPI`/`BarAPI` + recursive `SeriesAPI`), Indicators (TA-lib dropped, modular `Technical/Fundamental/Sentimental`, O(1) incremental SMA/MACD, dual-mode batch/stream tests), Portfolio (`SizingAPI`/`StatisticAPI` extracted, symmetric Account/Order/Position/Trade, unified `.dict()`).

---

## 7. Known issues (non-blocking)
- **`--profile` not wired to the cBot UI** — invoke the Python CLI with `--profile` to dump `.pstat`. It wraps only the Python `run` (blind to the C#/cTrader side).
- **C# platform warnings** — 2× `CA1416` (`MemoryMappedFile.CreateOrOpen`, Windows-only); 3× `CS0618` (deprecated `PlaceStopOrder`/`PlaceLimitOrder`/`PlaceStopLimitOrder`). Non-breaking.
- **Logging is custom (not stdlib):** `logging.disable()` does nothing; silence via `LoggingAPI` (e.g. `HandlerLoggingAPI().console.set_verbose_level(VerboseLevel.Silent)`).
