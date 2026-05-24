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

Persistence and Realtime trading engine refactor complete. Phase D (Connector cBot rewrite) and Phase D2 (cBot parameter sheet + auto-resolution + verification) finished. Recent session shipped:
1. **Audit-column persistence fix** — `UpdatedBy/UpdatedAt` were silently NULL for buffer-drained tables (`Market.Tick`, `Market.Bar`, and any future `Portfolio.*` written through the buffer). Root cause: `BufferAPI._drain_` bypassed `Datapoint._push_`. Lifted the stamp logic into a `DatapointAPI._stamp_(by, at=None)` method; both `_push_` and `Buffer._drain_` now call it. `DatabaseAPI` stays generic — no audit-column awareness at the data-mover layer (explicit segregation decision: Database.py callers must supply correct data).
2. **Buffer dedupe + fan-out fix** — `_drain_` was crashing on warmup-replay duplicates (`ON CONFLICT DO UPDATE command cannot affect row a second time`) because identical `(Timestamp, Security)` keys arrived twice when the verification buffer replayed bars. Now collapses by natural-key tuple (stringified to handle unhashable values like `SessionAPI`); the post-upsert UID write-back fans the same DB UID back to every collapsed input record via a `key → [records]` mapping.
3. **`Market.pull_bars` SQL** — explicit column list was missing `b."UpdatedBy"`, `b."UpdatedAt"`; added. All other `pull_*`/`load_*` paths in `Library/Universe`, `Library/Market`, `Library/Portfolio` audited as ✅ (either `SELECT *` or `<alias>.*`).
4. **Observability** — Python `RealtimeAPI` gained phase Timers (Warmup → Execution → Shutdown) and a `_metrics_` dict (`Ticks/Bars/Accounts/Orders/Positions/Trades/Actions`). Phase boundaries hooked into the state-machine actions (`init_market`, `report_statistics`). `BufferAPI._drain_` logs per-pass `Drain <Table>: N records, M unique rows (Xms)`. cBot mirrors the counters (single `_ticks_sent_` = bar sub-ticks + targets, `_bars_sent_`, etc.) and emits `Summary:` and 100-bar `Progress:` lines with Ticks-first ordering. `--profile` CLI flag in `Library/System/Main.py` opt-in wraps `run()` with `@profiler` (dumps a `profile-*.pstat` snapshot).

Smoke test on 1 month EURUSD Daily passes end-to-end: Python + cTrader terminate gracefully, `Market.Tick`/`Bar` populated with correct `UpdatedBy="Autosave"` + `UpdatedAt`. **Currently running 10-year (Jan 2015 → now) Daily smoke** to measure throughput — investigation is now on bottlenecks (cTrader tick-download phase is slow before the strategy even starts).

**Tests passing:** 265 / 265.
**C# Build:** 0 Warnings, 0 Errors.

---

## 3. What was done in the recent sessions

### Latest session — Persistence audit-column fix + Observability [DONE]

#### `DatapointAPI._stamp_`
- New method `_stamp_(by: str, at: datetime | None = None)` on `DatapointAPI` (single source of truth for audit-column write).
- `_push_` calls `self._stamp_(by)` instead of inline `self.UpdatedBy, self.UpdatedAt = ...`.
- `BufferAPI._drain_` calls `r._stamp_(self._by_, stamp)` (single `stamp = datetime.now()` shared per drain pass for batch consistency).
- `BufferAPI.__init__` gained `by: str = "Autosave"` so callers can override the audit label per buffer.
- **Design decision recorded**: `DatabaseAPI` (insert/update/upsert) stays generic — no `by=`, no stamping, no audit-column awareness. Callers must supply correct data. Audit logic lives in `DatapointAPI` only.
- Buffer's typing contract is now strict: `Sequence[Type[DatapointAPI]]`. Test mocks (`_RecA_/_RecB_/_RecC_` in `Tests/Database/test_Buffer.py`) gained a no-op `_stamp_` to honor it.

#### `BufferAPI._drain_` dedupe + fan-out
```python
unique, mapping = {}, {}
for r in records:
    r._stamp_(self._by_, stamp)
    row = {k: v for k, v in r.dict().items() if (columns is None or k in columns) and k not in identity}
    k = tuple(str(row.get(c)) for c in key)   # str() handles unhashable values (SessionAPI etc.)
    unique[k] = row                            # last-wins (matches single-save semantics)
    mapping.setdefault(k, []).append(r)
data = list(unique.values())
if identity:
    df = db.upsert(..., data=data, key=key, returning=identity)
    for i, k in enumerate(unique.keys()):
        if i >= len(df): break
        for col in identity:
            val = df[col][i]
            for r in mapping[k]: setattr(r, col, val)  # fan returned UID to all collapsed dupes
```
Fixes both the warmup-replay crash and a latent UID-misassignment bug where `enumerate(records)` no longer matched `df` rows after dedupe.

