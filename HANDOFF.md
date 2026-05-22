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

Persistence and Realtime trading engine refactor complete. Phase D (Connector cBot rewrite) finished and verified. Setup module reorganized; C# enums codegen'd from Python source of truth. Ready for live smoke test against a cTrader demo account.

**Tests passing:** 265 / 265.
**C# Build:** 0 Warnings, 0 Errors.

---

## 3. What was done in the recent sessions

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
- **`Setup/Strategy.py`, `Setup/Logging.py`, `Setup/Update.py`, `Setup/Action.py`** each export an `*_block()` function that returns one C# `public enum` block. Standalone `__main__`s call `write_all()` and log via `HandlerLoggingAPI`.
- **Generated `Enum.cs`** now contains four enums: `StrategyType`, `VerboseLevel`, `UpdateID` (76 members), `ActionID` (~70 members). All sourced from the Python enums — drift is structurally impossible.

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

## 5. Realtime System Live Smoke Checklist

Run against a cTrader **demo** account before declaring a Realtime release safe.

- [ ] `Quant` Postgres reachable.
- [ ] `Tests` Postgres reachable (mirrors `Quant` schema; used by non-Live runs).
- [ ] Connector cBot deployed on cTrader (host=`localhost`, port=`5555`).
- [ ] `python -m Setup.Main --enums` regenerates `Sources/.../Enum.cs` cleanly.
- [ ] `dotnet build Sources/Robots/Connector/Connector.sln` → 0 warnings, 0 errors.
- [ ] cBot start triggers Python `Library/System/Main.py --system=Live --strategy=Download ...` via `cmd.exe /c conda run -n Quant python -m Library.System.Main ...`.
- [ ] `Account` and `Security` rows appear in `Quant` DB (Live) or `Tests` DB (Simulation/Testing).
- [ ] Warm-up bars stream as `BarClosed` (5 Tick + 1 Bar per insert).
- [ ] Live execution (Buy/Sell/Modify/Close) reflected in `Portfolio.*` tables under the correct DB.
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

- **Residual circular imports in `Library/`.** Two `Library.Utility` ↔ `Library.Database` back-edges remain after this session's fixes:
    - `Library.Utility.Path` → `Library.Database.Dataclass`
    - `Library.Database.Query` → `Library.Utility.File`
  `-m` invocation (the standard path) works fine. Path-style invocation of leaf scripts (`python Library/.../X.py`) may hit the cycle. Proper fix is the same playbook used for `Timer` and `EnumerationAPI`: move misfiled types to their semantic home, or break unnecessary inheritance.

- **`AccountNumber` not emitted by C#.** `Connector/System.cs::SendUpdateAccount` does not send `AccountNumber`. Python `Realtime.receive_update_account` reads `content.get("AccountNumber")` → `None`. If `AccountAPI.Number` should hold the broker account number, add `AccountNumber = account.Number` (or equivalent) to the C# payload.
