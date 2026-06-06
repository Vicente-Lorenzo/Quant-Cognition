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

> **This section is a self-contained brief for a fresh chat.** It carries the full intent, the design, the codebase findings, and the user's decisions. The user will still adjust details in the implementation chat. Read this whole section, then the "Reference files to read first" list, before writing any code.

### 2.1 Goal & core principle

Mimic the cTrader backtesting engine in Python so backtests run **fully decoupled from cTrader**. The breakthrough framing: **the C# Connector cBot (`Sources/Robots/Connector/Connector/Robot.cs`) is already a broker simulator.** The backtester is simply a **second, in-process broker simulator written in Python**, driven by DB market data instead of cTrader, that emits the **same `UpdateID` protocol** into the **same `SystemAPI.deploy()` loop** the realtime path uses.

**Therefore strategy, engine, indicators, portfolio, and reporting code stay byte-for-byte untouched.** Only the data-source + broker-simulation layer is new. This is also why the realtime golden report is a valid oracle — the backtester runs the exact same downstream code that produced it.

This is a **ground-up re-engineering**, not a port. The legacy `Library/System/Backtesting.py` is pre-refactor and not runnable (old API: `Library.Classes`, `DatabaseAPI(broker=…)`, `Bar(*row)`, `MachineAPI("…")`, `on_complete`, old `UpdateID`/`ActionID` names, `deploy(strategy=…)`). Its **only** salvage value is the **domain math**: the fee model (spread/commission/swap across all `CommissionMode`/`SwapMode` cases) and especially `calculate_overnights` (overnight/rollover/DST logic). Everything else gets rewritten against the current dataclasses (`Library/Market`, `Library/Portfolio`, `Library/Universe`) and the current protocol (`Library/Protocol`).

### 2.2 User decisions (locked for the first pass)

1. **Single file.** Implement as one cohesive `Library/System/Backtesting.py` (`BacktestingAPI(SystemAPI)`), mirroring the one-file-per-system convention of `Realtime.py` — **not** a `Backtesting/` subpackage. (Internal helper classes for feed/broker/fees are fine within the file.)
2. **Bar mode (fidelity mode 1) first.** Build and validate the bar-only feed first, using the daily OHLC ticks already in the DB. Lower-fidelity by design — see the validation caveat in 2.6.
3. **Accurate fees first.** Port the contract-driven `Accurate` spread/commission/swap modes first (these match cTrader and the golden report); add the other modes (Points/Pips/Percentage/Amount/Random) afterward.

### 2.3 Full target design (the eventual feature set; build incrementally per 2.2)

**Three fidelity modes** (selectable; all feed one uniform intrabar event stream so the broker logic is identical across modes):
- **(1) Bar mode** — only bar data, no intrabar source. Reconstruct the intrabar path from the bar's own Gap/Open/High/Low/Close ticks. **Least accurate.** *(Build first.)*
- **(2) m1 mode** — use m1 bars as the intrabar path inside each target bar. m1 data must first be downloaded via the **Download strategy**. **Slightly more accurate.**
- **(3) Tick mode** — use the raw tick stream. Tick data must first be downloaded via realtime with **Tick Stream = All**. **Should equal realtime-system results.**

**Configurable fee modes** for spread, commission, and swap — each an enum-driven model: `Points | Pips | Percentage | Amount | Accurate | Random`. *(Accurate first.)* **Random** = draw uniformly within configured thresholds (seed it for reproducibility) — this is a new mode the user wants added to model fee uncertainty. Port the legacy account-currency conversion (base/quote) logic and `calculate_overnights` for the swap math.

**Parallel-ready from the start.** The backtester must run efficiently in parallel for the downstream **Optimization** and **Learning** systems (CPU-bound → favor `ProcessPoolExecutor`; the GIL rules out threads for real speedup). Design implications:
- Pull market data **once** into an immutable, injectable dataset that is shared read-only across workers (replaces the legacy "pull in `__init__` unless preset on the class" hack — keep the "inject if already set" capability but make it explicit and clean).
- Each run owns its own broker/account/portfolio/UID state; nothing mutable is shared.
- DB connections cloned per worker (`DatabaseAPI` supports cloning).
- Keep the inner backtest self-contained/picklable so a pool can fan it out.

