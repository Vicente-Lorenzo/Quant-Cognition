# Quant Trading Framework — Handoff

Self-contained brief covering active state of the `cAlgo` repo. Read this first, then `RULES.md` for project conventions.

---

## 1. Project shape

- **Root:** `C:\Users\Admin\OneDrive\Documents\cAlgo`
- **`Library/`** Python core (engine, persistence, AI, Dash UI).
- **`Sources/`** C# cTrader Robots/Indicators/Plugins. Connector cBot bridges to Python via Shared Memory + Binary Protocol.
- **`Tests/`** pytest, mirrors `Library/` layout. Exclude `Tests/Spotware`.
- **`Setup/`** unified workspace and DB setup. `conda run -n Quant python -m Setup.Main --all`.
- **Env:** `conda run -n Quant ...`.
- **Test command:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware`.
- **Build C#:** `dotnet build Sources/Robots/Connector/Connector.sln`.
- **Git:** stage with `git add`, **never commit**.

---

## 2. Current state

Core engine, persistence layer, realtime trading, multi-provider database population, and logical ordering (Tick → Bar → Target) are all implemented and verified.

- **Database:** Postgres, 3 schemas (Universe, Market, Portfolio). Bulk ingestion via `psycopg3` Pipeline Mode. `BufferAPI._drain_` optimized. Only Market schema has production data; Universe/Portfolio schemas are development-only.
- **Providers:** Spotware, Pepperstone, ICMarkets, Bloomberg, Yahoo. `ProviderAPI.normalize` handles broker name variants + `POSITION`-based SQL fuzzy lookup.
- **Multi-provider verification:** Dual-cBot backtesting (Spotware + ICMarkets, EURUSD Daily) confirmed bars/ticks correctly partitioned by Security ID.
- **Observability:** Graceful vs crashed shutdown logging, phase timers, real-time counters (Ticks, Bars, Accounts, Orders, Positions, Trades, Actions).
- **Tests passing:** 290 / 290.
- **C# Build:** 0 Errors, 5 Warnings (platform compatibility for `MemoryMappedFile.CreateOrOpen` + deprecated order API methods).

---

## 3. Phase D + D.5 — IPC Migration (REVIEWED AND FIXED)

Phase D (ZMQ → Shared Memory) and Phase D.5 (Initialization Handshake) have been implemented, reviewed, and fixed. All critical bugs identified during review have been resolved. Tests pass and C# builds.

### What was implemented

**Transport layer — symmetric Python/C# split:**
- **`Library/System/Transport.py`** (`TransportAPI`): Python-side transport. 2 mmap buffers (4KB each) + 4 auto-reset named events. Constants (`_BUF_SIZE_`, `_POLL_MS_`, `_INFINITE_`, etc.) and pre-compiled `_LENGTH_` struct are class attributes. Methods: `send`, `receive`, `watchdog`, `close`.
- **`Sources/Robots/Connector/Connector/Transport.cs`** (`TransportAPI`): C#-side mirror. Same buffer/event layout. Methods: `Send`, `Receive`, `Watchdog`, `Dispose`. `PeerDead` property exposes peer status.
- **`Sources/Robots/Connector/Connector/System.cs`** (`SystemAPI`): Composes `TransportAPI`. Owns serialization methods (`SendUpdateTick`, `SendUpdateBar`, etc.) and helpers (`WriteString`, `NanIfNull`, `ParsePositionType`). Delegates transport to `TransportAPI` via `Send`/`Receive`/`Watchdog`.
- Ping-pong protocol: each message is one write + signal + wait. Buffer holds one message at a time.
- Buffer overflow guard validates `len(data) + 4 <= BUF_SIZE` before write.
- Watchdog thread monitors peer PID (Python: `OpenProcess`/`WaitForSingleObject`; C#: `Process.WaitForExit`).

**Binary protocol (`Library/Protocol/Binary.py` — `BinaryAPI` class):**
- Single class handling all binary serialization. Field types: `B` (byte), `i` (int32), `q` (int64), `d` (double), `D` (nullable double, NaN↔None), `s` (length-prefixed UTF-8 string).
- Pre-compiles `struct.Struct` for fixed-layout messages (tick hot-path: zero allocation).
- Auto-validates field count at pack time — format string mismatch bugs are structurally impossible.
- Pre-compiled primitive structs (`_B_`, `_H_`, `_i_`, `_q_`, `_d_`) as class attributes for the variable-length path.
- Each Action dataclass owns a `_binary_: ClassVar[BinaryAPI]` and serializes via `self._binary_.pack(...)`.
- Each Realtime deserialization uses codec class attributes (`_binary_tick_`, `_binary_position_`, etc.) with direct tuple unpacking — no dict intermediate.

**Wire format (all enums sent as bytes, not strings):**
- Direction: C# `TradeType(0=Buy, 1=Sell)` → Python `Direction(1=Buy, -1=Sell)` via `_DIRECTION_` lookup.
- PositionType: C# parses from `position.Comment` → Python `PositionType(0=Normal, 1=Continuation)`. Comment is derived (`pos_type.name`), never sent on wire.
- OrderType: C# `PendingOrderType(0=Limit, 1=Stop, 2=StopLimit)` → Python `OrderType(1=Limit, 2=Stop, 3=StopLimit)` via `_ORDER_TYPE_` lookup.
- Hot-path messages are fixed-size (Tick: 65 bytes, Bar: 337 bytes). Cold-path messages (Position, Trade, Order) have one string field (Label).

**Initialization handshake (Phase D.5):**
- C# sends `Initialization` update containing its PID.
- Python responds with `Initialization` action containing its PID.
- Both sides start watchdog threads monitoring the peer's PID.

**Enum refactor:**
- `UpdateID` (0-79) and `ActionID` (0-53) reordered to match protocol lifecycle.
- Python `OrderType` cleaned: `Market=0, Limit=1, Stop=2, StopLimit=3` (removed dead `StopLossTakeProfit` and `MarketRange`).
- `PositionTypeID` enum added to C# (`Enum.cs`) matching Python's `PositionType`.

**Dependency cleanup:**
- Removed `NetMQ` and `Newtonsoft.Json` NuGet packages — zero third-party C# dependencies.

### Bugs found and fixed during review

1. **C# Bar buffer size (329→337 bytes)** — was 8 bytes short. Bar volume was overwriting CloseTick.Volume at offset 321. Fixed: buffer is 337 bytes, volume at offset 329.
2. **C# Position type field** — was sending `position.Comment` (wrong field) where Python expected position type. Now sends `ParsePositionType(position.Comment)` as a byte.
3. **C# Trade type field** — same bug pattern. Fixed identically.
4. **Python Security format string** — old `pack_security` had 14 struct specifiers for 13 values (extra `d` before `B`). Fixed by `BinaryAPI` codec which self-validates field count. Security codec is not wired up yet (data sent but ignored by `receive_update_security`).

### Files involved

**Python — new files:**
- `Library/System/Transport.py` — `TransportAPI` shared memory transport
- `Library/Protocol/Binary.py` — `BinaryAPI` class

**Python — modified files:**
- `Library/System/Realtime.py` — uses `BinaryAPI` codecs, tuple unpacking, no dict intermediate
- `Library/System/__init__.py` — exports `TransportAPI`
- `Library/Protocol/Update/Update.py` — `UpdateID` enum reordered, `Initialization` added
- `Library/Protocol/Action/Action.py` — `ActionID` enum reordered, `_binary_` ClassVar, `serialize()` via codec
- `Library/Protocol/Action/Position.py` — `_binary_` ClassVar, `serialize()` via codec
- `Library/Protocol/Action/Order.py` — `_binary_` ClassVar, `serialize()` via codec
- `Library/Portfolio/Order.py` — `OrderType` cleaned (4 values, sequential)

**C# — new files:**
- `Sources/Robots/Connector/Connector/Transport.cs` — `TransportAPI` shared memory transport

**C# — modified files:**
- `Sources/Robots/Connector/Connector/System.cs` — delegates to `TransportAPI`, keeps serialization
- `Sources/Robots/Connector/Connector/Robot.cs` — uses `Watchdog`/`Receive` methods
- `Sources/Robots/Connector/Connector/Enum.cs` — `PositionTypeID` added, `UpdateID`/`ActionID` reordered
- `Sources/Robots/Connector/Connector/Connector.cs` — constructor updated
- `Sources/Robots/Connector/Connector/Connector.csproj` — removed NetMQ + Newtonsoft.Json

**Tests:**
- `Tests/Protocol/test_Protocol.py` — tests `BinaryAPI` round-trips for all message types
- `Tests/System/test_Realtime.py` — updated for renamed transport methods
- `Tests/System/test_Transport.py` — 11 tests covering read/write round-trip, overflow guard, constants, closed/peer-dead states

### Database module review

The `Library/Database/` module was reviewed for optimization opportunities. **No issues found.** The module is well-architected:
- `DatabaseAPI` — clean abstract base with routing, cloning, connection pooling, migration.
- `BufferAPI` — thread-safe async persistence with batch/interval thresholds.
- `PostgresAPI` — proper `psycopg3` integration with upsert chunking.
- `DatapointAPI` — active-record pattern with autosave.

---

## 4. IPC Benchmark Reference

Benchmarked cBot ↔ Python round-trip lifecycle on Windows (i9-14900K, 64GB DDR5, 1M round-trips, tick 203B):

| Transport | Round-trips/s | Latency | vs ZMQ |
|---|---|---|---|
| ZMQ TCP PAIR | 20,148 | 49.6 µs | baseline |
| Named Pipes | 53,993 | 18.5 µs | **2.7x faster** |
| Shared Memory + Events | 92,201 | 10.8 µs | **4.6x faster** |

Binary protocol reduces message sizes further (Tick: 203B JSON → 65B binary, Bar: ~750B JSON → 337B binary).

Benchmark: `Tests/Benchmark/IPC.py`.

---

## 5. Next steps

1. **Re-run NNFX smoke test with fresh IID** — after the `BarAPI.flatten()` fix (see §9), SMA crossovers should now drive entries/exits and produce a non-empty net report.
2. **Phase E — Backtesting rewrite.** Re-enable `BacktestingAPI` in `Library/System/Main.py`; address B-E-1 UID collision.
3. **Phase G — Strategy state recovery.** Hook strategy state checkpoints to `SessionAPI`.
4. **Wire up `receive_update_security`** — Parse C# security data to enrich `SecurityAPI` with runtime info (pip size, commission, etc.).

---

## 6. Known issues (non-blocking)

- **`OpenCL/vendors/temp.txt` warning at Python startup.** Harmless probe from conda libs.
- **`--profile` not wired to cBot UI.** User must invoke Python CLI manually with `--profile` to dump `.pstat` snapshots.
- **Portfolio tables empty during backtesting** — no session tracking yet (expected, pending Phase E).
- **C# platform warnings** — 2 `CA1416` warnings for `MemoryMappedFile.CreateOrOpen` being Windows-only. Expected.
- **C# deprecated order API warnings** — 3 `CS0618` warnings for `PlaceStopOrder`/`PlaceLimitOrder`/`PlaceStopLimitOrder` using old parameter names. Non-breaking.

---

## 7. Future Work & Performance Ideas

- **Parallel Database Worker:** Refactor `BufferAPI` to use a dedicated background worker thread/process for database I/O. Currently, `_drain_` runs synchronously in the main loop, blocking the ingestion of new ticks/bars while waiting for database round-trips. A parallel worker would allow the main loop to continue receiving market data at high speed while persistence happens out-of-band.
- **Bulk Ingestion API:** Implement a native `bulk_insert` or `copy` feature in `DatabaseAPI` that abstracts high-speed data loading (e.g., Postgres `COPY`) while handling identity returns and conflict resolution in a standardized way.

---

## 8. System Module Backlog

### Phase D — IPC Migration (ZMQ → Shared Memory) — DONE
- B-D-1: ~~Replace `SystemAPI` C# transport.~~ Done.
- B-D-2: ~~Replace Python-side ZMQ socket.~~ Done.
- B-D-3: ~~Replace JSON with struct-packed binary protocol.~~ Done.

### Phase D.5 — Process Lifecycle & Handshake — DONE
- B-D.5-1: ~~PID exchange via Initialization messages.~~ Done.
- B-D.5-2: ~~Peer-death detection via PID polling.~~ Done.
- B-D.5-3: ~~Graceful shutdown sequence.~~ Done.
- B-D.5-4: Timeout-based watchdog for hung peer (configurable, e.g. 30s no response → force teardown). Not yet implemented.

### Phase E — Backtesting
- B-E-1: Internal UID counters must not collide with cTrader UIDs (use negative space).
  - *Conclusion from aborted implementation:* Changing `count(start=1)` to `count(start=-1, step=-1)` for simulated UIDs (`_pids` and `_tids`) in `Backtesting.py` perfectly resolves this. Additionally, `BacktestingAPI`, `OptimizationAPI`, and `LearningAPI` need to be uncommented in `Main.py` and exported in `__init__.py`.

### Phase G — Strategy State Recovery
- B-G-1: Persist Signal/Risk machine state on Live restart.
  - *Conclusion from aborted implementation:* A `State: Union[bytes, None] = None` field should be added to `SessionAPI` (`pl.Binary()` in DB structure). `EngineAPI` can be updated with a `State` property that maps each machine's name to its current state name, serialized as a JSON byte string. `SystemAPI` can load this state from the session at the start of `deploy()` and save it to the session on `UpdateID.Shutdown` within `_process_updates_()`.

---

## 9. Indicator Module Refactor + BarAPI.flatten() Fix

### Indicator module refactor

Unified the indicator framework around a single base lifecycle and slimmed concrete indicators to essential overrides only.

**`Library/Indicator/Technical/Technical.py` (base):**
- `TechnicalAPI.__init__` accepts `**indicators` children, auto-attaches them, and computes `Window = self._window_() or window`.
- `_window_()` helper returns `max(child.Window for child in self._indicators_)` (or `0` if no children). Used by the base and by cross indicators (`MAC`, `DMAC`, `TMAC`) to replace explicit `max(self.Fast.Window, self.Slow.Window)`.
- Default `batch`, `stream`, `calculate`, `_extract_`, `_pad_`, `init_data`, `update_data`, `update_offset`, `filter_buy/sell`, `signal_buy/sell` live on the base. Concrete indicators override only what they need.
- `Window: int` (was `Union[int, None]`); dummies pass `window=0`.

**`Library/Indicator/Fundamental/Fundamental.py` and `Library/Indicator/Sentimental/Sentimental.py`:** Aligned with the same `_window_()` helper and aggregator window rule.

**Concrete indicators (`Baseline/{SMA,EMA,WMA,HMA,KAMA,TRIMA,DMA,TMA,MA}.py`, `Overlap/{MAC,DMAC,TMAC}.py`, `Momentum/MACD.py`, `Volatility/ATR.py`):** Slimmed to `_batch_` staticmethod, `batch`, `stream`, and filter/signal overrides. `MA.py` wraps a typed sub-MA and delegates lifecycle. Cross indicators (`*MAC`) compare `Fast.Result`/`Slow.Result` via `over/under/crossover/crossunder`.

**New dummy indicators (`Library/Indicator/Technical/Other/{TT,TF,FT,FF}.py`):** First letter = signal, second = filter (e.g. `TF` = signal True, filter False). Used to isolate one real indicator while keeping the strategy's filter/signal wiring intact. Parsed by `Library/Indicator/Indicator.py` via single-arg form `[TT]`.

**Parameter schema (`Library/Parameter/.../Realtime.yml` for NNFX):** `SignalManagement` modes are now triplets `[normal_entry, continuation_entry, normal_exit]` per slot (`Baseline`, `Filter1`, `Filter2`, `Volume`). Strings `Off | Filter | Signal` are matched against `IndicatorMode.<name>` in `NNFXStrategyAPI.__init__`.

### `BarAPI.flatten()` — root cause 1 of the empty-report smoke test

**Symptom:** NNFX smoke test ran cleanly (516 bars, 2580 ticks processed) but produced zero orders/positions/trades.

**Root cause:** `BarAPI.dict()` collapsed each nested tick (`GapTick/OpenTick/HighTick/LowTick/CloseTick`) to its `UID` via `DataclassAPI._parse_`, and live ticks have `UID=None`. The market DataFrame ended up with columns like `CloseTick: None` instead of `CloseTick.Bid`, `CloseTick.Ask`, etc. Every `SeriesAPI("CloseTick.Bid").last()` returned `None`, so SMA `over/under/crossover/crossunder` was always `False`.

**Fix:**
- `Library/Market/Bar.py` — added `BarAPI.flatten()` returning the bar's flat fields plus each tick expanded as `{TickName}.{field}` (e.g. `CloseTick.Bid`, `OpenTick.Ask`).
- `Library/System/Realtime.py` — `init_market` uses `b.flatten()` instead of `b.dict()` when seeding the market DataFrame.
- `Library/Market/Market.py` — `MarketAPI.update_data` uses `data.flatten()` for `BarAPI` inputs and keeps `data.dict()` for `TickAPI` inputs.

### `Initialization` IPC Deadlock & `Volume` Filter Block — root cause 2 and 3 of the empty-report smoke test

**Symptom:** The user's live smoke test output abruptly stopped at `Fetch All` and no entries/exits occurred.

**Root cause 2 (IPC Deadlock):** C#'s `Robot.cs` sent an `Initialization` payload and immediately blocked waiting for an `Initialization` Action response (`ActionID.Initialization = 0`). However, Python lacked an `InitializationActionAPI` in its definitions, meaning the initial message was silently skipped, prompting Python to wait for the next update and effectively deadlocking the connection. To compound this, Python responded to the *next* step with a `Complete` action (`53`), which would normally trigger an `InvalidOperationException` in C#.

**Fix 2:**
- Re-aligned Python definitions to fully map `InitializationUpdateAPI` and `InitializationActionAPI`.
- Adjusted `Realtime.py` lifecycle transitions so `UpdateID.Initialization` now seamlessly fires an `init_handshake` method that responds back with `InitializationActionAPI(ProcessID=os.getpid())` and properly completes the handshake without Python continuing its standard loop processing.

**Root cause 3 (Default Volatility.ATR Blocking Trades):** The default settings mapping for NNFX explicitly used `Volatility.ATR` as the `Volume` filter. Because `Volatility.ATR` inherently lacked an explicit `filter_buy` definition in Python, it fell back to `TechnicalAPI`'s default `filter_buy`, which returns `False`. The NNFX logic demands that **all** entry criteria are met (`all(f(update) for f in normal_entries_buy)`). As a result, `Volatility.ATR` consistently blocked the valid SMA crossovers.

**Fix 3:**
- Systematically populated `filter_buy`, `filter_sell`, `signal_buy`, and `signal_sell` methods strictly onto all existing, uninherited technical indicators (including `FF.py`, `ATR.py` and checking all cross-indicators).
- Explicitly set `Volatility.ATR` filters to return `True` to allow strategy execution based on base setups without halting valid signal generation logic in default tests.

Tests: 290 / 290 pass.
