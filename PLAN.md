# Plan

The single planning file for the framework. Written 2026-09-10, replacing `TODOS.md`,
`Research/THESIS-NOTES.md` and the project memory set, all of which were folded in here or into
`RULES.md` and then deleted. Reordered 2026-09-17 and rewritten 2026-09-18 — Appendix C maps every
earlier item number to its current one.

**What belongs here:** work not yet done, in the order it will be done, with the evidence that
justifies it and the condition that closes it. **What does not:** conventions, current state and traps
(those are `RULES.md`), architecture (`ARCHITECTURE.md`), delivered results
(`Research/CAMPAIGN-7PAIR.md`, `Research/DDPG-EURUSD-H1/REPRODUCE.md`) and anything git history
already records. **A finished phase is reduced to one row of the Done log** — what it was, when it
closed, where its facts now live — and every detail of it is deleted from this file; a finished item
inside a live phase keeps one line in that phase's **Done** list until the phase itself closes.

**The thesis is delivered and stays delivered.** Its numbers are a safety net, not a hostage. Nothing
below is a quick fix applied to make a result look better; every phase is a structural change that
leaves the framework permanently correct. A second thesis iteration is produced in Phase 6 from the
corrected engine, and it replaces the first only if it is stronger.

---

## Done

A finished phase keeps one line here; its facts live where the last column says, and its details are
gone from this file.

| Phase | What it delivered | Done | Facts in |
|---|---|---|---|
| **0** | Safety net — the online and offline goldens, the DDPG self-consistency golden, the `Contract.yml` pin | 2026-09-17 | `RULES.md` ("Goldens", "Contract terms"), `Tests/Golden/RESIDUALS.md` |
| **1** | Credential manager — `Library/Credential`, owner and threshold access on credentials, workflows and tasks, the credential page and CLI, the stored session key | 2026-09-23 | `RULES.md` ("`Library/Credential`", "Two thresholds"), `ARCHITECTURE.md` |

---

## Order of work

| Phase | Scope | Gate | Can start |
|---|---|---|---|
| **2** | Spotware access and feed equivalence | none — the credential store is in place | **now** |
| **3** | Database structure and TimescaleDB | 3.6 waits for 2.5; the rest has no gate | **now**, beside 2 |
| **4** | Continuous capture — Spotware replaces the Download cBot | 2.5 and 3.6 | after 3.6 |
| **5** | Backtesting engine accuracy, plus the cBot protocol items | 3.3; 5.0 needs 3.2, 5.4 needs 3.5, 5.13 needs 3.6 | after 3.3 |
| **6** | Optimization and Learning — thesis iteration two | Phase 5 complete | after 5 |
| **7** | Web app | 3.7 complete | after 3.7 |
| **8** | Remaining | none | any time |
| **9** | Indicator connector — Python indicators on cTrader charts | Phases 2 and 5 complete | after 5 |
| **10** | Live trading panel at `/trading` | Phases 4, 5 and 7 complete | after 7 |
| **11** | Interactive Brokers provider | Phase 10 complete | after 10 |
| **12** | Option strategy pricer and backtester | Phase 11 complete (chain data) | last |

**Five rules bind the order.**

1. **Nothing touches the engine without the goldens.** They exist as of 2026-09-17 —
   `Tests/Golden/Online` and `Tests/Golden/Offline` (runs 1-5 each) plus `Tests/Golden/Consistency/DDPG`.
   `pytest Tests/Golden --golden` replays the six offline-engine goldens byte for byte, each with its own
   `Parameters.yml` and `Contract.yml` pinned, and `verify_lock.py` section 3 fingerprints `Tests/Golden/`.
2. **There is exactly one golden re-baseline, and it is item 5.13.** Both the v2 tick schema (3.6) and
   the sizing fixes (5.2, 5.3) change engine output deliberately. Re-baselining after each would cost
   two cTrader sessions and would hide which change moved which number. Everything before 5.13 therefore
   runs against the Phase 0 goldens as a *tripwire* — a break is expected at 3.6 and 5.2, and every break
   must be explained before 5.13 accepts it. **Declared exception, 2026-09-15:** the offline half was
   re-baselined once outside 5.13, when `shrink_dtype()` was removed from `DataframeAPI.frame` — every
   database read and preload tape had been downcasting `Float64` prices to `Float32`. That corrected an
   input, not engine logic; the pre-fix exports stay in commit `578c9a5`, and the before/after is in
   `Tests/Golden/RESIDUALS.md`, "Re-baselined 2026-09-15".
3. **Phase 6 retrains once, at the end.** Every engine change invalidates trained weights. Retraining
   between phases burns the longest-running job in the framework for a result the next phase throws
   away.
4. **No secret lives anywhere but the credential store, and it travels by reference.** Not in code,
   git, a log line, a command line, a run artifact, an environment variable or a file in the repository —
   the store is a plain database table, so the discipline is what protects it. Every phase that talks to
   an external API — Spotware (2, 4), the live panel (10), Interactive Brokers (11) — starts from the
   store instead of retrofitting it.
5. **No second source writes into the tick tape before 2.5 has written down what a tick is.** The stored
   history is cTrader's own tick store, and that store is **sampled by era** (Appendix A). A feed with a
   different sampling, colliding keys or missing columns mixed into it would move every engine number
   without raising a single error.

**Why this order, 2026-09-18.** The Open API application was approved. Spotware is the first of several
external APIs whose secrets need a home, so the credential manager comes first. Spotware then splits in
two: *access and feed equivalence* (Phase 2) must come **before** the tick schema is decided, because
measuring the stored tape showed it is sampled differently in different years and a live Open API
stream almost certainly is not; *continuous capture* (Phase 4) must come **after** it, because the Open
API carries no conversion columns and the capture has to write into whatever schema 3.6 settles. The
database work that does not depend on the feed — aggregates, the table swap, the cache, the Research
schema — goes ahead beside Phase 2.

---

## Phase 2 — Spotware access and feed equivalence

**The application (id 39640) was approved and is active as of 2026-09-18.** This phase writes nothing
into the tick tape. It connects, verifies the module against a live session, measures how the Open API
feed relates to the history already stored, and ends by writing down (2.5) what Phases 3 and 4 build
on.

### 2.1 Sign in once, refresh forever

- **The authorization-code flow.** Open the consent page, receive the code on a local redirect, exchange
  it for the access and refresh tokens, and store them with the application id and secret as one
  `OAuth2` credential. Nothing like it exists yet — `SpotwareAPI` takes `client_id`,
  `client_secret`, `access_token` and `account_id` as arguments and stops there. The HTTP exchange is
  library code; the one-off browser step is a `Script/`.
- **The accounts.** `ProtoOAGetAccountListByAccessTokenReq` (already called in `Spotware/Portfolio.py`)
  lists the `ctidTraderAccountId`s the token reaches; store the EUR and USD demo accounts of 5.13's checklist.
- **Refresh** — the `refresh_token` grant or `ProtoOARefreshTokenReq`, registered with
  `CredentialManagerAPI.refresher("Spotware", ...)` so the daily `Environment.Credential` task rotates it.
- **Test** — a connection check the credential page runs on demand, so a wrong or expired token
  surfaces on the page rather than in a failed overnight run.

Hard constraints from the official documentation, verified 2026-09-15: **5 requests a second per
connection for historical data**, 50 for everything else; access tokens expire after **2 628 000 s**,
refresh tokens do not; application approval and blocking are undocumented, and the official support
channel is the Telegram group linked from the documentation.

### 2.2 Restore TLS hostname verification

Twisted warns that `service_identity` cannot import, because 26.1.0 needs a newer `cryptography` than
the 42.0.8 that the `ctrader-open-api` pin (`pyOpenSSL==24.1.0`) holds it to, so the connection is not
verifying the server's hostname. The 2026-09-14 environment update reinstalled that pair.
`service-identity` 24.2.0 parses certificates through `pyasn1` and declares no `cryptography` floor
(checked by dry-run metadata, not yet installed); pin it in `Quant.yml` or the next update reverts it.

**Before any token crosses the wire.** It is a precondition of 2.1, not a clean-up after it.

### 2.3 Verify `Library/Spotware` against a live session

The offline half is done (2026-09-15): `Tests/Spotware` runs in the default suite, the module went from
1 624 to 1 033 lines, and its decoding rules are in `RULES.md`. Four documented behaviours the offline
suite cannot exercise, in this order:

1. **Closing-deal direction.** `trades()` reports the deal's own `tradeSide`, which for a closing deal is
   the opposite of the position it closes. `TradeAPI` convention is the position's direction. Decide
   which the frame carries before 2.4 compares trades.
2. **Pagination.** `ProtoOADealListRes` and `ProtoOAOrderListRes` both carry `hasMore`; `trades()` and
   `orders()` read only the first page.
3. **Live trendbars** may require an active spot subscription first.
4. **Rate limit.** The tick pagination loop has no throttle against the 5-a-second historical limit.

**Done when:** all four are verified or fixed against a live demo session.

### 2.4 Feed equivalence — the gate for 3.6 and Phase 4

Same broker backend, different transport, never compared. The stored history came through the
Download cBot from cTrader's own tick store, and that store is **sampled by era** — no minimum spacing
before March 2016 and again in July-August 2017, a 150 ms floor from 2016 to August 2024 and a 300 ms
floor since, identical on all seven pairs (Appendix A). A live spot stream is very unlikely to be
sampled the same way, and cTrader's backtester replays the sampled store, which is the reference every
golden is measured against. Three comparisons, each written down:

- **A — historical ticks against the stored tape.** `ProtoOAGetTickDataReq` over one window in each
  era (2014, 2017-07, 2019, 2025) plus the 2016-01-11 to 2016-01-25 hole, against `Market.Tick`. Measure:
  tick counts; **ticks sharing a millisecond**, because the tick `UID` is `security << 42 | epoch_ms`
  and holds one tick per millisecond per security — the unsampled eras have 1 ms gaps, and the cBot's
  upsert would have kept only the last of any collision without an error; prices; how the endpoint's
  one side per request (BID and ASK fetched separately, then merged) lines up with the stored rows, half
  of which change one side only; `Volume`, which is 1.0 on every stored tick; and the page size and wall
  clock per day of ticks under the 5-a-second limit.
- **B — trendbars against `Market.Bar`.** H1 and D1 on the same windows: OHLC, the 22:00 (21:00 DST)
  session stamp, and whether the platform's bars are built from the sampled tape or from denser quotes.
  A platform high above the stored bar's high would mean the latter, and it bears directly on 3.2 and
  5.0.
- **C — live spots against the live Download cBot.** One symbol, one session, both running at once. The
  only comparison that needs cTrader open.

**Done when:** a written comparison per window says where the feeds agree and names exactly where they
do not.

### 2.5 Decision checkpoint — what a tick is

Written into this file before 3.6 or Phase 4 starts:

1. **The canonical source and its sampling** — the historical endpoint fetched the day after, which
   matches what cTrader's backtester replays, or live spots.
2. **The columns a tick carries.** The Open API supplies no conversion columns and no real volume. This
   is the input to 3.5 and 3.6.
3. **The key.** Whether one tick per millisecond per security holds for every source and era; if not,
   what the `UID` becomes. A key change lands in 3.6, never after the capture starts.
4. **Provenance.** Every stored tick reads `UpdatedBy = 'Autosave'`. Mark the source before a second one
   writes, or drift between them becomes invisible.
5. **Whether live spots are stored at all**, and where. They drive Phase 10's live panel either way;
   they enter the canonical tape only if item 1 says so.

---

## Phase 3 — Database structure

`Market.Tick` is **295 GB** over 1 663 014 876 rows, the exact count taken at the 2026-09-17 reload.
Ranked levers:

