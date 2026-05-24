# Quant Trading Framework — Handoff

Self-contained brief covering active state of the `cAlgo` repo. Read this first, then `RULES.md` for project conventions.

---

## 1. Project shape

- **Root:** `C:\Users\Admin\OneDrive\Documents\cAlgo`
- **`Library/`** Python core (engine, persistence, AI, Dash UI).
- **`Sources/`** C# cTrader Robots/Indicators/Plugins. Connector cBot bridges to Python via ZeroMQ.
- **`Tests/`** pytest, mirrors `Library/` layout. Exclude `Tests/Spotware`.
- **`Setup/`** unified workspace and DB setup. `conda run -n Quant python -m Setup.Main --all`.
- **Env:** `conda run -n Quant ...`.
- **Test command:** `conda run -n Quant python -m pytest Tests/ --ignore=Tests/Spotware`.
- **Build C#:** `dotnet build Sources/Robots/Connector/Connector.sln`.
- **Git:** stage with `git add`, **never commit**.

---

## 2. Where we are right now

Persistence and Realtime trading engine refactor complete. The framework has undergone a deep architectural review and optimization session focused on high-throughput data ingestion and logical consistency.

### 2.1 Database & Persistence Layer [OPTIMIZED]
- **`DatabaseAPI` Genericity**: Confirmed generic; it operates agnostic to trading domain entities. Bridge handled by `DataframeAPI.parse()`.
- **`BufferAPI` Performance**: Optimized the `_drain_` loop by pre-filtering valid columns once per batch, eliminating redundant `hasattr()` checks on millions of records.
- **Bulk Ingestion Path**: Confirmed that for millions of ticks, the optimal path is passing a **Polars DataFrame** to `Market.push_ticks()`, leveraging `executemany` which hooks into `psycopg3` **Pipeline Mode**.
- **Audit Columns**: `UpdatedBy/UpdatedAt` logic centralized in `DatapointAPI._stamp_`. Both single `_push_` and batched `Buffer._drain_` calls are audited.

### 2.2 Logical Reordering (Tick -> Bar -> Target) [ENFORCED]
- **Priority Standardized**: Codebase-wide enforcement of "Tick before Bar before Target" ordering.
- **Method & Property Alignment**: Affects `UpdateID` enum, `UpdateAPI` classes, System engine methods (`receive_update_*`), Strategy imports, and C# event handlers (`OnTick` before `OnBarClosed`).
- **Simplification**: `UpdateID.BarClosed` renamed to **`UpdateID.Bar`** (since updates only occur on close).

### 2.3 C# Connector & HANDSHAKE Fixes
- **`AccountNumber` Fix**: `Sources/Robots/Connector/Connector/System.cs` now correctly transmits `IAccount.Number` in the `SendUpdateAccount` payload.
- **Provider Normalization**: `ProviderAPI.normalize` updated to robustly strip `" Demo"` and `" Live"` suffixes and handle substring matches (e.g., `"Spotware-Demo"` -> `"Spotware"`).

### 2.4 Observability
- **Shutdown Differentiation**: `RealtimeAPI.__exit__` now logs whether a shutdown was **GRACEFUL** or **CRASHED** (with explicit exception reasons).
- **Phase Timers**: Capturing Warmup, Execution, and Shutdown deltas.
- **Metrics**: Real-time counters for Ticks, Bars, Accounts, Orders, Positions, Trades, and Actions.

**Currently running:** 10-year (Jan 2015 → now) Daily smoke test to measure throughput and identify DB bottlenecks.

**Tests passing:** 265 / 265.
**C# Build:** 0 Warnings, 0 Errors.

---

## 3. Notable session changes

#### Database Optimization (`BufferAPI._drain_`)
```python
valid_cols = [c for c in columns if c not in identity and hasattr(records[0], c)]
for r in records:
    r._stamp_(self._by_, stamp)
    row = {c: r._parse_(c) for c in valid_cols}
    # ... dedupe and upsert logic ...
```
Optimized to prevent CPU-bound bottlenecks during massive flushes.

#### Logical Ordering (Tick -> Bar)
```python
# UpdateID Enum
Tick = 13
Bar = 14
AskAboveTarget = 15
# ...
```
Standardized everywhere (Protocol, System, Strategies, Connector).

---

## 4. Likely next steps

1. **Continue Performance Investigation (10-year run)** — Verify if the optimized `BufferAPI` and Pipeline Mode handle the throughput. Monitor `Drain Tick: ... unique rows (Xms)` logs.
2. **Phase E — Backtesting rewrite.** Re-enable `BacktestingAPI` in `Library/System/Main.py`; address B-E-1 UID collision.
3. **Phase G — Strategy state recovery.** Hook strategy state checkpoints to `SessionAPI`.
4. **NNFX Strategy Smoke Test** — Exercise Position/Order/Trade streaming + PnL accounting coherence.

---

## 5. Known issues (non-blocking)

- **`OpenCL/vendors/temp.txt` warning at Python startup.** Harmless probe from conda libs. Suppressible but not blocking.
- **`--profile` not wired to cBot UI.** User must invoke Python CLI manually with `--profile` to dump `.pstat` snapshots.

---

## 6. System Module Backlog

### Phase E — Backtesting
- B-E-1: Internal UID counters must not collide with cTrader UIDs (use negative space).

### Phase G — Strategy State Recovery
- B-G-1: Persist Signal/Risk machine state on Live restart.
