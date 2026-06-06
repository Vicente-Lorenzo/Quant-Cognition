# Quant Trading Framework — Handoff

Forward-looking brief for the `cAlgo` repo. Read this for orientation and the active roadmap, then `RULES.md` for conventions.

---

## 1. Orientation

- **Root:** `C:\Users\Admin\OneDrive\Documents\cAlgo`
- **`Library/`** Python core (engine, persistence, AI, Dash UI).
- **`Sources/`** C# cTrader Robots/Indicators/Plugins. Connector cBot bridges to Python via Shared Memory + Binary Protocol.
- **`Tests/`** pytest, mirrors `Library/` layout. Exclude `Tests/Spotware`.
- **`Setup/`** unified workspace and DB setup. `conda run -n Quant python -m Setup.Main --all`.
- **Env:** `conda run -n Quant ...`.
- **Test command:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware`.
- **Build C#:** `dotnet build Sources/Robots/Connector/Connector.sln`.
- **Git:** stage with `git add`, **never commit**.

The realtime path (Live/Simulation/Testing) is complete and validated: the cBot streams updates over shared memory, Python (`RealtimeAPI`) runs the strategy through the shared lifecycle and produces reports that reconcile **exactly** with cTrader. The NNFX smoke test (EURUSD Daily, 2023-01-01 → 2024-01-01) is the validated golden reference for everything below.

---

## 2. Next focus — Phase E: decoupled Python Backtesting

**Goal:** mimic the cTrader backtesting engine in Python so backtests run without cTrader. The simulator replaces the cBot+broker role: it reads market data from the DB, simulates execution (spread, commission, swap, SL/TP, margin), and feeds the **same** `UpdateID` stream into the **same** `SystemAPI.deploy()` lifecycle and strategy/engine code used by realtime. Strategy and engine code stay untouched; only the data-source + broker-simulation layer differs.

**Validation method:** the NNFX golden report (`Reports/2026-06-06 02-02-03 …`) is the template. The backtester is correct when its `trades.csv` / `deals.csv` / `net.csv` reproduce it. This is why the smoke-test accuracy work mattered.

### Key facts established
- `Library/System/Backtesting.py` exists but is **pre-refactor** — it targets the old API (`Library.Classes`, `DatabaseAPI(broker=…)`, `Bar(*row)`, `MachineAPI("…")`, `on_complete`, old `UpdateID`/`ActionID` names, `deploy(strategy=…)`). It is **not runnable** and needs a near-total rewrite, but its **domain logic is the asset to port**: the fee model (spread/commission/swap with all `CommissionMode`/`SwapMode` cases + overnight/rollover/DST), the account-currency conversion logic, the intrabar OHLC walk, and the SL/TP fill mechanics.
- The new `SystemAPI` (base) already owns `deploy()`, `_process_updates_()`, `_report_()`, `_export_()`. `RealtimeAPI` is the working reference for driving the lifecycle (warmup → market init → execution → report).
- **Data dependency (decisive):** the `Market` schema currently holds **Daily (D1) bars only** for one security; the `Tick` table is just the 5 OHLC ticks per daily bar — **there is no dense intraday tick stream**. However, each daily bar's Gap/Open/High/Low/Close ticks carry **real intraday timestamps** (the actual time the high/low printed). This is exactly the granularity to replay cTrader's daily-bar backtest path: walk each bar as Gap → Open → (High, Low in timestamp order) → Close, apply spread to derive ask/bid, and check SL/TP at each step. A true tick-by-tick mirror would require ingesting intraday data; the OHLC-path approach is what the existing data supports and what the rewrite should target first.
- B-E-1 (UID collisions): simulated UIDs must use negative space — `count(start=-1, step=-1)` for `_pids`/`_tids` so they never clash with cTrader UIDs.

### Files to touch
- **Rewrite** `Library/System/Backtesting.py` (`BacktestingAPI(SystemAPI)`):
  - Implement the abstract `receive_update_*` methods as queue pops, matching the **exact pop order** the base `_process_updates_()` expects (e.g. for `OpenedBuyPosition` it pops bar then position).
  - Implement `send_action()` as the broker: interpret `OpenBuyPosition`/`CloseBuyPosition`/`Modify…` actions, mutate simulated positions, enqueue resulting updates.
  - Implement `receive_update_id()` as the simulation driver (bar/tick walk + action-result queue + SL/TP/target checks), returning `Shutdown` when exhausted.
  - Implement `system_management()` (warmup seeded from DB `pull_bars`, then `init_data` once + `update_data` per bar — mirror `RealtimeAPI`, not the old offset approach).
  - Port the fee/conversion/overnight logic to the new entities (`PositionAPI`, `TradeAPI`, `AccountAPI`, `SecurityAPI`, `BarAPI`, `TickAPI`) and new DB access (`PostgresAPI` + `MarketAPI.pull_bars`).
- **`Library/System/Main.py`** — uncomment/restore the `BacktestingAPI` construction in `_system_()` (lines ~151-165). CLI parser is already wired.
- **`Library/System/__init__.py`** — export `BacktestingAPI`.
- **`Tests/System/test_Backtesting.py`** — new: assert the backtester reproduces the golden report tables.

### Open decision before/while implementing
Fill fidelity: (A) ingest intraday (tick/m1) data so fills match cTrader bit-for-bit, or (B) OHLC-path approximation from the daily ticks we already have. Recommendation: start with **B** (data already present; reproduces bar-close-driven trades exactly, approximates intrabar SL/TP), measure divergence vs the golden report, then decide if **A** is worth the ingestion effort.

---

## 3. Other backlog

### Phase E follow-ons (after Backtesting)
- **Optimization** — uncomment `OptimizationAPI` in `Main.py` + export; depends on a working `BacktestingAPI`.
- **Learning** — uncomment `LearningAPI` in `Main.py` + export; depends on a working `BacktestingAPI`.

### Phase G — Strategy state recovery
- B-G-1: persist Signal/Risk machine state on Live restart.
  - *Sketch:* add `State: Union[bytes, None] = None` to `SessionAPI` (`pl.Binary()` in DB structure). Give `EngineAPI` a `State` property mapping each machine name → current state name, serialized as JSON bytes. `SystemAPI` loads it from the session at the start of `deploy()` and saves it on `UpdateID.Shutdown` in `_process_updates_()`.

### Smaller items
- **Wire up `receive_update_security`** — parse C# security data to enrich `SecurityAPI` with runtime info (pip size, commission, etc.). Currently sent but the codec is not consumed.
- **B-D.5-4 timeout watchdog** — configurable timeout for a hung peer (e.g. 30s no response → force teardown). Current watchdog only detects peer-death via PID.

---

## 4. Known issues (non-blocking)

- **`OpenCL/vendors/temp.txt` warning at Python startup.** Harmless probe from conda libs.
- **`--profile` not wired to cBot UI.** Invoke the Python CLI manually with `--profile` to dump `.pstat` snapshots.
- **Portfolio tables empty during backtesting** — no session tracking yet (expected until Phase E).
- **C# platform warnings** — 2 `CA1416` for `MemoryMappedFile.CreateOrOpen` (Windows-only). Expected.
- **C# deprecated order API warnings** — 3 `CS0618` for `PlaceStopOrder`/`PlaceLimitOrder`/`PlaceStopLimitOrder` old parameter names. Non-breaking.

---

## 5. Future work & performance ideas

- **Parallel database worker:** refactor `BufferAPI` so DB I/O runs on a dedicated background worker; `_drain_` currently runs synchronously in the main loop, blocking ingestion during DB round-trips.
- **Bulk ingestion API:** native `bulk_insert`/`copy` in `DatabaseAPI` (e.g. Postgres `COPY`) abstracting high-speed loading with identity returns and conflict resolution.
- **Intraday data ingestion:** prerequisite for tick-fidelity backtesting (Phase E decision A above).