| Lever | Saving | State |
|---|---|---|
| TimescaleDB compression | 295 GB → **58 GB** measured | built as `Market.TickReload`; the swap is 3.3 |
| drop the 4 conversion columns | 53 GB | 3.6 — reconstructible from the pair's own price plus EURUSD, worst error 0.036% |
| narrow types | ~23 GB | 3.6 — price to int32 scaled by `PipSize`, `Security` to int16 |
| drop `Mid` | 13 GB | 3.6 — derivable from Ask and Bid |

**Keep the goldens byte-identical across the table swap itself.** The reload copied the current
columns so it proves itself lossless against the same exports; 3.6's column changes come after, where
the golden break is expected and explained.

**Done.**

- **The TimescaleDB extension** is created in `Quant` (2.24.0, already preloaded — no restart).
- **The reload is built and verified**, 2026-09-17 — absorbing in-place compression and the UID
  repopulation. Facts under 3.3.
- **The timestamp type is decided and implemented** — `timestamptz` columns, the server and every
  session pinned to `UTC`, the driver loading `timestamptz` back as naive UTC (Appendix B).
- **Closed: the `(Security, Timestamp)` index.** It is not needed. Every tick read — `pull_ticks`,
  `count_ticks`, `last_tick_uid` — filters on a `UID` range, which the UID-partitioned hypertable prunes
  to the matching chunks (`EXPLAIN`: a `ColumnarScan` on one chunk, off `_ts_meta_min/max`).

### 3.1 Server configuration — what is left

Hardware: Intel i9-14900K (24 cores, 32 threads), 64 GB DDR5-5800, **one** Samsung 990 PRO NVMe (930 GB),
PostgreSQL 18.3 with `timescaledb` preloaded and 16 background workers. Already correct — do not touch:
`shared_buffers` 8GB · `effective_cache_size` 48GB · `random_page_cost` 1.1 · `effective_io_concurrency`
200 · `max_worker_processes` 32 · `max_parallel_workers` 24 · `max_wal_size` 16GB · `checkpoint_timeout`
15min at 0.9 · `jit` off.

**Applied 2026-09-17, no restart:** `vacuum_cost_limit` 200 → 2000, `wal_compression` pglz → zstd,
`track_io_timing` off → on; `synchronous_commit = off` only inside `Script/Setup/Reload.py`'s session.

**Left, each a decision:**

| Setting | Now | Proposed | Why |
|---|---|---|---|
| huge pages | `huge_pages_status = off` despite `huge_pages = try` | grant *Lock pages in memory* to the service account, then restart | 8 GB of shared buffers through 4 KB pages is 2 M TLB entries |
| statistics on `Security`/`UID` | 100 | 1000 per column | seven securities across twelve years is a skewed distribution |
| `max_parallel_maintenance_workers` | 4 | 8-12, per session for index builds | 24 cores available |
| `maintenance_work_mem` | 2 GB | 8-16 GB, per session for index builds | 46 GB free; fewer merge passes |
| `work_mem` | 64 MB | keep global, raise per session for preload and analytics | `max_connections` is 400, so a global raise is a memory hazard |

### 3.2 Continuous aggregates and the two-sided bar

Derive every timeframe on demand from the tick tape and retire the `Bar` table (5.9 GB). This unlocks
H4, D2, W1 and arbitrary intervals, which the framework cannot offer today. **`Tick` becomes the only
stored market table** — and removing `Bar` removes its five foreign keys into `Tick(UID)`, which is what
blocks 3.3.

**The session-stamp convention must survive.** Bars are stamped at 22:00, or 21:00 under DST, so a
Thursday-stamped D1 bar *is* Friday's session and D1 carries five bars a week stamped Sunday through
Thursday. An aggregate built on calendar days silently produces a different tape. 2.4-B checks the
convention against the platform's own trendbars.

#### The bar becomes two-sided, which is what makes 5.0 exact

Today `High` is the tick at which the **bid** was highest, and its ask is incidental. Measured on
USDJPY 2023-05-10 14:00: the stored `HighTick.Bid` is 134.718, exactly the true maximum bid, while the
stored `HighTick.Ask` is 134.721 against a true maximum ask of **134.724**. The bar is bid-biased, and
that bias is the entire reason `_should_descend_` carries a spread pad.

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
can.

**Tested 2026-09-11 — `first`/`last` ARE supported, but argmax is not tie-safe.** Probed on a throwaway
database:

| Test | Result |
|---|---|
| CAGG with `max`/`min` only | created, refreshed, correct |
| CAGG with `last(ts, bid)`, `last(ask, bid)`, `first(ts, bid)` | **created and refreshed** — the old restriction is gone |
| CAGG vs direct scan, **strictly unique** bids | **6/6 identical** |
| CAGG vs direct scan, heavy ties | agreed in one layout, **disagreed in another**; `max`/`min` agreed in **both** |

The four scalars the gate needs are safe and deterministic. **The extremum timestamps are not.**
`last(ts, bid)` picks an arbitrary row among ties, and which one depends on chunk layout and insertion
order — real tick data ties constantly. So `HighPoint.BidTick.Bid` is safe, while
`HighPoint.BidTick.Timestamp` needs a **total order**: break ties on the timestamp itself, so "the
maximum bid, earliest occurrence" is a definition rather than an accident. Write the rule down; do not
inherit whatever the aggregate happens to return. **Auto is unaffected either way** — it reads only
`max`/`min` and always descends to real ticks for the fill.

#### `BarAPI` -> `PointAPI` -> `TickAPI`

```
BarAPI            PointAPI        TickAPI
  GapPoint          AskTick         Timestamp
  OpenPoint         BidTick         Ask
  HighPoint                         Bid
  LowPoint                          Volume
  ClosePoint
```

Accessed as `bar.HighPoint.AskTick.Ask` and `bar.HighPoint.BidTick.Bid`. For `GapPoint`, `OpenPoint`
and `ClosePoint` both pointers reference the **same** tick; only `HighPoint` and `LowPoint` differ. The
flatten machinery already supports this — a `PointAPI` with `_flatten_ = ("AskTick", "BidTick")` nested
in a `BarAPI` with `_flatten_ = ("GapPoint", "OpenPoint", "HighPoint", "LowPoint", "ClosePoint")` emits
`HighPoint.AskTick.Ask` with no change to the flattening code.

Three consequences:

1. **`BarAPI` stops being a `DatapointAPI`.** No `Structure`, no five `ForeignKey` declarations, no
   `_pull_`, no migrate path — a read-only projection over an aggregate row. A net deletion.
2. **Dedup the identical points.** Three of five have `AskTick is BidTick`, so a naive flatten takes the
   bar frame from 20 columns to 40 where 28 suffices. `_build_intra_arrays_` holds these as numpy arrays
   per intra level, so it is real memory on an M1 tape.
3. **A wide but mechanical rename.** `_build_intra_arrays_` reads `frame["HighTick.Ask"]`,
   `_row_to_bar_` constructs `GapTick=...`, `_should_descend_` reads `bar.HighTick`. All become
   `HighPoint.BidTick.*`. It touches every price path, so it lands **with** this item.

**Done when:** a derived bar frame matches the stored one on every column that exists today, for a
sampled window on all seven pairs, across a DST boundary in both directions; the four extrema are
present and verified against a direct tick scan; and 5.0 passes with the pad removed.

### 3.3 Swap the reloaded tick table in

**Built and verified 2026-09-17; only the swap is left, and it waits for 3.2.** `Script/Setup/Reload.py`
built `Market.TickReload` beside the source in 3 h 10 min and never wrote to the source.

| | Source `Market.Tick` | `Market.TickReload` |
|---|---|---|
| Rows | 1 663 014 876 | **1 663 014 876** (equal, checked after the build) |
| Size | 295 GB | **58 GB** — 80.3% saved |
| Chunks compressed | — | **1049 of 1049** |
| One busy day, 192 258 ticks | 1274 ms | **178 ms** |
| `Timestamp` | naive | `timestamptz`, read back **naive UTC** through `PostgresDatabaseAPI` — values identical |

- **Partitioned on `UID`, not `Timestamp`**, 31 days in milliseconds: one chunk per security-month, and
  the `UID` primary key survives — a hypertable on `Timestamp` could not carry it.
- **Compressed segment-by `Security`, order-by `UID`** — one instrument's prices compress far better
  than seven interleaved, and every read addresses one security.
- **A foreign key pointing into a chunk blocks compression** (`found a FK into a chunk while
  truncating`). That is why the swap waits for 3.2 to retire `Bar`. Dropping the five keys early is the
  alternative, and it leaves `Bar` without integrity until 3.2 lands — decide deliberately.
- **Every chunk was verified before it was compressed:** row count plus
  `BIT_XOR(HASHTEXTEXTENDED(CONCAT_WS('|', every column), 0))` on both sides, with the time columns cast
  to `TIMESTAMP` so the `timestamptz` target hashes the same as the naive source. Progress is a marker
  under `inspect_persistent("Migrations")`, so a rebuild resumes where it stopped.
- **~113-139k rows a second** sustained, one chunk per transaction.

Sequence: stop every writer (the Download cBot), rename `Tick` aside and `TickReload` into place,
`ANALYZE`, replay the goldens against it, re-measure run 5's cold preload against **568 s**, and drop the
old table only then.

**Done when:** the goldens are byte-identical on the new table, the cold preload is re-measured, and the
295 GB is reclaimed.

### 3.4 Retire the Parquet preload cache — the tape belongs in the database

**Decided: no folder of `.parquet` files holding data the database already has.** Either the database
serves the tape fast enough that no cache is needed, or the cache lives *in* the database.

**What the cache is worth today.** `<Local>/cAlgo/Cache/Preload`, **7.9 GB** over 69 folders — 6.13 GB
of `ticks.parquet` and 1.67 GB of intra-bar frames. Measured on run 5 (EURUSD, eleven years, a 247 MB
tape): cold **568 s**, warm **9.1 s**. Inside one process the in-memory `_TAPE_CACHE_` already serves
every candidate, so the disk cache earns its keep in exactly two places: **parallel workers**, each a
fresh `ProcessPoolExecutor` process with a fresh preload, and **across sessions**. About 400 MB is provably
duplicated (three tapes stored twice at identical byte sizes), and 43 of the 69 folders hold an empty
`ticks.parquet`, because a bar-level run with no conversion need writes zero ticks — both from the
over-keyed signature (5.8).

Three candidate designs, in the order they should be measured:

1. **Make the pull fast enough to need no cache.** After 3.3 the table is a compressed hypertable read by
   `UID` range (178 ms for a dense day). Read it on a binary path — `COPY ... TO STDOUT (FORMAT BINARY)`
   or Arrow — straight into the three numpy arrays, skipping the Polars round trip. **The bottleneck is
   very likely the wire and the materialisation, not the disk**; measure the whole path. If this lands
   near a minute, delete the cache and stop here.
2. **Materialise the tape in the database** — a relation keyed by `(security, start, stop, kind)` holding
   the arrays as compressed binary.
3. **Keep a disk cache but fix its key** — the cheap interim, and a bug regardless: the tick tape does
   not depend on `auto` or `resolution`, yet both are in `_cache_signature_`, so switching resolution
   re-pulls an identical tape (5.8).

**Done when:** the preload path reads from the database with no `.parquet` file on disk, a cold
eleven-year tape is measured against 568 s, and the goldens are byte-identical across the change.

### 3.5 Write the currency algebra design

**Before any code in 3.6, 5.4 or Phase 4.** `account`, `base`, `quote`, and the bridge-pair graph for
the cases where no direct rate exists — a CHF account trading GBPJPY — including what happens when a
required bridge pair has no data for part of the window. **Now also required by the capture:** the Open
API carries no conversion columns, so every tick it supplies depends on this design from the first day.