### 2.4 Event sequencing & no look-ahead (mirror `Robot.cs` exactly)

cTrader's per-bar-boundary order, which the simulator must reproduce: **`OnBarClosed` → `OnTick` (open tick) → `OnBarOpened`.** Confirmed mechanics from `Robot.cs`:
- The cBot keeps **one accumulating `xBar` (`_bar_`)**. On each `OnTick`: update High/Low if exceeded, set Close. On `OnBarClosed`: set volume, send `BarClosed`, then **`_bar_.GapTick = _bar_.CloseTick`** (next bar's gap = prior close) and `_bar_.Timestamp = lastBar.OpenTime`. On `OnBarOpened`: reset Open/High/Low/Close to the current tick, volume 0, send `BarOpened`.
- **No look-ahead is structural, not a check:** the strategy only sees a bar's indicators at *that bar's* `BarClosed`; entries fill on the *next* open tick / `BarOpened`. As long as the broker never sees a price beyond the current simulated timestamp, look-ahead is impossible. (See `Library/Market/Series.py` `_offset_`/`last()` — the offset is how "current bar" is enforced; the backtester must drive it like `RealtimeAPI` does, via streaming `init_data` once + `update_data` per bar, **not** the legacy `update_offset` walk.)

**Stream modes already exist in `Robot.cs`** and define the fidelity contract: `TickStreamMode` = `Off | Target | All | Auto`. The golden NNFX run used **`Target`** (only ticks crossing SL/TP targets, plus the 5 OHLC ticks per bar). `All` = every tick = realtime-equal (maps to fidelity mode 3). `BarStreamMode` = `Off | All | Auto`. The Python backtester reproduces these behaviors itself.

### 2.5 Protocol completeness (the legacy never did this)

The simulator must emit the full update vocabulary the cBot emits — the legacy backtester predates most of it. Required: `BarOpened`, `Execution`, the **entire Order update family** (Stop/Limit/StopLimit × Opened/Modified*/Closed/Filled/Expired), position updates, and position+trade pairs. Mirror `Robot.cs`'s `ResolveOrderUpdateID` mapping precisely. Critical implementation detail: the base `SystemAPI._process_updates_()` pops sub-objects in a **fixed order** (e.g. for `OpenedBuyPosition` it pops **bar then position**; for closes it pops a position+trade pair). The backtester's `receive_update_*` methods must enqueue/pop in that exact order.

### 2.6 Validation method & caveat

Oracle: the realtime golden report at `Reports/2026-06-06 02-02-03 d1b07c7e-3d42-43f6-97d9-aa47356d3674` (NNFX, EURUSD Daily, 2023-01-01 → 2024-01-01). "Correct" = the backtester's `trades.csv` / `deals.csv` / `net.csv` reproduce it.

**Caveat the user is aware of:** that golden report was generated from cTrader **tick/target** data, so **bar mode (mode 1) will NOT reproduce it exactly** — intrabar SL/TP exits (e.g. trades 4 & 5's stop-outs, PID26's trailing-stop close at 1.08982) fired at millisecond timestamps that bar-only data cannot recover. Expect bar-close/at-open-driven trades to match closely while intrabar exits diverge. Mode 1 proves the scaffolding bottom-up; **mode 3 (tick) is what should match the golden report bit-for-bit.** When validating mode 1, either accept the known divergence or compare against a fresh cTrader **bar-only** backtest as a like-for-like oracle. (This is one of the things the user expects to adjust in the implementation chat.)

### 2.7 Data reality (verified against the live DB)

- `Market` schema holds **Daily (`D1`) bars only**, one security, 2012→2026 (3628 bars). The `Tick` table's ~19k rows are just the **5 OHLC ticks per daily bar**, not a dense intraday stream.
- **But** each daily bar's Gap/Open/High/Low/Close ticks carry **real intraday timestamps** (verified: e.g. the 2023-01-04 daily bar's high printed at `2023-01-06 20:32:56`, low at `12:07:04`, open `22:05:00.003`, close `21:56:58`). This is exactly the granularity bar mode needs: walk Gap → Open → (High, Low in timestamp order) → Close, apply spread to derive ask/bid, check SL/TP at each step.
- Mode 2 (m1) and mode 3 (tick) require **ingesting** the finer data first (Download strategy for m1; realtime + Tick Stream = All for ticks), stored in the same `Market.Bar` (with the m1 `Timeframe`) / `Market.Tick` tables.

