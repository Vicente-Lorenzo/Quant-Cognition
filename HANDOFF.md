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

Persistence and Realtime trading engine refactor complete. Phase D (Connector cBot rewrite) and Phase D2 (cBot parameter sheet + auto-resolution + verification) finished. Setup module reorganized; C# enums codegen'd from Python source of truth (now includes `SystemMode`). cBot is thin: it only resolves `SystemMode` (from `Robot.RunningMode`) and `DatabaseType` (Auto → concrete or Off); all other Auto resolution lives in Python. Buffer defaults are computed in `Main.py::_market_`/`_portfolio_` based on the positional system subcommand. Stream-level gating is per-type (`BarStreamMode`/`OrderStreamMode`/`PositionStreamMode`/`TradeStreamMode`/`TickStreamMode`). Database = Off is wire-represented by omitting `--database` (Python None = Off). Ready for backtest and live smoke tests against a cTrader demo account.

**Tests passing:** 265 / 265.
**C# Build:** 0 Warnings, 0 Errors.

---

## 3. What was done in the recent sessions

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

### Phase D — Connector cBot refinements [DONE]

#### Library/System
- **System.py / Realtime.py cleanup.** Removed Gemini's hallucinated `update_data` / `Update(...)` dead block at the bottom of `_process_updates_`. Reverted the `_receive_update_security_` wrapper that incorrectly called `_attach_session_` on `SecurityAPI` (universe data, no Session/Account fields). Restored project style (blank lines between methods, etc.).
- **Critical Realtime fix.** `RealtimeAPI.__enter__` was referencing `self._strategy_cls_`, but the base stores it as `self._strategy_` — would have raised `AttributeError` on first instantiation. Fixed.
- **DB isolation by SystemType.** `RealtimeAPI` now opens `PostgresAPI(database="Quant" if Live else "Tests")`. Every record built in `receive_update_*` is constructed with `db=self._db_`, so Simulation/Testing runs cannot pollute the production DB. Universe lookup in `Library/System/Main.py` keeps using `Quant` (separate, intentional — Security/Ticker/Provider/Timeframe live there).
- **Target tick `Volume`** is now read from the wire (`content.get("Volume")`), matching the OHLC ticks. Both ends emit/consume symmetrically.

#### C# Connector (`Sources/Robots/Connector/Connector/`)
- **Files renamed**: `RobotAPI.cs` → `Robot.cs`, `SystemAPI.cs` → `System.cs`. Classes kept as `RobotAPI` / `SystemAPI` to avoid shadowing `cAlgo.API.Robot` (the cTrader base class) and the .NET `System` namespace.
- **Old enum files deleted**: `StrategyEnum.cs` and `LoggingEnum.cs` replaced by a single generated `Enum.cs`.
- **`host` parameter** added to both `RobotAPI` and `SystemAPI` ctors (default `"localhost"`, mirrors `RealtimeAPI.__init__`). Hardcoded `127.0.0.1` is gone.
- **No more magic ints.** All `UpdateID` and `ActionID` references in `Robot.cs` / `System.cs` use the generated C# enums:
    - `SendUpdate*` methods take `UpdateID update_id` (cast to `int` only at JSON emission).
    - `OnPositionOpened/Modified/Closed`, `OnBarClosed`, `OnTick`, `OnShutdown` reference `UpdateID.OpenedBuyPosition`, `UpdateID.ModifiedSellPositionStopLoss`, etc.
    - `ReceiveAndProcessActions` switches on `ActionID` (`case ActionID.OpenBuyPosition: ...`).
- **`xBar.TickVolume` → `xBar.Volume`** for consistency with `xTick.Volume`. Wire-level JSON key is now `Volume` (Python `Realtime.receive_update_bar` updated accordingly).

#### Setup module (`Setup/`)
- **`Setup/Main.py`** orchestrates universe population and enum codegen. `python -m Setup.Main --enums | --universe | --all`.
- **`Setup/Enum.py`** owns the writer (`write_enum_file`) and the `write_all()` helper that pulls every block in one place — single source of truth, no N×N cross-imports.
- **`Setup/Strategy.py`, `Setup/Logging.py`, `Setup/System.py`, `Setup/Update.py`, `Setup/Action.py`** each export an `*_block()` function that returns one C# `public enum` block. Standalone `__main__`s call `write_all()` and log via `HandlerLoggingAPI`.
- **Generated `Enum.cs`** contains five enums: `StrategyType`, `VerboseLevel`, `SystemMode` (mirrors Python `SystemType`, 6 members), `UpdateID` (76 members), `ActionID` (~70 members). All sourced from the Python enums — drift is structurally impossible.