Conversions must be rebuilt from **full tick streams, not H1 bars**. Accuracy over convenience.

### 3.6 The v2 tick schema

**Gated on 2.5 and 3.5.** Drop the four conversion columns, narrow the types, drop `Mid` — roughly 89 GB
before compression — and take whatever 2.5 decides about the key, the provenance marker and `Volume`
(1.0 on every stored tick).

Two things this breaks, both expected:

- **The goldens.** Reconstructed conversions are not bit-identical to stored ones — float ordering alone
  guarantees that. The break is the tripwire working (5.13's split). Explain the residual and carry it to
  5.13.
- **Cache keys and the memory ceiling.** A new cross-stream dependency appears: backtesting GBPUSD now
  requires EURUSD ticks loaded. The campaign already hit a hard wall here, a cold multi-worker start on an
  uncached pair exceeding 51 GB. Revisit preload sizing before this lands, not after.

`UpdatedAt` and `UpdatedBy` stay — they are part of the `DatapointAPI` contract.

### 3.7 Research schema — DB-only inputs and outputs

Every input a model consumes and every output it produces moves from scattered files into Postgres.
Today the two most valuable series — the timestamped equity curve and the per-bar signal tape — are
persisted only *inside* a plot or result artifact. Nothing is queryable and nothing links a run to the
exact inputs that produced it.

Target: results in a `Research` schema, weights as rows, one `Run` row tying them together, identical
CLI behaviour, a thin web UI on top. Parameters are already done — `Library/Strategy/Ladder.py` replaced
the YAML tree — and the contract snapshot (`Input/Contract.yml`) belongs in the run row beside them. `Library/Research`,
this module, is distinct from the top-level `Research/` folder.

**Layout**

| File | Contents |
|---|---|
| `Run.py` | `ResearchStatus`, `ResearchRunAPI` — `UID` primary key, `System`, `Status`, `Arguments`, `Command`, scope columns, `Parameters` and `Contract` as JSON snapshots at launch (what makes a run reproducible), `Owner` foreign key to `Auth.User`, `PID`, `ExitCode`, `Log`, timing, headline metrics |
| `Result.py` | all with `RID` foreign key to Run **ON DELETE CASCADE**: `TradeResultAPI`, `DealResultAPI`, `PositionResultAPI`, `OrderResultAPI`, `StatisticResultAPI` (long form: RID, Report in Net / Realized / Unrealized, Metric, six values), `EquityResultAPI`, `SignalResultAPI`, `EpisodeResultAPI`, `BenchmarkResultAPI`, `WeightResultAPI`, plus `ResultAPI` as the writer and reader facade |
| `Model.py` | `ModelAPI` — a named deployable weights registry. The `Weights:` parameter holds a Model UID instead of a folder path |
| `Research.py` | `ResearchAPI`, shaped like `Library/Scheduler/Manager.py`: `command()`, `launch()`, `run()` and `runs()`, `reap()`, `cancel()`, `delete()`, `promote()`, `materialize()`, `fingerprint()` |
| `Runner.py` | `python -m Library.Research.Runner <uid>` — Popen the CLI, persist Running and the PID, wait, **reload the row so a Cancelled status wins**, write the terminal state |

`Script/Setup/Research.py` provisions after `setup_auth` for the foreign keys, with indexes on
`Run(Status)`, `Run(System, StartedAt)` and `(RID, Timestamp)` on the series tables.

**Backend contract**

1. `--rid <uid>` on the shared base parser, threaded into `SystemAPI` like `iid`. Absent means the writer
   auto-creates its own Run row, so console runs still enter history.
2. At `_report_` time call `ResultAPI`. The import direction is one-way — `System` may import `Research`,
   `Research` must never import `System`. Write `.trades`, `.deals`, `.positions`, `.orders`,
   `.statistics(rid, report, df)` for **all three** reports, `.equity(rid, df)` **keeping the
   timestamps** (the three `CurveAPI` tracks), `.benchmarks` and `.headline`.
3. **Ungate the signal tape** so it records independently of `--plot`, then flush via `.signals`. Today
   `StrategyAPI._emit_` appends only when recording, only two strategies call it, and `Signals` resets per
   `deploy()`.
4. Learning: `.episode(...)` per episode, replacing log parsing; `.manifest`; `.weights` at completion.
   Parallel seed workers need the rid in their payload. Weight loading moves to a Model UID plus
   `materialize()` into the local cache.
5. Retire the CSV export once the DB path is verified (7.6).

**Measured gotchas**

- **Payload size binds.** A full 11-year H1 run is roughly 34 MB of JSON across about ten series, some
  68k points each. Thin to about 2k points a series, roughly 4 MB, before shipping to a browser; over
  8 MB wedges the Dash dev server. **Decimation must use one shared time grid** or cross-pane crosshair
  lookups break.
- `net.csv` is 90 metric rows by 6 value columns with the label column `Statistical Metrics`, and
  historical files drift — `Annualised` against `Annualized`. **Key by normalised label, never by row
  index.**
- Cancel and finish race: the Runner must reload before writing terminal state.
- PID reuse: guard reaping with `psutil.Process(pid).create_time() <= StartedAt + grace`. Never kill on a
  reap, only mark.
- Bars stay in the `Market` schema. Do not persist them per run.
- DB parameters plus materialized weights change the deployed path. Verify on a Simulation run **before**
  archiving anything.

**Reading list, in order:** `Library/System/System.py` for `_report_`, `_export_`, `_plot_`, `_curves_`,
`_bars_` and `deploy`; `Library/Portfolio/Portfolio.py` for `EquityCurve` (a `CurveAPI`, whose `Track` is the stamped series) and
`_record_equity_`;
`Library/Strategy/Strategy.py` for `_emit_`, `Recording` and `Signals`; `Library/Scheduler/Run.py` with
`Manager.py` and `Executor.py`; `Script/Setup/Scheduler.py` with `Script/Install.py`;
`Library/App/V2/Lightweight/Lightweight.py` for the consumer contract.

**Done when:** `python -m Script.Setup.Research` provisions cleanly; a console run goes Waiting to Running
to Success with result rows and non-null headline metrics; a second run cancelled mid-flight lands
Cancelled with its process tree dead; a real short backtest produces equity and signal row counts
matching bar counts; a one-seed one-episode Learning run records episodes, stores its manifest, and
`promote()` plus `materialize()` round-trips byte-identically in torch; the full suite is green; and
`verify_lock.py` still reproduces the campaign.

### 3.8 Move the `Data` tier under OneDrive

The seven thesis winners' weights (639 KB, 28 files) exist **only** in `<Data>/Models` on one machine's
local AppData. Verified safe from pruning, but not pruned is not backed up.

| tier | files | size | pruned by | verdict |
|---|---|---|---|---|
| `Temp` | 843 | 3.49 GB | retention, by age | **no** — sync locks make deletion unreliable |
| `Data` | 15 645 | 3.15 GB | never | **yes** — write-once, the only copy of every model |
| `Cache` | 180 | 6.61 GB | retention, by last use | **no** — Files On-Demand can dehydrate a preload tape to a placeholder |

**Resolve first:** does anything assume `Data` and `Temp` share a volume? Save and Release move a run
folder between tiers as a rename; across volumes that becomes copy-and-delete — slower, and no longer
atomic. Also open: whether `inspect_root()` stays derived with only `Data` redirected; a retention policy
for `Data/Models`, since roughly 1 100 wave-archive models (about 110 MB) are search byproduct; and a
per-machine namespace if two machines ever sync the same `Data`.

---

## Phase 4 — Continuous capture

Goal: Spotware keeps the tick tape current by itself, replacing the per-ticker Download-strategy cBot
workflow. **Gated on 2.5 and 3.6** — the capture writes into the settled schema, under the settled key,
with the settled provenance, from the source 2.5 chose.

### 4.1 Bulk writes go through `copy`, not `upsert`

`MarketAPI.push_ticks` routes to `db.upsert(..., key=["UID"])`, which does per-row conflict resolution.
That is right for the handful of ticks an online run writes and **wrong by orders of magnitude** for a
day or a month of ticks into a range where no conflict is possible. The bulk path already exists —
`DatabaseAPI.copy(...)` down to `PostgresDatabaseAPI._copy_`, a real `COPY ... FROM STDIN (FORMAT CSV)`
fed from a Polars `write_csv` buffer, and `_csvframe_` already accepts a `pl.DataFrame`. Either give `push_ticks` a bulk mode that dispatches to `copy`, or
have the capture call `copy` directly and leave `push_ticks` to the online path. Measure both on one
month of one security before choosing.

### 4.2 The capture service

An always-on `Service` task under the Scheduler, in the `Market` workflow:

- **Credentials from the store**, the token refreshed by `Environment.Credential` — the service never sees an expired token and
  never holds a secret in its arguments.
- **The source and sampling 2.5 chose.** If it is the historical endpoint, the service fetches each
  closed day once it is complete, which is also what makes a retry idempotent.
- **The rate budget.** Every tick window costs two historical requests, one per side, each paginated,
  under 5 a second. Size the per-day wall clock from 2.4-A before promising a schedule.
- **Provenance on every row** (2.5, item 4).
- **Gaps are reported, never papered over** — a day that comes back short is logged and retried, and a
  day that stays short is recorded like the 2016 hole.

### 4.3 Close the tail

Backfill from the last tick the Download cBot stored to the day the service starts, and verify an
overlap window where both the cBot's history and the service's own fetch exist. A full-history Open API
backfill was judged weeks of wall clock and is not the plan — the tail is days to weeks of data, sized from
2.4-A's measured rate. Then retire the Download
cBot workflow.

**Done when:** the tape extends itself every day without a cTrader session, the overlap window agrees
with the cBot's history to the standard 2.4 set, and the Download cBot is no longer needed.

---

## Phase 5 — Backtesting engine accuracy

The engine already reverse-engineers the cTrader engine byte for byte on the golden protocol and extends
it. This phase closes the places where that fidelity is incomplete and makes the account currency
generic. **5.9 to 5.12 are the cBot protocol items**; none needs the Open API, but each changes the wire
and must be verified by a live round-trip, so they ship in the same cTrader session as the re-baseline
(5.13).

**Done.** Facts in `RULES.md` ("`net.csv` had four defects") and `Tests/Golden/RESIDUALS.md`.

- `net.csv`'s concat dropped `Position`, silently disabling aggregation whenever a position was open —
  fixed 2026-09-11 (`_aligned_positions_`).
- `initial_balance` was the closing balance, so every balance-relative percentage was wrong — fixed
  2026-09-11 (`equity_curve[0]`).
- Holding time collapsed to `stop - entry` with a position open — fixed 2026-09-11 by the same change.
- `net.csv`'s "Net Return (%)" compounded per-trade log returns (38.29 % on the DDPG golden against an
  account return of 34.02 %) — fixed 2026-09-17: it is Σ NetPnL / opening balance, so Buy + Sell = Total,
  and `FitnessType.AnnualizedReturn`, the default `--fitness`, ranks by account CAGR.
- Report folder collisions — closed 2026-09-16: every run mints its own folder, and `_export_` suffixes an
  explicit path that exists. The one case left is `--plot PATH` for the same ticker and strategy twice in
  one second.

### 5.0 The auto-resolution descend gate skips bars whose ticks would have triggered a target

**The largest accuracy defect the offline engine has, found 2026-09-11 by the first `BacktestingAPI`
comparison against cTrader. Gated on 3.2, and ships with it.**

