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
| **8** | Live trading panel at `/trading` | Phases 1, 3 and 5 complete | after 5 |
| **9** | Interactive Brokers provider | Phase 8 complete | after 8 |
| **10** | Option strategy pricer and backtester | Phase 9 complete (chain data) | last |

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

**Each configuration is run twice because there are two engines, not two ways of launching one.**
`RealtimeAPI` and `BacktestingAPI` are siblings under `SystemAPI` with zero references between them.

- **The cTrader half** is the Connector cBot inside cTrader's own Backtesting tab, which is
  `Simulation`, which is `RealtimeAPI`. cTrader owns the account, the window and the feed, and
  `Realtime.py:283-303` **unpacks gross, commission, swap and net from the wire** — they are cTrader's
  numbers, stored verbatim. Only the user can run it, from the platform, never the terminal.
- **The CLI half** is a standalone `Backtesting` run, which is `BacktestingAPI`, which computes its own
  fills and fees. It is CLI-only because there is no cTrader tab for it, and it is the engine every
  item in Phase 3 targets.

**This matters for what a golden proves.** The 2026-09-10 set is `Simulation` only. It gates the wire
decode, the portfolio bookkeeping, the trade-to-deal aggregation and `Library/Statistic` — and it found
three real defects in exactly those places (3.6, 3.6.1, 3.6.3). What it **cannot** do is measure a fill
or a fee, because those figures came from cTrader; agreement on them is tautological. **A
`BacktestingAPI` change cannot move these files at all.** Deciding item 3.2 needs the CLI half for the
same reason: in `Simulation` our sizer computes the volume and cTrader merely executes it.

So the set below is entered twice: once in cTrader's Backtesting tab, once as CLI flags — and until the
CLI half exists, Phase 3 has no gate.

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

### 0.3 The `BacktestingAPI` half — the gate Phase 3 actually needs

**The cTrader half is done: all five runs captured 2026-09-10 in `Tests/Golden/`** with `Run.json`,
`Parameters.yml` and the five exports each, `RESIDUALS.md` recording the measured comparison per run,
and `Contract.json` freezing the terms. Three defects fixed to get there — the `deals.csv` UID export
writing a Polars `Series` repr, `Run.json` never written on `Simulation` because `_snapshot_` read
`args.start`, and `wt.exe` collapsing quotes so a multi-word `--description` killed the run.

**The `BacktestingAPI` half is not started, and nothing in Phase 3 has a gate until it is.** Run the
`Backtesting` subcommand on the same five configurations, pinned to `Contract.json` rather than `Auto`,
because contract terms are a mutating input — `Universe.Contract` is overwritten by every cBot run
(`UpdatedBy` reads `Autosave`), swap feeds balance, balance feeds `Risk` sizing at 1%, so a drifted
swap rate moves every volume and every number downstream, not just `SwapPnL`.

Two things fall out that nothing else can give:

1. **A regression gate for the engine Phase 3 changes.** Byte-identity on
   `trades/positions/orders/deals` across an engine change.
2. **The first real accuracy measurement.** The five cTrader reports are now reference points, so
   comparing our *computed* P&L against them tests what the old "sub-pip intrabar exit, ~0.5%/y swap"
   note claimed. That note is currently **unverified, not disproven** — the `Simulation` runs could
   never test it. Expect divergence; it is a measurement, not a byte check.

**Done when:** five `Backtesting` folders committed beside the `Simulation` ones, the residual against
cTrader written per run in `RESIDUALS.md`, and item 3.2 decided on evidence from this half.

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

**Offline half done 2026-09-15; the live half waits on the Open API application (1.4 gate).**
`Tests/Spotware` runs in the default suite, 77 passed and none skipped. The module went from 1 624 to
1 037 lines in a final pass that removed every re-implementation it carried:

- **Wire enums come from the vendor's own protobuf descriptors**, not hand-written maps. `_code_`
  encodes a wire name, a framework member (`TimeInForce.GoodTillCancel`) or an integer; `_named_`
  decodes to the framework's naming, so `OrderStatus[...]`, `TimeInForce[...]` and `Direction[...]` read
  the output directly. `TimeframeAPI.normalize` resolves `Hour`/`Daily` before the period lookup.
- **Timestamps are exact integer milliseconds** through `datetime_to_epoch`/`epoch_to_datetime`,
  naive UTC out. The old path went through float seconds and could truncate a millisecond, and
  `Portfolio` returned aware datetimes against the framework convention.
- **Units are decoded symmetrically.** Prices from 1/100000, money by `moneyDigits` (a zero-digit
  account was silently treated as two), and volumes from cents to units in both directions.
- **One subscription loop.** `SpotwareAPI._listen_` replaces four copies (three streams and the depth
  snapshot); trendbar and depth-quote decoding exist once, on `MarketAPI`.
- **Removed:** the eight side-less `*_buy_*`/`*_sell_*` wrappers, which acted on either side and so lied
  by name; the ten sided ones are `partialmethod`s. Twelve docstrings, all inline imports, stale
  `list[...]` return types.
- **Fixed in passing:** `disconnect` blocked forever when the reactor was not running, reached from
  `__del__` and `atexit` — the real cause of the test skipped as "Hangs during execution". `ticker()`
  read `digits` off archived symbols, which do not carry it. `cashflow()` now walks the documented
  one-week maximum window. Market and range orders take `relative_stop_loss`/`relative_take_profit`,
  because the documentation states absolute levels are not supported on `MARKET` orders.

**Verify against a live session before trusting, in this order** — each is documented behavior the
offline suite cannot exercise:

1. **Closing-deal direction.** `trades()` reports the deal's own `tradeSide`, which for a closing deal is
   the opposite of the position it closes. `TradeAPI` convention is the position's direction. Decide
   which the frame should carry before 1.1 compares trades.
2. **Pagination.** `ProtoOADealListRes` and `ProtoOAOrderListRes` both carry `hasMore`; `trades()` and
   `orders()` read only the first page.
