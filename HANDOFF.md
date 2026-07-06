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

## 2. Where we are now (2026-06-29)

The **download + realtime tracks AND the offline backtesting engine are DONE** (engine validated + optimized + closed, §4) and committed; a round of `Library/Utility` consolidation also landed (shared `Math`/`Datetime` helpers + named `EPOCH`/`MILLISECOND`/`MICROSECOND` constants, suite 370 green). **Focus moves to the offline Learning system** — a DRL trainer for model-based / hybrid strategies, designed in §6 — built on the validated `BacktestingAPI` + its `dataset=` tape.

**Landed this arc (all validated):**
- **Offline engine validated + optimized + closed (§4).** Reproduces all 6 fresh goldens at the data-bound floor (counts bit-exact, USDJPY "neither" path Daily ≈ bit-exact). OPT-A caches `_load_bars_` across runs (repeat-run init 1.1s → 0.02s); the preloaded market is one frozen `DatasetAPI` tape with `extract()`/`inject()` (`dataset=`) as the load-once / inject-across-N-runs seam. Measured 10y per-pass: D1 3.2s, H1 25.4s. Suite 363 green.
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

## 4. Offline Backtesting Engine — VALIDATED, OPTIMIZED, CLOSED (2026-06-26)

The engine is **closed**: validated against the 6 fresh goldens and optimized for the Optimization/Learning multi-run path. Full suite **363 green**. Library edits unstaged for user commit.

**Validation (Auto resolution; all 6 goldens reproduced at the data-bound floor; trade counts bit-exact):**

| Run | count | NET off / gold | dev | note |
|---|---|---|---|---|
| EURUSD D1 2023 | 25/25 | 75.28 / 75.55 | −0.35% | floor |
| EURUSD D1 2022-25 | 76/76 | −136.54 / −127.33 | +7.24% | all swap (ΔGross −0.22) |
| EURUSD H1 2023 | 696/696 | −2837.11 / −2936.65 | −3.39% | hi-freq sub-pip TSL + cent-round |
| USDJPY D1 2023 | 14/14 | 47.07 / 47.13 | −0.12% | "neither" path ≈ bit-exact |
| USDJPY H1 2023 | 709/709 | −57.42 / −61.04 | −5.92% | small denominator |
| USDJPY D1 2022-25 | 58/58 | 76.84 / 76.74 | +0.13% | "neither" 3y ≈ bit-exact |

Residuals are the documented data-bound floor (swap historical-rate/DST, commission cent-rounding, sub-pip intrabar exits), NOT engine error. The USDJPY "neither" cross-pair conversion path is now golden-validated (Daily ≈ bit-exact). Frozen offline exports double as a bit-exact guard for future changes.

**Measured 10y performance (EURUSD, Auto, dense 2015-2025, 209M ticks):**

| | bars | one-time cold setup | **warm per-pass** (DRL multiplier) |
|---|---|---|---|
| D1 | 2,634 | ~12 min (preload 675s + cache-write 36s) | **3.2s** (init 0.02 + exec 3.03 + final 0.22) |
| H1 | 61,940 | ~15.5 min (preload 856s + cache-write 49s) | **25.4s** (init 0.02 + exec 23.5 + final 1.9) |

DRL total = setup(once) + N × per-pass. At 1000 passes/fold: D1 ~53 min, H1 ~7.1 h (× walk-forward folds). Skip the full report during training → `final` ≈ 0.

**Optimizations LANDED (bit-exact, suite green):**
- **OPT-A — `_load_bars_` cached across runs.** Routed the bar pull + BarAPI/TickAPI construction through the in-memory `_PRELOAD_CACHE_` (keyed value = one `DatasetAPI` tape). Repeat-run **init 1.1s → 0.02s** (~50-75×); at 10y H1 it ~halves per-pass (~52s → 25s). Read-only data → golden-safe; all 6 outputs byte-identical.
- **Tier2-B — the tape: `extract()` / `inject()` + `dataset=` (`DatasetAPI`).** All preloaded, decision-independent market data lives in ONE frozen `DatasetAPI` held as `self._dataset_` (fields: `WarmupBars`, `ExecutionBars`, `TickTimestamps`/`Asks`/`Bids`, `TickConversions`, `IntraLevels`, `IntraBars`). `extract() -> DatasetAPI` exports it; `inject(dataset)` (or `BacktestingAPI(..., dataset=...)`) supplies it; `_preload_` uses the injected tape (skips the DB) else builds one via `_build_dataset_` and caches it. The Auto descent ladder and the fixed finer-resolution frame are unified into `IntraLevels`/`IntraBars` (Auto = the multi-level case). Engine reads through `self._dataset_.X` (no flat attrs). Default (no-dataset) path byte-identical; round-trips `inject(extract())`. This is the seam Optimization/Learning use to extract once + inject across N runs/folds (and per `ProcessPoolExecutor` worker).