`_intrabar_source_` walks a bar's interior only when `_should_descend_(bids, asks)` passes; otherwise
the bar is **skipped whole** and none of its ticks are examined. The gate decides from the bar's four
OHLC bid and ask values plus a spread pad. When a bar's stored high ask under-represents the true maximum
ask inside it, an armed stop the tape *could* have triggered is never checked.

**The failing case, with data.** Offline run 2, trade 236: Sell USDJPY entered 2023-05-10 14:00:00.217
at 134.397. cTrader exits 14:35:11.798 at **134.724**; the offline engine holds to 18:40:09.578 and exits
at 134.178 — **4h05m late, 54.6 pips**, turning a stop-out into a profit. The hour holds **9 337 ticks**
with a maximum bid of 134.718, and a Sell exits at the ask: 134.718 plus the spread is exactly 134.724.
**The tick is in the tape.** The stop comparison is correct; only the gate is wrong.

**Scale.** In run 2, where clamped volumes keep both paths aligned, **703 of 709 exits are identical in
timestamp and price** and the median exit price gap is 0.000 pips. Six trades differ, one badly, and that
one carries nearly the whole gross gap. **It compounds** — a different exit changes the balance, which
changes the next volume and every later decision; run 1 keeps only 473 of 1024 identical entry
timestamps after diverging at trade 2.

**Proven by bypassing it.** `--resolution Tick` takes every branch that does **not** consult the gate:

| | Exit | Price | Net |
|---|---|---|---|
| cTrader | 14:35:11.798 | 134.724 | -2.29 |
| auto-resolution | 18:40:09.578 | 134.178 | +1.41 |
| `--resolution Tick` | **14:35:11.798** | **134.724** | **-2.29** |

| | Exits matching | Net | Δ vs online | Wall clock |
|---|---|---|---|---|
| auto-resolution | 703 / 709 | -57.42 | 3.78 | 1.05s |
| `--resolution Tick` | **704 / 709** | **-61.12** | **0.08** | 2.20s |
| online (cTrader-fed) | — | -61.20 | — | — |

What remains after the gate is bypassed is the real sub-pip residual: five exits, lags of -24s, -5s, -1s
and twice 0s, price gaps of 0.1 to 0.3 pips, **0.08 EUR across 709 trades**. On run 5 (EURUSD D1, eleven
years) the gate changes nothing — same gross, commission, swap and net to the cent at 9.1s either way.
**It is cheapest where it is useless and wrong where it is cheap.**

**Decision: `Auto` stays the default and gets fixed, not replaced.** **The binding invariant: `Auto` and
`Tick` must produce byte-identical output, with `Auto` much faster.** `Auto` is a *lossless* optimization;
any divergence is a bug in `Auto`, never an acceptable trade.

**The fix is to delete the pad, not to tune it — and it comes from 3.2.** On the failing bar the true
maximum spread was **0.007** where the four sampled points showed **0.004**; the bound held elsewhere
**by luck, not by construction**. With the two-sided bar the gate reads four exact bounds —
`bar.HighPoint.AskTick.Ask`, `bar.LowPoint.AskTick.Ask`, `bar.HighPoint.BidTick.Bid`,
`bar.LowPoint.BidTick.Bid` — with **no pad at all**, which removes the misses *and* strengthens pruning.
**Over-bounding is free; under-bounding is the bug.** If 3.2's argmax proves awkward, a stored
`MaxSpread` per bar is a provably safe fallback (`max ask <= max bid + MaxSpread`, and `min ask >= min
bid` for free), at the cost of slightly weaker pruning.

The D1 run still leaves **24 of 510 exits differing** at tick resolution while landing within 0.93 on
net — small or offsetting, and separate from this item.

**Done when:** run 2 reproduces cTrader on all 709 exits or the remainder is explained, the tick-
resolution cost is measured on run 5, and the other four runs are re-measured under the fix.

### 5.1 Write the spread charge to the trade record

`BacktestingAPI._build_position_` charges the spread correctly — `gross = (bid - ask) * volume *
quote_conversion` — but never surfaces it as a field. The only recovery route today is the identity
`spread = abs(commission) * points / 7`, which **fails when commission is zero — exactly the training
configuration** (`--commission-value 0`). So in every Learning run the single largest cost component,
about 42% of total cost, is invisible. Fix: an additive `SpreadPnL` field on `PositionAPI` and
`TradeAPI`. Goldens stay byte-identical apart from the new column.

### 5.2 Risk sizing ignores the quote-to-account conversion

**The defect is confirmed (golden run 4); the fix stands.** `calculate_fixed_amount_volume` computes
`amount / (sl_pips * PipSize)` where `amount` is in **account** currency and the stop is in **quote**
currency, with no conversion. `PipSize` cancels, so contract tick metadata is not the lever. Effective
risk becomes `RiskPercentage / price`:

| pair | intended | actual |
|---|---|---|
| EURUSD | 1.0% | 0.909% |
| USDJPY | 1.0% | **0.0067%** |

On USD/JPY the raw volume — 133 units at a 10 000 balance — falls under `VolumeMin`, which is why DDPG
could never open a position there. **Raising the balance does not help**: risk stays `1/price` because
volume and balance scale together. The published campaign is unaffected — every winner ran with active
risk sizing, 26 to 124 distinct volumes, 0.0 to 4.1% of trades at the floor; USD/JPY alone used a
research-only compensation, `RiskPercentage` scaled by 119.1994, restoring roughly 1% risk a trade,
exact at the window start and easing to about 0.8% by the end. **Remove that compensation as part of
this fix, not before.**

**Verified correct — do not "fix" these.** P&L quote-to-account conversion is right for every base and
quote combination under a EUR account: `account == base` uses `1/price` (EURUSD 30.27/1.0743 = 28.1765
against a recorded 28.1760), and `account == third` uses the tick's `QuoteConversion` per tick — USD/JPY
0.00707514, 0.00707354, 0.00698959, 0.00704379. `QuoteConv / BaseConv` equals `1/price` to four decimals
on all seven majors.

### 5.3 Unify the exposure feature with the order sizer

`DDPGObservationAPI._position_features_` normalises exposure by `ActionAPI.maximum_volume`
(`SizingMode.Balance`), while orders are sized by `_reference_volume_`, which is risk-based. They
disagree by 9x on EURUSD and GBPUSD and by **238x on USD/JPY**, so the feature clips to plus or minus one
above an `abs(action)` of 0.109, 0.112 and **0.004** respectively. On USD/JPY the agent is effectively
blind to its own position and can only trade all-in or flat. **This invalidates trained weights** — the
main reason Phase 6 retrains.

### 5.4 Generic account currency

**Needs 3.5.** Stored rates convert to EUR only. `quote` to `account` is derivable as `1.0` when
`account == quote`, and as `QuoteConv / BaseConv` when `account == base`, but a fourth currency unrelated
to the pair — a CHF account trading GBPJPY — needs a cross rate the tick does not carry. A designed rate
source, not a bolt-on.

### 5.5 Hedging

`PositionMode.Hedging` is a stated goal and is **unproven, not merely untested** — everything to date ran
`PositionMode.Netting`. Treat it as new work with its own validation, not as a flag to flip.

### 5.6 The position open at the stop date is valued differently from cTrader

cTrader closes any position still open at the end of the window, at the final tick, and charges its
closing commission and a full swap. We mark it earlier, and `_build_position_` sets `SwapPnL=0.0` at open
with swap only ever applied in `_build_trade_`, so an open position accrues **no swap at all**. The open
position's mark-to-market gap equals the entire short-side gross gap, exactly, every time:

| Run | Open position | Our mark | cTrader implied | Gap | Short gross gap |
|---|---|---|---|---|---|
| 1 | Sell 28 000 @ 1.10473 | 2.53 | 26.64 | 24.11 | 24.11 |
| 2 | Sell 1 000 @ 141.001 | 0.53 | -0.77 | -1.30 | -1.30 |
| 3 | Sell 27 000 @ 1.10473 | 2.70 | 28.35 | 25.65 | 25.65 |
| 4 | Sell 23 000 @ 141.001 | 12.11 | 41.65 | 29.54 | 29.54 |

Golden 5 has no open position and reconciles to the cent — the control. Fix: value the open position at
the final tick of the window, charge its closing commission, and accrue swap on open positions. **Ship
with 5.13** — it moves `positions.csv` and the `net.csv` totals deliberately.

### 5.7 A backtest contaminates the next one in the same process

Mitigated, not fixed. Bounded in practice because runs are process-per-run, but a real correctness hole
in any in-process sequence.

### 5.8 Backtesting engine performance

Measured 2026-09-11 by `cProfile` on the online hot path — `Trend` on EURUSD H1 over 2023, warm tape,
6 217 bars, 17.6M calls. Ranked by what the profile said, with what has happened since:

| Cost | Evidence | State |
|---|---|---|
| **Datapoint construction** | `Datapoint.__setattr__` 1 006 870 calls, the single largest entry; `Dataclass.data` 1.8s cumulative; `isinstance` 3 237 615 calls inside the same parse path; `TickAPI.__post_init__` 33 101 calls, 1.2s cumulative | **Mostly taken 2026-09-17:** the unused autosave hook removed and the `data()` field plan cached — `TickAPI()` 12.0 → 6.3 µs, `bar.dict(flatten=True)` 46.9 → 24.1 µs, goldens unmoved |
| **Polars frame churn** | `dict_to_pydf` 18 658 calls, three per bar | **Partly taken 2026-09-17** — `_scalar_` and ATR's `_extract_`; the per-bar indicator frame remains |
| **Preload** | `_load_bars_` 3.76s of the 4.04s `_preload_`, 40% of a single backtest | open — see the first row of 8.8 |
| **`select.select`** | 0.558s over 693 calls | open — database round trips *during* a run, after preload. Find what is still talking to Postgres |

**The preload disk cache is over-keyed** — the same mistake `window` taught. `_cache_signature_` hashes
`(security, start, stop, timeframe, auto, resolution)`, but the **tick tape does not depend on `auto` or
`resolution`**: both pull byte-identical tick columns; only the intra-bar frames differ. Switching
resolution discards a valid tape and re-pulls it — 12-15 minutes for a dense ten-year window. Key
`ticks.parquet` without `auto`/`resolution` and only the intra frames with them — or retire the cache
(3.4). **The 568 s is not the cost of tick resolution:** run 5 cold at tick resolution took 568.1 s, of
which the bar loop was under two seconds — the rest was this redundant cold preload. `_should_descend_` is
**not** a hot spot (5%), which matters because 5.0 will make it descend more often. **Do not** re-attempt the recorded dead ends (Appendix A).

### 5.9 Delay and batch protocol

Sliding FIFO plus `UpdateID.Batch` plus a 256 KB slot, replacing the single-slot request/response lockstep
for bulk transfer. Roughly 10% validated already.

### 5.10 Decide DDPG's `Subscription` deliberately

`NNFXStrategyAPI` moved to `Stream.All & ~Stream.Tick` because its intrabar reactivity is entirely
target-driven — 21.3 M raw ticks collapsed to bar closes plus a few thousand target crossings, bit-exact.
**DDPG has never been reviewed.** An RL agent may genuinely act per tick. Decide from its actual channels;
do not copy NNFX. Base `StrategyAPI.Subscription = Stream.All` is a safe superset; every strategy should
declare its minimal subscription.

### 5.11 Protocol symmetry

`Decreased{Buy,Sell}PositionVolume` updates 65 and 66 exist; the gap is on the **action** side. Add four
target-volume actions in the logical order `Increase`, `Decrease`, `Modify`. Renumbering is safe because
`Script/Setup/Enum.py` regenerates the C# side. Run `python -m Script.Setup.Enum`, rebuild, reinstall the
`.algo`, then verify a live round-trip — a wire-ID mismatch mis-decodes silently. Logs must be symmetric
with the existing pairs.