3. **Live trendbars** may require an active spot subscription first.
4. **Rate limit.** The tick pagination loop has no throttle against the 5 requests a second historical
   limit in 1.4.
5. **TLS hostname verification is degraded in the environment.** Twisted warns that `service_identity`
   cannot import, because 26.1.0 needs a newer `cryptography` than the 42.0.8 that the
   `ctrader-open-api` pin (`pyOpenSSL==24.1.0`) holds it to. The 2026-09-14 environment update
   reinstalled that pair. `service-identity` 24.2.0 parses certificates through `pyasn1` and declares no
   `cryptography` floor (checked by dry-run metadata, not yet installed); pin it in `Quant.yml` or the
   next update reverts it again.

**Done when:** the five points above are verified or fixed against a live demo session.

### 1.3 Connector abstraction — deferred

**No shared provider base class until many providers pull genuinely different kinds of data** (decided
2026-09-15). Each provider is its own package on `ServiceAPI` + `DataframeAPI`, as `SpotwareAPI` and
`BloombergAPI` already are; simplification comes after the providers exist, not before.

An attempt was built 2026-09-11 and stripped 2026-09-15: a `Library/Provider` package (`ProviderAPI`,
`ProviderSectionAPI`, `Capability`), `ResultAPI` in `Database/Dataframe.py` and `ServiceAPI._listen_`.
None of it had a production caller. `ResultAPI` duplicated Polars plus `DataframeAPI.frame(legacy=)`;
the section vocabulary was a second set of column names beside `TickAPI.ID`; the symbol-to-`Security`
map was in-memory where it has to be persisted Universe data; `ProviderAPI` collided with
`Library/Universe/Provider.py`; and `_listen_` was shadowed by `RemoteAPI._listen_` in Bloomberg. What
survived is the Spotware drift repair — columnar frames and the canonical keys `Symbol · Timeframe ·
Timestamp · Ask · Bid · Open · High · Low · Close · Volume · Quote · Size · Action`.

### 1.4 Continuous live capture

Replace the per-ticker Download-strategy cBot workflow with an always-on capture service under the
Scheduler. Tick-only storage (Phase 2) is what makes this affordable.

Keep per tick: Ask, Bid and Volume, plus OHLC ticks rather than prices alone, for intrabar accuracy —
possibly High and Low for **both** Ask and Bid rather than bid-only pillars.

**Hard constraints from the official Open API documentation, verified 2026-09-15:**

- **5 requests a second per connection for historical data**, 50 for everything else. Every tick window
  costs **two** requests — `ProtoOAGetTickDataReq` returns one quote side, so BID and ASK are fetched
  separately and merged — and each is paginated. This, not the network, bounds the backfill's wall
  clock; size it before promising a date.
- **Access tokens expire after 2 628 000 s (about 30 days); refresh tokens do not expire.** An
  always-on service must refresh in place, via the `refresh_token` grant or `ProtoOARefreshTokenReq`,
  and persist the new token outside git.
- **Application approval and blocking are undocumented.** Neither the FAQ, the authentication guide nor
  the getting-started page describes application statuses or why one is blocked. The official support
  channel is the Telegram group linked from the documentation.

**Gate:** the application (id 39640) was **Submitted**, then **blocked**, reason unknown as of
2026-09-15. Nothing in this item can be exercised until it is active. The Download cBot path remains
the working acquisition route meanwhile, so no other phase is blocked by it.

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

### 2.1.1 `Market.Tick` has no index on `(Security, Timestamp)` — but do NOT build it yet

**Measured 2026-09-11.**

```
indexes on Market.Tick:  Tick_pkey  UNIQUE btree ("UID")
```

That is the **only** index on a **1.66 billion row, 295 GB** table (244 GB heap, 51 GB index, 153 bytes
a row). Every query the engine issues is `WHERE "Security" = ? AND "Timestamp" BETWEEN ? AND ?`, so
every one is a **full sequential scan**. This is almost certainly the real cause of the 12-15 minute
cold preload, and it is why a diagnostic running sixty one-hour range queries had to be abandoned.

**Deliberately deferred.** Phase 1 ends with the tick tape being **deleted and re-backfilled** from the
Spotware feed, so an index built now is thrown away — and worse, bulk-loading 1.66 bn rows *into* an
indexed table is far slower than loading first and indexing after. The canonical order is **create →
bulk load → index → compress**, and building it now inverts it.

**The index belongs in the reload sequence at 2.10, not here.** This item stays only to record why the
current database is slow and that the cause is understood.

### 2.1.2 Server configuration against the actual hardware

**Audited 2026-09-11.** The server is **already deliberately tuned** — not a stock install. Hardware:

| | |
|---|---|
| CPU | Intel i9-14900K — 24 cores / 32 threads, 36 MB L3 |
| RAM | 64 GB DDR5-5800, ~46 GB free |
| Disk | **single** Samsung 990 PRO NVMe, 930 GB, **379 GB free** |
| Server | PostgreSQL 18.3, `shared_preload_libraries = timescaledb`, `timescaledb.max_background_workers = 16` |

**Already correct — do not touch:** `shared_buffers` 8GB · `effective_cache_size` 48GB ·
`random_page_cost` 1.1 · `effective_io_concurrency` 200 · `max_worker_processes` 32 ·
`max_parallel_workers` 24 · `max_wal_size` 16GB · `checkpoint_timeout` 15min at 0.9 · `jit` off.

**Timescale is already preloaded**, so 2.1 is a bare `CREATE EXTENSION` with **no restart**.

Worth changing, in value order:

| Setting | Now | Proposed | Why |
|---|---|---|---|
| huge pages | **`huge_pages_status = off`** despite `huge_pages = try` | grant *Lock pages in memory* to the service account | 8 GB of shared buffers through 4 KB pages is 2 M TLB entries. The setting is asking and being refused |
| `vacuum_cost_limit` | 200 (the spinning-disk default) | **2000** | Throttles autovacuum to a crawl on a billion-row table sitting on NVMe |
| `wal_compression` | `pglz` | **`zstd`** (`lz4` also available) | The backfill is WAL-heavy; pglz is the oldest and weakest of the three |
| `track_io_timing` | off | **on** | This project tunes by measurement; without it `pg_stat_statements` cannot attribute I/O |
| statistics on `Security`/`Timestamp` | 100 | **1000** per column | Seven securities across twelve years is a skewed distribution |
| `max_parallel_maintenance_workers` | 4 | **8-12**, per session for index builds | 24 cores available |
| `maintenance_work_mem` | 2 GB | **8-16 GB**, per session for index builds | 46 GB free; fewer merge passes |
| `work_mem` | 64 MB | keep global, **raise per session** for preload and analytics | `max_connections` is 400, so a global raise is a memory hazard |
| `synchronous_commit` | on | **off for the backfill session only** | The largest single bulk-write win. It can lose the last commits on a crash but never corrupts, and a backfill is replayable by definition |

### 2.10 The reload — the only chance to never materialise 295 GB again

**The strategic point.** Compression was measured at **90.7%**, so the 244 GB heap becomes roughly
**23 GB**. Doing that as a migration of existing data (the old 2.2) needs both copies on a disk with
379 GB free. Doing it as part of a **reload** never materialises the uncompressed table at all.

Sequence, and the order is load-bearing:

1. Create the hypertable **empty**, with the chunk interval set before any data lands.
2. Session settings for the load: `synchronous_commit = off`, `maintenance_work_mem` raised.
3. **Bulk load** the Spotware backfill.
4. **Then** create `(Security, Timestamp)`.
5. **Then** enable compression, segmented by security.
6. `ANALYZE`, restore `synchronous_commit`.

**Chunk interval: one month.** Guidance is that an actively-written chunk should fit about 25% of
`shared_buffers`, so ~2 GB. At 153 bytes a row that is ~13 M rows; the tape runs ~11.5 M ticks a month
across the seven pairs, or ~1.8 GB. One month lands on the number.

**Compression settings:** `compress_segmentby = "Security"`, `compress_orderby = "Timestamp"`. Segmenting
by security matches the access pattern exactly — every query filters on one security — and raises the
ratio, because one instrument's prices compress far better than seven interleaved.

**Do not add a space partition on `Security`.** Timescale partitions by time; a space dimension earns
its keep across nodes, and there are seven securities on one machine. The index handles it.

**Done when:** the reloaded table is measured against the 295 GB baseline, a bounded range query shows
an index scan in `EXPLAIN`, and the run 5 cold preload is re-measured against today's 568s.

### 2.2 Compress `Market.Tick` as it stands

No schema change, so the goldens cannot move — which is what makes this the right first step. Convert
to a hypertable, set a compression policy, verify row counts before and after, and re-read a known day.

**Done when:** row count preserved exactly, a spot-check day reads back identical, and the reclaimed
size is recorded here.

### 2.3 Continuous aggregates for bars, and the two-sided bar

Derive every timeframe on demand from the tick tape and retire the `Bar` tables (5.9 GB). This unlocks
H4, D2, W1 and arbitrary intervals, which the framework cannot offer today. **`Tick` becomes the only
stored market table.**

**The session-stamp convention must survive.** Bars are stamped at 22:00, or 21:00 under DST, so a
Thursday-stamped D1 bar *is* Friday's session and D1 carries five bars a week stamped Sunday through
Thursday. An aggregate built on calendar days silently produces a different tape.

#### The bar becomes two-sided, which is what makes 3.0 exact

Today `High` is the tick at which the **bid** was highest, and its ask is incidental. Measured on
USDJPY 2023-05-10 14:00: the stored `HighTick.Bid` is 134.718, which is exactly the true maximum bid,
while the stored `HighTick.Ask` is 134.721 against a true maximum ask of **134.724**. The bar is
bid-biased, and that bias is the entire reason `_should_descend_` carries a spread pad.

A crossing test needs four extrema, and they live on two different series:

| Armed level | Triggers on | Needs |
|---|---|---|
| Buy stop loss | `bid <= sl` | min bid |
| Buy take profit | `bid >= tp` | max bid |
| Sell stop loss | `ask >= sl` | **max ask** |
| Sell take profit | `ask <= tp` | **min ask** |

An aggregate supplies all four natively — `max("Bid")`, `min("Bid")`, `max("Ask")`, `min("Ask")` — so
the pad disappears and the gate becomes exact rather than heuristic. Prices are discrete, so max and
min are **necessary and sufficient**: if `max ask >= sl` some tick triggers, and if `max ask < sl` none
can. No interpolation assumption anywhere.

**Tested 2026-09-11 — `first`/`last` ARE supported, but argmax is not tie-safe.** Probed on a throwaway
database (created, tested, dropped; `Quant` untouched). TimescaleDB **2.24.0** is available on the
server though **not yet installed** in `Quant` — that is item 2.1.

| Test | Result |
|---|---|
| CAGG with `max`/`min` only | created, refreshed, correct |
| CAGG with `last(ts, bid)`, `last(ask, bid)`, `first(ts, bid)` | **created and refreshed** — the old restriction is gone |
| CAGG vs direct scan, **strictly unique** bids | **6/6 identical** |
| CAGG vs direct scan, heavy ties | agreed in one layout, **disagreed in another**; `max`/`min` agreed in **both** |

So the four scalars the gate needs are safe and deterministic. **The extremum timestamps are not.**
`last(ts, bid)` picks an arbitrary row among ties, and which one depends on chunk layout and insertion
order — real tick data ties constantly, because the same bid is quoted repeatedly inside a bar. A
golden that embeds an argmax timestamp would therefore not be reproducible.

**Consequence for the model:** `HighPoint.BidTick.Bid` is safe; `HighPoint.BidTick.Timestamp` needs a
**total order** to be deterministic — break ties on the timestamp itself, so "the maximum bid, earliest
occurrence" is a definition rather than an accident. Decide the rule explicitly and write it down;
do not inherit whatever the aggregate happens to return.

**Auto is unaffected either way** — it reads only `max`/`min` and always descends to real ticks for the
fill. Argmax determinism matters for a deliberate coarse `--resolution` and for the stored bar frame.