#### Observability layer
- **`RealtimeAPI._metrics_`** (`Library/System/Realtime.py`): `{"Ticks": 0, "Bars": 0, "Accounts": 0, "Orders": 0, "Positions": 0, "Trades": 0, "Actions": 0}`. Incremented inside the `receive_update_*` methods (`receive_update_bar` does `Bars+=1, Ticks+=5` since each bar carries 5 sub-ticks: Gap/Open/High/Low/Close; `receive_update_target` does `Ticks+=1`; `send_action` does `Actions+=1`).
- **Phase Timers** — three `Timer` instances on `RealtimeAPI`:
    - `_warmup_timer_.start()` at the tail of `__enter__`, `_warmup_timer_.stop()` inside `init_market` (transition from Initialisation → Execution state).
    - `_execution_timer_.start()` inside `init_market`, `_execution_timer_.stop()` inside `report_statistics` (Shutdown transition).
    - `_shutdown_timer_.start()/stop()` bracketing `__exit__` body.
    - Both `init_market` and `report_statistics` hooks are guarded against the test path that calls them without going through `__enter__` (defensive `if timer._start_ is not None` checks).
- **`_log_metrics_()`** called at end of `__exit__`:
    ```
    Phase Warmup: 1s 234ms
    Phase Execution: 45s 678ms (277.1 Ticks/s, 55.4 Bars/s)
    Phase Shutdown: 123ms
    Summary: Ticks=12600, Bars=2520, Accounts=1, Orders=0, Positions=0, Trades=0, Actions=0
    ```
- **`BufferAPI._drain_`** wraps each drain pass with a `Timer`, emits `debug` log: `Drain Tick: 5000 records, 4521 unique rows (156ms)`. Read this to spot DB-side bottlenecks (high `records:unique` ratio = lots of dedupe; high ms = slow upsert).
- **cBot Robot.cs** mirrors counters: single `_ticks_sent_` (incremented by 5 per bar send + 1 per target). `Summary:` and per-100-bar `Progress:` lines emit `Ticks=, Bars=, Positions=, Trades=, Actions=` (Ticks-first).
- **`--profile` CLI flag** in `Library/System/Main.py`: when set, `Main.py` does `profiler(run)()` instead of `run()`. `@profiler` decorator already existed in `Library/Utility/Statistic.py` — wraps `cProfile`, dumps `profile-YYYYMMDD-HHMMSS.pstat` in CWD. Not auto-wired to the cBot UI; user invokes via Python CLI (or wires a Parameter later).

#### `Market.pull_bars` audit-column hydration
- `Library/Market/Market.py` `pull_bars` SQL — explicit `b.<col>` list now includes `b."{BarAPI.ID.UpdatedBy}", b."{BarAPI.ID.UpdatedAt}"`. All other `pull_*` use `SELECT *` or `<alias>.*` which already cover the audit columns.

### Phase D2 — cBot parameter sheet + auto-resolution + verification [DONE]