### 5.12 `receive_update_security`

Parse the C# security payload to enrich `SecurityAPI`. Small; ship with 5.11.

### 5.13 The cTrader session — re-baseline the goldens

**Blocked on you — one cTrader session, the single re-baseline for Phases 3 and 5.** Run the checklist
below first, then in the same session:

1. **Confirm both `.algo` files load and run** (`Sources/Robots/Connector.algo`,
   `Sources/Indicators/Connector.algo`). They are built by the pinned `cTrader.Automate` on SDK 10;
   everything so far is compile-time evidence, none of it proves the platform accepts the artefact. Do
   it first, so a later wire mismatch can only be the enum change, never the compiler.
2. **Round-trip 5.9 to 5.12** live.
3. **Regenerate the five `Simulation` runs** below, and the matching `Backtesting` runs, under 5.6's
   change and everything 3.6, 5.2 and 5.3 moved. Every deviation from the current goldens must already have
   a written explanation. Compare, accept, commit, and update `verify_lock.py`.

This is a **versioned** change — the old goldens stay in git history as the pre-fix reference. Never
absorb a re-baseline into an ordinary refactor. The one declared exception so far is rule 2's
(2026-09-15); it does not replace this item.

#### The session checklist

**Two Spotware demo accounts, EUR and USD**, same broker and symbols. The USD one exists solely to reach
the `account == quote` branch (run 3). Both are **Hedging**; record it, but it is not a variable here —
`Trend` holds one position at a time, so netting and hedging are observationally identical.

Four checks before the session, or the whole set is void:

1. **Fees run at the demo account's own terms.** `Auto` resolves to `Accurate` for spread, commission
   **and** swap, and `Accurate` reads `Universe.Contract` — or the pinned `Contract.yml`:
   `Commission` 45.0 as `BaseAssetPerMillionVolume`, `SwapMode` `Pips` with per-pair `SwapLong`/
   `SwapShort`, `SwapPeriod` 24. **45 is correct here** — the demo standard, and what cTrader's
   accurate-commission backtest charges. **Do not confuse it with the thesis cost model**, which
   deliberately prices a raw-spread, swap-free account at 3.5 USD per 100 000. The goldens prove the
   **engine** matches cTrader; the thesis prices a **realistic broker**. Neither is edited to match the
   other.
2. **Leave swap on.** The swap residual against cTrader is one of the accuracy floors and these runs pin
   it.
3. **cTrader's "download historical data for additional symbols to convert profit/margin" must be on.**
   Off, the cross-pair spot freezes and conversions go stale — a silent, plausible-looking wrong number.
4. **Set the cBot's `Description` to `Golden1` … `Golden5`** in the Reporting Management group. It
   travels as `--description` into `Run.json` and is the only thing that tells the run folders apart.

#### The five runs

Strategy **`Trend`** throughout — the only strategy that drives stop loss, take profit, break-even,
trailing stop with step re-arming and scale-out through armed intrabar targets, which is exactly where
the engine has to agree with cTrader. **Each configuration runs twice because there are two engines:**
the cTrader half is the Connector cBot in cTrader's Backtesting tab (`Simulation`, `RealtimeAPI`, P&L
arriving over the wire), the CLI half is `Backtesting` (`BacktestingAPI`, computing its own fills and
fees). Agreement on fills and fees is tautological in the first and a real measurement in the second.

| Table column | Where it goes in cTrader's Backtesting tab |
|---|---|
| Ticker | the chart symbol |
| `--timeframe` | the chart timeframe — `h1` or `Daily` |
| `--start` / `--stop` | From / To |
| `--account-asset` | which demo account is selected, EUR or USD |
| `--account-balance` | Balance |
| `--account-leverage` | the account's own leverage, 30 |
| `--spread-type` / `--commission-type` / `--swap-type` | cTrader's accurate-commission configuration — nothing to set per run |

Common CLI flags: `--strategy Trend --provider Spotware --account-leverage 30 --spread-type Auto
--commission-type Auto --swap-type Auto --export --run FOLDER`, `--resolution` unset so auto-resolution
runs, and `--contract` pointing at the golden's `Contract.yml`.

| # | Ticker | `--timeframe` | `--start` | `--stop` | `--account-asset` | `--account-balance` | The only cover for |
|---|---|---|---|---|---|---|---|
| 1 | EURUSD | `Hour` | 2023-01-01 | 2024-01-01 | EUR | 10 000 | `account == base` (`1/rate`); commission base **is** the account; raw volume clear of `VolumeMin`; the tick tape, auto-resolution and intrabar exits at roughly a thousand trades |
| 2 | USDJPY | `Hour` | 2023-01-01 | 2024-01-01 | EUR | 10 000 | third currency with a **non-USD quote**; the only 3-digit, 0.01-pip contract of the seven |
| 3 | EURUSD | `Hour` | 2023-01-01 | 2024-01-01 | **USD** | 10 000 | **`account == quote`**; commission base is not the account |
| 4 | USDJPY | `Hour` | 2023-01-01 | 2024-01-01 | EUR | **1 000 000** | raw volume clearing `VolumeMin` on a 3-digit pair — the full volume distribution 5.2 needs |
| 5 | EURUSD | `Daily` | 2015-01-01 | 2026-01-01 | EUR | 10 000 | eleven years: **swap accumulation over long holds**, the D1 auto-resolution path, the 2016-01-11 to 2016-01-25 hole, every DST transition, a position open at the stop date (5.6) |