#### Decide the timestamp type deliberately — naive or aware

**Raised 2026-09-11 by the UTC fix, and it must be settled before the reload.** The Python side now
produces **naive UTC**; `Market.Tick.Timestamp` is `timestamp without time zone`; and the server's
`TimeZone` is **`Europe/London`**. Those three agree today only by convention.

Both types are 8 bytes, so this is not a storage question. Two coherent positions, and the layers must
match — mixing them is what produced the bug this fix removed:

| | Python emits | Column type | Server `TimeZone` | Enforced by |
|---|---|---|---|---|
| **A** status quo | naive UTC | `timestamp` | irrelevant | convention |
| **B** self-describing | **aware** UTC | `timestamptz` | **must be `UTC`** | the type system |

**Recommendation: B, but only with `TimeZone = UTC` pinned in the server config.** `timestamptz`
stores UTC internally and converts on input and output **using the session timezone** — so on a server
set to `Europe/London` it would render every stored instant in London time and silently reintroduce
exactly the defect just fixed. Pinned to UTC it is strictly better than A, because the column then
declares "absolute instant" instead of relying on everyone remembering.

⚠️ **If B is chosen, the Python side must emit aware datetimes.** psycopg binds a *naive* Python
datetime to a `timestamptz` column by assuming the session timezone — the same trap one layer down.
That is what the new `zone` argument is for.

Timescale bucketing is also DST-correct on `timestamptz` and merely arithmetic on `timestamp`, which
matters for any non-UTC bucket the aggregates may later need.

**Add `TimeZone = UTC` to the 2.1.2 configuration pass either way** — it costs nothing under A and is a
hard prerequisite under B.

#### `BarAPI` -> `PointAPI` -> `TickAPI`

The object model keeps the five familiar points and makes each one two-sided:

```
BarAPI            PointAPI        TickAPI
  GapPoint          AskTick         Timestamp
  OpenPoint         BidTick         Ask
  HighPoint                         Bid
  LowPoint                          Volume
  ClosePoint
```

Accessed as `bar.HighPoint.AskTick.Ask` and `bar.HighPoint.BidTick.Bid`. For `GapPoint`, `OpenPoint`
and `ClosePoint` both pointers reference the **same** tick; only `HighPoint` and `LowPoint` differ.

**The flatten machinery already supports this** — `Dataclass.py:141` recurses, so a `PointAPI` with
`_flatten_ = ("AskTick", "BidTick")` nested in a `BarAPI` with
`_flatten_ = ("GapPoint", "OpenPoint", "HighPoint", "LowPoint", "ClosePoint")` emits
`HighPoint.AskTick.Ask` with no change to the flattening code.

Three consequences to plan for:

1. **`BarAPI` stops being a `DatapointAPI`.** No `Structure`, no five `ForeignKey` declarations, no
   `_pull_`, no migrate path — it becomes a read-only projection over an aggregate row. A net deletion.
2. **Dedup the identical points.** Three of five have `AskTick is BidTick`, so a naive flatten emits
   every field twice and takes the bar frame from 20 columns to 40 where 28 suffices.
   `_build_intra_arrays_` holds these as numpy arrays per intra level, so it is real memory on an M1
   tape.
3. **A wide but mechanical rename.** `_build_intra_arrays_` reads `frame["HighTick.Ask"]`,
   `Backtesting.py:252` constructs `GapTick=...`, `_should_descend_` reads `bar.HighTick`. All become
   `HighPoint.BidTick.*`. It touches every price path, so it lands **with** this item, not before or
   after.

**Done when:** a derived bar frame matches the stored one on every column that exists today, for a
sampled window on all seven pairs, across a DST boundary in both directions; the four extrema are
present and verified against a direct tick scan; and 3.0 passes with the pad removed.

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

### 2.9 Retire the Parquet preload cache — the tape belongs in the database

**Decided: no folder of `.parquet` files holding data the database already has.** Either the database
serves the tape fast enough that no cache is needed, or the cache lives *in* the database. Not beside
it. This is a design constraint on 2.2 and 2.3, and it is why they come first.

**What the cache is worth today.** `<Local>/cAlgo/Cache/Preload`, **7.9 GB** over 69 folders — 6.13 GB
of `ticks.parquet` and 1.67 GB of intra-bar frames. Measured on run 5 (EURUSD, eleven years, a 247 MB
tape): cold **568s**, warm **9.1s**. So it is worth roughly nine and a half minutes per process that
needs a tape it has not got.

**Where it actually earns that, which is narrower than it looks.** Inside one process the in-memory
`_TAPE_CACHE_` already serves every candidate — a serial Optimization sweeping thousands of backtests
pays one preload regardless of the disk cache. The disk cache earns its keep in exactly two places:
**parallel workers**, since `ProcessPoolExecutor` gives each worker a fresh process with fresh class
attributes and therefore a fresh preload, and **across sessions**, where every new run would otherwise
pay again. Both are real; neither is "thousands of backtests".

**Three candidate designs, in the order they should be measured.**

1. **Make the pull fast enough to need no cache.** After 2.2 the table is a compressed hypertable, so
   chunk exclusion and columnar storage should make an eleven-year range scan a fraction of what it is
   today. Then read it on a binary path — `COPY ... TO STDOUT (FORMAT BINARY)` or Arrow — straight into
   the three numpy arrays, skipping the Polars round trip. **The bottleneck is very likely the wire and
   the materialisation, not the disk**, so compression alone will not decide it; measure the whole path
   before assuming. If this lands near a minute, delete the cache entirely and stop here — it is the
   only option with no duplication at all.
2. **Materialise the tape in the database.** A relation keyed by `(security, start, stop, kind)` holding
   the arrays as compressed binary, so one row fetch replaces a scan of hundreds of millions. Removes
   the folder and keeps the speed, at the cost of duplication that is at least backed up, shared across
   machines, and visible to every consumer rather than hidden in a local cache directory.
