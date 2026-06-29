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

**FUTURE work (NOT needed to proceed to Learning; do only if H1/intraday throughput demands it):**
- **(b) Precompute + inject the fixed market/indicator dataset (in the Learning system).** In DRL the market + indicators are identical every episode (only the agent's actions change) — compute them once (the already-validated *batch* path) and replay. Eliminates ~45% of per-pass exec (the per-bar indicator recompute) with **zero changes to the streaming `MarketAPI`/`IndicatorAPI` that RealtimeAPI shares**. Biggest, safest H1 lever; belongs in Learning, plugs into the `dataset=` hook. Est. H1 per-pass 25.4s → ~12-14s.
- **(a) Numpy-ize the streaming per-bar feed + indicators (engine-level, DEFERRED — risky).** Replace `SeriesAPI` per-bar storage + indicators' `stream()` with numpy/scalar incremental; keep Polars for warmup/IO/batch. Expected ~2-4× on the walk + fixes the chunk-accumulation pathology at 10y-Hourly (per-bar `extend` accrues ~60k Polars chunks). **Touches accuracy-critical math SHARED with RealtimeAPI → must keep realtime bit-identical; validate bit-for-bit.** Smaller + riskier than (b) for the DRL use case → do as its own deliberate pass, not a close-out. Also: array-backed bar access at load (`_row_to_bar_` builds BarAPI + 5 TickAPI/bar — ~370k objects at 10y-Hourly).
- **(c) Lean cold pull.** Rung/finer bars via a 12-col / 4-join query (vs the 60-col / 5-join `pull_bars`) → trims the one-time cold setup + shrinks the cache write (the cold "final" writeback). One-time-per-window only; low value unless walk-forward re-preloads many windows.
- **Other:** DB connection pooling (per-run ~0.02s after OPT-A); batch the "neither" `_conversion_at_` searchsorted.

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
- **`ModelStrategyAPI` (new base) + `DDPGStrategyAPI` / `SACStrategyAPI` = the MDP.** Builds the observation, maps action→orders, computes reward, records transitions (`agent.memorise`), exposes a `training` flag (explore + record on/off). Inference-capable standalone (a trained agent later deploys through the same strategy in backtest/live).
- **`LearningAPI(BacktestingAPI)` = the trainer** (sibling of `OptimizationAPI`: Optimization = derivative-free param search for rule strategies; Learning = gradient policy training for model strategies — both WF trainers on the same engine). Owns the agent's training lifecycle, episode/WF loop, gradient cadence, exploration schedule, validation + early-stopping, checkpointing, seeding, logging.
- **Decisions per `BarClosed`** → `Subscription = Stream.All & ~Stream.Tick` (like NNFX; fills next open). Revisit tick-level only if research demands it.
- **Loop:** `tape = extract()` once per WF fold; per episode `inject(tape)` → `run()` (strategy collects transitions + learns) → periodic greedy validation → checkpoint best.

### 6.2 MDP specification (locked decisions)
- **Observation (confirmed 2026-06-29; raw values z-scored on train-only stats — no look-ahead; single bar, no lookback for v1):** cyclical time encoding (sin/cos of day-of-week AND time-of-day), current signed-normalized position, **raw OHLC + Volume** (volume added for volatility/liquidity awareness), and **two indicators: SMA + ATR** (ATR essential for volatility). SMA and ATR periods are **YAML-configurable**.
- **Action — "intended volume" controller (continuous):** model output `a∈[-1,1]` → signed intended volume = `a × MaxVolume`, **floor-normalized to the volume step** via `calculate_normalized_volume`, clamped to `[VolumeMin, VolumeMax]` (below min → 0 = flat). **`MaxVolume` from a YAML sizing config (confirmed 2026-06-29): `mode=fixed` (value = volume cap) or `mode=percentage` (value = % of account → notional ÷ price → volume).** The engine does **not net/aggregate positions**, so the controller maintains an invariant of **≤ 1 open position**:

  | Current `p` (signed) | Target `v` (signed) | Action |
  |---|---|---|
  | 0 | 0 | nothing (flat) |
  | 0 | ≠ 0 | open `\|v\|` in `sign(v)` |
  | same sign, `\|v\| < \|p\|` | | **scale out** (partial close to `\|v\|`) |
  | same sign, `\|v\| ≥ \|p\|` | | **hold** (NO scale-in) |
  | opposite sign, `v ≠ 0` | | **reverse** (close `p`, open `\|v\|`) |
  | ≠ 0 | 0 | close `p` (flat) |

  Intent: orient the agent toward **few, long-lasting trend trades** — scale-out + reversal allowed, scale-in forbidden.
- **Reward (simple for now): per-bar Δ(net equity)** — change in realized+unrealized account equity, net of cost (the "net PnL" interpretation; **configurable**). Differential Sharpe / drawdown-penalized = later refinement.
- **Episode:** whole training window per pass (replay buffer persists across passes); `done` at window end or bankruptcy. N-bar chunking = later.

### 6.3 Model layer audit (`Library/Model/`) — DDPG + SAC built + tested (2026-06-29)
DDPG is a faithful Lillicrap-2016 implementation (400/300 + LayerNorm, fan-in + ±3e-3 init, twin target soft-update τ=1e-3, critic L2 1e-2, OU noise). **DDPG fixes LANDED + unit-tested** (`Tests/Model/test_DDPG.py`, 8 green); **SAC BUILT + unit-tested** (`Tests/Model/test_SAC.py`, 10 green). **Env:** torch upgraded 2.2.2 → **2.5.1+cu121** (NumPy-2 compat — torch <2.3 can't use NumPy 2.x; full suite 388 green; unused `torchvision`/`torchaudio` 2.2.2 still pin old torch — harmless, align/remove later).
- **DDPG fixes applied:** `np.bool`→`np.bool_`; warmup guard now on `memory.counter` (was capacity `memory.size`); `Network.device` falls back to `cpu` (was `cuda:1`); `decide()` clips action to `[-1,1]` + runs under `no_grad` with fast `as_tensor`; `learn()` target under `no_grad` + warmup guard; fan-in init `size()[1]`; per-agent **seeding** (torch + `Memory` sampler RNG + OU noise); **+ a latent crash fixed** — `nn.Module.__init__` was called *after* layer assignment (the layer never instantiated) → reordered via a `build()` finalizer; `save()` now mkdirs; `load(weights_only=True)`.
- **SAC built** (Haarnoja 2018; `Library/Model/Method/SAC/`): `GaussianActorNetworkAPI` (squashed-Gaussian — mean+log_std, log_std clamp [-20,2], reparameterized `rsample` → `tanh` + log-prob correction), twin `SoftCriticNetworkAPI` (clipped double-Q, concat-input Q(s,a)) + two targets, **automatic entropy temperature α** (learnable `log_alpha`, target entropy = −action_dim, separate Adam); **no OU noise** (intrinsic exploration; eval = `tanh(mu)`). Reuses `MemoryAPI`/`NetworkAPI`; same `[-1,1]` interface; defaults 256/256 + Adam 3e-4 (all) + τ=0.005 + γ=0.99 + batch 256; seeded; save/load persists all 5 nets + `log_alpha`.
- **Import convention enforced (2026-06-29):** all `np`/`pd`/`pl` now imported from `Library.Database.Dataframe` (shared print/display config) — audited Library-wide, 16 files converted (Model + Noise + Indicator Baseline + System); codified in RULES.md §Imports. Exceptions = `Dataframe.py` + its closure (`Database.Dataclass`, `Utility.Typing`). Tests still use direct `numpy`/`torch` (no table display in tests).
- **Model restructured (2026-06-29):** `Library/Model/` is now two-tier — `Core/` (Agent · Network · Memory · Noise primitives) + `Method/` (DDPG · SAC algorithms); each algorithm keeps Actor·Critic·Agent together. Umbrella `Library.Model` still re-exports `DDPGAgentAPI`/`SACAgentAPI` (tests unchanged). Also: misplaced `Library/System/Archive/` moved to `Archive/Library/System/`. RULES.md project map updated.
- **Paper-fidelity audit + documentation (2026-06-29):** deep-read DDPG (Lillicrap 2016, arXiv:1509.02971) and SAC v1/v2 (Haarnoja, arXiv:1801.01290 / 1812.05905); added paper-mapping docstrings + inline comments to `Method/DDPG` and `Method/SAC` (explicit exception to the no-docstrings rule — for thesis validation). **Fidelity fixes:** DDPG OU θ/σ were swapped (Phil-Tabor-tutorial lineage, youtu.be/4jh32CvwKYw) → now **θ=0.15, σ=0.2, μ=0** per §7; SAC weight init switched from borrowed DDPG fan-in to **PyTorch default** (SpinningUp/CleanRL). **Decided deviations (documented in-code):** DDPG keeps **LayerNorm** (renamed `ln*`, not the paper's BatchNorm) for single-sample stability; SAC log-std clamp [−20,2] + 1e-6 ε + log-α optimization are reference-impl conventions (papers silent). Otherwise DDPG is paper-exact (400/300, action@2nd-Q-layer, [−3e-3,3e-3] final init, L2 1e-2 on Q only, Adam 1e-4/1e-3, γ0.99, τ1e-3, OU dt=1e-2 flagged non-paper) and SAC is v2-exact (twin clipped-double-Q, auto-temp Eq.18, H̄=−dim A, 256/256, Adam 3e-4, τ0.005, batch 256). 388 green.

### 6.4 Persistence — weights (binary) + recipe (YAML)
Mirror standard ML practice (HF `config.json`+`model.bin`; SB3 zip): **config in YAML, weights in binary.**
- **Weights** = PyTorch `state_dict` checkpoints (binary; `NetworkAPI.save/load` already writes `path/model/role`) — one per network (actor / critic(s) / targets / α).
- **Recipe/config** = **YAML** — strictly **"how it learns"** + rule params (consistent with rule-param YAML): seed, noise type, feature set, action type, reward type, network sizes, γ/τ/lr/batch/buffer. Agent = `(YAML recipe + weights checkpoint)`.
- **"When it learns" = CLI args** (like `OptimizationAPI`), NOT YAML: symbol, timeframe, start, stop, and the walk-forward split (training / validation / testing). The YAML stays purely "how it learns"; the CLI owns the data window + WF schedule.
- **Hybrid** = one parameter tree carrying BOTH a model sub-config (SignalManagement) AND rule sub-config (RiskManagement) — fits the existing `*Management` YAML layout.
- Save a **training manifest** (seed, git commit, data window, hyperparameters, final validation metric) beside the checkpoint for reproducibility/audit.

### 6.5 Reproducibility, train/validation/test, throughput
- **Seeding:** one configured seed → torch + numpy + `Memory` sampler RNG + noise RNG; engine is already bit-exact. Report **mean±std over multiple seeds** (RL variance is high — one run is not signal).
- **Train / Validation / Test:** yes — train (agent learns) + validation (greedy early-stopping & checkpoint selection) + held-out **OOS test** (never seen in training); reuse `OptimizationAPI`'s WF splitter; **fit observation normalization on train only**.
- **Throughput:** skip the full report during training (reward only); add precompute **(b)** (fixed market+indicator series reused across episodes) for scale; single-env first, ProcessPool parallel collection (per-worker `dataset=`) later.

### 6.6 Phased build
1. **Model fixes + SAC** — fix the 4 DDPG bugs + hygiene; build `SACAgentAPI` (twin critic + gaussian policy + temperature); unit-test agents in isolation (seeded, tiny shapes).
2. **MDP layer** — `ModelStrategyAPI` base + `DDPGStrategyAPI`/`SACStrategyAPI`: observation builder, action→order controller, reward, `memorise`, `training` flag, greedy/eval path; unit-test vs a frozen tiny tape.
3. **Trainer core** — `LearningAPI(BacktestingAPI)`: single-window episode loop, inline learning, seeding, checkpoint, reward/fitness, logging; overfit a tiny window to prove signal flows.
4. **WF + validation** — port WF splitter, greedy validation, early-stopping, multi-seed; 10y EURUSD D1.
5. **Scale** — precompute (b); optional parallel collection.

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
