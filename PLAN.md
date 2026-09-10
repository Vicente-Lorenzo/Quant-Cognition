# Plan

The single planning file for the framework. Written 2026-09-10, replacing `TODOS.md`,
`Research/THESIS-NOTES.md` and the project memory set, all of which were folded in here or into
`RULES.md` and then deleted.

**What belongs here:** work not yet done, in the order it will be done, with the evidence that
justifies it and the condition that closes it. **What does not:** conventions, current state and traps
(those are `RULES.md`), architecture (`ARCHITECTURE.md`), delivered results
(`Research/CAMPAIGN-7PAIR.md`, `Research/DDPG-EURUSD-H1/REPRODUCE.md`) and anything git history
already records.

**The thesis is delivered and stays delivered.** Its numbers are a safety net, not a hostage. Nothing
below is a quick fix applied to make a result look better; every phase is a structural change that
leaves the framework permanently correct. A second thesis iteration is produced in Phase 4 from the
corrected engine, and it replaces the first only if it is stronger.

---

## Order of work

| Phase | Scope | Gate | Can start |
|---|---|---|---|
| **0** | **Safety net — regenerate the goldens** | a cTrader session | **now** |
| **1** | Spotware module and data acquisition | broker API credentials | **now**, in parallel with 2 |
| **2** | Database structure and TimescaleDB | Phase 0 complete | after 0 |
| **3** | Backtesting engine accuracy | Phases 0 and 2 complete | after 2 |
| **4** | Optimization and Learning | Phase 3 complete | after 3 |
| **5** | Web app | 2.8 complete | after 2.8 |
| **6** | Remaining | none | any time |
| **7** | Indicator connector — Python indicators on cTrader charts | Phases 1 and 3 complete | after 3 |
| **8** | Live trading panel at `/trading` | Phases 1, 3 and 5 complete | last |

**Three rules bind the order.**

1. **Nothing touches the engine until Phase 0 exists.** There is no regression gate today — `Reports/`
   holds only `Plots/`, and `Research/DDPG-EURUSD-H1/verify_lock.py` section 3 fingerprints goldens
   that are not on disk and never were in git.
2. **There is exactly one golden re-baseline, and it is item 3.9.** Both the v2 tick schema (2.6) and
   the sizing fixes (3.2, 3.3) change engine output deliberately. Re-baselining after each would cost
   two cTrader sessions and would hide which change moved which number. Phases 2 and 3 therefore run
   against the Phase 0 goldens as a *tripwire* — a break is expected at 2.6 and 3.2, and every break
   must be explained before 3.9 accepts it.
3. **Phase 4 retrains once, at the end.** Every engine change invalidates trained weights. Retraining
   between phases burns the longest-running job in the framework for a result the next phase throws
   away.

Phases 1 and 2 touch nothing in common and are both gated on things outside the code, so they run
concurrently.

---

## Phase 0 — Safety net

The 2026-07-05 set was `Trend` on EURUSD and USDJPY across `{D1 2023, H1 2023, D1 2022-25}`. It is gone
from disk and is not being reconstructed: three of those six gated the same code paths as each other,
while three real branches had no cover at all. The set below is smaller and covers all of them.

### 0.0 Prerequisites

**A second Spotware demo account denominated in USD**, alongside the existing EUR one. Same broker,
same symbols, only the account currency differs. It exists solely to reach the `account == quote`
branch — see 0.1 run 3 — which no golden has ever exercised and which item 3.4 would otherwise land on
untested.

Both demo accounts are **Hedging**. Record it as part of the protocol, but do not treat it as a
variable: `Trend` holds one position at a time — `_last_position_id_` is singular, and scale-out
reduces that position rather than opening a second — so netting and hedging are observationally
identical here, which is why the lost set matched byte for byte against a hedging backtester. The
mode only becomes load-bearing when a strategy opens overlapping positions, and none of these do.

Four checks before the session, or the whole set is void:

1. **Fees run at the Spotware demo account's own terms, which is what makes the comparison valid.**
   `Auto` resolves to `Accurate` for spread, commission **and** swap, and `Accurate` reads
   `Universe.Contract`: `Commission` 45.0 as `BaseAssetPerMillionVolume`, `SwapMode` `Pips` with
   per-pair `SwapLong`/`SwapShort`, `SwapPeriod` 24. **45 is correct here** — it is the demo standard,
   and cTrader's accurate-commission backtest configuration charges exactly that. Do not change it.

   **Do not confuse this with the thesis cost model.** The thesis deliberately models a *different*
   account — raw-spread and swap-free, commission 3.5 USD per 100 000, i.e. 35 per million — because 45
   is unrepresentative of what this strategy would actually be traded on. Two configurations, two
   purposes: the goldens prove the **engine** matches cTrader, the thesis prices a **realistic broker**.
   Neither is a defect in the other, and neither should be edited to match.
2. **Leave swap on.** Do not zero it to match the swap-free thesis account, for the same reason. Swap
   is the known ~0.5% a year residual against cTrader and these runs are what pin it; the swap-free
   configuration only removes a term, so it cannot introduce an error these would miss.
3. **cTrader's "download historical data for additional symbols to convert profit/margin" must be on.**
   With it off the cross-pair spot freezes and conversions go stale — a silent, plausible-looking wrong
   number.
4. **Set the cBot's `Description` parameter to `Golden1` … `Golden5`** before each cTrader run, in the
   Reporting Management group. It travels as `--description` into the run folder's `Run.json`, and it is
   the only thing that tells one auto-minted `<Temp>/Runs/<uid>` folder from another afterwards.

### 0.1 The five runs

Strategy **`Trend`** throughout. It is the only strategy that drives the full risk machinery — stop
loss, take profit, break-even move, trailing stop with step re-arming, scale-out — through armed
intrabar targets, which is exactly where the engine has to agree with cTrader. `NNFX` is `Trend` minus
signals; `DDPG` has none of that machinery and gets its own golden at 0.2.

**Each configuration is run twice, and the two halves prove different things.** The **cTrader half** is
the Connector cBot inside cTrader's own Backtesting tab: cTrader owns the account, the date range and
the feed, and Python mirrors the stream in `Simulation` mode. That half measures **accuracy** — the
residual against cTrader — and only the user can run it. The **CLI half** is a standalone `Backtesting`
run over the same window; it is the artifact that becomes the **golden**, because it is the only one
reproducible without the platform. So every row below is entered twice: once in cTrader's Backtesting
tab, once as flags.

| Table column | Where it goes in cTrader's Backtesting tab |
|---|---|
| Ticker | the chart symbol |
| `--timeframe` | the chart timeframe — `h1` or `Daily` |
| `--start` / `--stop` | From / To |
| `--account-asset` | which demo account is selected, EUR or USD |
| `--account-balance` | Balance |
| `--account-leverage` | the account's own leverage, 30 |
| `--spread-type` / `--commission-type` / `--swap-type` | cTrader's accurate-commission configuration — nothing to set per run |

Common flags for the CLI half: `--strategy Trend --provider Spotware --account-leverage 30
--spread-type Auto --commission-type Auto --swap-type Auto --export --run FOLDER`, with `--resolution`
left unset so auto-resolution runs, which is the production path.

| # | Ticker | `--timeframe` | `--start` | `--stop` | `--account-asset` | `--account-balance` | The only cover for |
|---|---|---|---|---|---|---|---|
| 1 | EURUSD | `Hour` | 2023-01-01 | 2024-01-01 | EUR | 10 000 | `account == base` (`1/rate`); commission base **is** the account, so no commission conversion; raw volume clear of `VolumeMin`, so sizing is validated rather than clamping; and the tick tape, auto-resolution and intrabar exits at roughly a thousand trades |
| 2 | USDJPY | `Hour` | 2023-01-01 | 2024-01-01 | EUR | 10 000 | third currency with a **non-USD quote**; the only 3-digit, 0.01-pip contract of the seven, at the density where sub-pip rounding shows |
| 3 | EURUSD | `Hour` | 2023-01-01 | 2024-01-01 | **USD** | 10 000 | **`account == quote`, never tested in any golden**; commission base is not the account |
| 4 | USDJPY | `Hour` | 2023-01-01 | 2024-01-01 | EUR | **1 000 000** | raw volume clearing `VolumeMin` on a 3-digit pair — **the only run that can decide item 3.2**, with a full volume distribution rather than a handful of trades |
| 5 | EURUSD | `Daily` | 2015-01-01 | 2026-01-01 | EUR | 10 000 | eleven years: **swap accumulation over long holds**, the D1 auto-resolution path, the 2016-01-11 to 2016-01-25 hole, every DST transition, and a position still open at the stop date (item 3.6) |

`--timeframe` takes the friendly key `Hour` or `Daily` — **never** `H1` or `D1`. A wrong key
auto-vivifies an empty node and fails silently.

**Why four of five are `Hour`.** Conversion topology, sizing, spread, commission and intrabar exits are
all timeframe-independent code paths, so running them hourly buys roughly a thousand trades to compare
against cTrader instead of a few dozen — strictly more chances to catch a discrepancy, at no extra
cost. This also collapsed what were two separate runs into run 1.