3. **Keep a disk cache but fix its key** — the cheap interim. Independent of the above and worth doing
   regardless, because it is a bug, not a design: see 3.11. The tick tape does not depend on `auto` or
   `resolution`, yet both are in the signature, so switching resolution re-pulls an identical tape.

**Do not start this before 2.2 and 2.3.** Both change what a fetch costs, and option 1 is only
answerable once they have landed.

**Done when:** the preload path reads from the database with no `.parquet` file on disk, a cold
eleven-year tape is measured against today's 568s, and the goldens are byte-identical across the change.

---

## Phase 3 — Backtesting engine accuracy

The engine already reverse-engineers the cTrader engine byte for byte on the golden protocol and extends
it. This phase closes the four places where that fidelity is incomplete, and makes the account currency
generic.

### 3.0 The auto-resolution descend gate skips bars whose ticks would have triggered a target

**The largest accuracy defect the offline engine has, found 2026-09-11 by the first `BacktestingAPI`
comparison against cTrader. Fix this before anything else in the phase.**

`_intrabar_source_` (`Backtesting.py:1007`) walks a bar's interior only when
`_should_descend_(bids, asks)` passes; otherwise the bar is **skipped whole** and none of its ticks are
examined. The gate decides from the bar's four OHLC bid and ask values plus a spread pad
(`_should_descend_`, line 955). When a bar's stored high ask under-represents the true maximum ask
inside it, an armed stop the tape *could* have triggered is never checked.

**The failing case, with data.** Offline run 2, trade 236: Sell USDJPY entered 2023-05-10 14:00:00.217
at 134.397. cTrader exits 14:35:11.798 at **134.724**; the offline engine holds to 18:40:09.578 and
exits at 134.178 — **4h05m late, 54.6 pips**, turning a stop-out into a profit. The hour holds **9 337
ticks** with a maximum bid of 134.718, and a Sell exits at the ask: 134.718 plus the spread is exactly
134.724. **The tick is in the tape.** The stop comparison is also correct — line 795 tests a Sell stop
against the ask. Only the gate is wrong.

**Scale.** In run 2, the only run where clamped volumes keep both paths aligned, **703 of 709 exits are
identical in timestamp and price** and the median exit price gap is 0.000 pips. Six trades differ, one
badly, and that one carries nearly the whole gross gap. The engine is not mispricing; it misses the
occasional intrabar trigger.

**Why it compounds.** The divergence is path-dependent — a different exit changes the balance, which
changes the next volume, which changes every later decision. Run 1 keeps only 473 of 1024 identical
entry timestamps after diverging at trade 2. That is why runs 1, 3 and 4 look far worse in aggregate
than the per-trade accuracy warrants.

**Proven by bypassing it.** Re-running run 2 with `--resolution Tick`, which takes every branch of
`_intrabar_source_` that does **not** consult the gate, reproduces cTrader on that trade **exactly**:

| | Exit | Price | Net |
|---|---|---|---|
| cTrader | 14:35:11.798 | 134.724 | -2.29 |
| auto-resolution | 18:40:09.578 | 134.178 | +1.41 |
| `--resolution Tick` | **14:35:11.798** | **134.724** | **-2.29** |

Across the whole run the effect is decisive, and the cost is small:

| | Exits matching | Net | Δ vs online | Wall clock |
|---|---|---|---|---|
| auto-resolution | 703 / 709 | -57.42 | 3.78 | 1.05s |
| `--resolution Tick` | **704 / 709** | **-61.12** | **0.08** | 2.20s |
| online (cTrader-fed) | — | -61.20 | — | — |

**A 47x accuracy improvement for 2.1x the wall clock**, on this run, warm.

**What remains after the gate is bypassed is negligible and is the real sub-pip residual.** Five exits
still differ: lags of -24s, -5s, -1s and twice 0s — always marginally *earlier* — and price gaps of 0.1
to 0.3 pips, worth 0.00 to 0.01 EUR each and **0.08 EUR in total across 709 trades**. That is the
figure the old "sub-pip intrabar exit residual" note was reaching for, now measured, and it is
0.0001 EUR a trade. Chase it only if something else has been fixed first.

**The cost is measured, and it does not justify the gate.** Both runs warm, same machine:

| | auto | `--resolution Tick` | Accuracy change |
|---|---|---|---|
| Run 2 — USDJPY H1, one year | 1.05s | 2.20s (**2.1x**) | net 3.78 off → **0.08 off** |
| Run 5 — EURUSD D1, eleven years | 9.1s | **9.1s (no cost)** | **identical** — same gross, commission, swap and net to the cent |

On Daily the gate changes **nothing**: bar ranges are wide, so almost every bar has a reachable target,
the gate passes, and the engine descends anyway. The optimization only bites on narrow H1 bars — which
is exactly where it also skips a bar whose ticks would have triggered a stop. **It is cheapest where it
is useless and wrong where it is cheap.**

**Decision: `Auto` stays the default and gets fixed, not replaced.** An earlier draft of this item
proposed defaulting to `--resolution Tick`; that is abandoning a sound optimization because it has a
bug. The hierarchical descent is the right design and `--resolution` exists for deliberately coarse
runs (`Daily`, `H1`), not as a substitute for `Auto`.

**The binding invariant: `Auto` and `Tick` must produce byte-identical output, with `Auto` much
faster.** `Auto` is a *lossless* optimization — it may only skip work that provably cannot change the
result. Any divergence is a bug in `Auto`, never an acceptable trade.

**The fix is to delete the pad, not to tune it — and it comes from 2.3.** The gate is inexact because
the bar is bid-biased: `High` is the maximum-**bid** tick and its ask is incidental, so `max ask` has
to be guessed as `max(sampled asks) + spread ceiling`. On the failing bar the true maximum spread was
**0.007** where the four sampled points showed only **0.004**, and the resulting bound cleared the true
maximum ask by 0.001 — it held **by luck, not by construction**. One point wider and H1 would have
skipped too.

Once 2.3 makes the bar two-sided, the gate reads four exact bounds straight off the object:

```
high_ask = bar.AskPoint... -> bar.HighPoint.AskTick.Ask     low_ask = bar.LowPoint.AskTick.Ask
high_bid = bar.HighPoint.BidTick.Bid                        low_bid = bar.LowPoint.BidTick.Bid
```

with **no pad at all**. That removes the misses *and* strengthens pruning, because today's pad also
forces descent on bars where an armed level merely sits within a spread of the range.

**Over-bounding is free; under-bounding is the bug.** Descending more often than necessary costs only
time, never correctness — which is why a conservative exact bound is acceptable and a sampled one is
not. If 2.3's argmax proves awkward, a single stored `MaxSpread` per bar is a provably safe fallback
(`max ask <= max bid + MaxSpread`, and `min ask >= min bid` for free), at the cost of slightly weaker
pruning.

**This item is therefore gated on 2.3** and ships with it.

Note the D1 run still leaves **24 of 510 exits differing** at tick resolution while landing within 0.93
on net, so those are small or offsetting. Separate from this item.

**The 568s figure is not the cost of tick resolution.** Run 5 cold at tick resolution took 568.1s, of
which the bar loop was under two seconds — the rest was a redundant cold preload forced by the cache
being keyed on resolution. See 3.11 and 2.9.

**Done when:** run 2 reproduces cTrader on all 709 exits or the remainder is explained, the tick-
resolution cost is measured on run 5, and the other four runs are re-measured under whichever fix is
chosen.

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

### 3.6 The `net.csv` concat drops `Position` and silently disables aggregation

**Explained 2026-09-10, both halves, one mechanism. The plus-one is correct; the Aggregated column is not.**

**The plus-one is right and matches cTrader.** `generate_net_report` concatenates `trades_df` with
`positions_df`, so a position still open at the stop date is counted alongside the closed trades.
cTrader does the same — it closes any open position at the end of the window and counts it — so its
"Total trades" is our `trades.csv` plus `positions.csv`. Golden 1: 1024 + 1 = **1025 on both sides**.
Nothing to fix; `net.csv` is the table to compare against cTrader, never `trades.csv` alone.

**The Aggregated column is the defect.** The concat uses the **intersection** of the two frames'
columns. `Position` is declared on `TradeAPI` and not on `PositionAPI`, so the intersection drops it,
and `aggregate_items` returns its input unchanged when `Position` is absent. The result is that
**whenever any position is open at the stop date, the entire Aggregated half of `net.csv` degrades to a
copy of the Individual half** — silently, with no error.

Measured on the 2026-09-10 set:

| Run | Open positions | `Nr Total` Individual / Aggregated | Correct Aggregated | Rows identical |
|---|---|---|---|---|
| Golden 1 | 1 | 1025 / 1025 | 697 (696 deals + 1) | **85 of 85** |
| Golden 5 | 0 | 510 / 359 | 359 | 24 of 85 |

That is exactly the old observation — goldens 19, 27 and 36 showed Aggregated equal to Individual and
those are precisely the plus-one runs, while 18 had 25 against 37 because nothing was open.

Fix: carry `Position` through the concat rather than intersecting it away — give the open position a
`Position` value of its own `UID`, which is what a deal of one position means. Then aggregation groups
correctly whether or not anything is open. Guard with a test asserting Aggregated `Nr Total of Trades`
equals `deals + open positions` on a frame that has both.

**DONE 2026-09-11.** `generate_net_report` now aligns the positions frame to the trades frame before
concatenating (`_aligned_positions_`): the open position takes its own `UID` as `Position` and a null
`ExitTimestamp`, and the concat uses the trades' **column order** rather than `list(set(...))`, which
was also non-deterministic. Verified on offline golden 1 — Aggregated `Nr Total of Trades` is now 697
against 696 deals plus one open position, and rows identical between Individual and Aggregated fell
from 85 of 85 to 21 of 85. Four tests in `Tests/Portfolio/test_Statistic.py`; suite 1371 passed.


### 3.6.1 `initial_balance` is the closing balance, so every balance-relative percentage is wrong

**Root cause found 2026-09-10, one line.**

`generate_net_report` opens with `initial_balance = (account.Balance if account is not None else 0.0)`.
`Account.Balance` is the **live** balance, so by report time it is the *closing* balance, not the
opening one. It then feeds `equity_metrics` and both `dependent_metrics` calls, and through them
`calculate_drawdown`/`calculate_runup`.

`calculate_excursion` itself is correct. Called on golden 1's trades with the true opening balance it
returns **31.6415%**, which is cTrader's 31.64% exactly; called with the closing balance it returns
44.2376%, which is what `net.csv` reports.

| Run | Opening balance | Closing balance | cTrader | `net.csv` |
|---|---|---|---|---|
| 1 | **31.6415%** | 44.2376% | 31.64% | 44.2376% |
| 2 | 0.8213% | 0.8263% | 0.82% | 0.8263% |
| 3 | — | — | 34.26% | 49.5901% |
| 4 | — | — | 0.36% | 0.3649% |

The error scales with how far the balance travelled, which is why it is invisible on runs 2 and 4
(both moved under 1%) and 40% relative on runs 1 and 3 (both lost over 30%). On runs 1 and 3 it also
reports a balance drawdown **larger than the equity drawdown**, which is impossible.

Fix: pass the opening balance.

**DONE 2026-09-11.** `initial_balance` now prefers `equity_curve[0]`, the opening equity, falling back
to `account.Balance` only when no curve exists. Verified on offline golden 1: the reported
`Max Balance Drawdown (%)` is **30.7076** and `absolute / peak balance` recomputed from that run's own
trades is **30.7076** — an exact match, where before the fix it read 42.32. The same recomputation on
the pre-fix online golden gives 31.6415 against cTrader's 31.64. `equity_metrics` and the runup
percentages take the same variable and are corrected by the same change; only the drawdown side has
been measured against cTrader.

### 3.6.2 The position open at the stop date is valued differently from cTrader

cTrader closes any position still open at the end of the window, at the final tick, and charges its
closing commission and a full swap. We mark it earlier and `_build_position_` sets `SwapPnL=0.0` at
open with swap only ever applied in `_build_trade_`, so an open position accrues **no swap at all**.

