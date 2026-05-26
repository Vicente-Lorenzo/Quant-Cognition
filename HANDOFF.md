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

- **Database:** Postgres, 3 schemas (Universe, Market, Portfolio). Bulk ingestion via `psycopg3` Pipeline Mode. `BufferAPI._drain_` optimized.
- **Providers:** Spotware, Pepperstone, ICMarkets, Bloomberg, Yahoo. `ProviderAPI.normalize` handles broker name variants + `POSITION`-based SQL fuzzy lookup.
- **Multi-provider verification:** Dual-cBot backtesting (Spotware + ICMarkets, EURUSD Daily) confirmed bars/ticks correctly partitioned by Security ID.
- **Observability:** Graceful vs crashed shutdown logging, phase timers, real-time counters (Ticks, Bars, Accounts, Orders, Positions, Trades, Actions).
- **Tests passing:** 276 / 276.
- **C# Build:** 0 Errors, 2 Warnings (platform compatibility for `MemoryMappedFile.CreateOrOpen`, expected on Windows-only system).

---

## 3. Phase D + D.5 — IPC Migration (PENDING REVIEW)

Phase D (ZMQ → Shared Memory) and Phase D.5 (Initialization Handshake) have been implemented but require thorough manual review before being considered complete. All tests pass and C# builds, but the changes are large and touch the core communication layer.

### What was done

**Transport layer replacement:**
- Removed ZMQ TCP PAIR sockets and JSON serialization entirely.
- Replaced with Shared Memory (`mmap` / `MemoryMappedFile`) + Named Events (`EventWaitHandle`) for IPC.
- New file `Library/System/Transport.py` — Python transport: 2 mmap buffers (4KB each) + 4 auto-reset named events (`cAlgo_{iid}_ur`, `_uc`, `_ar`, `_ac`).
- C# `System.cs` rewritten — `MemoryMappedFile.CreateOrOpen` + `EventWaitHandle`, binary read/write via `Buffer.BlockCopy`.

**Binary protocol:**
- New file `Library/Protocol/Binary.py` — struct-packed binary serialization for all message types.
- Hot-path messages are fixed-size (Tick: 65 bytes, Bar: 329 bytes, Complete/Shutdown: 1 byte). No field names, no JSON overhead.
- Cold-path messages (Account, Security, Order, Position, Trade, Denied, Exception) use length-prefixed UTF-8 strings.
- Nullable convention: `NaN` for optional floats, `0` for optional timestamps, `-1` for optional IDs.
- C# action parsing in `Robot.cs` now reads binary directly via `BitConverter` / `ReadString`.

**Initialization handshake (Phase D.5):**
- C# sends `Initialization` update containing its PID as the very first message after launching Python.
- Python responds with `Initialization` action containing its PID.
- Both sides start watchdog threads monitoring the peer's PID via `OpenProcess`/`WaitForSingleObject`.
- PID file mechanism (`cAlgo_{iid}.pid`) completely removed — no more temp file writes/reads.

**Enum refactor:**
- `UpdateID` (0-79) and `ActionID` (0-53) reordered to match protocol lifecycle: `Initialization → Account → Security → Tick → Bar → Targets → Orders (Stop/Limit/StopLimit) → Positions → Complete → Denied → Exception → Shutdown`.
- Both Python and C# enums updated in lockstep.

**Dependency cleanup:**
- Removed `NetMQ` and `Newtonsoft.Json` NuGet packages from `Connector.csproj` — zero third-party dependencies.

### Files changed

**Python — new files:**
- `Library/System/Transport.py` — shared memory transport
- `Library/Protocol/Binary.py` — binary pack/unpack for all message types

**Python — modified files:**
- `Library/System/Realtime.py` — replaced ZMQ with TransportAPI, JSON with binary unpack, added handshake, removed PID file
- `Library/System/Main.py` — removed `--pid` CLI argument (Python gets cTrader PID from Initialization update)
- `Library/System/__init__.py` — exports TransportAPI
- `Library/Protocol/Update/Update.py` — UpdateID enum reordered, Initialization added
- `Library/Protocol/Action/Action.py` — ActionID enum reordered, Initialization added, `serialize()` returns `bytes`
- `Library/Protocol/Action/Position.py` — all position action `serialize()` methods return binary bytes
- `Library/Protocol/Action/Order.py` — all order action `serialize()` methods return binary bytes
- `Tests/Protocol/test_Protocol.py` — updated for binary serialization + new binary round-trip tests
- `Tests/System/test_Realtime.py` — mocks TransportAPI instead of ZMQ socket