**Why run 5 stays `Daily`.** Trade count is the wrong axis for exactly one thing. Swap accrues per
24-hour period, so a swap error scales with **hold duration, not trade count** — a thousand short
hourly trades accrue almost nothing, while positions held for months accrue hundreds of charges each.
The ~0.5% a year swap residual against cTrader is one of the two documented accuracy floors and is only
measurable here. Daily is also far cheaper in cTrader over eleven years than hourly would be, so this
is the better test *and* the faster one.

**Why not the other four majors.** `GBPUSD`, `NZDUSD`, `USDCAD` and `USDCHF` reach no branch these do
not. All four are 5-digit, 0.0001 pip, `VolumeMin` 1000, commission 45 per million,
`SwapMode` `Pips` — structurally identical to run 1 or run 2.

**Two optional additions, if the session has room.** Neither gates a branch, so neither is required.
`AUDUSD Daily 2023 EUR 10 000` is the only major with a **positive** `SwapLong` (+0.105 against
EURUSD's -2.445), so it is the only way to prove a swap credit is credited rather than debited — an
arithmetic risk, not a code path. `USDJPY Hour 2023 EUR 10 000` puts the 3-digit contract under the
same density as run 5, which is where the sub-pip intrabar residual compounds fastest.

**Why 4 needs its own run.** All 781 USD/JPY trades in the old set sat at exactly `VolumeMin` — one
distinct volume, 100% at the floor — because `calculate_normalized_volume` clamps upward. The
byte-identical match therefore proved both engines clamp, not that raw sizing agrees. EURUSD spanned
2 000 to 82 000 across 61 distinct volumes and did validate it. If cTrader's volumes at a million
stay tiny, our engine is faithful and item 3.2 must not change it; if they come out roughly 150 times
larger, the fix is warranted. Deciding 3.2 without this control anchors the framework to the wrong
reference permanently.

**The split that makes this set a tripwire for item 2.6.** `_needs_conversion_` is
`account_asset not in (base, quote)`, so the set partitions itself:

| Reads the stored conversion columns | Runs | Expected when 2.6 drops them |
|---|---|---|
| **No** — derives from the pair's own price | 1, 3, 5, 6 | **must stay byte-identical**; any movement is a real regression |
| **Yes** — reads the EUR-denominated columns | 2, 4 | break expected; explain the float-ordering residual and carry it to 3.9 |

**What is compared:** `trades`, `positions`, `orders` and `deals`, byte for byte. `net.csv` is excluded
by design — label drift (`Annualised` against `Annualized`) and the Upside/Downside Volatility rows
make it a moving target.

**The accuracy floor is data-bound, not a defect:** a sub-pip intrabar exit residual, and a swap
residual of roughly 0.5% a year. Record both against cTrader at creation time; they are the tolerance
every later comparison is read against.

`--export` defaults to the temp tier, so pass `--run FOLDER` or retention sweeps the reports. **Commit
the folders.** The previous set was lost precisely because it never entered git.

**Done when:** five folders committed, the residual against cTrader written down per run, and
`verify_lock.py` updated to fingerprint them and passing all three sections.

### 0.2 The DDPG golden

**No cTrader session — we generate this one ourselves.**

Every golden the framework has ever had ran `Trend`. The DDPG sizing path — `_reference_volume_`, which
items 3.2 and 3.3 both change, and which every published thesis number rides on — has **no regression
gate at all**.

`--strategy DDPG --ticker EURUSD --timeframe Hour --start 2015-01-01 --stop 2026-01-01
--account-asset EUR --account-balance 10000`, with `Weights` pointed at the committed champion under
`Research/DDPG-EURUSD-H1/Models/`.

This is a **self-consistency** golden, not a cTrader-equivalence one. It answers "did this refactor
move the DDPG path", never "does cTrader agree". Label it distinctly in `verify_lock.py` so the two
kinds are never read as the same guarantee. It costs nothing and catches the change most likely to
silently invalidate the campaign.

**Done when:** the run is committed and re-running it reproduces byte-identically.

---

## Phase 1 — Spotware module and data acquisition

Goal: one connector abstraction, Spotware first, capturing continuously — replacing the per-ticker
Download-strategy cBot workflow.

### 1.0 Modernise the .NET toolchain — DONE 2026-09-10, one verification outstanding

**What was wrong.** Both csproj files carried `<PackageReference Include="cTrader.Automate"
Version="*" />`. A floating version, so NuGet silently took 1.0.20 the moment it was published, and
1.0.20's targets file probes for .NET 10 via `$([System.Environment]::Version.Major)` — a property
function the installed MSBuild 17.0 refused to evaluate, failing with `MSB4185`. **Nothing in the repo
had changed**; the build broke because the feed moved. The only SDK present was 6.0.100, from November
2021, out of support since November 2024.

**What was done.**

- Installed **.NET SDK 10.0.401** via winget, side by side. 6.0.100 remains, so `global.json` pinning
  `6.0.100` is an instant rollback if anything surfaces later. With no `global.json`, `dotnet` selects
  10.0.401.
- **`cTrader.Automate` is pinned to `1.0.19`** in both projects, which are byte-identical.
- Both solutions build 0 warnings / 0 errors, still targeting `net6.0`, and emit
  `Sources/Robots/Connector.algo` and `Sources/Indicators/Connector.algo`. The SDK move left `Enum.cs`
  untouched at `8376276ae3a71fbe`; it was regenerated separately in 1.0.2 and is now
  `36d2f69f2fa39698`.

**⚠ The `dotnet` CLI is NOT the toolchain that matters. cTrader's Build button is.**

This cost a wrong fix on 2026-09-10 and is the single most important thing in this section. The package
was briefly unpinned to `Version="*"` on the reasoning that a cBot should track the platform it deploys
into, and the CLI built clean on SDK 10 — but **cTrader's own Build still failed with the identical
`MSB4185` at `cTrader.Automate.targets` line 23**. cTrader bundles only the .NET 6.0.0 runtime and
targeting pack plus RoslynPad; it ships no SDK and no MSBuild, sets no `DOTNET_*` overrides and writes
no `global.json`, yet it plainly does not compile through the system SDK 10.0.401. Whatever it invokes
rejects `[System.Environment]::Version`, and **MSBuild does not short-circuit the `AND` in that
condition**, so the failure cannot be dodged by pre-setting `_TaskAssemblyTFM` from the project file.

**The rule: `cTrader.Automate` is pinned to the newest version cTrader's own Build accepts.** Bump it
deliberately when cTrader updates, and verify by clicking Build — never by a CLI build, which uses a
different compiler and will report success on a version the platform cannot compile. The package can
only float as fast as the slowest toolchain that builds it, and that toolchain is cTrader's.

**`net6.0` is a requirement, not legacy debt.** cTrader bundles `Microsoft.NETCore.App.Ref` **6.0.0**
and nothing newer, so retargeting would break the `.algo`. That question is closed.

**cTrader owns the `.csproj` formatting.** Opening or building in cTrader rewrites the file — it adds a
UTF-8 BOM and an XML declaration and strips blank lines between element groups. Both projects are
stored in exactly that form so cTrader's normalisation is a no-op and they stay identical; do not
"clean up" the BOM, it comes straight back.

**Still outstanding, and only you can do it.** The `.algo` files are now produced by the 1.0.20
toolchain on SDK 10. **Load both in cTrader and confirm they run**, ideally with one live round-trip.
Everything above is compile-time evidence; none of it proves the platform accepts the artefact.

Do this **before 1.7**, which rebuilds and reinstalls the `.algo` after an enum renumber. Confirming the
toolchain now means a wire-ID mismatch there can only be the enum change, never the compiler.

### 1.0.1 Sources hard pass — done 2026-09-10

Every tracked file under `Sources/` was read and both solutions were rebuilt after each change. Twelve
files are tracked; `.idea/`, `bin/`, `obj/` and `*.algo` are correctly gitignored, and `Sources/Export`
plus `Sources/Plugins/Plugin/Plugin` are empty scaffolding git does not carry.

**Fixed and staged.**

- **The two `.csproj` files are now byte-identical.** `Sources/Indicators` was missing
  `SuppressTfmSupportBuildWarnings` and carried a trailing newline the other did not.
- **Three dead `using` directives removed** from `Sources/Robots/Connector/Connector/Connector.cs` —
  `cAlgo.API.Collections`, `cAlgo.API.Indicators`, `cAlgo.API.Internals`, all cTrader template
  leftovers. Every `using` in all six Robots files was then verified by removing it and rebuilding:
  the remaining nineteen are genuinely used.
- **Six private constants in `Logging.cs`** renamed from `_lower_` to `_UPPER_` per the naming rule
  (`_default_error_log_` to `_DEFAULT_ERROR_LOG_`, and the five beside it). File-local, no other
  reference in the tree.

**Verified as non-issues, so nobody re-opens them.**

- Line endings look mixed in the working tree but `.gitattributes` already carries `* text=auto
  eol=lf`, so the repository is uniform and the CRLF warnings on `git add` are checkout artifacts.
- The two `.sln` files are identical apart from their project GUIDs, which is correct.
- **The `CA1416` and `CS0618` backlog recorded in 6.7 is stale.** Both solutions build warning-free in
  Debug *and* Release, and did so on SDK 6.0.100 before the upgrade, so this is not an SDK artefact.
  Removed from 6.7.

**Two decisions left, both yours.**

1. **`Sources/Indicators` is not a peer project — it is the untouched cTrader template.** Its single
   file still prints `"Hello world!"` from `Initialize()` with an empty `Calculate()`, four of its five
   `using` directives are dead, and it declares `namespace cAlgo.Indicators` where the Robots project
   declares `namespace Connector`. Making it *look* symmetric would be polishing scaffolding. Either
   implement it, delete it, or leave it and accept that the asymmetry is real and intended. I left the
   source untouched and only made the project file symmetric.
### 1.0.2 Enum.cs — done 2026-09-10

Fixed in the **generator**, never in the output. `Setup/Enum.py` now emits:

- **A file-scoped `namespace Connector;`**, matching all six hand-written files; the old block-scoped
  form was the last file in the project indented an extra level.
- **An `// <auto-generated>` header** naming `Setup/Enum.py` and the `python -m Setup.Enum` command.
  This is the one comment the no-comment rule should never have excluded: the file's single documented
  trap is that hand-editing it silently desynchronises the wire, and until now nothing in the file said
  so. Roslyn also skips analyzers on files marked this way, which is correct for generated output.

**Safety, in the order it was checked.** Every enum name, member and value was diffed
whitespace-normalised against the previous output: **171 members across 7 enums, identical**. Only
layout changed. A wire-ID or member rename here mis-decodes silently, so this was verified before the
build, not after. The generator is idempotent — a second run is byte-identical. `[System.Flags]` is
still emitted for `Stream`, and the build is clean.

**The pinned hash moves to `36d2f69f2fa39698`**, updated in `RULES.md` and `ARCHITECTURE.md`.

**Deliberate, not an omission:** `Stream.All` is absent from the C# output because Python's `IntFlag`
excludes composite aliases from iteration. That is correct — the C# side receives a bitmask and tests
bits; it never needs the alias.

**Still to do when 7.1 lands.** `OUTPUT_PATH` is a single hardcoded path into the Robots project. The
indicator connector needs the same enums, so the generator will have to emit to both projects. Left
alone deliberately — a one-element list today would be speculative generality.

### 1.1 Feed equivalence: Open API against the Download cBot

**Blocked on you — needs an app `clientId` and `clientSecret`, an OAuth `accessToken` and a
`ctidTraderAccountId`.**

The blocking unknown for the entire phase. Same broker backend, different transport, never compared.
Capture one symbol for one session through both paths and diff tick counts, timestamps and prices.

Historical backfill through the Open API is **not** viable — weeks of wall clock. Keep the existing
history and capture forward. Nothing else in this phase is worth building until this test passes.

**Done when:** a written comparison exists showing the two feeds agree, or naming exactly where they do
not.

### 1.2 Repair `Library/Spotware`

Deliberately left broken on 2026-09-05; 1.1 is what makes fixing it worthwhile.

`Market.py`, `Streaming.py` and `Portfolio.py` construct datapoints with pre-rename keywords —
`TickAPI(SecurityUID=, DateTime=, AskPrice=, BidPrice=)`, `BarAPI(SecurityUID=, TimeframeUID=,
DateTime=, OpenBidPrice=..., TickVolume=)`, `OrderAPI(OrderID=, PositionID=)`, `TradeAPI(TradeID=)`,
`PositionAPI(PositionID=)`. The datapoints are `kw_only`, so every one raises `TypeError`.
`Tests/Spotware/test_Market.py:52` and `test_Portfolio.py:100-268` assert the stale names too.

Rename to `Security` / `Timestamp` / `Ask` / `Bid` / `Volume`, `Timeframe` / `GapTick` through
`CloseTick`, `UID` / `Position`, and update both test files. While in there: `Execution.py` has eight
pure pass-through buy and sell wrappers whose `side` argument is unused (`partialmethod` or drop),
`Streaming.py` imports inside per-message closures, five imports are unused, and `Spotware.py` carries
twelve docstrings outside the RULES exemption list.

**Done when:** `Tests/Spotware` runs green against a live broker session and is no longer excluded from
the default pytest invocation.

### 1.3 Connector abstraction

One instance per broker, Spotware first, Bloomberg and Yahoo behind the same seam later. Design the
interface against two providers on paper before implementing one, or it will encode Spotware's shape.

### 1.4 Continuous live capture

Replace the per-ticker Download-strategy cBot workflow with an always-on capture service under the
Scheduler. Tick-only storage (Phase 2) is what makes this affordable.

Keep per tick: Ask, Bid and Volume, plus OHLC ticks rather than prices alone, for intrabar accuracy —
possibly High and Low for **both** Ask and Bid rather than bid-only pillars.

### 1.5 Delay and batch protocol

Sliding FIFO plus `UpdateID.Batch` plus a 256 KB slot, replacing the single-slot request/response
lockstep for bulk transfer. Roughly 10% validated already.

### 1.6 Decide DDPG's `Subscription` deliberately

`NNFXStrategyAPI` moved to `Stream.All & ~Stream.Tick` because its intrabar reactivity is entirely
target-driven — 21.3 M raw ticks collapsed to bar closes plus a few thousand target crossings,
bit-exact. **DDPG has never been reviewed.** An RL agent may genuinely act per tick. Decide from its
actual channels; do not copy NNFX.

Base `StrategyAPI.Subscription = Stream.All` is a safe superset. Every strategy should declare its
minimal subscription.

### 1.7 Protocol symmetry

`Decreased{Buy,Sell}PositionVolume` updates 65 and 66 exist; the gap is on the **action** side. Add four
target-volume actions in the logical order `Increase`, `Decrease`, `Modify`.

Renumbering is safe because `Setup/Enum.py` regenerates the C# side. Run `python -m Setup.Enum`, rebuild,
reinstall the `.algo`, then verify a live round-trip — a wire-ID mismatch mis-decodes silently, with no
error. Logs must be symmetric with the existing pairs.

### 1.8 `receive_update_security`

Parse the C# security payload to enrich `SecurityAPI`. Small; ship with 1.7.

---

## Phase 2 — Database structure

`Market.Tick` is **295 GB** (244 heap plus 51 index) over 1 663 564 416 rows — 157 bytes a row actual
against 104 declared, the difference being header, alignment and varchar. Ranked levers:

| Lever | Saving | Note |
|---|---|---|
| TimescaleDB compression | ~250 GB | measured 90.7% on 1 203 593 real ticks (173 MB to 16 MB, one second to compress, a one-day read-back of 367 389 rows in 0.03 s). Reads got *faster*. No schema change |
| drop the 4 conversion columns | 53 GB | fully redundant — reconstructible from the pair's own price plus EURUSD, worst error 0.036% |
| `Tick_pkey` | 51 GB | the only index, and the sole reason `UID` exists |
| narrow types | ~23 GB | price to int32 scaled by `PipSize`, `Security` to int16 |
| drop `Mid` | 13 GB | derivable from Ask and Bid |

Ordered so nothing in flight breaks. The dangerous path is doing 2.6 first.

### 2.1 Create the TimescaleDB extension in `Quant`

2.24.0 is installed and `shared_preload_libraries` already contains `timescaledb`, but `CREATE
EXTENSION` has only ever been run in `Tests`. One statement; everything below depends on it.

### 2.2 Compress `Market.Tick` as it stands

No schema change, so the goldens cannot move — which is what makes this the right first step. Convert
to a hypertable, set a compression policy, verify row counts before and after, and re-read a known day.

**Done when:** row count preserved exactly, a spot-check day reads back identical, and the reclaimed
size is recorded here.

### 2.3 Continuous aggregates for bars

Derive every timeframe on demand from the tick tape and retire the `Bar` tables (5.9 GB). This unlocks
H4, D2, W1 and arbitrary intervals, which the framework cannot offer today.

**The session-stamp convention must survive.** Bars are stamped at 22:00, or 21:00 under DST, so a
Thursday-stamped D1 bar *is* Friday's session and D1 carries five bars a week stamped Sunday through
Thursday. An aggregate built on calendar days silently produces a different tape.

**Done when:** a derived bar frame is byte-identical to the stored one for a sampled window on all seven
pairs, across a DST boundary in both directions.

### 2.4 UID encoding Phase 6

DROP and repopulate `Tick` and `Bar` with the encoded scheme — encoded Tick UID, composite-primary-key
Bar in milliseconds as Int64. Implemented and green since 2026-06-07; only the repopulation is
outstanding. Gated on no in-flight downloads.

### 2.5 Write the currency algebra design

**Before any code in 2.6 or 3.4.** `account`, `base`, `quote`, and the bridge-pair graph for the cases
where no direct rate exists — a CHF account trading GBPJPY — including what happens when a required
bridge pair has no data for part of the window.

Conversions must be rebuilt from **full tick streams, not H1 bars**. Accuracy over convenience.

### 2.6 The v2 tick schema

Drop the four conversion columns, narrow the types, drop `Mid`. Roughly 89 GB on top of compression.

Two things this breaks, both expected:

- **The goldens.** Reconstructed conversions are not bit-identical to stored ones — float ordering alone
  guarantees that. The break is the tripwire working. Explain the residual and carry it to 3.9.
- **Cache keys and the memory ceiling.** A new cross-stream dependency appears: backtesting GBPUSD now
  requires EURUSD ticks loaded. The campaign already hit a hard wall here, a cold multi-worker start on
  an uncached pair exceeding 51 GB. Revisit preload sizing before this lands, not after.

`UpdatedAt` and `UpdatedBy` stay — they are part of the `DatapointAPI` contract, and dropping them would
have to be a `Library/Database` opt-out capability, not a one-off.

### 2.7 Move the `Data` tier under OneDrive

The seven thesis winners' weights (639 KB, 28 files) exist **only** in `<Data>/Models` on one machine's
local AppData. Verified safe from pruning, but not pruned is not backed up.

| tier | files | size | pruned by | verdict |
|---|---|---|---|---|
| `Temp` | 843 | 3.49 GB | retention, by age | **no** — sync locks make deletion unreliable |
| `Data` | 15 645 | 3.15 GB | never | **yes** — write-once, the only copy of every model |
| `Cache` | 180 | 6.61 GB | retention, by last use | **no** — Files On-Demand can dehydrate a preload tape to a placeholder, so a backtest's first read blocks on a network fetch or fails |

**Resolve first:** does anything assume `Data` and `Temp` share a volume? Save and Release move a run
folder between tiers as a rename. Across volumes that becomes copy-and-delete — slower, and no longer
atomic.

Also open: whether `inspect_root()` stays derived with only `Data` redirected, since a per-tier root is
the cleaner shape; a retention policy for `Data/Models`, since roughly 1 100 wave-archive models (about
110 MB) are search byproduct rather than deliverables; and a per-machine namespace if two machines ever
sync the same `Data`.

### 2.8 Research schema — DB-only inputs and outputs

Every input a model consumes and every output it produces moves from scattered files into Postgres.
Today the two most valuable series — the timestamped equity curve and the per-bar signal tape — are
persisted only *inside* a plot HTML. Nothing is queryable and nothing links a run to the exact inputs
that produced it.

Target: results in a `Research` schema, weights as rows, one `Run` row tying them together, identical
CLI behaviour, a thin web UI on top. Parameters are already done — `Library/Strategy/Ladder.py` replaced
the YAML tree.

Note that `Library/Research`, this module, is distinct from the top-level `Research/` folder.

**Layout**

| File | Contents |
|---|---|
| `Run.py` | `ResearchStatus`, `ResearchRunAPI` — `UID` primary key, `System`, `Status`, `Arguments`, `Command`, scope columns, `Parameters` as a JSON snapshot at launch (which is what makes a run reproducible), `Owner` foreign key to `Auth.User`, `PID`, `ExitCode`, `Log`, timing, headline metrics |
| `Result.py` | all with `RID` foreign key to Run **ON DELETE CASCADE**: `TradeResultAPI`, `DealResultAPI`, `PositionResultAPI`, `OrderResultAPI`, `StatisticResultAPI` (long form: RID, Report in Net / Realized / Unrealized, Metric, six values), `EquityResultAPI`, `SignalResultAPI`, `EpisodeResultAPI`, `BenchmarkResultAPI`, `WeightResultAPI`, plus `ResultAPI` as the writer and reader facade |
| `Model.py` | `ModelAPI` — a named deployable weights registry. The `Weights:` parameter holds a Model UID instead of a folder path |
| `Research.py` | `ResearchAPI`, shaped like `Library/Scheduler/Manager.py`: `command()`, `launch()`, `run()` and `runs()`, `reap()`, `cancel()`, `delete()`, `promote()`, `materialize()`, `fingerprint()` |
| `Runner.py` | `python -m Library.Research.Runner <uid>` — Popen the CLI, persist Running and the PID, wait, **reload the row so a Cancelled status wins**, write the terminal state |

`Setup/Research.py` provisions after `setup_auth` for the foreign keys, with indexes on `Run(Status)`,
`Run(System, StartedAt)` and `(RID, Timestamp)` on the series tables. Copy `Library/Scheduler/Run.py`.

**Backend contract**

1. `--rid <uid>` on the shared base parser, threaded into `SystemAPI` like `iid`. Absent means the writer
   auto-creates its own Run row, so console runs still enter history.
2. At `_report_` time call `ResultAPI`. The import direction is one-way — `System` may import `Research`,
   `Research` must never import `System`. Write `.trades`, `.deals`, `.positions`, `.orders`,
   `.statistics(rid, report, df)` for **all three** reports, `.equity(rid, df)` **keeping the
   timestamps**, `.benchmarks` and `.headline`.
3. **Ungate the signal tape** so it records independently of `--plot`, then flush via `.signals`. Today
   `StrategyAPI._emit_` appends only when `--plot` is passed, only two strategies call it, and `Signals`
   resets per `deploy()`.
4. Learning: `.episode(...)` per episode, replacing log parsing; `.manifest`; `.weights` at completion.
   Parallel seed workers need the rid in their payload. Weight loading moves to a Model UID plus
   `materialize()` into the local cache.
5. Retire the CSV export once the DB path is verified.

**Measured gotchas**

- **Payload size binds.** A full 11-year H1 run is roughly 34 MB of JSON across about ten series, some
  68k points each. Thin to about 2k points a series, roughly 4 MB, before shipping to a browser; over
  8 MB wedges the Dash dev server. **Decimation must use one shared time grid** or cross-pane crosshair
  lookups break.
- `net.csv` is 85 metric rows by 6 value columns with the label column `Statistical Metrics`, and
  historical files drift — `Annualised` against `Annualized`. **Key by normalised label, never by row
  index.**
- Cancel and finish race: the Runner must reload before writing terminal state.
- PID reuse: guard reaping with `psutil.Process(pid).create_time() <= StartedAt + grace`. Never kill on a
  reap, only mark.
- Bars stay in the `Market` schema. Do not persist them per run.
- DB parameters plus materialized weights change the deployed path. Verify on a Simulation run **before**
  archiving anything.

**Reading list, in order:** `Library/System/System.py` for `_report_`, `_export_`, `_plot_`, `_curves_`,
`_bars_` and `deploy`; `Library/Portfolio/Portfolio.py` for `EquityTrack`, `EquityCurve` and
`_record_equity_`; `Library/Strategy/Strategy.py` for `_emit_`, `Recording` and `Signals`;
`Library/Scheduler/Run.py` with `Manager.py` and `Executor.py`; `Setup/Scheduler.py` with
`Setup/Install.py`; `Library/App/V2/Lightweight/Lightweight.py` for the consumer contract.

**Done when:** `python -m Setup.Research` provisions cleanly; a console run goes Waiting to Running to
Success with result rows and non-null headline metrics; a second run cancelled mid-flight lands Cancelled
with its process tree dead; a real short backtest produces equity and signal row counts matching bar
counts; a one-seed one-episode Learning run records episodes, stores its manifest, and `promote()` plus
`materialize()` round-trips byte-identically in torch; the full suite is green; and `verify_lock.py` still
reproduces the campaign.

---

## Phase 3 — Backtesting engine accuracy

The engine already reverse-engineers the cTrader engine byte for byte on the golden protocol and extends
it. This phase closes the four places where that fidelity is incomplete, and makes the account currency
generic.

### 3.1 Write the spread charge to the trade record

`BacktestingAPI._build_position_` charges the spread correctly — `gross = (bid - ask) * volume *
quote_conversion` — but never surfaces it as a field. The only recovery route today is the identity
`spread = abs(commission) * points / 7`, valid because commission is 7 points round-turn, the spread is
crossed once, and both scale identically with volume and conversion.

**That identity fails when commission is zero, which is exactly the training configuration**
(`--commission-value 0`). So in every Learning run the single largest cost component — the spread is
about 42% of total cost — is invisible.

Fix: an additive `SpreadPnL` field on `PositionAPI` and `TradeAPI`. Goldens must stay byte-identical
apart from the new column.

### 3.2 Risk sizing ignores the quote-to-account conversion

**Decided by item 0.2.**

`calculate_fixed_amount_volume` computes `amount / (sl_pips * PipSize)` where `amount` is in **account**
currency and the stop is in **quote** currency, with no conversion. `PipSize` cancels, so contract tick
metadata is not the lever. Effective risk becomes `RiskPercentage / price`:

| pair | intended | actual |
|---|---|---|
| EURUSD | 1.0% | 0.909% |
| USDJPY | 1.0% | **0.0067%** |

On USD/JPY the raw volume — 133 units at a 10 000 balance — falls under `VolumeMin`, which is why DDPG
could never open a position there. **Raising the balance does not help**: risk stays `1/price` because
volume and balance scale together.

The published campaign is unaffected — every winner ran with active risk sizing, 26 to 124 distinct
volumes, 0.0 to 4.1% of trades at the floor. USD/JPY alone used a research-only compensation,
`RiskPercentage` scaled by 119.1994, restoring roughly 1% risk a trade, exact at the window start and
easing to about 0.8% by the end. **Remove that compensation as part of this fix, not before.**

**Verified correct — do not "fix" these.** P&L quote-to-account conversion is right for every base and
quote combination under a EUR account, validated against the goldens: `account == base` uses `1/price`
(EURUSD 30.27/1.0743 = 28.1765 against a recorded 28.1760), and `account == third` uses the tick's
`QuoteConversion`, with the implied rate varying per trade — USD/JPY 0.00707514, 0.00707354, 0.00698959,
0.00704379 — which proves a per-tick read rather than a constant. The tick conversion data is accurate,
EUR-denominated and has zero nulls; `QuoteConv / BaseConv` equals `1/price` to four decimals on all seven
majors.

### 3.3 Unify the exposure feature with the order sizer

`DDPGObservationAPI._position_features_` normalises exposure by `ActionAPI.maximum_volume`
(`SizingMode.Balance`), while orders are sized by `_reference_volume_`, which is risk-based. They
disagree by 9x on EURUSD and GBPUSD and by **238x on USD/JPY**, so the feature clips to plus or minus one
above an `abs(action)` of 0.109, 0.112 and **0.004** respectively.

On USD/JPY the agent is effectively blind to its own position and can only trade all-in or flat. Present
on every pair; tolerable at 9x, fatal at 238x.

**This invalidates trained weights.** It is the main reason Phase 4 retrains.

### 3.4 Generic account currency

**Needs 2.5 first.** Stored rates convert to EUR only. `quote` to `account` is derivable as `1.0` when
`account == quote`, and as `QuoteConv / BaseConv` when `account == base`, but a fourth currency unrelated
to the pair — a CHF account trading GBPJPY — needs a cross rate the tick does not carry. A designed rate
source, not a bolt-on.

### 3.5 Hedging

`PositionMode.Hedging` is a stated goal and is **unproven, not merely untested** — everything to date ran
`PositionMode.Netting`. Treat it as new work with its own validation, not as a flag to flip.

### 3.6 `Nr Total of Trades` disagrees with the Trades table by one

Statistics report 113, 1026 and 710 where `trades.csv` has 112, 1025 and 709, in goldens 19, 27 and 36;
the other three agree. The plus-one runs hold an open position at the stop date, but the open trade **is**
present in the Trades sheet as a Sell with an empty `ExitPrice` — so "statistics count it, the table drops
it" does not explain it. Pre-existing: the 2026-07-05 files carry the same numbers.

Goldens 19, 27 and 36 have Aggregated equal to Individual, while 18 has 25 against 37. Explain both in one
pass. This moves statistics semantics, so it gets its own focused change.

### 3.7 A backtest contaminates the next one in the same process

Mitigated, not fixed. Bounded risk in practice because runs are process-per-run, but it is a real
correctness hole in any in-process sequence.

### 3.8 Report folder seconds collision

Two exports in the same second overwrite each other. Needs a uniqueness suffix. Trivial; ship with the
above.

### 3.9 Re-baseline the goldens against cTrader

**Blocked on you — one cTrader session. The single re-baseline for Phases 2 and 3.**

By this point 2.6, 3.2 and 3.3 have each moved engine output deliberately. Every deviation from the Phase
0 set must already have a written explanation. Regenerate in cTrader, compare, accept, commit, and update
`verify_lock.py`.

This is a **versioned** change — the old goldens stay in git history as the pre-fix reference. Never
absorb a re-baseline into an ordinary refactor.

---

## Phase 4 — Optimization and Learning

Goal: out-of-sample strength that survives scrutiny, and a walk-forward protocol that is what it claims to
be.

### Rules that bind every item in this phase

Each of these cost a wasted campaign or a wrong conclusion. Apply before believing any result.

- **Never rank arms on a single promoted model.** Training is bit-exactly reproducible only at
  `threads=1` and `worker_threads=1`; multi-threaded it is not — the same config and seed gave -3.1 and
  -26.3. Thread reduction order is the confirmed cause. A manifest's `FullRange`, `BuyTrades` and
  `SellTrades` describe **one checkpoint**, not the arm. Compare per-seed distributions.
- **Arms sharing a seed set are paired.** Never compare them with independent-sample tests. An invalid
  Welch comparison on exactly this data produced a "significant variance collapse" finding that had to be
  retracted.
- **Power: seed sigma is 20 to 25 points.** Detecting a 10-point mean difference needs about 100 seeds an
  arm. Two to four seeds resolve only seed variance ratios, structural outcomes such as trade counts and
  direction collapse, and catastrophes such as divergence or NaN. **Pre-register which of those decides
  the arm before launching it.** A previous campaign's +4.80% headline died at n=10, t=0.79.
- **The frictionless cost decomposition is the decisive diagnostic.** Replay the same trained model with
  zero spread, commission and swap against normal costs. It separates "no edge" from "edge destroyed by
  costs" in about ten minutes. Run it **before** building any turnover-reduction, deadband or
  slower-timeframe fix — it says whether the fix can possibly matter. The 2026-07-21 result: gross Sharpe
  about 0.05 across three models with all costs removed, so no edge existed and costs were real but not
  binding.
- **Beta before alpha on any positive result.** A one-sided policy earns leverage times instrument drift,
  which looks like alpha. EURUSD H1 2015 to 2026 drifted -2.92%; the best-returning model, +31.54% gross,
  was a permanent short at about 10x, so 10 times 2.92% is about +29% — fully explained, with a Sharpe of
  0.11. Rank by Sharpe and buy/sell balance, never by raw return.
- **`balance=N` does not enforce two-sidedness.** The gate is `min(buys, sells) >= N`, so a 41-buy,
  1891-sell model at 2.1% buys passes `balance=3` trivially. Judge by ratio.
- **Silent-zero traps.** Any `x or fallback` on a config value turns a legitimate 0 into a fallback —
  `SizingATRScale` falls back to `StopLossScale`, so a no-risk arm that zeroes it yields zero volume
  silently under `SizingMode: Risk`. Always verify an arm actually traded before interpreting its return.
- **Config travels as a Parameter, never a class attribute.** Spawn workers rebuild the strategy from the
  payload, so a class attribute set in the parent process silently does not propagate. Read new knobs via
  `getattr(self.SignalManagement, "X", None)` with a class-attribute fallback.
- **`DifferentialSortino` and `DifferentialSharpe` are exactly scale-invariant** — numerator and
  denominator both scale with k cubed — so leverage cannot act through the reward. It acts only through
  the observation, since a portion of the features are account and position state. Sizing tuning is
  therefore legitimately replay-only, but replaying at a different size is **not** a pure scaling:
  different account features give different actions. Measure, never extrapolate.
- **Reward clipping is occupancy-driven, and diagnosis is not cure.** The clip rate tracks market
  occupancy; relieving it did not improve learning.
- **Record the netting knobs yourself.** The manifest records none of `SignalMode`, `TurnoverCost`,
  `PositionMode` or the sizing settings, so arms become indistinguishable unless the sweep results carry
  them.

### 4.1 Purging and embargo at fold boundaries

Golden 19 has an average hold of **537 days**. A naive train/test boundary leaks badly — a position opened
inside training and closed inside validation puts future information on both sides. This is the strongest
methodological criticism available to a reader of the thesis, and it is fixable.

Purge the training window of any sample whose label horizon crosses the boundary, then embargo a band
after it.

### 4.2 Probability of backtest overfitting and a deflated Sharpe

**The overfitting budget compounds; it does not reset per stage.** Staging turns a product into a sum —
6, 2, 2, 1 is 24 combinations flat but 11 staged — and coarse-to-fine turns a sweep into a funnel, so both
genuinely cut trials. But stage three is conditioned on winners already fitted to the same data, so the
effective trial count is the **accumulated total across every stage, round and fold**. A run already
records that number, so the deflated metric can be computed against the real one.

### 4.3 True walk-forward with `--continuous`, reported honestly

Continuity makes folds path-dependent — every fold starts near the previous winner — so `Frequency`
election becomes near-tautological, since the folds agree by construction. With `--continuous`, `Last` or
`Mean` is the honest choice, and the run must record which it used.

Note the existing seam: `SplitAPI.walk_forward_folds` takes the single-split branch when `training <= 0`
rather than entering the rolling loop. A fold's model is scored on its **validation** window, never its
training window, and the held-out `--testing` pass is the only unbiased number.

### 4.4 One untouched holdout, used exactly once

Structural discipline rather than code. Decide the window now, write it down here, and do not look at it
until the campaign is otherwise finished.

### 4.5 A real risk-free rate curve

`--risk-free` is a single constant applied across Sharpe, Sortino, Calmar, Sterling and Jensen's alpha. A
constant is wrong over 2014 to 2026 — it flatters every ratio in the ZIRP years and penalises them after
2022.

Backfill the **ECB deposit facility rate** from 2014: the right reference for a EUR account, published
daily, free. Store it as a dated series beside the market data and have the statistics read the rate in
force at each period. Keep the flag as an override for reproducibility.

### 4.6 Search beyond three free parameters

TPE or random search once the space exceeds three free dimensions; the grid stops being the right tool
there.

**The trap that would silently corrupt every sweep:** `DatasetAPI` carries `IndicatorResults`. Learning
caches them safely because its indicators never change between episodes. **Optimization varies indicator
parameters**, so reusing a cached tape wholesale evaluates every candidate with the *first* candidate's
indicators — the sweep completes, produces plausible numbers, and is meaningless. Rule: reuse the
market-data tape, always `inject(replace(tape, IndicatorResults=None))`.

Related: do **not** warm every candidate to the grid's worst-case window. It is self-consistent but breaks
standalone reproducibility — on 192 candidates, 160 scores changed and the top ten shifted — and it makes
a score depend on grid membership.

### 4.7 Re-run the seven-pair campaign on the corrected engine

The output of Phases 0 through 3, and the input to thesis iteration two. Single-threaded so it is exactly
reproducible. Compare against `Research/CAMPAIGN-7PAIR.md` pair by pair and write down what moved and why.

Then decide, on evidence, whether iteration two replaces iteration one. If the corrected engine produces
weaker numbers, that is a finding worth stating, not a result worth hiding.

**Three claims iteration one could not make. Items 4.1 through 4.4 exist to earn them.**

1. **It was not walk-forward and not continuous.** The invocation was `--training 0 --validation 12
   --testing 12`, and `SplitAPI.walk_forward_folds` takes the `training <= 0` branch, producing **one**
   split: train 2015-01 to 2024-01, validate 2024-01 to 2025-01, test 2025-01 to 2026-01. The rolling
   multi-fold loop needs `training > 0`, and `--continuous` was never passed. Iteration two must pass
   both, and 4.3 says how to elect honestly once it does.
2. **There was no genuinely held-out evaluation.** `robust_eval.py` scores over the full 2015-01-01 to
   2026-01-01, which contains the nine training years. Iteration one states this as a limitation and must
   never sell it as train/validate/test rigour. 4.4 is what fixes it.
3. **"Ten-plus years of data" is not a differentiator.** Across the 18 surveyed articles, 12 already use
   ten years or more, at a median span of 11 — identical to this work. What *is* distinctive is
   resolution over that span: only Carapuço and co-authors use tick data, over seven years. Claim
   tick-derived data across 11 years and seven pairs; never span alone.

**Numbers from iteration one that must not drift when they are recomputed.** The five-balance
path-robustness protocol is 9 900 / 10 000 / 10 050 / 10 100 / 10 200, and every pair came back
robust-positive five times out of five. Alpha leads, not return, because in every pair the
highest-return candidate failed the permutation test. USD/JPY is a documented negative — beta +1.012,
alpha -1.07% a year — and after 3.2 and 3.3 it is the pair most likely to move, since it is the one the
sizing and exposure defects hit hardest. The regime null is per-model, not a constant.

**Two facts about the delivered agent that were each got wrong at least once — read the source, do not
restate these from memory.** Gradient clipping at norm 1.0 on both critic and actor is **not** an
anti-collapse mechanism; it bounds update norm against exploding gradients, and presenting it as the
collapse fix is an error a DDPG-literate evaluator catches. Collapse is prevented by two other things:
the scale-*sensitive* reward, since a scale-invariant one collapses the actor to about 3% of available
size, and `ActorRegularization` at 0.001.

**The feature bank lives in the run manifest, nowhere else.** `<Data>/Runs/<id>/Input/Parameters.yml`
holds the 16 indicators actually used. `Research/DDPG-EURUSD-H1/Learning.yml` is a trimmed base carrying
only the fast half, and `champion_override.py` does not touch `TechnicalManagement`, so neither file is
authoritative. Always read the manifest.

---

## Phase 5 — Web app

Gated on 2.8, which is where the data comes from.

### 5.1 Move the pages onto the Research schema

`Library/Web/Research/` reads run rows and result series instead of parsing artifacts. A result detail page
renders an immutable artifact and therefore **does not poll** — polling re-mounted the grid and discarded
sheet tabs and chart zoom.

### 5.2 Profit, risk and ratio columns on `/backtesting` rows

Build as a DB read once 2.8 lands, never by re-parsing each run's stored plot HTML.

### 5.3 Signal and plot refactor

Direction and Volume signal on the Strategy **base** class; thresholds default **off** and one-sided
capable; eight toggleable lines; `Parameter` returns None for a missing key; a `--plot` hardcode audit;
optional markers and a deal map.

**Land it as a no-op first, prove the suite and the goldens, then tune the bounds.**

### 5.4 Payload thinning on one shared time grid

See the measured note in 2.8. This is what makes an 11-year H1 run openable in a browser at all.

### 5.5 iPad pass

`Library/Web` is used from a Windows desktop browser **and an iPad 12.9 inch**. Both are first-class: a
page is not done until it works on touch as well as mouse.

- **Charts must not capture touch gestures.** On the old app the Plotly DAG on the Scheduler workflow page
  swallowed one-finger drags, so trying to scroll the page zoomed the graph instead. Any embedded figure
  that does not *need* zoom must disable it — for Plotly that is `layout.xaxis.fixedrange = True`,
  `layout.yaxis.fixedrange = True`, `layout.dragmode = False`, plus `config={"scrollZoom": False,
  "doubleClick": False, "displayModeBar": False}`. Do **not** use `staticPlot: True` when clicks are still
  wanted — it kills click events too.
- **Prefer fits-without-interaction.** The workflow DAG should render every task and edge visible at once;
  the only interaction wanted is tapping a node to open that task's page.
- Touch targets, sticky headers and virtualized grids all need checking at iPad width. `LightweightTableAPI`
  is virtualized, so verify momentum scrolling behaves. Playwright emulates the viewport at 1024 by 1366
  CSS pixels.

### 5.6 Retire the CSV export

Once 2.8 is verified end to end.

### 5.7 Known and unfixed

- An ordinal pane with very few points does not fill the width — a three-fold generalization chart leaves
  space at the right edge. Lightweight clamps bar spacing and setting it explicitly is overridden.
  Cosmetic and legible.
- Multi-tab `Open` depends on the browser, not the code. Browsers permit one popup per gesture. The button
  opens the first in place, attempts the rest, and reports how many were blocked. No code-only fix.

---

## Phase 6 — Remaining

### 6.1 Logging

`StorageAPI` is unit-tested against a fake record but has never been exercised against a live Postgres run
end to end, and the Scheduler still writes durable rows through `ExecutorAPI._open_log_`. Close both.

Measured dead end, do not retry: a drain thread for the console and file sinks. A CPU-bound Python thread
starves a concurrent writer 253 times over, and the queue fell 93k records behind. Async is a per-sink
property — console and file synchronous, `StorageAPI` not.

### 6.2 Realtime hardening

Audited 2026-07-02, needs a cTrader session: warmup bars are double-added to the market buffer;
`BufferAPI._worker_` can deadlock on a flush when connect fails; transport hardening; an unused universe
buffer; the watchdog is armed only on `Init`; no hung-peer timeout.

### 6.3 Strategy state recovery

Persist Signal and Risk machine state across a Live restart — `SessionAPI.State` bytes, loaded at
`deploy()`, saved on `Shutdown`.

### 6.4 Test coverage gaps

`Statistic` 1 file for 1889 lines; `Scheduler` 1 for 1700; `Model` 2 for 1654; `Web` 3 for 3449; `Auth` 1
for 460; `Indicator` 4 files for 43 modules.

### 6.5 Dead surface

Zero callers outside the package `__init__`. Delete, or keep deliberately as a library offering.

`Utility/Path.py` 28 of the 36 `traceback_*` and `inspect_*` grid, about 120 lines; `Utility/Datetime.py`
`string_to_datetime`, `datetime_to_iso`, `iso_to_datetime`, `weekday_shift_datetime` and seven
`<day>_shift_datetime`; `Utility/Runtime.py` `is_local`, `is_service`, `find_user`, `is_python`,
`is_ipython`, `is_terminal`, `is_console`, `match_env_vars`; `Utility/IO.py` `is_readable`, `is_writable`,
`smartlink`, `symlink`, `hardlink`; `Utility/Typing.py` `findvariable` and `getvariable`; `Utility/HTML.py`
entirely.

`Portfolio.py` all 16 `load_`, `save_`, `pull_` and `push_` statics for accounts, orders, positions and
trades — about 150 lines including a 25-column Contract JOIN repeated three times — plus
`calculate_statistics`, `BuyOrders` and `SellOrders`; `Portfolio/Statistic.py`
`generate_realized_report` and `generate_unrealized_report`; `Market.py` `load_ticks`, `save_ticks`,
`count_ticks`, `load_bars`, `save_bars`; `Universe.py` all 12 `save_` and `load_` plus `pull_timeframes`.

Convenience properties never read and not emitted by `dict()`: `Account` IsDemo, IsHedged, IsNetted,
UnrealizedReturn, MarginRatio, FreeMarginRatio, CreditRatio; `Order` IsAccepted, IsFilled, IsRejected,
IsExpired, IsCancelled, ExecutionRatio, UnfilledVolume; `PnL.LogPnL`; `Position.MarginUtilization`;
`Trade` DurationDays and IsClosed; `Bar.RangeTick`; `Price.LogPrice`; `Tick.InvertedMid`; `Timestamp` Sin,
Cos, Epoch, Yearday, Millisecond; `Contract` IsSpot, IsDerivative, IsLinear, IsNonLinear; `Ticker` Dashed,
Slashed, Underscored; `Timeframe.Hours`. Plus about 25 `@overridefield` Position columns computed by every
`dict()` and dropped by `reporting_view`.

`Database.structured`, `ManagerAPI.delete_run`, `OptimizationAPI.trials`, `BrownianNoiseAPI`,
`GeometricBrownianNoiseAPI` (no factory; DDPG hardcodes OU),
`Sources/Indicators/Connector/Connector.cs` (the cTrader hello-world template), the empty
`Sources/Plugins/Plugin`, and `Requirements.txt` at 0 bytes.

`Library/Formulas/` stays — an xlwings Excel UDF feature with zero callers that you intend to renovate.
The `xlwings` pin stays with it.

### 6.6 Simplifications

Behaviour-preserving, provable by AST body hash plus the suite. The golden-adjacent ones need Phase 0
first.

- `Position.py`: about 40 `@overridefield` properties are four body shapes — `pnl/(Volume*unit)`, a signed
  price difference over unit, `min`/`max(0, x)`, and `_max_equity_*_pnl_.<attr> or 0` — so one helper each.
  `Order` and `Position` share `_unwrap_price_`, `_make_price_` and `_assign_price_`, timestamp assignment
  and the Session and Account property pairs, which is a Portfolio mixin with two hooks.
- Indicators: a `BaselineAPI(TechnicalAPI)` carrying the four `filter_` and `signal_` rules plus `batch` —
  9 classes times 4 identical methods, 6 identical `batch`, about 125 lines; `MAC`, `DMAC` and `TMAC`
  collapse to one `_AVERAGE_` class attribute; ROC, ATR and RV have identical rules; `FundamentalAPI`
  equals `SentimentalAPI` equals `TechnicalAPI`'s composite half; `MA.py` builds the six-way `match` twice.
- `SystemAPI._process_updates_` is 190 lines and about 70 `match` arms rebuilding the same seven-key
  context — an `UpdateID` to `(class, reader)` table plus one `context()`. `_fitness_()` is byte-identical
  in `LearningAPI` and `OptimizationAPI`, so it belongs on `BacktestingAPI`. `Realtime._binary_*_` are
  `_lower_` class constants.
- `Strategy.py` `strategy_management`: `update_closed`, `stop_loss`, `take_profit`, `margin_call`, the
  `update_modified_*` family and `update_closed_order`, `filled` and `expired` differ only in the log line,
  so closures. `Hybrid/DDPG.py`: `Defaults["Realtime"]` equals `Defaults["Learning"]` for 35 lines, the
  12-field state block appears in both `__init__` and `_initialize_`, the optional-parameter idiom repeats
  ten times, and `_hedge_(update, close)` never uses `update`.
- `Model`: the `memorize`, `remember`, `_soft_update_` and `decide` scaffold is copied into the DDPG, SAC
  and TD3 agents and belongs on `AgentAPI`; SAC and TD3 `Critic.forward` are byte-identical; the whole
  module uses `_name` privates where RULES says `_name_`; `remember()` annotates a tuple literal instead of
  `tuple[np.ndarray, ...]`.
- `Market.py`: `pull_bars` repeats an 11-column tick join five times; `init_data`, `update_data` and
  `update_offset` list the same series three times; `Series.py` `last()` and `tail()` share a 500-character
  row-to-`TickAPI` expression, and `over`, `under`, `crossover` and `crossunder` share a five-line prelude;
  `Tick.py` has seven same-shape setters. `Universe.py` has 11 live `pull_` and `push_` of one shape;
  `Timeframe.py` has five comparison dunders that are `total_ordering`.
- `Database.py`: the seven-line target-validation block is copied into `exists`, `diff`, `create`, `delete`
  and `migrate`; `executeone` and `executemany` share a 12-line prelude; `search` repeats an empty-catalog
  literal three times; `executemany` logs a failure via `.error` then `.exception`, the same double-log as
  `Service`, `Bloomberg.Streaming` and `Remote`. `Dataclass.py` `tuple`, `list`, `dict` and `json` forward
  seven kwargs explicitly. In `Auth`, Cloudflare `_verify_` and OIDC `authenticate` share the JWKS and
  `jwt.decode` block, which is a `_claims_()`.
- Two near-identical `TrayAPI` classes in `Scheduler/Tray.py` and `Web/Service/Tray.py`; `Runner.load` and
  `SchedulerAPI._task_` both build a detached `TaskAPI`, which is a `TaskAPI.fetch(db, uid)`;
  `Logging.File.FileAPI` and `Utility.File.FileAPI` share a name, so consider renaming the sink
  `FileSinkAPI`.
- `Sources/Robots/.../Logging.cs` private constants are lower-case; `Tests/Strategy/test_Strategy.py`
  imports `MagicMock` inside six tests and `test_Workspace.py` imports `json` inside three; comments appear
  in seven test files, and the `test_Sizing.py` derivations could move into the assertions;
  `Tests/Benchmark/IPC.py` is a benchmark script living under `Tests/`.

### 6.7 Blocked

- **Dataframe dtype preservation and an FK-aware `reorder`.** `reorder` must become FK-aware before the
  per-fetch `shrink_dtype` can go, which would remove the latent Float64-to-Float32 price downcast.
  Do **not** "fix" this by making `diff` or `migrate` order-sensitive: migrate's rebuild path uses rename,
  recreate and INSERT-SELECT, which does not re-point inbound foreign keys, so an order-aware migrate would
  break FK-referenced tables such as Scheduler to Auth.User on boot.
- **`Setup/Install.py` and `Setup/Task.py` both define `provision()`** — different modules, different jobs,
  no collision today. Rename one if it ever confuses.
- ~~C# warnings: two `CA1416`, three `CS0618` deprecated order APIs.~~ **Stale — closed 2026-09-10.**
  Both solutions build warning-free in Debug and Release, on SDK 6.0.100 and 10.0.401 alike. See 1.0.1.

---

## Phase 7 — Indicator connector

`Sources/Indicators/Connector` is the untouched cTrader indicator template today (see 1.0.1). This is
what it becomes: **a bridge that plots a Python-implemented indicator directly onto a cTrader chart, so
it can be compared against cTrader's own built-in by eye and by value.**

That makes it a **validation instrument, not a feature.** `Library/Indicator/Technical` is the input
half of every strategy in the framework — the DDPG feature bank alone is 16 indicators — and nothing
has ever proven those implementations agree with the platform's. A silent disagreement in, say, `ATR`
or `ER` does not crash anything; it quietly changes every observation the agent ever sees. This phase
is how that class of error stops being invisible.

### 7.1 The bridge

Mirror the Robots connector rather than inventing a second mechanism: shared memory, single-slot
request/response lockstep, the same `Protocol` vocabulary. An indicator is a far smaller surface than a
robot — it needs bars in and a series out, with no orders, positions or account state — so the
subscription is minimal and most of `Action/` and `Update/` does not apply.

**`Setup/Enum.py` must emit into both projects** once this starts; `OUTPUT_PATH` is currently a single
hardcoded path (see 1.0.2). The two `.algo` artefacts must always be generated from the same enum
source, or the wire mis-decodes exactly as it would between mismatched robot builds.

### 7.2 The comparison harness

The point of the phase, and worth designing before the bridge:

- Plot the Python series and cTrader's native equivalent on the same chart, and a **difference series**
  beneath. Eyeballing two overlapping lines hides small persistent offsets; a difference pane does not.
- Report the maximum absolute difference, and the bar index where it occurs, over the loaded range.
- **Warmup is where these will actually disagree.** A rolling indicator's first N bars depend on how
  the seed is chosen — cTrader and this framework need not agree, and a difference that vanishes after
  N bars is a warmup convention mismatch rather than a formula error. Report the two regimes
  separately or the diagnosis is wrong.
- Where the framework has no native counterpart, the comparison is against a hand-computed fixture
  instead, not skipped.

### 7.3 Coverage

Start with the DDPG feature bank, since those are the implementations carrying published results:
`ATR 14`, `ER 120`, `RV 16/480`, the `SMA` family and the `ROC` family. Then the rest of
`Library/Indicator/Technical`. Record each verdict — agrees, agrees after warmup, or disagrees with the
measured magnitude.

**A disagreement is a finding, not a bug to rush.** If a Python indicator differs from cTrader's, the
framework's own goldens and campaign are internally consistent regardless; what changes is the claim
that can be made about it. Decide per indicator whether to match the platform or document the
difference — do not reflexively change an implementation the published results depend on.

**Done when:** the connector plots any registered Python indicator on a cTrader chart beside its native
counterpart with a difference pane, and the feature-bank indicators each carry a recorded verdict.

---

## Phase 8 — Live trading panel at `/trading`

`Library/Web/Trading/Trading.py` is a 910-byte placeholder today: a title, a lead paragraph and a panel
reading "No strategies running." This phase replaces it with the console the framework is actually for.

It is last because it consumes almost everything above it: per-tick updates need the live connector
(1.3, 1.4) and the batch protocol (1.5); order actions need the four target-volume actions (1.7); a
non-EUR account needs generic currency (3.4); a hedged account needs 3.5; surviving a restart needs 6.3;
and the run and result surfaces it links into come from 2.8.

### 8.1 The transport seam

Every other page in the app either polls on a timer or renders an immutable artifact and does not poll
at all. **A live panel is neither.** It needs push, and it needs to stay correct when push drops.

- Build on the Scheduler's existing listen, notify and wait seam rather than inventing a second one.
- **Connection count is a correctness budget, not a tuning knob.** Postgres here is `max_connections`
  400. A per-viewer subscription needs a hard ceiling and a return path — verify with a soak where
  `pg_stat_activity` plateaus, never by watching a page feel responsive. A thread-local cache is not a
  pool; one grew to 409 clients and was reverted.
- Degrade explicitly. If the push channel drops, the panel must say so in the header and fall back to a
  slow poll — never silently show stale prices as though they were live. Stale numbers on a trading
  screen are worse than no numbers.

### 8.2 Account header

Balance, equity, margin used, free margin, margin level, unrealized P&L, and open exposure broken out by
currency. Equity and margin level update per tick; balance only on a closed deal.

Margin level is the number that matters when things go wrong, so it gets a status treatment — good,
warning, serious, critical — with an icon and a label, never colour alone.

### 8.3 Position and order blotters

Two virtualized `LightweightTableAPI` grids.

**Positions:** symbol, side, volume, entry price, current price, stop loss, take profit, swap,
commission, spread paid (from 3.1), gross and net unrealized P&L, duration, and the strategy that owns
it. Row actions: modify stop and target, close partially, close fully.

**Orders:** symbol, side, type, volume, limit or stop price, expiry, state. Row actions: modify, cancel.

Both need a totals row that is computed server-side, not summed in the browser from a thinned payload.

### 8.4 Order ticket

Market, limit and stop, with the volume field driven by the **same** sizing path the engine uses — not a
reimplementation. After 3.2 and 3.3 there is exactly one correct sizing formula in the framework and this
ticket must call it, so that what the panel shows and what the engine does can never disagree again.

Show the derived risk in account currency and as a percentage of balance before the button is armed.
Stops and targets accept pips or price, and convert visibly.

### 8.5 Strategy control and the kill switch

Which strategies are deployed, on which securities and timeframes, what state each Signal and Risk
machine is in, and how long since the last update. Per-strategy start, stop and flatten.

**The kill switch is the most important control on the page and is therefore the one that must work when
everything else is degraded.** Flatten-all and disconnect must not depend on the chart layer, the push
channel, or a payload having loaded. Give it its own path, confirm destructively, and log the outcome
where `Run.log` will capture it even if the process dies immediately after.

Mutations are `Editor` and above through the existing router gate. A `Viewer` sees the panel and touches
nothing.

### 8.6 Live chart

One Lightweight chart per watched security: price, the open position overlaid with its entry, stop and
target as price lines, and fill markers as they arrive. The live signal tape from 2.8 item 3 goes
underneath as its own pane, which is what makes an agent's behaviour legible while it is trading rather
than only in hindsight.

Reuse `Library/Statistic/Workspace.py` for the spec — it is the single composition layer and imports no
Dash, so the same definition serves the panel and the backtest view.

### 8.7 Connection health

Connector state, last heartbeat, tick latency, ticks a second, reconnect count, and the current
subscription per strategy. This is the panel that answers "is it actually running", and it is the first
thing to look at when a result looks wrong.

### 8.8 iPad

The whole panel is subject to 5.5, and more strictly: this is the page most likely to be opened away from
the desk. Blotter rows need touch-sized targets, the order ticket must be usable one-handed, and the kill
switch must be reachable without a precise tap.

**Done when:** a Simulation deployment drives the full panel end to end — positions open and close,
orders fill and cancel, the account header tracks, the kill switch flattens — and then the same against a
live demo account, with the push channel deliberately severed mid-session to prove the degrade path.

---

## Appendix A — Measured, do not re-derive

- **Performance.** Warm NNFX H1 year about 1.5 s; D1 ten years about 3.2 s; H1 ten years about 25 s.
  Learning frozen-tape replay about 3.12x a pass. Cold preload 12 to 15 minutes per ten-year dense-tick
  window, cached at `~/.cache/cAlgo/preload`.
- **Dead ends, do not retry.** A numpy ring buffer for `SeriesAPI`; mypyc and Cython; a drain thread for
  the console and file sinks.
- **Logging cost.** Suppressed record 128 ns, emitted 1188 ns, timestamp 234 ns — down from 271, 4961 and
  1990.
- **The warmup window belongs in the cache key; the tick tape does not.** `BacktestingAPI._preload_` keys
  on security, start, stop, timeframe, auto, resolution and window. Omitting the window let the first
  candidate's warmup define every later one's. But keying the *whole* dataset per window was the wrong
  granularity: 0.7% of a rebuild depends on the window, 99.3% does not. `_tape_` caches
  `_acquire_frames_` on a window-free key. `OptimizationAPI._ordered_` groups candidates by technical
  parameters to keep the cheap per-window rebuild consecutive — 192 EURUSD D1 candidates went 26.96 s to
  19.09 s with identical scores.
- **Market data, audited 2026-08-25.** Seven majors — AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF,
  USDJPY — carry D1, H1, M1 and MN1 from 2014-01 to 2026-08, about 78k H1 and 4.6M M1 each. EURJPY and
  US500 have `Security` rows but no data; 1000 defined, 7 populated.
- **2016-01-11 to 2016-01-25 is absent in all seven pairs, ticks and bars, and is not repairable.** Proven
  2026-08-25 by a re-download that visited the month and wrote zero rows. Do not spend another download on
  it; it predates the thesis and is uniform across pairs, so it does not bias comparison.
- **Stored conversions are accurate across the whole history.** Implied cross rates track the real rate to
  within -0.001% to -0.009%, consistently bid-side, with zero static stretches. No re-download is needed
  for conversion accuracy. The cTrader "download historical data for additional symbols to convert
  profit/margin" option must stay **on** — with it off, the live cBot path freezes the cross-pair spot and
  the conversion goes stale, while the offline engine reading stored fields stays correct.
- **Postgres.** PostgreSQL 18 on Windows, service `postgresql-x64-18`, data directory
  `C:/Program Files/PostgreSQL/18/data`. Tuned 2026-06-24 and live since: `synchronous_commit = on`
  (never lose a committed trade), shared_buffers 8 GB, work_mem 64 MB, maintenance_work_mem 2 GB,
  effective_cache_size 48 GB, max_wal_size 16 GB, checkpoint_timeout 15 min, wal_compression on,
  random_page_cost 1.1, effective_io_concurrency 200, max_parallel_workers 24. shared_buffers is
  deliberately 8 GB rather than the Linux 25% rule — on Windows large shared-memory segments are less
  effective and the OS file cache does the heavy lifting, while 8 GB pins all hot indexes with margin. For
  heavy connection scale use PgBouncer rather than raising `max_connections` further.

## Appendix B — Decided, do not re-litigate

| Decision | Rationale |
|---|---|
| DB-first for 2.8, no CSV interim | the backend must be touched anyway to capture equity and signals |
| Weights in the DB as bytea, with `materialize()` | self-contained and atomic with results; nets are kilobytes to megabytes |
| Reuse the Scheduler executor, plus a `Task.Arguments` column | `ExecutorAPI` and `Runner` already own spawn, heartbeat leases, PID tracking, tree-kill, retry, peak RSS, reaping and log capture. `Research.Run` **references** a `Scheduler.Run` rather than reimplementing it, exactly as `Scheduler.Run` references `Logging.Log` |
| `Library/Research` owns the domain | parameter snapshots, result series, headline metrics and `KeptAt` are research concepts the Scheduler must not learn |
| Retention as a nullable `KeptAt` on the Run row | null means eligible for the 30-day sweep, set means retained with its full series. One column, one index; no second table and no status enum to keep in sync |
| `UpdatedAt` and `UpdatedBy` stay on every datapoint | part of the `DatapointAPI` contract; removing them would have to be a `Library/Database` capability |
| Conversions rebuilt from full tick streams, not H1 bars | accuracy over convenience |
| `Library/Formulas` stays | the xlwings Excel UDF surface is to be renovated, not deleted |
| Paper-mapping docstrings stay | `Library/Model/Method/DDPG`, `SAC`, `TD3`, `Model/Core/Noise`, `Strategy/Model`, `Strategy/Hybrid/DDPG.py` including the reward-clipping comment in `Strategy/Model/Reward.py` |
| The search space lives in a sibling `Optimization.yml` | it cannot live in `Backtesting.yml`, whose list arity is **structural** — `RiskPercentage: [1.0]` unpacks with `self._risk_percentage_, = ...` and `BaselineMode: [Signal, Off, Signal]` unpacks as three positions |
| Retention is one horizon, 30 days, everywhere | log files, `Logging.Log` rows, temp run logs, repo caches |