#### cBot parameter sheet (`Connector.cs`)
- **AccessRights = FullAccess.** Required for `Process.Start("cmd.exe", ...)`. Previous `AccessRights.None` silently denied subprocess spawn and the cBot hung on the first `ReceiveFrameString()`.
- **Groups (in display order):** Logging Management → Strategy Management → System Management → Buffering Management.
- **Logging:** `Console`, `File` (VerboseLevel).
- **Strategy:** `Strategy` (StrategyType).
- **System:** `Database` (DatabaseType: Auto/Quant/Tests/Off), `Verification` (int, default 3, min 1), `Tick Stream` (TickStreamMode: Auto/All/Target/Off), `Bar Stream` (BarStreamMode), `Order Stream` (OrderStreamMode), `Position Stream` (PositionStreamMode), `Trade Stream` (TradeStreamMode) — each non-tick stream is its own enum (Auto/All/Off) for future divergence.
- **Buffering:** `Market Batch`/`Portfolio Batch` (int, -1=Auto), `Market Interval`/`Portfolio Interval` (double, -1=Auto).
- `Sources/Robots/Connector/Connector/Parameter.cs` holds the cBot-side UI enums (`DatabaseType`, `TickStreamMode`, `BarStreamMode`, `OrderStreamMode`, `PositionStreamMode`, `TradeStreamMode`).
- Generated `Sources/Robots/Connector/Connector/Enum.cs` (codegen'd by `python -m Setup.Main --enums`) contains `StrategyType`, `VerboseLevel`, `SystemMode` (mirrors Python `SystemType`, 6 values; cBot emits only Live/Simulation/Testing), `UpdateID`, `ActionID`.

#### Thin cBot responsibility split
Only two pieces of logic live in `Robot.cs`:
1. **`ResolveSystemMode(RunningMode)`** → `SystemMode` (`RealTime → Live`, `Visual/SilentBacktesting → Simulation`, `Optimization → Testing`).
2. **`ResolveDatabase(SystemMode, StrategyType, DatabaseType)`** → resolves Auto to one of {Quant, Tests, Off}. Rule: Live → Quant; non-Live + Download → Quant; otherwise → Tests.

Stream-mode `Auto` is resolved trivially in-place: `Auto → All` (Target for ticks). No table lookup.
Buffer-mode `-1` (sentinel for Auto) is **NOT** resolved by the cBot — the flag is simply omitted from the CLI when the value is < 0; Python applies its own defaults.

#### CLI emission (`Robot.cs::Activate`)
```
{SystemMode} --console <X> --file <X> --strategy <X> --provider "<BrokerName>" --ticker <X> --timeframe <X> --iid <X>
  [--database <Quant|Tests>]                    omitted when DatabaseType.Off
  [--market-batch N] [--market-interval F]      omitted when value < 0 (Auto)
  [--portfolio-batch N] [--portfolio-interval F] same
```
`--provider` carries the raw broker name from `Robot.Account.BrokerName`. Python's `ProviderAPI.normalize` handles the string→Provider lookup (may need enhancement for broker-suffixed names like `"Spotware-Demo"` — see §7).

#### Data accuracy verification heuristic (`Robot.cs::OnBarClosed`)
- In `RealTime`, verification is auto-passed; Python is spawned immediately.
- In Backtesting/Optimization, the cBot buffers the first `Verification` bars in memory (no ZMQ traffic, no Python spawn). For each closed bar it counts distinct timestamps among the five intra-bar ticks (`GapTick`/`OpenTick`/`HighTick`/`LowTick`/`CloseTick`). A bar is **degraded** if there are ≤ 2 distinct timestamps.
- After `Verification` bars: if **all V are degraded**, the data is non-Accurate → `_log_.Exception(...)` with explicit remediation message and `Stop()`. Else verification passes, Python is spawned (`Activate()`), Account/Symbol/Complete handshake fires, then the buffered V bars are replayed in order. From then on `_verified_ = true` and normal emission resumes.
- Why timestamp distinctness (not `LastBar.TickVolume`): `TickVolume` can be the broker's historical aggregate even in M1 mode, which would false-positive Accurate. Timestamp distinctness observes what the cBot itself received via `OnTick`, which collapses in non-Accurate mode.

#### Stream gating
Every `SendUpdate*` call site in `Robot.cs` is gated by its corresponding stream parameter. `*Stream = Off` → the cBot never emits that UpdateID family. No coupling to Python — if the strategy depends on a missing stream, it just sees no events. Startup warning is intentional only for `Tick Stream = All`.

#### Database = Off semantics (`Library/System/Realtime.py`)
`database: Union[str, None]` — None means Off:
- Forces `market = (0, 0.0)` and `portfolio = (0, 0.0)` so `BufferAPI.Active = False` and `add`/`flush` become no-ops.
- Sets `self._db_ = None`. Every `Datapoint._push_` early-returns via existing `if self._db_ is None: return` guard. No PostgresAPI context is opened. No `SessionAPI` row is created.
- Updates and Actions still flow through ZMQ; the strategy runs in-memory only. Loads/pulls are also no-ops, but Realtime doesn't read any trading-data records at runtime (Universe lookups use a separate `Quant` connection in `Main.py`).

#### CLI args (`Library/System/Main.py`)
- `--system` flag removed; positional subcommand instead (e.g. `python -m Library.System.Main Live --console Debug ...`).
- `--provider` (string) maps via `ProviderAPI.normalize(args.provider)` directly. cBot passes `Robot.Account.BrokerName` as the value.
- `--database` optional (`required=False, default=None, choices=["Quant", "Tests"]`). Omitted = None = Off.
- `--market-batch`, `--market-interval`, `--portfolio-batch`, `--portfolio-interval` all optional (`default=None`). Auto-resolution lives in two helpers in `Main.py`:
  - `_market_(SystemType, batch, interval)` — Live → (100, 60.0); Simulation → (5000, 0.0); else → (0, 0.0).
  - `_portfolio_(SystemType, batch, interval)` — Live → (100, 60.0); else → (0, 0.0).
- Commented Backtesting/Optimization/Learning blocks preserved in `_system_` for future re-enablement (Phase E/G/L).

#### Idempotency verified
The Postgres upsert SQL (`Library/Database/Postgres/Postgres.py::_upsert_`) emits `INSERT ... ON CONFLICT (<keys>) DO UPDATE SET col = EXCLUDED.col, ...`. `TickAPI` natural key is `(Timestamp, Security)`; `_push_` excludes the `UID` identity column from the payload. Running the same Backtesting + Download cBot 10 times with identical params yields 1 row per `(Timestamp, Security)`, overwritten 9 times with the latest values. Timestamp determinism in backtests is by-architecture (replay from fixed historical store); not contractually guaranteed by Spotware but holds in practice within a session.

### Phase D3 & D4 — Streaming Implementations [DONE]

#### Phase D3 — Tick Stream = All
- `UpdateID.Tick` added to `Library/Protocol/Update/Update.py` and `Enum.cs` regenerated.
- Re-used `receive_update_target`'s payload shape by renaming it to `receive_update_tick`.
- cBot now emits `UpdateID.Tick` in `OnTick` when `_tick_stream_ == TickStreamMode.All`.
- Removed startup warning regarding unimplemented stream.
- Added `case UpdateID.Tick:` handler to `_process_updates_` in Python engine.

#### Phase D4 — Order Streaming
- `LastOrderData` structure added to `Robot.cs` to track mutations (Volume, TargetPrice, StopLoss, TakeProfit).
- cBot subscribed to `Robot.PendingOrders` events (`Created`, `Modified`, `Cancelled`, `Filled`). `Expired` is not supported by the current cTrader API and was skipped.
- Gated all order updates by `_order_stream_`.
- Implemented `SendUpdateOrder(UpdateID, PendingOrder)` mapping to Python's `OrderAPI` parsing schema.
- Integrated `receive_update_order` directly into Python engine updates processing (`case UpdateID.ExpiredBuyStopLimitOrder | ...`).

### Optional Cleanup — Circular imports resolution [DONE]
- Broke `Library.Utility.Path` -> `Library.Database.Dataclass` inheritance.
- Broke `Library.Database.Query` -> `Library.Utility.File` inheritance by duplicating the file path resolution explicitly.

---

## 4. Likely next steps

1. **Performance investigation (10-year run)** — current focus. Use the Phase Timer output to identify which phase dominates wall time. Suspected bottlenecks in priority order:
    a. **cTrader historical tick-download** (pre-strategy phase, before Python even spawns) — appears slow for 10-year ranges. Outside framework scope unless we can configure or work around.
    b. **ZMQ round-trip latency per bar** — cBot does `SendUpdate*` → `SendUpdateComplete` → `ReceiveAndProcessActions` synchronously per bar. For 2520 bars that's 2520 round-trips; at ~1ms each that's only ~2.5s of latency, so likely not dominant.
    c. **Buffer drain DB upsert** — read `Drain Tick: N records, M unique (Xms)` lines. If `X` scales superlinearly with `N`, parameter-limit chunking might be hitting the 1000-binding cap (`_PARAMETER_LIMIT_` in `DatabaseAPI`).
    d. Use `--profile` to drill into whichever phase the Timers point at.
    e. *Note: `r.dict()` allocation in `_drain_` was successfully optimized out by surgically accessing `r._parse_(c)` directly.*
2. **End-to-End Smoke Test extension — add NNFX strategy** (B-D-3 follow-up) — exercises Position/Order/Trade streaming + PnL accounting, final statistics report coherence.
3. **Phase E — Backtesting rewrite.** Re-enable `BacktestingAPI` in `Library/System/Main.py`; address B-E-1 UID collision.
4. **Phase G — Strategy state checkpointing** to `SessionAPI`.

---

## 5. Smoke Checklist

### Backtest smoke (Download strategy, populate Quant) — 1-month: PASSED, 10-year: in progress
- [x] Open cTrader → Backtesting tab → Non-Visual.
- [x] **Data** dropdown = "Tick data from Server".
- [x] **Download historical data for additional symbols** ticked.
- [x] **Apply commission automatically** ticked.
- [x] Strategy = Download (Auto resolves: Database=Quant, Market=(5000,0.0), Portfolio=(0,0.0)).
- [x] Run 1 month range. cBot waits `Verification` bars before spawning Python, then replays them.
- [x] If accuracy check fails: cBot logs Exception with remediation steps and Stops. Fix the dropdown/ticks, restart.
- [x] After completion: `Tick` and `Bar` rows under `Market` schema in `Quant` DB, with `UpdatedBy="Autosave"` + `UpdatedAt` populated.
- [x] Re-run with identical params: row counts unchanged (idempotent upsert).
- [ ] **10-year range (2015–now), Daily, target ticks only** — measures throughput. Read `Phase Execution: <time> (X Ticks/s, Y Bars/s)` and per-drain `Drain Tick: ... ms` lines to identify bottleneck. cTrader's pre-spawn tick-download phase is noticeably slow for long ranges.

### Live smoke (any strategy, demo account)
- [ ] `Quant` Postgres reachable.
- [ ] Connector cBot deployed (host=`localhost`, port=`5555`).
- [ ] `dotnet build Sources/Robots/Connector/Connector.sln` → 0/0.
- [ ] cBot start triggers Python via `cmd.exe /c conda run -n Quant python -m Library.System.Main Live --console <X> --file <X> --strategy <X> --provider "<BrokerName>" --ticker <X> --timeframe <X> --iid <X>` (database/buffer flags omitted → Python applies Live defaults). If user picked explicit values in the cBot UI, they appear as additional flags.
- [ ] `Account` and `Security` rows appear in `Quant` DB.
- [ ] Live execution (Buy/Sell/Modify/Close) reflected in `Portfolio.*` tables.
- [ ] Shutdown emits `UpdateID.Shutdown`, statistics report logged.

---

## 6. System Module Backlog

### Phase E — Backtesting
#### B-E-1 — Internal UID counters must not collide with cTrader UIDs
- Define a disjoint UID range (negative-space or high-offset).
- Implement in `BacktestingAPI`.

### Phase G — Strategy State Recovery
#### B-G-1 — Persist Signal/Risk machine state on Live restart
- Hook strategy state checkpoints to `SessionAPI`.

---

## 7. Known issues (non-blocking)

- **`AccountNumber` not emitted by C#.** `Connector/System.cs::SendUpdateAccount` does not send `AccountNumber`. Python `Realtime.receive_update_account` reads `content.get("AccountNumber")` → `None`. If `AccountAPI.Number` should hold the broker account number, add `AccountNumber = account.Number` (or equivalent) to the C# payload.

- **`ProviderAPI.normalize` may not match suffixed broker names.** Current implementation is `uid.replace("-", " ")`. Broker names like `"Spotware-Demo"` normalize to `"Spotware Demo"`, which won't match `Provider.Spotware` via `EnumerationAPI._missing_` fuzzy lookup (SequenceMatcher ≥ 0.9). Consider enhancing `ProviderAPI.normalize` (or adding a broker → provider mapper) to strip common suffixes (`-Demo`, `-Live`, ` Demo`, etc.) or do substring-containment matching against `Provider` member names.

- **`OpenCL/vendors/temp.txt` warning at Python startup.** First three lines of every run are: `Access is denied. / The system cannot find the file specified. / Could Not Find C:\ProgramData\miniforge3\envs\Quant\Library\etc\OpenCL\vendors\temp.txt`. Harmless — one of the conda libs probes for an OpenCL vendor file. Suppressible by creating an empty `temp.txt` there or by silencing OpenCL probe via env var. Not blocking.

- **`--profile` not wired to cBot UI.** The flag exists in `Library/System/Main.py` but the cBot's `Activate` script-args builder doesn't emit it. To profile, run Python directly with the same arg string the cBot prints in `Debug` mode + add `--profile`. Or add a `Profile` Parameter to `Connector.cs` and append `--profile` conditionally in `Activate()`.

- **Wishlist for observability** (open for the next session, not yet started):
    - Symmetric Python-side debug logs for Validation window usage, Warmup window send-count vs receive-count parity, per-stream update receipt confirmation.
    - Graceful-vs-crash shutdown log differentiation (currently both paths go through `__exit__`).
    - NNFX added to the smoke test so Position/Order/Trade flows exercise end-to-end + final report coherence.