**C# — modified files:**
- `Sources/Robots/Connector/Connector/System.cs` — full rewrite: MemoryMappedFile + EventWaitHandle + binary
- `Sources/Robots/Connector/Connector/Robot.cs` — removed host/port/PID file, binary action parsing, handshake
- `Sources/Robots/Connector/Connector/Enum.cs` — UpdateID/ActionID reordered with Initialization
- `Sources/Robots/Connector/Connector/Connector.cs` — constructor call updated (no host/port)
- `Sources/Robots/Connector/Connector/Connector.csproj` — removed NetMQ + Newtonsoft.Json

### What to review

1. **Binary protocol correctness** — verify `Binary.py` pack/unpack matches `System.cs` write layout for every message type (especially Position/Trade/Order with length-prefixed strings).
2. **Transport flow** — confirm the 4-event ping-pong (ur/uc/ar/ac) correctly prevents buffer overwrite and deadlocks.
3. **Handshake sequence** — C# creates mmap/events → launches Python → sends Initialization → Python opens mmap/events → responds with Initialization → watchdog starts.
4. **Watchdog behavior** — peer death sets `_peer_dead_` event, transport `_wait_` loop polls with 500ms timeout and checks the flag.
5. **C# action parsing** — `ReceiveAndProcessActions()` in `Robot.cs` reads binary fields at correct offsets for each ActionID.
6. **Enum values** — Python and C# enums must match exactly (0-79 for UpdateID, 0-53 for ActionID).

---

## 4. IPC Benchmark Reference

Benchmarked cBot ↔ Python round-trip lifecycle on Windows (i9-14900K, 64GB DDR5, 1M round-trips, tick 203B):

| Transport | Round-trips/s | Latency | vs ZMQ |
|---|---|---|---|
| ZMQ TCP PAIR | 20,148 | 49.6 µs | baseline |
| Named Pipes | 53,993 | 18.5 µs | **2.7x faster** |
| Shared Memory + Events | 92,201 | 10.8 µs | **4.6x faster** |

The new binary protocol reduces message sizes further (Tick: 203B JSON → 65B binary, Bar: ~750B JSON → 329B binary), so real-world throughput improvement should exceed 4.6x.

Benchmark: `Tests/Benchmark/IPC.py`.

---

## 5. Next steps

1. **Review Phase D + D.5** — thorough manual review of all changed files listed above.
2. **Phase E — Backtesting rewrite.** Re-enable `BacktestingAPI` in `Library/System/Main.py`; address B-E-1 UID collision.
3. **Phase G — Strategy state recovery.** Hook strategy state checkpoints to `SessionAPI`.
4. **NNFX Strategy Smoke Test** — Exercise Position/Order/Trade streaming + PnL accounting coherence.

---

## 6. Known issues (non-blocking)

- **`OpenCL/vendors/temp.txt` warning at Python startup.** Harmless probe from conda libs.
- **`--profile` not wired to cBot UI.** User must invoke Python CLI manually with `--profile` to dump `.pstat` snapshots.
- **Portfolio tables empty during backtesting** — no session tracking yet (expected, pending Phase E).
- **C# platform warnings** — 2 `CA1416` warnings for `MemoryMappedFile.CreateOrOpen` being Windows-only. Expected and harmless.

---

## 7. System Module Backlog

### Phase D — IPC Migration (ZMQ → Shared Memory) — IMPLEMENTED, PENDING REVIEW
- B-D-1: ~~Replace `SystemAPI` C# transport (`PairSocket` → `MemoryMappedFile` + `EventWaitHandle`).~~ Done.
- B-D-2: ~~Replace Python-side ZMQ socket with `mmap` + `ctypes` named events.~~ Done.
- B-D-3: ~~Keep JSON serialization initially.~~ Went further: replaced JSON with struct-packed binary protocol.

### Phase D.5 — Process Lifecycle & Handshake — IMPLEMENTED, PENDING REVIEW
- B-D.5-1: ~~Add `UpdateID.Initialization` / `ActionID.Initialization` as first exchange (PID exchange, no files).~~ Done.
- B-D.5-2: ~~Rework `_peer_dead_` detection for shared memory (PID polling via `OpenProcess` / `WaitForSingleObject`).~~ Done.
- B-D.5-3: ~~Graceful shutdown sequence: `Shutdown` update → Python processes → `Complete` action → release resources.~~ Unchanged, works as before.
- B-D.5-4: Timeout-based watchdog for hung peer (configurable, e.g. 30s no response → force teardown). Not yet implemented.

### Phase E — Backtesting
- B-E-1: Internal UID counters must not collide with cTrader UIDs (use negative space).

### Phase G — Strategy State Recovery
- B-G-1: Persist Signal/Risk machine state on Live restart.