**Engine-optimization program — code-level deep dive done 2026-07-01; decision: build (b) then (a).** Four independent readers converged on ONE root cause: the per-bar hot loop **rebuilds + re-reads growing Polars DataFrames to feed values the math already holds as scalars.** Measured per-bar shares on the golden H1 pass: indicator `Technical.update_data`+`_indicator_` reads **~43%**, `Market.update_data` (Transform.Market: `bar.dict(flatten=True)` → `pl.DataFrame([dict])` → `extend` + re-init 7 child Series) **~22%**, Bar/Tick construction ~10%. **Honest framing:** the engine is NOT the DRL *training* bottleneck (CPU-only torch NN dominates → engine cuts buy only ~2-3% there); it IS ~100% of every DRL validation/test pass and of NNFX/tick/optimization runs → those get the full win. So this speeds the feature/reward iteration loop, not training itself.
- **(b) Precompute + inject the fixed indicator/market series (Learning-only) — ✅ IMPLEMENTED + VALIDATED (2026-07-01).** Indicators are provably **episode-invariant** (they take only `MarketAPI`; never touch portfolio/account/position — the only episode-varying state, which stays live). The observation reads them through one clean seam: `getattr(update.Technical, name).Result.last()`. **Built:** `DatasetAPI` gains `IndicatorResults: dict|None` (default None → normal backtests byte-identical); `LearningAPI._pass_` captures each sub-indicator's `Result` sliced to the last `len(ExecutionBars)` values into the tape after the first pass of a window (`_capture_`); subsequent passes on that window inject the tape and `LearningAPI._connect_` swaps `self.technical`/`self.indicator.Technical` for a module-level `_FrozenTechnicalAPI_` (a cursor-advancing container whose sub-indicators' `Result.last()` serve `array[cursor]`, NaN→None). Capture is bit-exact-by-construction (same stream code produces it; **stream, NOT batch**). `Backtesting.advance` per-bar `Market.update_data` is gated `and self._dataset_.IndicatorResults is None`, so the frozen path also skips the 22% market churn (the observation reads prices from the live `update.Bar`, never the `Market` series — verified). Machine ordering is irrelevant: frozen only changes *what* `update_data` does (O(1) cursor++) not *when*. **Zero changes to realtime-shared `MarketAPI`/`IndicatorAPI`.** **Validated:** 17,130/17,130 indicator reads bit-identical real-vs-frozen; **warm per-pass 2.24s → 0.72s = 3.12× (68% saved)** on H1 (beats the 45-55% projection because it kills both the 43% and 22%). Full suite 448 green. **Golden guard:** all 6 goldens re-run with-(b) vs (b)-reverted are **byte-identical across all 5 CSVs** (deals/net/orders/positions/trades) — (b) is provably inert for non-Learning backtests. (Note: configs 2/3/5 no longer match §5's *table* values — that's DB data/param drift since 2026-06-26, present identically in both with-(b) and pre-(b), NOT an engine change; 2023-D1 configs 1/4 still match the table exactly.)
- **(a) Numpy ring-buffer the shared `SeriesAPI`/`Market` — ❌ CLOSED (2026-07-02, premise falsified by measurement).** Measured on the NNFX golden path: the warm engine walk is **O(N) linear at ~3.07s/year H1** (1y/3y/5y = 1.00×/3.02×/5.02×) — the projected ~60k-chunk accumulation pathology does NOT exist; and removing the per-bar child-Series re-init in `Market.update_data` measured **zero** wall-clock change (cProfile's high-call-count hotspots are profiler overhead, not real cost). Realistic upside is a ~10-15% constant factor, not 2-4×, against real bit-exactness risk to the realtime-shared path → **not worth it**. Revisit only if a future workload makes the per-bar walk the measured bottleneck again.
- **Validation harness (either lever):** re-profile the golden config (same 12,160-bar pass) + diff the 6 goldens for byte-identical output. No behavioral change ships without both green.
- **(c) Lean cold pull.** Rung/finer bars via a 12-col / 4-join query (vs the 60-col / 5-join `pull_bars`) → trims the one-time cold setup + shrinks the cache write (the cold "final" writeback). One-time-per-window only; low value unless walk-forward re-preloads many windows.
- **Other:** DB connection pooling (per-run ~0.02s after OPT-A); batch the "neither" `_conversion_at_` searchsorted.

**Deep-dive batch (2026-07-02) — ✅ LANDED, 2.0× warm per-pass (3.00s → 1.50s NNFX H1 year; 450 green; all 6 goldens byte-identical vs the post-Annualized baseline).** Measured first (perf_counter monkeypatch breakdown + cProfile caller attribution), then implemented only what the numbers supported:
- **Feed descent numpy-ized (Backtesting-only; was ~31% wall).** `_build_intra_arrays_` precomputes per-rung epoch-µs + float64 price arrays from `IntraBars` at `_connect_`; `_descend_`/`_finer_bars_` iterate arrays via `np.searchsorted` (replacing per-bar polars `search_sorted` on a Datetime series at ~0.34ms/call + `iter_rows(named=True)` dict building); `_sub_rows_` removed; `_bounds_`/`_ticks_` accept epoch ints. **Float32 trap (real divergence caught by the goldens):** DB prices are Float32 — raw `.to_numpy()` kept f32 and `_spread_ceiling_`/`_should_descend_` arithmetic rounded at f32, flipping a borderline USDJPY SL-reachability decision (margin ~1.6e-5 < one f32 ulp at 134.7). Fixed with `.astype("float64")` (reproduces the old `iter_rows` widening exactly).
- **Market rows precomputed (was ~22% wall).** `DatasetAPI` gains `ExecutionRows` (bulk `bar.dict(flatten=True)` frame built once in `_load_bars_`, warmup+execution in ONE frame so schema inference is shared); `advance` extends the market with `ExecutionRows.slice(i, 1)` (zero-copy) instead of per-bar dict-flatten (53µs) + 1-row DataFrame inference (47µs). `MarketAPI.update_data` accepts a pl.DataFrame row (column-based Bar/Tick fanout); Realtime keeps the object path unchanged.
- **Composite indicator skip.** `TechnicalAPI` instances whose class doesn't override `batch`/`stream` (umbrella containers, MAC/DMAC/TMAC wrappers) skip self-calculate/`_pad_`/extend/Result-init — their Result was an unread all-null column costing 3 polars ops/bar each.
- **`SeriesAPI.dataframe` fast path.** try/`get_column`/except instead of `prefix in columns` (the `.columns` property builds a ~60-string list per call; 76k calls/run), and the multiple-path membership test hoisted to one `set(columns)` per call.
- **Remaining wall (1.50s warm H1 year):** strategy filter logic + machine dispatch (~0.6s; `Series.last` polars scalar reads ~4µs each), report ~0.11s, residual feed/walk ~0.4s. Logging costs ~0.3s at Debug console verbosity — config lever for fleets (Learning workers already run Warning). **C/Rust verdict:** polars IS Rust and numpy IS C — the hot loops now sit on them; the residue is Python orchestration where mypyc/Cython would buy the remaining ~2×, at real build/packaging cost — not worth it while the engine is 2× and Learning replays via the frozen tape anyway.
- **Latent issue (found, deferred):** report export folders are named at seconds granularity — two backtests finishing in the same second export to the SAME `Reports/<ts> BacktestingAPI` folder (observed once optimized runs got fast enough to collide). Needs a uniqueness suffix before fleet-scale exporting.

**Accuracy (optional, data-bound):** tick-resolution exact exits (closes the sub-pip residual); historical swap-rate schedule capture (closes the swap residual). See §3.4.

---

## 5. Golden reports — CAPTURED & VALIDATED (2026-06-26)

The 6 fresh NNFX online cTrader goldens were minted (EUR 10k, conversion option ON, tick data) and the offline engine reproduced ALL 6 at the data-bound floor (§4). Folders under `Reports/`, all iid `f9e14feb-7c74-44ba-856a-2f2ff0e04e28` (CSV exports only — no `report.html`). These are the **pinned goldens** (replacing the stale 2026-06-07/08 set); any engine change must keep reproducing all 6.

| # | Symbol | TF | Window | Folder (timestamp) | golden Net |
|---|---|---|---|---|---|
| 1 | EURUSD | D1 | 2023 → 24 | `2026-06-26 00-47-01` | 75.55 |
| 2 | EURUSD | D1 | 2022 → 25 | `2026-06-26 00-48-48` | −127.33 |
| 3 | EURUSD | H1 | 2023 → 24 | `2026-06-26 00-53-28` | −2936.65 |
| 4 | USDJPY | D1 | 2023 → 24 | `2026-06-26 00-56-52` | 47.13 |
| 5 | USDJPY | H1 | 2023 → 24 | `2026-06-26 01-03-54` | −61.04 |
| 6 | USDJPY | D1 | 2022 → 25 | `2026-06-26 01-01-56` | 76.74 |

---

## 6. Offline Learning System — DESIGN (next build, 2026-06-29)

The next system is an **offline DRL trainer** (`LearningAPI`) for **model-based / hybrid trend-following** strategies, built on the validated `BacktestingAPI` + `dataset=` tape. First deliverables: **two signal-only strategies — DDPG-Only and SAC-Only** (signal management = the agent; **no risk management**), evaluated on **10y walk-forward, EURUSD D1**. (DDPG + SAC are the chosen state-of-the-art continuous-action models; trend-following is the first strategy family — breakout/reversal/scalping come later.)

### 6.1 Architecture — agent-in-strategy (zero engine surgery)
The engine is event-driven (UpdateID → strategy state machines); RL assumes a step loop. Bridge by hosting the agent **inside the strategy** (the natural policy host the engine already calls per bar) — NOT by inverting `deploy()` into a gym `step()` (that would touch the realtime-shared lifecycle). Responsibility split:
- **`ModelStrategyAPI` (new base) + `DDPGStrategyAPI` / `SACStrategyAPI` = the MDP.** Builds the observation, maps action→orders, computes reward, records transitions (`agent.memorize`), exposes a `training` flag (explore + record on/off). Inference-capable standalone (a trained agent later deploys through the same strategy in backtest/live).
- **`LearningAPI(BacktestingAPI)` = the trainer** (sibling of `OptimizationAPI`: Optimization = derivative-free param search for rule strategies; Learning = gradient policy training for model strategies — both WF trainers on the same engine). Owns the agent's training lifecycle, episode/WF loop, gradient cadence, exploration schedule, validation + early-stopping, checkpointing, seeding, logging.
- **Decisions per `BarClosed`** → `Subscription = Stream.All & ~Stream.Tick` (like NNFX; fills next open). Revisit tick-level only if research demands it.
- **Loop:** `tape = extract()` once per WF fold; per episode `inject(tape)` → `run()` (strategy collects transitions + learns) → periodic greedy validation → checkpoint best.

### 6.2 MDP specification (locked decisions)
- **Observation (finalized + implemented 2026-06-30 — scale-free / transferable; `ObservationAPI`):** essential always-on core (**23**) — **Timestamp** sin/cos of Month·Weekday·Hour·Minute (8); **Account** Balance & Equity as returns-from-initial · EquityDrawdown · EquityRunup (4); **Position** signed exposure · unrealized return · max-DD · max-runup (4); **Market** gap·high·low·close as **vol-scaled log-moves vs prev close** (`ln(p/Cprev)/RV`) + Volume `ln(1+V)` (5); **Indicator** `ATR/Close` + `RV` (2). Optional (extensible): 3 MAs `(C−MA)/ATR`, then technical/sentimental/fundamental. **Two-layer normalization:** (1) per-feature causal encoding (log-returns, ratios, vol-scaling, sin/cos) → dimensionless; (2) causal EWMA rolling z-score over unbounded features (bounded ones — sin/cos, exposure, drawdown, already-vol-scaled prices — bypass). **Scaling rule:** only essential always-on vol measures (**RV** for return-space, **ATR** for price-space) may be denominators; optional features never are. Principle = invariance to price level, vol regime, account size (necessary for transfer; sufficiency needs multi-asset training).
- **Action — "intended volume" controller (`ActionAPI` decode + controller):** model output `a∈[-1,1]` → `SizingDeadzone` gate → signed intended volume = `a × MaxVolume`, **floor-normalized to the volume step** via `calculate_normalized_volume`, clamped to `[VolumeMin, VolumeMax]` (below min → 0 = flat). **`MaxVolume` from YAML `MoneyManagement` (finalized 2026-06-30): `SizingMode` = `Fixed` (`SizingMax` = volume cap) or `Percentage` (`SizingMax` = % of account → notional ÷ price → volume); `SizingDeadzone` suppresses tiny actions.** The engine does **not net/aggregate positions**, so the controller maintains an invariant of **≤ 1 open position**:

  | Current `p` (signed) | Target `v` (signed) | Action |
  |---|---|---|
  | 0 | 0 | nothing (flat) |
  | 0 | ≠ 0 | open `\|v\|` in `sign(v)` |
  | same sign, `\|v\| < \|p\|` | | **scale out** (partial close to `\|v\|`) |
  | same sign, `\|v\| ≥ \|p\|` | | **hold** (NO scale-in) |
  | opposite sign, `v ≠ 0` | | **reverse** (close `p`, open `\|v\|`) |
  | ≠ 0 | 0 | close `p` (flat) |

  Intent: orient the agent toward **few, long-lasting trend trades** — scale-out + reversal allowed, scale-in forbidden.
- **Reward (finalized + implemented 2026-06-30 — family on equity log-return `r=ln(E_t/E_{t-1})`; `RewardAPI`):** `LogReturn` (default) · `VolScaledReturn` (`r/σ`) · `DifferentialSharpe` (Moody–Saffell DSR) · `DifferentialSortino` (Moody DDR) · `DifferentialCalmar` (**our extension** = Δ(EMA-return / running max-DD), no paper). All share one online machine (EMA return numerator, swap the risk denominator). `RewardScale` knob (log-returns ~1e-4 on D1). Sharpe/Sortino to be **validated vs Moody & Saffell** for thesis; Calmar is documented as ours. **Reward → CLI** (training-only; see §6.4).
- **Episode:** whole training window per pass (replay buffer persists across passes); `done` at window end or bankruptcy. N-bar chunking = later.

### 6.3 Model layer audit (`Library/Model/`) — DDPG + SAC built + tested (2026-06-29)
DDPG is a faithful Lillicrap-2016 implementation (400/300 + LayerNorm, fan-in + ±3e-3 init, twin target soft-update τ=1e-3, critic L2 1e-2, OU noise). **DDPG fixes LANDED + unit-tested** (`Tests/Model/test_DDPG.py`, 8 green); **SAC BUILT + unit-tested** (`Tests/Model/test_SAC.py`, 10 green). **Env:** torch upgraded 2.2.2 → **2.5.1+cu121** (NumPy-2 compat — torch <2.3 can't use NumPy 2.x; full suite 388 green; unused `torchvision`/`torchaudio` 2.2.2 still pin old torch — harmless, align/remove later).
- **DDPG fixes applied:** `np.bool`→`np.bool_`; warmup guard now on `memory.counter` (was capacity `memory.size`); `Network.device` falls back to `cpu` (was `cuda:1`); `decide()` clips action to `[-1,1]` + runs under `no_grad` with fast `as_tensor`; `learn()` target under `no_grad` + warmup guard; fan-in init `size()[1]`; per-agent **seeding** (torch + `Memory` sampler RNG + OU noise); **+ a latent crash fixed** — `nn.Module.__init__` was called *after* layer assignment (the layer never instantiated) → reordered via a `build()` finalizer; `save()` now mkdirs; `load(weights_only=True)`.
- **SAC built** (Haarnoja 2018; `Library/Model/Method/SAC/`): `GaussianActorNetworkAPI` (squashed-Gaussian — mean+log_std, log_std clamp [-20,2], reparameterized `rsample` → `tanh` + log-prob correction), twin `SoftCriticNetworkAPI` (clipped double-Q, concat-input Q(s,a)) + two targets, **automatic entropy temperature α** (learnable `log_alpha`, target entropy = −action_dim, separate Adam); **no OU noise** (intrinsic exploration; eval = `tanh(mu)`). Reuses `MemoryAPI`/`NetworkAPI`; same `[-1,1]` interface; defaults 256/256 + Adam 3e-4 (all) + τ=0.005 + γ=0.99 + batch 256; seeded; save/load persists all 5 nets + `log_alpha`.
- **Import convention enforced (2026-06-29):** all `np`/`pd`/`pl` now imported from `Library.Database.Dataframe` (shared print/display config) — audited Library-wide, 16 files converted (Model + Noise + Indicator Baseline + System); codified in RULES.md §Imports. Exceptions = `Dataframe.py` + its closure (`Database.Dataclass`, `Utility.Typing`). Tests still use direct `numpy`/`torch` (no table display in tests).
- **Model restructured (2026-06-29):** `Library/Model/` is now two-tier — `Core/` (Agent · Network · Memory · Noise primitives) + `Method/` (DDPG · SAC algorithms); each algorithm keeps Actor·Critic·Agent together. Umbrella `Library.Model` still re-exports `DDPGAgentAPI`/`SACAgentAPI` (tests unchanged). Also: misplaced `Library/System/Archive/` moved to `Archive/Library/System/`. RULES.md project map updated.
- **Paper-fidelity audit + documentation (2026-06-29):** deep-read DDPG (Lillicrap 2016, arXiv:1509.02971) and SAC v1/v2 (Haarnoja, arXiv:1801.01290 / 1812.05905); added paper-mapping docstrings + inline comments to `Method/DDPG` and `Method/SAC` (explicit exception to the no-docstrings rule — for thesis validation). **Fidelity fixes:** DDPG OU θ/σ were swapped (Phil-Tabor-tutorial lineage, youtu.be/4jh32CvwKYw) → now **θ=0.15, σ=0.2, μ=0** per §7; SAC weight init switched from borrowed DDPG fan-in to **PyTorch default** (SpinningUp/CleanRL). **Decided deviations (documented in-code):** DDPG keeps **LayerNorm** (renamed `ln*`, not the paper's BatchNorm) for single-sample stability; SAC log-std clamp [−20,2] + 1e-6 ε + log-α optimization are reference-impl conventions (papers silent). Otherwise DDPG is paper-exact (400/300, action@2nd-Q-layer, [−3e-3,3e-3] final init, L2 1e-2 on Q only, Adam 1e-4/1e-3, γ0.99, τ1e-3, OU dt=1e-2 flagged non-paper) and SAC is v2-exact (twin clipped-double-Q, auto-temp Eq.18, H̄=−dim A, 256/256, Adam 3e-4, τ0.005, batch 256). 388 green.

### 6.3b Strategy/MDP layer — built + tested (2026-06-29 · redesigned 2026-06-30)
Phase 2 landed then was redesigned into a scale-free/transferable encoder stack. `Library/Strategy/Model/`: `Model.py` (`ModelStrategyAPI` base — hosts agent + composes encoders) + thin `DDPG.py`/`SAC.py` (only `_create_agent_` differs) + `Observation.py` · `Action.py` · `Reward.py` encoders. New supporting pieces: `RealizedVolatilityAPI` (`Indicator/Technical/Volatility/RV.py`, EWMA std of log-returns / RiskMetrics; registered in `parse_technical` as `RV`) and a `PortfolioAPI` equity extension (`Equity` · `EquityPeak`/`EquityTrough` · `EquityDrawdown`/`EquityRunup` · `InitialBalance`, tracked on every mark + close). Registered `StrategyType.SAC=4` + `Main` factory. Full suite **432 green** (+44 redesign tests: RV 5 · Equity 4 · Action 5 · Reward 8 · Observation 8 · Model 14).
- **Host pattern (mirrors NNFX):** `signal_management()` machine (Init →`Execution`→ Waiting, self-loop `BarClosed → _step_`, →`Shutdown`→ Term); `risk_management() → None`; `Subscription = Stream.All & ~Stream.Tick`.
- **`_step_`:** `ObservationAPI.encode` → read `Portfolio.Equity` → (if `Training` + prev step) `RewardAPI.reward` + `agent.memorize` + `agent.learn` → `agent.decide(explore=Training)` → `ActionAPI.target` → controller → Action list. `_initialize_` resets agent + observation + reward + transient state per episode.
- **Encoders = the finalized §6.2 spec.** `ObservationAPI` (23 essential core + optional MAs; two-layer causal normalization; reads indicators by name, defaults `ATR`/`RV`), `ActionAPI` (sizing decode + deadzone), `RewardAPI` (differential family). Category-documented (RULES docstring exception, by user request, for thesis understanding).
- **Trainer hooks (Phase 3):** class attrs `Agent` (inject persistent agent so replay buffer survives episode backtests — else each builds its own), `Weights` (checkpoint; loaded in `__init__` when not `Training`), `Training`, `Seed`, `Reward`/`RewardScale` (reward = training-only → set from CLI). Agent hyperparams from `SignalManagement` YAML via `_value_(section,key,default)` (falls back to paper defaults). Agent imports deferred in `_create_agent_` so `import Library.Strategy` stays torch-free.

### 6.3c Trainer core — `LearningAPI(BacktestingAPI)` built + tested (2026-06-30)
`Library/System/Learning.py`. **Episode loop** (`run()`): `extract()` the tape once → `_configure_` (set strategy class attrs `Training`/`Reward`/`Seed`/`Weights`/`Agent=None`) → per episode `_disconnect_ → inject(tape) → _connect_ → deploy()` (fresh sim each episode; tape reused via `_injected_`/`_PRELOAD_CACHE_`, no DB re-query for ticks) → after episode 1 capture `self.strategy._agent_` into the `Agent` class attr so the **replay buffer + networks persist** (only the OU noise resets per episode via `_initialize_`). **Checkpoint-on-best** (`agent.save()` when episode-final `Portfolio.Equity` improves) + a **JSON manifest** (the §6.4 bucket-B model contract: strategy·security·timeframe·window·reward·seed·observation-shape·sizing·best) written beside the weights at `_DEFAULT_WEIGHTS_/<security> <tf> <strategy>/`. Training class attrs reset in a `finally`. `resolution=MISSING` (bar-native auto replay). Full suite **439 green** (+7).
- **Layer-2 normalizer is causal-online** (EWMA z-score) — no separate train-fit step; it cold-starts identically at train and inference (no skew), so §6.5's "fit on train only" holds by construction. Normalizer state is not persisted (recomputed online both sides).
- **`Main` wiring:** uncommented the `SystemType.Learning` branch (`parameters.Learning[args.strategy]` recipe) + `--reward` (RewardType choices)/`--episodes`/`--seed` args; added `LearningAPI` to the `Library.System` export.
- **Pending for end-to-end:** a `Learning.yml` recipe (parallel to `Backtesting.yml`/`Realtime.yml`) with the DDPG/SAC `*Management` tree must exist for the named security·timeframe — else the recipe resolves to an empty `ParameterAPI`. Then `Learning --strategy DDPG --reward DifferentialCalmar --episodes N …` on a tiny window proves the gradient signal flows. **Open decision:** dedicated `Learning.yml` (per scaffold) vs reuse `Backtesting.yml` (DRY — same behavior recipe).
- **Phase-5 throughput:** per-episode `_connect_` opens a fresh DB connection (tape itself is cached); the initial `with`-connect builds one throwaway strategy before the loop re-connects with `Training=True`. Both are negligible for the proof window; precompute (b) + connection reuse deferred to §6.6.5.

### 6.3d Phase 4 trainer — full WF / validation pipeline (2026-06-30)
`LearningAPI` generalized from the single-window core into ONE fully-parameterized trainer that degrades cleanly, all from the CLI (logically ordered: objective → training dynamics → splitting → split mode → selection → reproducibility): `--reward --episodes --epochs --training --validation --testing --rolling --fitness --patience --seed --seeds --workers`.
- **Degradation (matches OptimizationAPI semantics):** `--validation 0 --testing 0` → train-only single window; `--testing N --validation 0` → train + held-out test; `--training T --validation V` → WF folds + optional test tail. **`--rolling`** picks the WF window mode: absent (default) = **anchored/expanding** train window (fixed start, more data per fold); present = **rolling/sliding** fixed-size train window (regime-adaptive). Fold COUNT emerges from window sizes over the range (rolled by `validation`), as in Optimization — tune the windows to get N folds.
- **Splitter** `_walk_forward_` is self-contained (does NOT import the stale Optimization): carve test tail → fold the remainder. Degenerate guards for short ranges.
- **Pipeline** seed × fold × episode: per fold a FRESH agent (WF retrain-per-fold), episodes accumulate the replay buffer; `--validation>0` → greedy eval pass (`Training=False`, no learn/memorize) each episode → checkpoint + early-stop (`--patience`) on the `--fitness` metric; else checkpoint on train metric. Held-out `--testing` → load best then greedy eval. Multi-seed → mean±std + best-seed weights promoted to the top dir; manifest carries every seed's per-fold OOS + test.
- **`--epochs`** plumbed to `ModelStrategyAPI.Epochs` — **no-op for off-policy** DDPG/SAC (off-policy has no rollout-reuse epochs; UTD=1), reserved for a future on-policy method (PPO-style `n_epochs`).
- **`--fitness`** reads a named row from `generate_net_report` (`Sharpe Ratio`/`Calmar Ratio`/`Net Return (%)`…) via `STATISTICS_METRICS_LABEL`/`NET_TOTAL_AGGREGATED`, with an equity-return fallback.
- **RV before ATR** everywhere (observation indicator block + ctor + `_RV_`/`_ATR_` + YAML `TechnicalManagement`) — RV = return-space "true" volatility, ATR = price-space proxy.
- **Inference loading:** `ModelStrategyAPI` reads optional `SignalManagement.Weights` → loads the trained checkpoint when not Training (the post-training validation path). `Backtesting.yml` AND `Realtime.yml` DDPG/SAC carry `Weights: [null]` placeholders to fill with the manifest's weights dir after training (Backtesting = offline validation; Realtime = cTrader-connected validation via the Connector cBot).
- **Recipes:** new `EURUSD/Daily/Learning.yml` (DDPG+SAC) + DDPG/SAC added to `EURUSD/Daily/Backtesting.yml` and `EURUSD/Daily/Realtime.yml`. `Tests/System/test_Learning.py` 15 (splitter + pipeline + early-stop + multi-seed + manifest + fitness + payload picklability). Non-torch suite green.
- **Parallelism — IMPLEMENTED (true multiprocessing):** seeds are independent (folds within a seed share the agent; episodes are sequential). Threading can't help — GIL + the per-bar engine walk is Python-bound, and the `_strategy_` class-attr training state is process-global (threads would race). So `run()` dispatches seeds over a `ProcessPoolExecutor(max_workers=min(workers, seeds))` when `--workers > 1` and `--seeds > 1`; else the sequential path. The Windows-spawn pickling wall (which forced threading in the legacy Optimization) is sidestepped by `_payload_` → a **module-level `_learn_seed_(payload)`** worker that reconstructs everything from picklable PRIMITIVES (strategy class by ref, provider/ticker/timeframe UIDs, `Parameter.data` dict, dates, enums, MISSING-collapsed-to-None fee tuples) — it opens its OWN DB + rebuilds Security/Timeframe per worker, so nothing DB-backed or logger-bound is ever pickled. Per-process isolation also REMOVES the class-attr race. `test_parallel_payload_is_picklable` asserts the payload round-trips through `pickle`. Parent aggregates results + promotes the best seed's weights. (End-to-end multi-process run validates once torch loads — `_train_seed_` itself is covered sequentially.)
- **torch env — ROOT CAUSE FOUND + FIXED (2026-06-30, suite 447 green w/ GPU):** the 12pm `Scripts/environment.bat` (`mamba env update -f Quant.yml --prune`) resolved the **unpinned conda `- pytorch`** (conda-forge ships only a **CPU** `pytorch` on Windows) to `pytorch 2.10.0 cpu_mkl` + `mkl 2025.3` + a 2nd OpenMP, clobbering the pip `torch 2.5.1+cu121` install dir → `fbgemm.dll` WinError 127. **Three-part fix:** (1) `Quant.yml` — torch moved off conda into the **pip** section pinned to the CUDA index (`--extra-index-url …/cu121` + `torch==2.5.1`/`torchvision==0.20.1`/`torchaudio==2.5.1`) so `--prune` can't re-pull the CPU build; (2) one-time repair = remove the mixed conda/pip installs + `--force-reinstall` the cu121 wheel; (3) **import-order:** torch 2.5.1 bundles its OWN `torch/lib/libiomp5md.dll` but conda's `intel-openmp 2025.3` ships a different one — whichever loads first wins, and MKL tolerates torch's OMP but NOT vice-versa, so `fbgemm` fails iff numpy/polars (MKL) imports first. Empty `Library/__init__.py` now `ctypes`-preloads torch's `libiomp5md.dll` (+ sets `KMP_DUPLICATE_LIB_OK`) BEFORE any `Library.*` submodule (so before `Dataframe`/MKL) — Windows-only, guarded, MKL+GPU+numerics all preserved. `KMP_DUPLICATE_LIB_OK=TRUE` also persisted via `conda env config vars set -n Quant`. (Alternative considered + rejected: pinning `mkl<2025` cleanly resolves but the solver flips numpy MKL→OpenBLAS — unwanted numerics change for a bit-exact thesis.)

### 6.4 Persistence — weights (binary) + recipe (YAML)
Mirror standard ML practice (HF `config.json`+`model.bin`; SB3 zip): **config in YAML, weights in binary.**
- **Weights** = PyTorch `state_dict` checkpoints (binary; `NetworkAPI.save/load` already writes `path/model/role`) — one per network (actor / critic(s) / targets / α).
- **Three config buckets (refined 2026-06-30 — discriminator: "does changing this produce a different / weight-incompatible trained model?"):**
  - **(A) Training-only / permanent → CLI** — data window (symbol·timeframe·start·stop), WF split, **reward type + params**, RL hyperparams (γ/τ/lr/batch/buffer), seed. Defines the trained weights; never used at inference.
  - **(B) Permanent AND needed at inference → manifest** — observation feature set + encodings + periods, network arch. The model contract; snapshotted beside the weights and auto-loaded read-only at deploy (like a HF `preprocessor_config.json`). Not hand-edited.
  - **(C) Tweakable behavior → YAML** (what Realtime live/backtest/optimization loads) — `SizingMode`/`SizingMax`/`SizingDeadzone`, which weights to load. Decoded at action time → re-tunable post-training without retraining.
- **Hybrid** = one parameter tree carrying BOTH a model sub-config (SignalManagement) AND rule sub-config (RiskManagement) — fits the existing `*Management` YAML layout.
- Save a **training manifest** (seed, git commit, data window, hyperparameters, final validation metric) beside the checkpoint for reproducibility/audit.

### 6.5 Reproducibility, train/validation/test, throughput
- **Seeding:** one configured seed → torch + numpy + `Memory` sampler RNG + noise RNG; engine is already bit-exact. Report **mean±std over multiple seeds** (RL variance is high — one run is not signal).
- **Train / Validation / Test:** yes — train (agent learns) + validation (greedy early-stopping & checkpoint selection) + held-out **OOS test** (never seen in training); reuse `OptimizationAPI`'s WF splitter; **fit observation normalization on train only**.
- **Throughput:** skip the full report during training (reward only); add precompute **(b)** (fixed market+indicator series reused across episodes) for scale; single-env first, ProcessPool parallel collection (per-worker `dataset=`) later.

### 6.6 Phased build
1. ✅ **DONE** — **Model fixes + SAC** — fix the 4 DDPG bugs + hygiene; build `SACAgentAPI` (twin critic + gaussian policy + temperature); unit-test agents in isolation (seeded, tiny shapes).
2. ✅ **DONE (2026-06-29)** — **MDP layer** — `ModelStrategyAPI` base + `DDPGStrategyAPI`/`SACStrategyAPI`: observation builder, action→order controller, reward, `memorize`, `training` flag, greedy/eval path; unit-tested with fakes (`Tests/Strategy/test_Model.py`, 20 green). See §6.3b.
3. ✅ **DONE (2026-06-30)** — **Trainer core** — `LearningAPI(BacktestingAPI)`: single-window episode loop, inline learning, seeding, checkpoint-on-best, JSON manifest, reward/fitness logging; `Main` wired (`SystemType.Learning` + `--reward`/`--episodes`/`--seed`); orchestration unit-tested (`Tests/System/test_Learning.py`, 7 green). See §6.3c. **Pending:** real-data overfit run (needs a `Learning.yml` recipe) to prove signal flows end-to-end.
4. ✅ **DONE (2026-06-30)** — **WF + validation** — one fully-parameterized trainer (single-window ↔ train/test ↔ train/val ↔ rolling/anchored WF) + greedy validation + early-stopping + multi-seed mean±std + risk-adjusted `--fitness` + inference weights-loading + DDPG/SAC recipes. See §6.3d. ← **NEXT (validate on real data once the torch env is fixed)**
5. **Scale** — precompute (b); **true multi-seed/fold parallelism via multiprocessing** (`_train_seed_` + `--workers` are parallel-ready; ProcessPool impl pending — see §6.3d).

### 6.7 Performance & hardware (i9-14900F · RTX 3060 Ti, 8 GB)
Per-episode cost = engine rollout + per-bar `decide` (forward) + `learn` (backprop). **Measure the breakdown first** (rollout vs decide vs learn) and optimize the real bottleneck — for D1 + small MLP the **engine walk dominates** the NN math; backprop becomes the bottleneck for **SAC** (twin critics + entropy ≈ 2-3× DDPG), H1/tick scale, larger nets, or high gradient-step counts.
- **GPU = batched backprop, not batch-1 inference:** per-bar batch-1 forwards are often *faster on CPU* (kernel-launch + PCIe latency > the tiny matmul) — keep training on GPU, profile `decide` CPU-vs-GPU, expose a device knob. Replay buffer stays on CPU (numpy); move only the sampled batch to GPU per `learn`.
- **Ampere accelerators (near-free):** TF32 matmuls (`allow_tf32=True`), AMP (`autocast`+`GradScaler`, ~1.5-2× + half VRAM, scales with net size/SAC), `cudnn.benchmark=True` (fixed RL batch shapes). Use **batch 256-512** to saturate the GPU (64 underutilizes it).
- **CPU = 32 threads → parallel experience:** N parallel rollout workers (ProcessPool), each injected with the tape (`dataset=`), feeding one GPU learner (Ape-X / multi-actor pattern). Processes not threads (GIL); `set_num_threads(1)` per worker; reserve cores for the learner. The per-worker `dataset=` seam (§4) is built for this — design the single-env v1 so it drops in.
- **Engine-side = the biggest D1 lever:** precompute **(b)** (fixed market+indicators replayed across episodes) removes ~45% of per-pass exec — more impactful than NN micro-opts for D1. Skip the report during training (reward only).
- **Algorithm-level:** `update_every` / `gradient_steps` knobs (don't backprop every bar if it's the cost; off-policy decouples); warmup random steps; allocation-free obs/action/reward Python path.
- **Determinism vs speed:** TF32/AMP/benchmark perturb determinism → a **"deterministic" mode** (TF32 off, `cudnn.deterministic`) for validation/repro + a **"fast" mode** for bulk training; seeds set in both.
- **Build a trainer-level profiler from day one** (rollout / decide / learn timing per episode) so we optimize the measured bottleneck, not the assumed one (RULES: measure don't guess).

---

## 7. Backlog
- **Realtime hardening (2026-07-02 audit — approved, deferred until a cTrader test session):** (1) warmup bars double-added to the market buffer (`Realtime.py` `warmup` action re-adds the 5 anchor ticks + bar that `System._receive_update_bar_` already added — masked by BufferAPI dedup but doubles warmup buffering); (2) `BufferAPI._worker_` deadlocks `flush()` if a persist worker's DB connect raises (nothing releases the dispatch latch); (3) transport hardening — validate `OpenEventW` handles at connect, log `OpenProcess` watchdog-arming failure, bound the 4-byte length field in `_read_`, guard zero-length payloads and batch offset overruns; (4) the universe buffer is started/flushed but nothing ever `add`s to it (`_receive_update_security_` saves synchronously — route through the buffer or drop it); (5) watchdog only armed on `UpdateID.Init` — a peer dying pre-Init hangs `receive` forever.
- **Optimization** — uncomment `OptimizationAPI` in `Main.py` + export; `tape = BacktestingAPI(...).extract()` once, then `inject(tape)` (or `dataset=tape`) across the N param runs (and per `ProcessPoolExecutor` worker). Throughput seam is DONE (§4 Tier2-B).
- **Learning** — the offline DRL trainer; full design + phased build in §6.
- **Phase G — Strategy state recovery:** persist Signal/Risk machine state on Live restart. *Sketch:* `State: Union[bytes, None]` on `SessionAPI` (`pl.Binary()`); `EngineAPI.State` maps machine→state name as JSON bytes; loaded at `deploy()` start, saved on `UpdateID.Shutdown`.
- **Wire up `receive_update_security`** — parse C# security data to enrich `SecurityAPI` (pip size, commission). Sent but codec not consumed.
- **Timeout watchdog** — configurable hung-peer timeout (e.g. 30 s → teardown). Current watchdog only detects peer-death via PID.
- **`Schedule` orchestrator (future project, was `SCHEDULE.md`):** a Prefect-style task orchestrator integrated into the framework. New `Schedule` DB schema — `Workflow`, `Task` (Python script + cron), `Run` (status: Resting→Waiting→Approving→Running→Reviewing→Success/Failure, with duration/memory/message), plus `WorkflowTask` (sequence + auto-approve), `Dependency` (Finish-to-Start / Success-to-Start task graph), `Parameter` (per-run JSONB payload). Phases: (1) `Schedule` schema + `ScheduleDatabaseAPI`; (2) `SchedulerService` (cron monitor) + `WorkerService` (subprocess runner); (3) dependency-tree transition engine; (4) Dash dashboard with manual Approve/Review gates.
- **Completed refactors (was `plans/master-plan.md`):** Market (DB-aligned `TickAPI`/`BarAPI` + recursive `SeriesAPI`), Indicators (TA-lib dropped, modular `Technical/Fundamental/Sentimental`, O(1) incremental SMA/MACD, dual-mode batch/stream tests), Portfolio (`SizingAPI`/`StatisticAPI` extracted, symmetric Account/Order/Position/Trade, unified `.dict()`).

---

## 8. Known issues (non-blocking)
- **`--profile` not wired to the cBot UI** — invoke the Python CLI with `--profile` to dump `.pstat`. It wraps only the Python `run` (blind to the C#/cTrader side).
- **C# platform warnings** — 2× `CA1416` (`MemoryMappedFile.CreateOrOpen`, Windows-only); 3× `CS0618` (deprecated `PlaceStopOrder`/`PlaceLimitOrder`/`PlaceStopLimitOrder`). Non-breaking.
- **Logging is custom (not stdlib):** `logging.disable()` does nothing; silence via `LoggingAPI` (e.g. `HandlerLoggingAPI().console.set_verbose_level(VerboseLevel.Silent)`).

---

## 9. DRL model expansion — BUILT, VALIDATED & 11y WF DEPLOYED (2026-07-03)

- **Observation 26 → 31 features** (`Strategy/Model/Observation.py`): position duration `log1p(bars held)` (idx 16, UID-tracked); vol-normalized multi-horizon momentum `ln(C_t/C_{t-h})/(RV·√h)` for `MomentumHorizons` (H1: 24/120/480 · Daily: 5/21/63; idx 21-23); vol-regime `ln(RV/RVSlow)` (idx 27, `RVSlow: [RV, 480]` H1 / `[RV, 63]` Daily added to `TechnicalManagement`). All models retrain from scratch (shape change).
- **ExtendedDDPG** (`StrategyType.ExtendedDDPG = 5`): `DDPGAgentAPI(actor_regularization=λ)` adds `λ·mean(u²)` on the pre-tanh activation to the actor loss (anti tanh-collapse); λ=0 default is the paper-pure EXACT code path (600-step seeded trajectory proved bit-exact vs HEAD; λ=1e-3 diverges first at step 64 = first full batch). Strategy sets λ=1e-3 via `ActorRegularization`.
- **TD3** (`StrategyType.TD3 = 6`, `Library/Model/Method/TD3/`): Fujimoto 2018 (arXiv:1802.09477) Algorithm 1 exact — 400/300 no-norm nets, (s,a)-concat critics, Adam 1e-3, batch 100, τ 0.005, exploration N(0, 0.1), target smoothing σ̃ 0.2 clip 0.5, delay d 2, actor on Q1 only, no weight decay. Paper-mapping docstrings (RULES exception extended). 14/14 empirical fidelity checks.
- **`LearningAPI(threads=)` / `--threads`** caps torch threads per worker so two Learning processes can share the box without oversubscription.
- **Validation:** 31-col audit 20/20 PASS on 3,119 real bars (max rel err 5.9e-8); 6 NNFX goldens byte-identical vs `results_baseline.json`; 457 tests green; 4-strategy Learning smoke OK; profiling DDPG 4.1 / SAC 5.0 / ExtDDPG 4.2 / TD3 3.4 ms/step (6 threads).
- **CLI TRAP:** launch with `--timeframe Hour` (params folder key), never `H1` — a missing key auto-vivifies an empty parameter node and the strategy constructor gets `ParameterAPI` leaves.
- **11y WF v2 running since 2026-07-03 ~13:00** in two lanes (DDPG→ExtendedDDPG · SAC→TD3), each `--workers 5 --threads 3`, 2015→2026, DifferentialSortino, episodes 15, patience 5, 36/12/12 rolling (7 folds + 12mo test), seeds 5. Old 26-shape checkpoints purged. Manifests land in `~/.cache/cAlgo/models/1 H1 <Strategy>API/`.