#### Architectural fixes in `Library/`
- **`EnumerationAPI` moved** from `Library/Database/Enumeration.py` → `Library/Utility/Enumeration.py` (where it semantically belongs — it's stdlib `enum` + fuzzy lookup with zero DB code). All 15 importers updated; the old path is deleted.
- **`Timer` no longer inherits from `DataclassAPI`.** It's a profiling utility (`start`/`stop`/`delta`/`result`) and used none of `DataclassAPI`'s serialization features; the inheritance only created a back-edge from `Library.Utility` to `Library.Database`.
- **`Library/System/Main.py`** now does `sys.path.insert(...)` at the top so both `python -m Library.System.Main ...` and `python Library/System/Main.py ...` work.

### C.4 — Session / Account refactor (carried over)
- `SessionAPI` is the persistence anchor.
- `AccountAPI` is a snapshot model: `natural_key = (Timestamp, Session)`.
- Order/Position/Trade UIDs use cTrader IDs directly.

---

## 4. Likely next steps

1. **End-to-End Smoke Test** (B-D-3) per the checklist below — this is the immediate next action.
2. **Phase E — Backtesting rewrite.** Re-enable `BacktestingAPI` in `Library/System/Main.py`; address B-E-1 UID collision.
3. **Phase G — Strategy state checkpointing** to `SessionAPI`.
4. **Optional cleanup** — finish breaking the remaining `Library.Utility` ↔ `Library.Database` back-edges (see §7).

---

## 5. Smoke Checklist

### Backtest smoke (Download strategy, populate Quant)
- [ ] Open cTrader → Backtesting tab → Non-Visual.
- [ ] **Data** dropdown = "Tick data from Server".
- [ ] **Download historical data for additional symbols** ticked.
- [ ] **Apply commission automatically** ticked.
- [ ] Strategy = Download (Auto resolves: Database=Quant, Market=(5000,0.0), Portfolio=(0,0.0)).
- [ ] Run 1 month range. cBot waits `Verification` bars before spawning Python, then replays them.
- [ ] If accuracy check fails: cBot logs Exception with remediation steps and Stops. Fix the dropdown/ticks, restart.
- [ ] After completion: `Tick` and `Bar` rows under `Market` schema in `Quant` DB.
- [ ] Re-run with identical params: row counts unchanged (idempotent upsert).

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

### Phase D3 — Tick Stream = All wire path
- Add `UpdateID.Tick` to `Library/Protocol/Update/Update.py` and regenerate `Enum.cs`.
- Add `SendUpdateTick(xTick)` in `System.cs` (C#).
- In `Robot.cs::OnTick`, when `_tick_stream_ == All`, emit every tick (not just target hits).
- In `Realtime.py`, add `receive_update_tick` (likely reuse `receive_update_target` payload shape).
- In `System.py::_process_updates_`, add `case UpdateID.Tick`.
- Remove the startup warning in `Robot.cs` once wired.

### Phase D4 — Order streaming on cBot
The cBot currently has no order-event handling. `OrderStreamMode` exists in `Parameter.cs` and `_order_stream_` is wired into the Debug startup log, but no `SendUpdateOrder` call site exists yet. To enable:
- Subscribe to `Robot.PendingOrders.Created/Modified/Cancelled/Filled/Expired` in `Robot.cs` ctor (next to the existing `Robot.Positions.*` subscriptions).
- Implement `SendUpdateOrder(UpdateID, PendingOrder)` in `System.cs` analogous to `SendUpdatePosition`.
- Gate each emission on `_order_stream_ != OrderStreamMode.Off`.
- Map to existing `UpdateID.OpenedBuyStopOrder` / `OpenedBuyLimitOrder` / `OpenedBuyStopLimitOrder` / `Modified*Order*` / `Closed*Order` / `Filled*Order` / `Expired*Order` families (already in Python `UpdateID` and codegen'd to C#).
- Verify Python `Realtime.receive_update_order` payload shape matches what `SendUpdateOrder` emits (Position, OrderID, OrderType, TradeType, OrderStatus, TimeInForce, Volume, StopPrice, LimitPrice, StopLoss, TakeProfit).

### Phase E — Backtesting
#### B-E-1 — Internal UID counters must not collide with cTrader UIDs
- Define a disjoint UID range (negative-space or high-offset).
- Implement in `BacktestingAPI`.

### Phase G — Strategy State Recovery
#### B-G-1 — Persist Signal/Risk machine state on Live restart
- Hook strategy state checkpoints to `SessionAPI`.

---

## 7. Known issues (non-blocking)

- **Residual circular imports in `Library/`.** Two `Library.Utility` ↔ `Library.Database` back-edges remain after this session's fixes:
    - `Library.Utility.Path` → `Library.Database.Dataclass`
    - `Library.Database.Query` → `Library.Utility.File`
  `-m` invocation (the standard path) works fine. Path-style invocation of leaf scripts (`python Library/.../X.py`) may hit the cycle. Proper fix is the same playbook used for `Timer` and `EnumerationAPI`: move misfiled types to their semantic home, or break unnecessary inheritance.

- **`AccountNumber` not emitted by C#.** `Connector/System.cs::SendUpdateAccount` does not send `AccountNumber`. Python `Realtime.receive_update_account` reads `content.get("AccountNumber")` → `None`. If `AccountAPI.Number` should hold the broker account number, add `AccountNumber = account.Number` (or equivalent) to the C# payload.

- **`ProviderAPI.normalize` may not match suffixed broker names.** Current implementation is `uid.replace("-", " ")`. Broker names like `"Spotware-Demo"` normalize to `"Spotware Demo"`, which won't match `Provider.Spotware` via `EnumerationAPI._missing_` fuzzy lookup (SequenceMatcher ≥ 0.9). Consider enhancing `ProviderAPI.normalize` (or adding a broker → provider mapper) to strip common suffixes (`-Demo`, `-Live`, ` Demo`, etc.) or do substring-containment matching against `Provider` member names.