### 2.8 Implementation checklist (single file `Library/System/Backtesting.py`)

`BacktestingAPI(SystemAPI)` must implement the abstract surface:
- **`receive_update_id()`** — the simulation driver / clock. Walk the feed (bar mode: the OHLC-tick path), maintain the `_bar_` accumulator, emit `BarClosed → Tick(open) → BarOpened` at boundaries, run SL/TP + ask/bid-target checks per intrabar step, drain the action-result queue first, and return `UpdateID.Shutdown` when the feed is exhausted.
- **`send_action(action)`** — the broker. Interpret `OpenBuy/SellPosition`, `CloseBuy/SellPosition`, `Modify*Position*`, the Order actions, and the `AskAboveTarget`/etc. target-setters; mutate simulated positions/orders; enqueue the resulting updates (matching `_process_updates_` pop order). SL/TP arrive as **pip distances** on open (as in `Robot.cs` `ProcessActionOpenPosition`).
- **`receive_update_account/security/tick/bar/order/position/trade/position_trade/denied/exception`** — pop pre-built domain objects from the queue in the exact expected order.
- **`system_management()`** — warmup seeded from `MarketAPI.pull_bars` (like `RealtimeAPI`), then `Market.init_data` once + `update_data` per executed bar; `Initialization → Execution → Termination` machine; report on shutdown.
- **`run()`** — seed initial Account + Security + Complete, then `self.deploy()`.
- Fee/conversion/overnight math ported from legacy onto `PositionAPI`/`TradeAPI`/`AccountAPI`/`SecurityAPI`/`BarAPI`/`TickAPI` + `PostgresAPI` + `MarketAPI.pull_bars`/`pull_ticks`.
- **B-E-1 (UID collisions):** simulated `_pids`/`_tids` use negative space — `count(start=-1, step=-1)` — so they never clash with cTrader UIDs.

Wiring (parser already exists in `Main.py`):
- **`Library/System/Main.py`** — uncomment/restore the `BacktestingAPI(...)` construction in `_system_()` (currently `case SystemType.Backtesting: return None` with the body commented out, ~lines 151-165). Note it constructs from `parameters.Backtesting[args.strategy]` and passes `account`/`spread`/`commission`/`swap` tuples + `start`/`stop`.
- **`Library/System/__init__.py`** — export `BacktestingAPI`.
- **`Tests/System/test_Backtesting.py`** — new: assert reproduction of the golden tables (mind the 2.6 caveat for mode 1).

### 2.9 Reference files to read first (in the implementation chat)

- `Library/System/Realtime.py` — **the working `SystemAPI` reference.** The backtester is its sibling; copy the lifecycle/warmup/streaming/report patterns.
- `Library/System/System.py` — the shared base: `deploy()`, `_process_updates_()` (study the **exact pop order** per `UpdateID`), `_report_()`, `_export_()`, the abstract methods to implement.
- `Sources/Robots/Connector/Connector/Robot.cs` — **the broker behavior to mirror** (the `_bar_` accumulator, event sequencing, gap-tick handoff, `ResolveOrderUpdateID`, action handlers, stream modes, warmup/verification).
- `Library/System/Backtesting.py` (legacy) — **fee/conversion/overnight math only**; ignore its structure/API.
- `Library/Protocol/Update/Update.py` + `Library/Protocol/Action/Action.py` — the `UpdateID`/`ActionID` vocabularies and the update/action dataclasses to emit/consume.
- `Library/Market/Series.py` + `Library/Market/Market.py` — `_offset_`/`last()` (no-look-ahead mechanics), `init_data`/`update_data`, `pull_bars`/`pull_ticks`.
- `Library/Market/Bar.py`, `Library/Market/Tick.py`, `Library/Portfolio/{Position,Trade,Order,Account}.py`, `Library/Universe/{Security,Contract,Timeframe}.py` — current dataclass shapes to construct.

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
- **Intraday data ingestion:** prerequisite for backtesting fidelity modes 2 (m1, via Download strategy) and 3 (tick, via Tick Stream = All) — see §2.3/§2.7.
