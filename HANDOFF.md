# Quant Trading Framework — Handoff

Forward-looking brief for the `cAlgo` repo. Read this for orientation and the active roadmap, then `RULES.md` for conventions.

---

## 1. Orientation

- **Root:** `C:\Users\Admin\OneDrive\Documents\cAlgo`
- **`Library/`** Python core (engine, persistence, AI, Dash UI).
- **`Sources/`** C# cTrader Robots/Indicators/Plugins. Connector cBot bridges to Python via Shared Memory (Windows named `mmap` + auto-reset Event signaling, single-slot request/response lockstep) + Binary Protocol.
- **`Tests/`** pytest, mirrors `Library/` layout. Exclude `Tests/Spotware`. Full suite is **355 green**.
- **`Setup/`** unified workspace + DB setup. `conda run -n Quant python -m Setup.Main --all`. `Setup.Main --enums` regenerates `Connector/Enum.cs` (the **protocol/common** enums: `PositionTypeID`, `StrategyType`, `VerboseLevel`, `SystemMode`, `UpdateID`, `ActionID`) from their Python sources. `Connector/Parameter.cs` enums (`BufferingMode`, `AccuracyMode`, stream modes…) are **hand-authored cBot config**, NOT generated.
- **Env:** `conda run --no-capture-output -n Quant ...` (`--no-capture-output` avoids a charmap crash on log `·`/`→` glyphs; also set `PYTHONIOENCODING=utf-8`).
- **Test command:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware`.
- **Build C#:** `dotnet build Sources/Robots/Connector/Connector.sln` (the user builds the Connector; **do not** build it for them).
- **Git:** stage with `git add`, **never commit**.

Both the **realtime path** (Live/Simulation/Testing) and the **offline backtesting engine** are built and validated: the cBot streams updates over shared memory, Python (`RealtimeAPI` / `BacktestingAPI`) runs the strategy through the shared `SystemAPI.deploy()` lifecycle, and reports reconcile with cTrader. The NNFX golden (EURUSD Daily, 2023-01-01 → 2024-01-01) is the reference: **Gross 195.56 · Commission −18.24 · Swap −101.773 · Net 75.55 · 37 trades / 25 deals.**

---

## 2. Offline Backtesting Engine — BUILT & VALIDATED

`Library/System/Backtesting.py` → `BacktestingAPI(SystemAPI)`, a second in-process broker simulator that emits the **same `UpdateID` protocol** into the **same `deploy()` loop** as realtime, driven by DB market data instead of cTrader. Strategy / engine / indicators / portfolio / reporting code is byte-for-byte shared — which is why the realtime golden is a valid oracle. Wired in `Main.py` (`_system_` constructs `BacktestingAPI`); exported in `Library/System/__init__.py`; `Tests/System/test_Backtesting.py` = 41 mocked unit tests (data-independent, ~0.1s).

### 2.1 What's implemented
- **Fidelity:** bar mode + **auto-resolution** — when `--resolution` is omitted it builds an intrabar tick ladder (H1→M1) from finer bars in the DB (`_acquire_frames_`/`_load_frames_`), cached in-memory (`_PRELOAD_CACHE_`, class-level) **and** on disk (Parquet at `~/.cache/cAlgo/preload`, keyed by `_cache_signature_` + a `_data_token_` = tick count so stale data invalidates).
- **Feed:** `_generate_` walks `_bars_`; per boundary emits `BarClosed → Tick(open)`; `_intrabar_source_`/`_descend_`/`_walk_` reconstruct the intrabar path and run SL/TP + ask/bid-target checks. Vectorized leaf event-search + `_arm_version_` gating; int64-µs timestamps; deque queues; NumPy/Polars only (no Pandas).
- **Fees:** `Accurate` spread/commission/swap (contract-driven, matches cTrader). Swap uses the current `Contract` values as source of truth (no reliable historical swap source).
- **No look-ahead** is structural (the strategy only sees a bar's indicators at its `BarClosed`; fills happen on the next open tick).
- **Validation:** reproduces the golden tables; the only residual is a documented **sub-pip exit-price difference** on intrabar SL/TP exits (bar/target data can't recover ms-precise exits — tick mode would). Gross ≈ 195.68 vs golden 195.56 (+0.12) is this residual, not a conversion error.

### 2.2 Conversion rates — the 4-rate bid-side rule (validated this session)
Each tick stores **4** conversion rates: `AskBaseConversion`, `BidBaseConversion`, `AskQuoteConversion`, `BidQuoteConversion`, computed at **download time** by the cBot's `FindConversions` (`Robot.cs:304`) and snapshotted into `CurrentTick()`. The ask/bid rates genuinely differ (~1e-5–5e-4).

- **Rule (proven):** cTrader expresses any foreign amount (gross PnL, commission, swap) in the deposit currency at the **BID side** of the foreign→deposit conversion. Logic: converting foreign→deposit you SELL foreign / BUY deposit → land on the conversion pair's bid. Sign-independent. Empirically decisive on the aggregate (Σ golden_points·conv): **BidQuote 195.58 (Δ+0.02)** vs mid 195.49 vs AskQuote 195.40.
- **Engine (`_conversions_`, `_tick_conversions_`, `_synth_tick_`, `_conversion_at_`):** all 4 rates are carried on synth ticks. `_needs_conversion_ = account ∉ {base, quote}` gates IO: account-related symbols (e.g. EURUSD/EUR) compute conversions from the tick's **raw** ask/bid (zero array IO); the "neither" case loads the 4 stored per-tick arrays. Portfolio `_conversion_` also uses bid for unrealized gross.
- **Symbol test matrix (EUR account)** — needs each symbol's conversion pairs present in the broker universe; each needs a fresh cTrader Simulation golden:

  | Symbol | Account vs pair | base→EUR via | quote→EUR via | Validates |
  |---|---|---|---|---|
  | EURUSD ✅ | base | 1.0 | 1/Ask (own) | baseline (golden) |
  | EURJPY | base | 1.0 | 1/Ask (own, JPY) | JPY pip scaling |
  | GBPUSD | **neither** | EURGBP | EURUSD | both legs via majors |
  | GBPJPY | **neither** (purest) | EURGBP | EURJPY | no EUR-direct leg |
  | USDJPY | neither | EURUSD | EURJPY | USD + JPY legs |
  | AUDUSD | neither | EURAUD | EURUSD | AUD + USD legs |

  The "neither" path (`_conversion_at_` over stored arrays) is **implemented but unvalidated** — no cross-symbol data downloaded yet. **GBPJPY is the most stringent single test.**

### 2.3 Performance work landed this session (all 355-green, byte-identical output)
- **Dataclass serialization** (`Library/Database/Dataclass.py`): cached per-class emit-plan `_plan_` (kills the per-record MRO walk), `data()` rewritten as a **non-generator** list build, `dict()`/`tuple()`/`list()` de-wrapped (`dict(self.data(...))` direct). → engine ~**11% + ~5%**, `data()` tottime −62%, total calls −33%.
- `Datapoint.__setattr__` uses `__dict__.get` instead of `getattr` (195k calls/run).
- `SeriesAPI._column_()` caches its static column list.
- These help **every** path (backtest walk, buffer flush, reports).

### 2.4 Engine mechanics reference (still accurate — mirror `Robot.cs`)
- **Event order:** `OnBarClosed → OnTick(open) → OnBarOpened`. cBot keeps one accumulating `xBar`; on `OnBarClosed` sets volume, sends `BarClosed`, then `GapTick = CloseTick` (next bar's gap = prior close), `Timestamp = lastBar.OpenTime`.
- **Stream modes** (`Robot.cs`): `TickStreamMode = Off | Target | All | Auto` (Download→Off; golden used Target). `BarStreamMode = Off | All | Auto`.
- **Pop order:** `SystemAPI._process_updates_()` pops sub-objects in a fixed order (e.g. `OpenedBuyPosition` pops **bar then position**; closes pop a position+trade pair). `receive_update_*` must match exactly.
- **UID collisions:** simulated `_pids`/`_tids` use negative space (`count(start=-1, step=-1)`).
- **Reference files:** `Realtime.py` (sibling SystemAPI), `System.py` (`deploy`/`_process_updates_`), `Robot.cs` (broker behavior), `Market/Series.py` + `Market/Market.py` (`init_data`/`update_data`, no-look-ahead), `Market/Bar.py`+`Tick.py`, `Portfolio/*`, `Universe/*`.

---

## 3. Performance Roadmap — finalize the engine (A / B / C)

Profiled (golden, logging silenced via `LoggingAPI.set_verbose_level(Silent)`): warm walk ~**335 ms** for 1y Daily (~260 executed bars, ~1.1–1.5 ms/bar). Extrapolated: **10y Daily ≈ 5–10 s**, **10y Hourly ≈ 1.5–3 min** (engine-only, data already local). Remaining cost is **structural** — these three are queued (user approved all three; do **B first**, then evaluate A/C). Each MUST be golden-validated before commit.

- **B — Pull-once shared injectable dataset** *(start here; Optimization/Learning enabler).* Bundle everything `_load_bars_`+`_preload_` produce into a frozen `BacktestDataset` (`bars`, `warmup_frame`, `tick_ts/ask/bid`, `tick_conversions`, `rung_frames`, `ladder`, `finer_frame`). Add optional `dataset=` to `BacktestingAPI`; in `_connect_`, if injected → assign + skip the DB load, else load as today and expose `.Dataset`. Optimization loads **once**, injects across N runs (and once per `ProcessPoolExecutor` worker). **Default (no-dataset) path stays byte-identical → golden safe by construction.** Verified safe: market data is **read-only** during a run (only `_bars_.pop(0)` mutates, and that's during load). The `pop(0)` warmup-split moves into dataset construction.
- **A — Numpy-ize the per-bar hot path** *(biggest engine win; deep refactor).* The dominant remaining cost is **per-bar Polars churn**: every bar builds 1-row `pl.DataFrame`s (`from_dicts`, `dict_to_pydf`, `collect`, `row_tuples`, `iter_rows`) for the feed AND each indicator (`ATR`/`KAMA`/`MACD`/`HMA`/`SMA` wrap a *scalar* in a 1-row frame and `vstack`). Polars overhead ≫ the actual arithmetic. Replace `SeriesAPI` per-bar storage + indicators' `stream()` with numpy/scalar incremental; keep Polars for warmup/IO/batch. Expected **2–4× walk** + **fixes chunk-accumulation scaling** (per-bar `vstack`/`extend` accrues Polars chunks → pathological at 10y-Hourly, ~60k chunks). Risk: touches accuracy-critical math → validate bit-for-bit.
- **C — Targeted Polars de-churn** *(medium; partial).* Without full numpy: periodic `rechunk` to bound chunk growth + avoid the worst 1-row frames. Partial walk win + scaling fix.

Also surfaced: `_load_bars_` re-pulls from the DB **every run** (`select.select` ~0.05/run) — subsumed by B for multi-run/Optimization.

---

## 4. CURRENT FOCUS — Connector cBot Download Optimization

**Why now:** can't finalize/validate the engine without data, and the Download itself is the gate (D1/H1 downloadable; **M1 takes "days", ticks ~4h** — see §7). Measured facts: the shared-memory **bridge is fast** (~89k round-trips/s, 11 µs each, ping-pong over the real `TransportAPI`); Python's per-bar work in the Download path is ~0.5 ms/bar; the multi-year M1/tick cost is dominated by **cTrader's own "tick data from server" loading** (documented platform limit — a 2016→now tick backtest is ~2 days on cTrader). So the Python-side **Full buffering** already shipped (`BufferAPI` accumulate mode; `Main` Download+Auto→Full; `BufferingMode {Auto, Full, Manual, Off}` in `Parameter.cs` + `BufferingArgs` in `Robot.cs`) removed the per-flush GIL stalls — user reports "slightly better but not a lot," consistent with cTrader dominating.

**The remaining waste (user's insight, correct):** the cBot still **blocks per bar/tick** on Python's `Complete` action (`SendUpdateBar → SendUpdateComplete → ReceiveAndProcessActions` in `Robot.cs` `OnBarClosed`/`OnTick`). For Download the strategy only extends a dataframe and replies "done", so the per-item lockstep is pointless — and it keeps cTrader's replay on Python's critical path. Goal: **keep the Python connection but detach C# execution from per-item Python acks.**

**Proposed design (user):** a **Delay** parameter for bars + one for ticks, with `Auto | Full | Manual | Off`. `Full` = buffer ALL bars/ticks on the C# side and send in batch at the end; `Auto` (Download) → `Full`; `Manual` = explicit delay-by-N per bars/ticks; `Off` = current per-item lockstep. Requires C#-side `xBar`/`xTick` buffering + a **batch wire format**.

**Open design decisions (next session):**
- **Batch wire format** — the slot is 4096 B (`Transport._BUF_SIZE_`), ~12 bars or ~63 ticks per slot. Either send chunked batches (≤slot) or **enlarge the slot** (e.g. 256 KB–1 MB → thousands/slot). Need a `BarBatch`/`TickBatch` `UpdateID` carrying `count + items`; Python deserializes the batch, processes all, sends **one** `Complete`.
- **Delay-by-N vs Full** — `Full` (all-at-end) is simplest but holds the whole series in C# RAM and risks total loss on mid-run failure; **bounded N** (periodic batch) gives incremental persistence + bounded memory. A **double-buffer** (accumulate batch K+1 in C# while Python digests batch K, only block if Python is behind) fully overlaps cTrader replay with Python work.
- **Honest caveat to re-confirm:** if cTrader's per-bar *production* (tick-precision replay + server fetch) dominates, decoupling removes the ~0.5 ms/bar Python wait but not cTrader's time. Cheap decisive measurement first: instrument `Robot.cs` to log Δ-time between consecutive `OnBarClosed` (cTrader feed rate) vs time spent in `SendUpdate*+ReceiveActions` (the Python lockstep). If the lockstep is a large fraction → batching is a big win; if cTrader dominates → bounded. *(User builds/runs the cBot; agent cannot.)*

**Alternative considered:** a shared-memory **ring buffer / queue** (lock-free producer/consumer, no per-item ack) — most decoupled, but more complex than batch buffering. Batch-with-bounded-N + double-buffer is the recommended balance.

---

## 5. Backlog

- **Optimization** — uncomment `OptimizationAPI` in `Main.py` + export; depends on B (shared dataset) for throughput.
- **Learning** — uncomment `LearningAPI` in `Main.py` + export; depends on `BacktestingAPI` + B.
- **Phase G — Strategy state recovery (B-G-1):** persist Signal/Risk machine state on Live restart. *Sketch:* `State: Union[bytes, None]` on `SessionAPI` (`pl.Binary()`); `EngineAPI.State` maps machine→state name as JSON bytes; `SystemAPI` loads at `deploy()` start, saves on `UpdateID.Shutdown`.
- **Wire up `receive_update_security`** — parse C# security data to enrich `SecurityAPI` (pip size, commission). Sent but codec not consumed.
- **Timeout watchdog (B-D.5-4)** — configurable hung-peer timeout (e.g. 30s → teardown). Current watchdog only detects peer-death via PID.
- **Backtesting CLI param-folder** — RESOLVED: `Main.py` now keys the param tree on `provider.UID` (`Spotware(cTrader)`) not the normalized `args.provider` (`Spotware`).

---

## 6. Known issues (non-blocking)
- **`--profile` not wired to cBot UI.** Invoke the Python CLI with `--profile` to dump `.pstat`.
- **C# platform warnings** — 2× `CA1416` (`MemoryMappedFile.CreateOrOpen`, Windows-only). Expected.
- **C# deprecated order API** — 3× `CS0618` (`PlaceStopOrder`/`PlaceLimitOrder`/`PlaceStopLimitOrder`). Non-breaking.
- **Logging is custom (not stdlib):** `logging.disable()` does nothing; silence via `LoggingAPI` (e.g. `HandlerLoggingAPI().console.set_verbose_level(VerboseLevel.Silent)`). Default class level is `Silent`.

---

## 7. Current data/DB state (2026-06-21)
- `Market.Bar`/`Market.Tick` were **truncated** (cleared 87,666 bars + 72,399,337 ticks from a prior botched M1 download). Re-download in progress: **D1 + H1 bars done; M1 bars and Ticks NOT yet downloaded.**
- **Preload disk cache** (`~/.cache/cAlgo/preload`) still holds OLD EURUSD Daily frames — clear it after re-download so backtests don't serve stale data (token check catches tick-count changes but clear to be safe).
- Engine validation (golden + A/B/C) is **blocked until EURUSD Daily is back** in the DB.