Measured across the four 2026-09-10 runs that had one — the open position's mark-to-market gap equals
the entire short-side gross gap, exactly, every time:

| Run | Open position | Our mark | cTrader implied | Gap | Short gross gap |
|---|---|---|---|---|---|
| 1 | Sell 28 000 @ 1.10473 | 2.53 | 26.64 | 24.11 | 24.11 |
| 2 | Sell 1 000 @ 141.001 | 0.53 | -0.77 | -1.30 | -1.30 |
| 3 | Sell 27 000 @ 1.10473 | 2.70 | 28.35 | 25.65 | 25.65 |
| 4 | Sell 23 000 @ 141.001 | 12.11 | 41.65 | 29.54 | 29.54 |

Golden 5 has no open position and reconciles with cTrader to the cent on every figure, which is the
control that isolates this as the only difference.

Fix: value the open position at the final tick of the window, charge its closing commission, and accrue
swap on open positions rather than only at close. **Ship with 3.9** — it moves `positions.csv` and the
`net.csv` totals deliberately.

### 3.6.3 Holding time collapses to `stop - entry` when a position is open

`calculate_holding_times` is correct — called directly on golden 1's `trades.csv` it returns max 3.67
days, avg 0.20, matching a manual computation. `net.csv` for the same run reports **max 360.71, avg
181.64** for an H1 strategy inside a single year.

The report path hands it a frame with **no `ExitTimestamp` column**, so `exits` falls back to the run
stop for every row. Reconstructed exactly: dropping the column reproduces max 360.71 / avg 181.64 /
min 0, the zero arising because the last entry postdates the stop and clips. Golden 5, with no open
position, reports correctly.

Same root as 3.6 — the concat intersection drops columns `PositionAPI` does not declare, and
`ExitTimestamp` is one of them.

**DONE 2026-09-11, and the prediction held.** Fixing 3.6 fixed this: `_aligned_positions_` supplies a
null `ExitTimestamp` for the open position, which `calculate_holding_times` already fills with the run
stop — the correct semantic, since an open position is held to the stop. Offline golden 1 now reports
max **3.6667** days and avg **0.2041**, against 363.71 and 184.75 before. The average exceeds the
0.2019 measured from `trades.csv` alone precisely because the open position is now included.

### 3.11 Backtesting engine performance

Measured 2026-09-11 by `cProfile` on the online hot path — `Trend` on EURUSD H1 over 2023, warm tape,
6 217 bars. Total 9.95s under the profiler across **17.6M calls** (about 5.6s unprofiled). Ranked by
what the profile actually says, not by guess:

| Cost | Evidence | Note |
|---|---|---|
| **Datapoint construction** | `Datapoint.__setattr__` **1 006 870 calls**, 0.654s tottime — the single largest entry. `Dataclass._emit_` 566 565 calls (1.747s cumulative), `_parse_` 566 565 (0.924s), `Dataclass.data` 1.804s cumulative | Every tick, bar and position runs through property setters that parse. `RULES` already records mypyc and Cython as dead ends, so the lever is **fewer calls**, not faster ones |
| **`isinstance`** | **3 237 615 calls**, 0.517s | Almost all inside the dataclass parse path; falls out of the item above |
| **Polars frame churn** | `dict_to_pydf` **18 658 calls**, 0.876s cumulative — three per bar | A small DataFrame constructed per indicator per bar. `Technical.update_data` is 2.171s cumulative of a 5.97s backtest |
| **Preload** | `_load_bars_` 3.76s of the 4.04s `_preload_`, **40% of the whole run** | Amortised across an Optimization sweep by the tape cache, but it dominates a single backtest |
| **`select.select`** | 0.558s, 693 calls | Database round trips *during* the run, after preload. Find out what is still talking to Postgres in a backtest |
| **`TickAPI.__post_init__`** | 33 101 calls, 1.204s cumulative | Tick construction from tape rows; same family as the first item |

`_should_descend_` is **not** a hot spot (0.162s, 5%), which matters because 3.0 will make it descend
more often.

**The preload disk cache is over-keyed, and it is the same mistake `window` already taught.**
`_cache_signature_` (`Backtesting.py:324`) hashes `(security, start, stop, timeframe, auto, resolution)`
— but the **tick tape does not depend on `auto` or `resolution`**. Reading `_load_frames_`: `auto` and
`resolution=Tick` pull byte-identical tick columns (lines 295-306); only the intra-bar frames differ
(the `auto` branch pulls H1 and M1, an explicit finer resolution pulls one level, tick pulls none).

So changing resolution on an otherwise identical run discards a valid tick tape and re-pulls it from
Postgres — **12-15 minutes for a dense ten-year window**, for data already on disk. Measured
2026-09-11: run 5 warm on auto is **9.1s**, and the same run with `--resolution Tick` paid a full cold
preload purely because the key changed.

`RULES.md` already records the identical argument for the warmup window — "the warmup window belongs in
the cache key, the tick tape does not", which is why `_tape_` keys `_acquire_frames_` window-free. The
same split applies one level down: **key `ticks.parquet` without `auto`/`resolution`, and key only the
intra frames with them.**

Cache state when measured: `<Local>/cAlgo/Cache/Preload` at **7.9 GB** over 69 folders — 6.13 GB of it
`ticks.parquet` and 1.67 GB intra frames. About 400 MB is provably duplicated (three tapes stored
twice at identical byte sizes), and **43 of the 69 folders store an empty `ticks.parquet`** because a
bar-level run with no conversion need writes zero ticks. The wasted time matters more than the wasted
space, but both come from the same key.

**Order.** Take the preload and the indicator frame churn first — both are large, both are contained,
and neither touches engine semantics, so the goldens must stay byte-identical across them. The
datapoint construction path is the biggest prize and the most invasive; do it deliberately, after 3.0,
with the goldens as the gate.

**Do not** re-attempt the recorded dead ends: a numpy ring buffer for `SeriesAPI`, mypyc, Cython, or a
drain thread for the log sinks.