**Why four of five are `Hour`:** conversion, sizing, spread, commission and intrabar exits are
timeframe-independent, so hourly buys a thousand trades to compare instead of a few dozen. **Why run 5
stays `Daily`:** swap accrues per 24-hour period, so a swap error scales with hold duration, not trade
count. **Why not the other four majors:** GBPUSD, NZDUSD, USDCAD and USDCHF are structurally identical to
run 1 or 2. **Two optional additions:** `AUDUSD Daily 2023 EUR 10 000`, the only major with a positive
`SwapLong` (+0.105 against EURUSD's -2.445), proves a swap credit is credited; `USDJPY Hour 2023 EUR 10 000` puts the 3-digit contract
under run 5's density.

**The split that makes this set a tripwire for 3.6.** `_needs_conversion_` is
`account_asset not in (base, quote)`:

| Reads the stored conversion columns | Runs | Expected when 3.6 drops them |
|---|---|---|
| **No** — derives from the pair's own price | 1, 3, 5, DDPG | **must stay byte-identical**; any movement is a regression |
| **Yes** — reads the EUR-denominated columns | 2, 4 | break expected; explain the float-ordering residual and carry it to 5.13 |

**Compared:** `trades`, `positions`, `orders` and `deals`, byte for byte. `net.csv` is excluded by
design. Pass `--run FOLDER` and **commit the folders** — the 2026-07-05 set was lost because it never
entered git.

---

## Phase 6 — Optimization and Learning

Goal: out-of-sample strength that survives scrutiny, and a walk-forward protocol that is what it claims to
be. Thesis iteration two.

**Done.** Record the observation order with the weights (2026-09-17) — every `DDPGStrategyAPI.save()`
writes `Observation.json` and `load()` refuses a different layout; the champion and the DDPG golden are
backfilled (`RULES.md`, "Parameter key order is an input").

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
  slower-timeframe fix. The 2026-07-21 result: gross Sharpe about 0.05 across three models with all costs
  removed, so no edge existed and costs were real but not binding.
- **Beta before alpha on any positive result.** A one-sided policy earns leverage times instrument drift,
  which looks like alpha. EURUSD H1 2015 to 2026 drifted -2.92%; the best-returning model, +31.54% gross,
  was a permanent short at about 10x, and 10 times 2.92% is about +29% — fully explained, with a Sharpe
  of 0.11. Rank by Sharpe and buy/sell
  balance, never by raw return.
- **`balance=N` does not enforce two-sidedness.** The gate is `min(buys, sells) >= N`, so a 41-buy,
  1891-sell model at 2.1% buys passes `balance=3` trivially. Judge by ratio.
- **Silent-zero traps.** Any `x or fallback` on a config value turns a legitimate 0 into a fallback —
  `SizingATRScale` falls back to `StopLossScale`, so a no-risk arm that zeroes it yields zero volume
  silently under `SizingMode: Risk`. Always verify an arm actually traded before interpreting its return.
- **Config travels as a Parameter, never a class attribute.** Spawn workers rebuild the strategy from the
  payload, so a class attribute set in the parent process silently does not propagate. Read new knobs via
  `getattr(self.SignalManagement, "X", None)` with a class-attribute fallback.
- **`DifferentialSortino` and `DifferentialSharpe` are exactly scale-invariant** — numerator and
  denominator both scale with k cubed — so leverage cannot act through the reward, only through the
  observation. Sizing tuning is legitimately replay-only, but replaying at a different size is **not** a
  pure scaling: different account features give different actions. Measure, never extrapolate.
- **Reward clipping is occupancy-driven, and diagnosis is not cure.** The clip rate tracks market
  occupancy; relieving it did not improve learning.
- **Record the netting knobs yourself.** The manifest records none of `SignalMode`, `TurnoverCost`,
  `PositionMode` or the sizing settings, so arms become indistinguishable unless the sweep results carry
  them.

### 6.1 Purging and embargo at fold boundaries

Golden 19 has an average hold of **537 days**. A naive train/test boundary leaks badly — a position opened
inside training and closed inside validation puts future information on both sides. This is the strongest
methodological criticism available to a reader of the thesis, and it is fixable. Purge the training
window of any sample whose label horizon crosses the boundary, then embargo a band after it.

### 6.2 Probability of backtest overfitting and a deflated Sharpe

**The overfitting budget compounds; it does not reset per stage.** Staging turns a product into a sum —
6, 2, 2, 1 is 24 combinations flat but 11 staged — and coarse-to-fine turns a sweep into a funnel, so both
genuinely cut trials. But stage three is conditioned on winners already fitted to the same data, so the
effective trial count is the **accumulated total across every stage, round and fold**. A run already
records that number, so the deflated metric can be computed against the real one.

### 6.3 True walk-forward with `--continuous`, reported honestly

Continuity makes folds path-dependent — every fold starts near the previous winner — so `Frequency`
election becomes near-tautological. With `--continuous`, `Last` or `Mean` is the honest choice, and the
run must record which it used. `SplitAPI.walk_forward_folds` takes the single-split branch when
`training <= 0` rather than entering the rolling loop. A fold's model is scored on its **validation**
window, never its training window, and the held-out `--testing` pass is the only unbiased number.

### 6.4 One untouched holdout, used exactly once

Structural discipline rather than code. Decide the window now, write it down here, and do not look at it
until the campaign is otherwise finished.

### 6.5 A real risk-free rate curve

`--risk-free` is a single constant applied across every ratio and Jensen's alpha — and since 2026-09-17 it
reaches Learning and its workers too. A constant is wrong over 2014 to 2026 — it flatters every ratio in
the ZIRP years and penalises them after 2022. Backfill the **ECB deposit facility rate** from 2014: the
right reference for a EUR account, published daily, free. Store it as a dated series beside the market
data and have the statistics read the rate in force at each period. Keep the flag as an override for
reproducibility.

### 6.6 Search beyond three free parameters

TPE or random search once the space exceeds three free dimensions; the grid stops being the right tool
there. **The trap that would silently corrupt every sweep:** `DatasetAPI` carries `IndicatorResults`.
Learning caches them safely because its indicators never change between episodes. **Optimization varies
indicator parameters**, so reusing a cached tape wholesale evaluates every candidate with the *first*
candidate's indicators — the sweep completes, produces plausible numbers, and is meaningless. Rule: reuse
the market-data tape, always `inject(replace(tape, IndicatorResults=None))`. Do **not** warm every
candidate to the grid's worst-case window (`RULES.md`).

### 6.7 Re-run the seven-pair campaign on the corrected engine

The output of Phases 3 and 5, and the input to thesis iteration two. Single-threaded so it is exactly
reproducible. Compare against `Research/CAMPAIGN-7PAIR.md` pair by pair and write down what moved and why.
**State the tape's sampling eras** (Appendix A): the eleven years span four of them, with tick density
differing roughly thirty-fold, which a reader of a tick-derived result needs to know.

Then decide, on evidence, whether iteration two replaces iteration one. If the corrected engine produces
weaker numbers, that is a finding worth stating, not a result worth hiding.

**Three claims iteration one could not make. Items 6.1 through 6.4 exist to earn them.**

1. **It was not walk-forward and not continuous.** The invocation was `--training 0 --validation 12
   --testing 12`, which takes the `training <= 0` branch and produces **one** split: train 2015-01 to
   2024-01, validate 2024-01 to 2025-01, test 2025-01 to 2026-01. Iteration two must pass `training > 0`
   and `--continuous`, and 6.3 says how to elect honestly once it does.
2. **There was no genuinely held-out evaluation.** `robust_eval.py` scores over the full 2015-01-01 to
   2026-01-01, which contains the nine training years. Iteration one states this as a limitation and must
   never sell it as train/validate/test rigour. 6.4 is what fixes it.
3. **"Ten-plus years of data" is not a differentiator.** Across the 18 surveyed articles, 12 already use
   ten years or more, at a median span of 11. What *is* distinctive is resolution over that span: only
   Carapuço and co-authors use tick data, over seven years. Claim tick-derived data across 11 years and
   seven pairs; never span alone.

**Numbers from iteration one that must not drift when they are recomputed.** The five-balance
path-robustness protocol is 9 900 / 10 000 / 10 050 / 10 100 / 10 200, and every pair came back
robust-positive five times out of five. Alpha leads, not return, because in every pair the highest-return
candidate failed the permutation test. USD/JPY is a documented negative — beta +1.012, alpha -1.07% a year
— and after 5.2 and 5.3 it is the pair most likely to move. The regime null is per-model, not a constant.

**Two facts about the delivered agent that were each got wrong at least once — read the source, do not
restate these from memory.** Gradient clipping at norm 1.0 on both critic and actor is **not** an
anti-collapse mechanism; it bounds update norm against exploding gradients. Collapse is prevented by the
scale-*sensitive* reward, since a scale-invariant one collapses the actor to about 3% of available size,
and by `ActorRegularization` at 0.001.

**The feature bank lives in the run manifest, nowhere else.** `<Data>/Runs/<id>/Input/Parameters.yml`
holds the 16 indicators actually used. `Research/DDPG-EURUSD-H1/Learning.yml` is a trimmed base carrying
only the fast half, and `champion_override.py` does not touch `TechnicalManagement`, so neither file is
authoritative. Always read the manifest.

---

## Phase 7 — Web app

Gated on 3.7, which is where the data comes from. The credential page already exists (Phase 1).

### 7.1 Move the pages onto the Research schema

`Library/Web/Research/` reads run rows and result series instead of parsing artifacts. A result detail page
renders an immutable artifact and therefore **does not poll** — polling re-mounted the grid and discarded
sheet tabs and chart zoom.

### 7.2 Profit, risk and ratio columns on `/backtesting` rows

Build as a DB read once 3.7 lands, never by re-parsing each run's stored artifacts.

### 7.3 Signal and plot refactor

Direction and Volume signal on the Strategy **base** class; thresholds default **off** and one-sided
capable; eight toggleable lines; `Parameter` returns None for a missing key; a `--plot` hardcode audit;
optional markers and a deal map. **Land it as a no-op first, prove the suite and the goldens, then tune
the bounds.**

### 7.4 Payload thinning on one shared time grid

See the measured note in 3.7. This is what makes an 11-year H1 run openable in a browser at all.

### 7.5 iPad pass

`Library/Web` is used from a Windows desktop browser **and an iPad 12.9 inch**; both are first-class.

- **Charts must not capture touch gestures** (`RULES.md` has the exact Plotly settings, and why never
  `staticPlot: True`).
- **Prefer fits-without-interaction.** The workflow DAG should render every task and edge visible at once;
  the only interaction wanted is tapping a node to open that task's page.
- Touch targets, sticky headers and virtualized grids all need checking at iPad width. `LightweightTableAPI`
  is virtualized, so verify momentum scrolling behaves. Playwright emulates the viewport at 1024 by 1366
  CSS pixels.

### 7.6 Retire the CSV export

Once 3.7 is verified end to end.

### 7.7 Known and unfixed

- An ordinal pane with very few points does not fill the width — a three-fold generalization chart leaves
  space at the right edge. Lightweight clamps bar spacing and setting it explicitly is overridden.
  Cosmetic and legible.
- Multi-tab `Open` depends on the browser, not the code. Browsers permit one popup per gesture. The button
  opens the first in place, attempts the rest, and reports how many were blocked. No code-only fix.

---

## Phase 8 — Remaining

### 8.1 Logging

`StorageAPI` is unit-tested against a fake record but has never been exercised against a live Postgres run
end to end, and the Scheduler still writes durable rows through `ExecutorAPI._open_log_`. Close both.
Measured dead end, do not retry: a drain thread for the console and file sinks. Async is a per-sink
property — console and file synchronous, `StorageAPI` not.

### 8.2 Realtime hardening

Audited 2026-07-02, needs a cTrader session: warmup bars are double-added to the market buffer;
`BufferAPI._worker_` can deadlock on a flush when connect fails; transport hardening; an unused universe
buffer; the watchdog is armed only on `Init`; no hung-peer timeout.

### 8.3 Strategy state recovery

Persist Signal and Risk machine state across a Live restart — `SessionAPI.State` bytes, loaded at
`deploy()`, saved on `Shutdown`.

### 8.4 Test coverage gaps

`Statistic` 1 file for 1889 lines; `Scheduler` 1 for 1700; `Model` 2 for 1654; `Web` 3 for 3449; `Auth` 1
for 460; `Indicator` 4 files for 43 modules.

### 8.5 Dead surface

Zero callers outside the package `__init__`. Delete, or keep deliberately as a library offering.

`Utility/Path.py` 28 of the 36 `traceback_*` and `inspect_*` grid, about 120 lines; `Utility/Datetime.py`
`datetime_to_iso`, `iso_to_datetime`, `weekday_shift_datetime` and seven `<day>_shift_datetime`;
`Utility/Runtime.py` `is_local`, `is_service`, `is_python`, `is_ipython`, `is_terminal`, `is_console`,
`match_env_vars`; `Utility/IO.py` `is_readable`, `is_writable`, `smartlink`, `symlink`, `hardlink`;
`Utility/Typing.py` `findvariable` and `getvariable`; `Utility/HTML.py` entirely. **Not dead, despite an
earlier listing here:** `string_to_datetime` (`Web/Core/Artifact.py` parses run stamps with it) and
`find_user` (`StorageAPI.attach`).

Called only by their own tests (rechecked 2026-09-17 across `.py`, `.js`, `.sql`, `.yml`, `.cs`):
`Typing` `hasmember`, `hasmethod`, `getmethod`, `hasproperty`, `getproperty`; `Runtime`
`find_caller_module`, `find_caller_class`, `find_caller_package`; `DataclassAPI.tuple` and `list`.
`DataclassAPI.fields` and `json` have no caller at all — deleting those four also settles 8.6's note that
they forward seven keyword arguments.

`Portfolio.py` the five statics that remain of the original 16: `pull_accounts` and `push_accounts`,
`push_orders`, `push_positions`, `push_trades` — plus `calculate_statistics`, `BuyOrders` and `SellOrders`;
`Portfolio/Statistic.py` `generate_realized_report` and `generate_unrealized_report`; `Market.py`
`load_ticks`, `save_ticks`, `count_ticks`, `load_bars`, `save_bars`; `Universe.py` all 12 `save_` and
`load_` plus `pull_timeframes`.

Convenience properties never read and not emitted by `dict()`: `Account` IsDemo, IsHedged, IsNetted,
UnrealizedReturn, MarginRatio, FreeMarginRatio, CreditRatio; `Order` IsAccepted, IsFilled, IsRejected,
IsExpired, IsCancelled, ExecutionRatio, UnfilledVolume; `PnL.LogPnL`; `Position.MarginUtilization`;
`Trade` DurationDays and IsClosed; `Bar.RangeTick`; `Price.LogPrice`; `Tick.InvertedMid`; `Timestamp` Sin,
Cos, Epoch, Yearday, Millisecond; `Contract` IsSpot, IsDerivative, IsLinear, IsNonLinear; `Ticker` Dashed,
Slashed, Underscored; `Timeframe.Hours`. Plus about 25 `@overridefield` Position columns computed by every
`dict()` and dropped by `reporting_view`.

`IndicatorAPI.init_data` and `update_data` (the one instance is read only for its three members);
`App/V2/Assets/Scripts/Paginate.js`, which targets the retired `.dash-table-container` yet keeps a
`MutationObserver` on the whole body of every page, and the 11 `app.css` rules still styling
`.dash-table-container`, `.dash-spreadsheet` and `.cell-markdown`.

`Database.structured`, `ManagerAPI.delete_run`, `ManagerAPI.retained`, `OptimizationAPI.trials`,
`BrownianNoiseAPI`, `GeometricBrownianNoiseAPI` (no factory; DDPG hardcodes OU), the empty
`Sources/Plugins/Plugin`, and `Requirements.txt` at 0 bytes. `Sources/Indicators/Connector/Connector.cs` is
still the cTrader hello-world template — Phase 9 either makes it real or it goes.

`Library/Formulas/` stays — an xlwings Excel UDF feature with zero callers that you intend to renovate.
The `xlwings` pin stays with it.

### 8.6 Simplifications

Behaviour-preserving, provable by AST body hash plus the suite and the goldens.

- `Position.py`: about 40 `@overridefield` properties are four body shapes — `pnl/(Volume*unit)`, a signed
  price difference over unit, `min`/`max(0, x)`, and `_max_equity_*_pnl_.<attr> or 0` — so one helper each.
  `Order` and `Position` share `_unwrap_price_`, `_make_price_` and `_assign_price_`, timestamp assignment
  and the Session and Account property pairs, which is a Portfolio mixin with two hooks.
- Indicators: a `BaselineAPI(TechnicalAPI)` carrying the four `filter_` and `signal_` rules plus `batch` —
  9 classes times 4 identical methods, 6 identical `batch`, about 125 lines; `MAC`, `DMAC` and `TMAC`
  collapse to one `_AVERAGE_` class attribute; ROC, ATR and RV have identical rules; `FundamentalAPI`
  equals `SentimentalAPI` equals `TechnicalAPI`'s composite half; `MA.py` builds the six-way `match` twice.
- `SystemAPI._process_updates_` is about 190 lines of `match` arms rebuilding the same seven-key context.
  `RULES.md` keeps one `case` per `UpdateID` deliberately, so the lever is the shared `context()`, not a
  dispatch table. `_fitness_()` is byte-identical in `LearningAPI` and `OptimizationAPI`, so it belongs on
  `BacktestingAPI`. `Realtime._binary_*_` are `_lower_` class constants.
- `Strategy.py` `strategy_management`: `update_closed`, `stop_loss`, `take_profit`, `margin_call`, the
  `update_modified_*` family and `update_closed_order`, `filled` and `expired` differ only in the log line —
  but `RULES.md` prefers explicit named handlers, so only a shared log helper is in scope. `Hybrid/DDPG.py`:
  `Defaults["Realtime"]` equals `Defaults["Learning"]` for 35 lines, the 12-field state block appears in
  both `__init__` and `_initialize_`, the optional-parameter idiom repeats ten times, and
  `_hedge_(update, close)` never uses `update`.
- `Model`: the `memorize`, `remember`, `_soft_update_` and `decide` scaffold is copied into the DDPG, SAC
  and TD3 agents and belongs on `AgentAPI`; SAC and TD3 `Critic.forward` are byte-identical; the whole
  module uses `_name` privates where `RULES.md` says `_name_`; `remember()` annotates a tuple literal instead
  of `tuple[np.ndarray, ...]`.
- `Market.py`: `pull_bars` repeats an 11-column tick join five times (3.2 removes it); `init_data`,
  `update_data` and `update_offset` list the same series three times; `Series.py` `last()` and `tail()`
  share a 500-character row-to-`TickAPI` expression, and `over`, `under`, `crossover` and `crossunder`
  share a five-line prelude; `Tick.py` has seven same-shape setters. `Universe.py` has 11 live `pull_` and
  `push_` of one shape; `Timeframe.py` has five comparison dunders that are `total_ordering`.
- `Database.py`: the seven-line target-validation block is copied into `exists`, `diff`, `create`,
  `delete` and `migrate`; `executeone` and `executemany` share a 12-line prelude; `search` repeats an
  empty-catalog literal three times; `executemany` logs a failure via `.error` then `.exception`, the same
  double-log as `Service`, `Bloomberg.Streaming` and `Remote`. `Dataclass.py` `tuple`, `list`, `dict` and
  `json` forward seven kwargs explicitly. In `Auth`, Cloudflare `_verify_` and OIDC `authenticate` share
  the JWKS and `jwt.decode` block, which is a `_claims_()`.
- `Runner.load` and `SchedulerAPI._task_` both build a detached `TaskAPI`, which is a
  `TaskAPI.fetch(db, uid)`; `Logging.File.FileAPI` and `Utility.File.FileAPI` share a name, so consider
  renaming the sink `FileSinkAPI`.
- Tests: `Tests/Strategy/test_Strategy.py` imports `MagicMock` inside six tests and `test_Workspace.py`
  imports `json` inside three; comments appear in seven test files; the `test_Sizing.py` derivations could
  move into the assertions; `Tests/Benchmark/IPC.py` is a benchmark script living under `Tests/`.

### 8.7 Blocked

- **`Script/Install.py` and `Script/Task.py` both define `provision()`** — different modules, different
  jobs, no collision today. Rename one if it ever confuses.

### 8.8 Measured but not taken — the 2026-09-17 hard pass

Each was measured, each left the goldens byte-identical in a throwaway process, and each was left out for
the reason given. Take them with the golden gate in hand.

| Opportunity | Measured | Why not yet |
|---|---|---|
| `_load_bars_` builds a frame it already had — select it from the two SQL frames instead of `bar.dict(flatten=True)` | preload 1.52-1.86s → 1.17-1.29s on an H1 year, ~3s on H1 10y | The target schema (column order, dtypes, the 11 always-null bookkeeping columns) has to be reproduced exactly; needs its own equality proof per security and timeframe. 3.2 changes this code anyway |
| Optimization and Learning reconnect to Postgres for every candidate | 19-22ms per candidate, 0 queries sent on a warm replay | Making `_db_` lazy moves when a bad connection surfaces; wants a deliberate design |
| `_build_intra_arrays_` rebuilds 12 arrays per candidate from the cached dataset | 6-11ms per 369k M1 rows | A scope-keyed memo is wrong for Learning's mirrored tapes, which share the scope but not the prices |
| Whole-table polling fingerprint (`n_tup_*` on `Scheduler.Run`) | Service heartbeats every 15s make every open page rebuild: research pages ~every 15s, Scheduler pages ~every 20s | A narrower token (0.4-2.9ms, filtered `COUNT(*)` + `MAX`) must still catch Progress and Status without catching service beats |
| 78 KB of the 135 KB index page is duplicate inline JS (87 inline scripts, 33 distinct) | first load only | The fix is `dash.Dash._inline_scripts`, a private attribute Dash drains at index time. Not worth coupling the composition root to it |
| The "admin connect → create `Tests` → disconnect" block is copied in 5 test modules | — | One session fixture in `Tests/conftest.py` |
| The three drivers repeat `__init__`, `_driver_`'s name resolution, `_quote_` and the description mapping | ~100 lines | Only Postgres is proven against a live server. 1.6 touches the same `__init__`s — do both together |
| `_commission_`/`_swap_` carry a second conversion path (1/mid) that only tests reach | — | Production always passes `_conversions_(tick)`; making them required arguments deletes the fallback and the test that exercises it |
| `None` where `RULES.md` wants `MISSING` | — | `LoggingAPI.install(logger)`, `StorageAPI.attach(source, path)`, `BufferAPI(db)`, `find_caller_frame(skip)`, `MarketAPI.pull_bars(start, stop)`, `System._transition_(start)`, `_label_(suffix)`, `Strategy._emit_(raw)`, `Backtesting._stitch_(equity)`. Each needs its body read, not a blind swap |
| `Library/Statistic/Composition.py` wraps 21 calls across lines with several arguments each | — | `RULES.md` says one line or one name per line; mechanical but large |

---

## Phase 9 — Indicator connector

`Sources/Indicators/Connector` is the untouched cTrader indicator template today. This is what it becomes:
**a bridge that plots a Python-implemented indicator directly onto a cTrader chart, so it can be compared
against cTrader's own built-in by eye and by value.**

That makes it a **validation instrument, not a feature.** `Library/Indicator/Technical` is the input half
of every strategy in the framework — the DDPG feature bank alone is 16 indicators — and nothing has ever
proven those implementations agree with the platform's. A silent disagreement in, say, `ATR` or `ER` does
not crash anything; it quietly changes every observation the agent ever sees.

### 9.1 The bridge

Mirror the Robots connector rather than inventing a second mechanism: shared memory, single-slot
request/response lockstep, the same `Protocol` vocabulary. An indicator needs bars in and a series out,
with no orders, positions or account state, so the subscription is minimal. **`Script/Setup/Enum.py`
must emit into both projects** once this starts; `OUTPUT_PATH` is a single hardcoded path into the Robots
project today. The two `.algo` artefacts must always be generated from the same enum source, or the wire
mis-decodes exactly as it would between mismatched robot builds.

### 9.2 The comparison harness

The point of the phase, and worth designing before the bridge:

- Plot the Python series and cTrader's native equivalent on the same chart, and a **difference series**
  beneath. Eyeballing two overlapping lines hides small persistent offsets; a difference pane does not.
- Report the maximum absolute difference, and the bar index where it occurs, over the loaded range.
- **Warmup is where these will actually disagree.** A rolling indicator's first N bars depend on how the
  seed is chosen; a difference that vanishes after N bars is a warmup convention mismatch rather than a
  formula error. Report the two regimes separately or the diagnosis is wrong.
- Where the framework has no native counterpart, the comparison is against a hand-computed fixture
  instead, not skipped.

### 9.3 Coverage

Start with the DDPG feature bank, since those are the implementations carrying published results:
`ATR 14`, `ER 120`, `RV 16/480`, the `SMA` family and the `ROC` family. Then the rest of
`Library/Indicator/Technical`. Record each verdict — agrees, agrees after warmup, or disagrees with the
measured magnitude. **A disagreement is a finding, not a bug to rush.** Decide per indicator whether to
match the platform or document the difference — do not reflexively change an implementation the
published results depend on.

**Done when:** the connector plots any registered Python indicator on a cTrader chart beside its native
counterpart with a difference pane, and the feature-bank indicators each carry a recorded verdict.

---

## Phase 10 — Live trading panel at `/trading`

`Library/Web/Trading/Trading.py` is a 910-byte placeholder today. This phase replaces it with the console
the framework is actually for. It consumes almost everything above it: broker sessions and tokens come
from the credential store (1); per-tick updates need the Spotware session (2) and capture service (4) and
the batch protocol (5.9); order actions need the four target-volume actions (5.11); a non-EUR account
needs generic currency (5.4); a hedged account needs 5.5; surviving a restart needs 8.3; and the run and
result surfaces it links into come from 3.7.

### 10.1 The transport seam

Every other page either polls on a timer or renders an immutable artifact. **A live panel is neither.**
It needs push, and it needs to stay correct when push drops.

- Build on the Scheduler's existing listen, notify and wait seam rather than inventing a second one.
- **Connection count is a correctness budget, not a tuning knob.** A per-viewer subscription needs a hard
  ceiling and a return path — verify with a soak where `pg_stat_activity` plateaus.
- Degrade explicitly. If the push channel drops, the panel says so in the header and falls back to a slow
  poll — never silently shows stale prices as though they were live.

### 10.2 Account header

Balance, equity, margin used, free margin, margin level, unrealized P&L, and open exposure broken out by
currency. Equity and margin level update per tick; balance only on a closed deal. Margin level gets a
status treatment — good, warning, serious, critical — with an icon and a label, never colour alone.

### 10.3 Position and order blotters

Two virtualized `LightweightTableAPI` grids. **Positions:** symbol, side, volume, entry price, current
price, stop loss, take profit, swap, commission, spread paid (5.1), gross and net unrealized P&L,
duration, and the strategy that owns it; row actions modify stop and target, close partially, close
fully. **Orders:** symbol, side, type, volume, limit or stop price, expiry, state; row actions modify,
cancel. Both need a totals row computed server-side, not summed in the browser from a thinned payload.

### 10.4 Order ticket

Market, limit and stop, with the volume field driven by the **same** sizing path the engine uses — after
5.2 and 5.3 there is exactly one correct sizing formula and this ticket must call it. Show the derived
risk in account currency and as a percentage of balance before the button is armed. Stops and targets
accept pips or price, and convert visibly.

### 10.5 Strategy control and the kill switch

Which strategies are deployed, on which securities and timeframes, what state each Signal and Risk machine
is in, and how long since the last update. Per-strategy start, stop and flatten.

**The kill switch must work when everything else is degraded.** Flatten-all and disconnect must not depend
on the chart layer, the push channel, a payload having loaded — or the credential store being reachable at
that moment: the live session already holds its resolved token in memory, and the kill switch uses that
session. Confirm destructively, and log the outcome where `Run.log` will capture it even if the process
dies immediately after. Mutations are `Editor` and above through the existing router gate.

### 10.6 Live chart

One Lightweight chart per watched security: price, the open position with its entry, stop and target as
price lines, and fill markers as they arrive, with the live signal tape from 3.7 as its own pane. Reuse
`Library/Statistic/Workspace.py` for the spec, so the same definition serves the panel and the backtest
view.

### 10.7 Connection health

Connector state, last heartbeat, tick latency, ticks a second, reconnect count, the current subscription
per strategy, and the token's expiry from the credential store. The panel that answers "is it actually
running".

### 10.8 iPad

The whole panel is subject to 7.5, and more strictly: blotter rows need touch-sized targets, the order
ticket must be usable one-handed, and the kill switch must be reachable without a precise tap.

**Done when:** a Simulation deployment drives the full panel end to end — positions open and close, orders
fill and cancel, the account header tracks, the kill switch flattens — and then the same against a live
demo account, with the push channel deliberately severed mid-session to prove the degrade path.

---

## Phase 11 — Interactive Brokers provider

**Requested 2026-09-15.** A second broker adapter in the shape of Spotware, standalone, with no provider
base class (Appendix B). Its login lives in the credential store from the first line (rule 4). What it
changes, to be verified against its current documentation before design:

- **Transport.** Its API talks to a running Trader Workstation or IB Gateway process over a local socket,
  not a cloud endpoint. A provider that needs a desktop application alive is a different lifecycle, and the
  Scheduler service must supervise that dependency.
- **Multi-asset.** Stocks, futures, options and FX under one account. A security is a contract
  description, not a numeric id.
- **Historical pacing.** It documents strict limits on historical data requests — a poor bulk tick-history
  source and a good live-and-reference source.
- **Options chains and greeks.** One of the few retail-accessible sources for listed option chains, which
  is what makes this phase the data gate for Phase 12.

**Done when:** the provider fetches reference data, historical bars and a live stream for at least one
security per asset class it supports, with its own suite green.

---

## Phase 12 — Option strategy pricer and backtester

**Requested 2026-09-15.** A new asset class for the framework. **The data gate comes first:** cTrader lists
no vanilla options, so chains come from Bloomberg — already integrated — or from Interactive Brokers.
`Universe.Contract` already carries `Variant`, `Payoff`, `Strike`, `Maturity` and `Exercise`; the contract
model needs populating, not redesigning.

1. **The pricer.** Closed form where it exists (Black-Scholes for European equity-style, Black-76 on
   futures and forwards), lattices for early exercise (binomial or trinomial for American and Bermudan),
   an implied-volatility solver, the greeks, and a volatility surface built from observed chains. A
   multi-leg strategy is priced as the sum of its legs. Validate every model against a published reference
   value, not against itself.
2. **The backtester.** Very likely a **third engine**, a sibling of `RealtimeAPI` and `BacktestingAPI`. Its
   state is a chain and a surface evolving through time; its fills are per leg and per strike; and it must
   handle expiry, exercise and assignment. It should still reuse `Library/Portfolio`, `Library/Statistic`
   and `Workspace`.

A new top-level package when it starts, likely `Library/Derivative` or `Library/Option`, named and added
to `RULES.md` at that point.

**Done when:** the pricer reproduces reference values for European and American vanillas and their greeks,
and a multi-leg strategy backtests across at least one expiry cycle with exercise handled.

---

## Appendix A — Measured, do not re-derive

- **The stored tick tape is sampled by era — measured 2026-09-18 on `Market.TickReload`.** The minimum
  spacing between consecutive ticks, identical on all seven pairs:

  | Period | Minimum spacing | Ticks a month (EURUSD) |
  |---|---|---|
  | 2014-01 → 2016-02 | none — 1 ms gaps occur | ~60 000 |
  | 2016-03 → 2017-06 | **150 ms** | ~1.8 M |
  | 2017-07 → 2017-08 | none — 1 ms gaps occur | ~2.1 M |
  | 2017-09 → 2024-08 | **150 ms** | ~1.75 M |
  | 2024-09 → today | **300 ms** | ~1.35 M |

  One busy day (USDJPY, 192 258 ticks) has its 1st percentile gap at 150 ms and not one pair of ticks
  closer. Half the ticks change one side only; none repeats both sides; `Volume` is 1.0 on every tick; and
  every row reads `UpdatedBy = 'Autosave'`. The eras change on the same dates for every pair, which points
  at how cTrader's own tick store holds history — the store its backtester replays — rather than at the
  download; 2.4-A confirms it. It is the reason for rule 5 and for 2.4.
- **Performance.** Warm NNFX H1 year about 1.5 s; D1 ten years about 3.2 s; H1 ten years about 25 s.
  Learning frozen-tape replay about 3.12x a pass. Cold preload 12 to 15 minutes per ten-year dense-tick
  window. A dense day read from the compressed hypertable: 178 ms against 1274 ms from the plain table.
- **Dead ends, do not retry.** A numpy ring buffer for `SeriesAPI`; mypyc and Cython; a drain thread for
  the console and file sinks (a CPU-bound Python thread starves a concurrent writer 253 times over).
- **Logging cost.** Suppressed record 128 ns, emitted 1188 ns, timestamp 234 ns — down from 271, 4961 and
  1990.
- **The warmup window belongs in the cache key; the tick tape does not.** 0.7% of a rebuild depends on the
  window, 99.3% does not; `_tape_` caches `_acquire_frames_` on a window-free key.
  `OptimizationAPI._ordered_` keeps the cheap per-window rebuild consecutive — 192 EURUSD D1 candidates
  went 26.96 s to 19.09 s with identical scores.
- **Market data, audited 2026-08-25.** Seven majors — AUDUSD, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF,
  USDJPY — carry D1, H1, M1 and MN1 from 2014-01 to 2026-08, about 78k H1 and 4.6M M1 each. EURJPY and
  US500 have `Security` rows but no data; 1000 defined, 7 populated. Security ids: EURUSD 1, USDJPY 6,
  GBPUSD 11, USDCHF 16, AUDUSD 21, USDCAD 26, NZDUSD 31.
- **2016-01-11 to 2016-01-25 is absent in all seven pairs, ticks and bars, and is not repairable** through
  the cBot — proven 2026-08-25 by a re-download that visited the month and wrote zero rows. 2.4-A asks the
  Open API once; do not spend another cBot download on it.
- **Stored conversions are accurate across the whole history.** Implied cross rates track the real rate to
  within -0.001% to -0.009%, consistently bid-side, with zero static stretches. The cTrader "download
  historical data for additional symbols to convert profit/margin" option must stay **on** — with it off,
  the live cBot path freezes the cross-pair spot and the conversion goes stale.
- **Fee flags cannot reproduce broker terms — which is why every run pins `Contract.yml`.** `CommissionType.Amount` is
  a **flat** charge per trade, not per million, and `SwapType.Points` multiplies by `PointSize` where
  `Accurate` with `SwapMode.Pips` multiplies by `PipSize`, ten times apart on all seven majors.
- **Line endings are not mixed.** The working tree looks mixed, but `.gitattributes` carries
  `* text=auto eol=lf`, so the repository is uniform and the CRLF warnings on `git add` are checkout
  artifacts. `Sources/` builds warning-free in Debug and Release; the old `CA1416`/`CS0618` backlog is
  stale.
- **Postgres.** PostgreSQL 18 on Windows, service `postgresql-x64-18`, data directory
  `C:/Program Files/PostgreSQL/18/data`. `synchronous_commit = on` globally (never lose a committed
  trade). `shared_buffers` is deliberately 8 GB rather than the Linux 25% rule — on Windows large
  shared-memory segments are less effective and the OS file cache does the heavy lifting. For heavy
  connection scale use PgBouncer rather than raising `max_connections` further.

## Appendix B — Decided, do not re-litigate

| Decision | Rationale |
|---|---|
| Credentials are their own module, built on `Auth` | `Auth` authenticates people; the store decides what a person or a process acting for them may use. One-way dependency, like `Scheduler` on `Logging` |
| Credentials are stored in plain text, with `ViewRole`/`EditRole` thresholds | decided 2026-09-21. Database access already reads everything, so encryption and a master key buy nothing and cost a key to lose; the thresholds are a UI and bookkeeping control. Keeping secrets in the Windows Credential Manager instead would lose the page, the roles and the stamps |
| A run uses its task owner's credentials | permission to run is not permission to read. The starter is recorded as `Run.Auditor`, and a task's `EditRole` is a statement about who you trust with those credentials |
| The database logins stay in the drivers | the store lives in Postgres, so the Postgres login cannot come from it |
| `timestamptz`, with the server and every session pinned to `UTC`, converted at the driver | the column declares an absolute instant; the driver loads it back as naive UTC, so `RULES.md`'s one in-memory convention stands and every export stays byte-identical. Emitting aware datetimes framework-wide would touch every `utc_now()` caller, Polars dtype and CSV stamp for nothing the column type does not already give |
| The tick hypertable is partitioned on `UID` | keeps the primary key and the existing `UID`-range reads; one chunk per security-month |
| No shared provider base class until many providers pull genuinely different data | decided 2026-09-15; an attempt (`Library/Provider`, `ResultAPI`, `ServiceAPI._listen_`) was built and stripped because none of it had a production caller |
| `Auto` stays the default resolution and must equal `Tick` byte for byte | a lossless optimization; any divergence is a bug in `Auto` (5.0) |
| DB-first for 3.7, no CSV interim | the backend must be touched anyway to capture equity and signals |
| Weights in the DB as bytea, with `materialize()` | self-contained and atomic with results; nets are kilobytes to megabytes |
| Reuse the Scheduler executor, plus a `Task.Arguments` column | `ExecutorAPI` and `Runner` already own spawn, heartbeat leases, PID tracking, tree-kill, retry, peak RSS, reaping and log capture. `Research.Run` **references** a `Scheduler.Run` rather than reimplementing it, exactly as `Scheduler.Run` references `Logging.Log` |
| `Library/Research` owns the domain | parameter snapshots, result series, headline metrics and `KeptAt` are research concepts the Scheduler must not learn |
| Retention as a nullable `KeptAt` on the Run row | null means eligible for the 30-day sweep, set means retained with its full series |
| `UpdatedAt` and `UpdatedBy` stay on every datapoint | part of the `DatapointAPI` contract; removing them would have to be a `Library/Database` capability |
| Conversions rebuilt from full tick streams, not H1 bars | accuracy over convenience |
| `Library/Formulas` stays | the xlwings Excel UDF surface is to be renovated, not deleted |
| Paper-mapping docstrings stay | `Library/Model/Method/DDPG`, `SAC`, `TD3`, `Model/Core/Noise`, `Strategy/Model`, `Strategy/Hybrid/DDPG.py` including the reward-clipping comment in `Strategy/Model/Reward.py` |
| The search space lives in a sibling `Optimization.yml` | it cannot live in `Backtesting.yml`, whose list arity is **structural** — `RiskPercentage: [1.0]` unpacks with `self._risk_percentage_, = ...` |

## Appendix C — Renumbering, 2026-09-18

References written before this date resolve here. Phases 0 and 1 are done and live in the Done log; Phase 0's
session checklist and five runs (0.0, 0.1) moved into 5.13 on 2026-09-23.

| Before | Now | | Before | Now |
|---|---|---|---|---|
| 1.1 extension | Phase 3, done | | 2.13 | 5.11 |
| 1.1.1 index | closed (Phase 3, done) | | 2.14 | 5.12 |
| 1.1.2 | 3.1 | | 3.0, 3.0.1, 3.0.2 | done; the `.algo` check is 5.13 |
| 1.10 reload | built (Phase 3, done); swap 3.3 | | 3.1 | 2.4 |
| 1.2, 1.4 | done with the reload | | 3.2 | 2.3; its TLS point is 2.2 |
| 1.3 | 3.2 | | 3.3 | Appendix B |
| 1.5 | 3.5 | | 3.4 | 4.2 |
| 1.6 | 3.6 | | 3.5 | 4.1 |
| 1.7 | 3.8 | | 4.1 – 4.7 | 6.1 – 6.7 |
| 1.8 | 3.7 | | 4.8 | done (Phase 6) |
| 1.9 | 3.4 | | 5.1 – 5.7 | 7.1 – 7.7 |
| 2.0 | 5.0 | | 6.1 – 6.8 | 8.1 – 8.8 |
| 2.1 – 2.5 | 5.1 – 5.5 | | 7.1 – 7.3 | 9.1 – 9.3 |
| 2.6, 2.6.1, 2.6.3, 2.8 | done (Phase 5) | | 8.1 – 8.8 | 10.1 – 10.8 |
| 2.6.2 | 5.6 | | Phase 9 | Phase 11 |
| 2.7 | 5.7 | | Phase 10 | Phase 12 |
| 2.9 | 5.13 | | — | Phase 1 (new) |
| 2.10 | 5.9 | | | |
| 2.11 | 5.8 | | | |
| 2.12 | 5.10 | | | |