### 3.12 `push_ticks` upserts where the backfill needs `copy`

`MarketAPI.push_ticks` routes to `db.upsert(..., key=["UID"])`, which does per-row conflict resolution.
That is right for the handful of ticks an online run writes and **wrong by orders of magnitude** for a
1.66 bn-row backfill into an empty table where no conflict is possible.

The bulk path already exists and is complete — `DatabaseAPI.copy(...)` down to
`PostgresDatabaseAPI._copy_`, a real `COPY ... FROM STDIN (FORMAT CSV)` fed from a Polars
`write_csv` buffer, and `_csvframe_` already accepts a `pl.DataFrame`. Nothing needs inventing; the
backfill simply must not go through `upsert`.

Either give `push_ticks` a bulk mode that dispatches to `copy`, or have the backfill call `copy`
directly and leave `push_ticks` to the online path. Measure both on one month of one security before
choosing.

### 3.10 A run cannot record or pin the contract terms it used

**The gap that makes a golden perishable.** A run's folder records the command (`Run.json`) and the
resolved strategy parameters (`Input/Parameters.yml`), but **not the contract** — and the contract is
an input, not a constant. `Universe.Contract` carries `SwapLong`/`SwapShort` as *current* broker
values, and `Realtime.py:218-223` rewrites the row from the wire on every online run (`UpdatedBy` reads
`Autosave`). So the terms a golden ran under are gone the moment the next cBot starts.

It is not confined to `SwapPnL`. Sizing is a percentage of balance, swap feeds balance, so a drifted
rate moves every volume and therefore every number in the file.

**Nor can the terms be pinned from the CLI.** Verified 2026-09-11 against `Backtesting.py`:
`CommissionType.Amount` is a **flat** charge per trade, not per million, so `--commission-value 45.0`
would charge 45 on every trade; and `SwapType.Points` multiplies by `PointSize` where
`Accurate`/`SwapMode.Pips` multiplies by `PipSize`, which are 10x apart on all seven majors. Only
`Accurate` reproduces broker terms, and `Accurate` reads the mutable row. There is no flag combination
that reproduces a golden.

Two halves, both needed:

1. **Snapshot.** Write the resolved contract into every run folder as `Input/Contract.yml`, beside
   `Parameters.yml`, for the same reason `Parameters.yml` exists — so a later override cannot rewrite
   history. Cheap, no behaviour change, and it retires the hand-curated `Tests/Golden/Contract.json`.
2. **Pin.** Let a run take those terms back as input, so a golden replays under the contract it was
   born with rather than today's. Either a `--contract PATH` that loads the snapshot, or extend the fee
   flags so `Accurate` values can be supplied explicitly.

**Do this before 3.9.** Re-baselining onto terms that drift again reproduces the problem the
re-baseline is meant to end.

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

## Phase 9 — Interactive Brokers provider

**Requested 2026-09-15, to follow Phase 8.** A second broker adapter in the shape of Spotware.

**Standalone, no provider base class** — see 1.3. Interactive Brokers breaks Spotware's assumptions (one
asset class, a protobuf transport, a symbol id per instrument), which makes it good evidence for a later
simplification, not the trigger for one.

What Interactive Brokers changes, to be verified against its current documentation before design:

- **Transport.** Its API talks to a running Trader Workstation or IB Gateway process over a local
  socket, not to a cloud endpoint. A provider that needs a desktop application alive is a different
  lifecycle from one that dials a host, and the Scheduler service must supervise that dependency.
- **Multi-asset.** Stocks, futures, options and FX under one account. A security is a contract
  description, not a numeric id — which is what 2.x's identity mapping must already accommodate.
- **Historical pacing.** It documents strict limits on historical data requests. That makes it a poor
  bulk tick-history source and a good live-and-reference source; plan its role accordingly rather than
  assuming it can backfill like Spotware.
- **Options chains and greeks.** It is one of the few retail-accessible sources for listed option
  chains, which is what makes this phase the natural data gate for Phase 10.

**Done when:** the provider fetches reference data, historical bars and a live stream for at least one
security per asset class it supports, with its own suite green.

---

## Phase 10 — Option strategy pricer and backtester

**Requested 2026-09-15, to follow Phase 9.** A new asset class for the framework.

**The data gate comes first.** cTrader lists no vanilla options, so Spotware cannot supply this. Option
chains must come from Bloomberg — already integrated — or from Interactive Brokers once Phase 9 lands.
That dependency is why this phase is ordered after 9.

**The universe already anticipates it.** `Universe.Contract` carries `Variant` (Call · Put · Deliverable ·
NDF), `Payoff` (Trivial · Vanilla · Asian · Barrier · KnockOut · Digital), `Strike`, `Maturity` and
`Exercise` (European · American · Bermudan). The contract model does not need redesigning, only
populating.

Two parts, in order:

1. **The pricer.** Closed form where it exists (Black-Scholes for European equity-style, Black-76 on
   futures and forwards), lattices for early exercise (binomial or trinomial for American and Bermudan),
   an implied-volatility solver, the greeks, and a volatility surface built from observed chains. A
   multi-leg strategy is priced as the sum of its legs, so the pricer must price one leg exactly before
   strategies are meaningful. Validate every model against a published reference value, not against
   itself.
2. **The backtester.** Very likely a **third engine**, a sibling of `RealtimeAPI` and `BacktestingAPI`
   rather than an extension of either. Its state is a chain and a surface evolving through time, not one
   price; its fills are per leg and per strike; and it must handle expiry, exercise and assignment, which
   the spot engines have no concept of. It should still reuse `Library/Portfolio`, `Library/Statistic`
   and `Workspace`, exactly as the other two engines do.

**Structural addition when it starts:** a new top-level package, likely `Library/Derivative` or
`Library/Option`, to be named and added to `RULES.md` at that point.

**Done when:** the pricer reproduces reference values for European and American vanillas and their
greeks, and a multi-leg strategy backtests across at least one expiry cycle with exercise handled.

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