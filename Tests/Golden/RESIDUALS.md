# Golden runs — the record

> **Two halves, two engines. `Online/` and `Offline/` hold different things.**
>
> **`Online/`** is `Simulation` — `RealtimeAPI`, the Connector cBot launched from cTrader's Backtesting
> tab with Python mirroring cTrader's stream. `Realtime.py:277-302` unpacks `gross_pnl`,
> `commission_pnl`, `swap_pnl` and `net_pnl` **from the wire**, so those figures are cTrader's own and
> agreement on them is largely tautological. It gates the wire decode, the portfolio bookkeeping, the
> trade-to-deal aggregation and `Library/Statistic` — and it found three real defects in exactly those
> places.
>
> **`Offline/`** is `Backtesting` — `BacktestingAPI`, which reads its own tick tape from Postgres and
> computes its own fills, spread, commission, swap and sizing. This is the engine Phase 2 targets, the
> one `Optimization` and `Learning` run on, and the only half whose agreement with cTrader means
> anything. Run 2026-09-11 with the contract terms then frozen in `Contract.json`, verified unchanged
> since the online half; since 2026-09-17 each folder carries those terms as its own `Contract.yml`,
> which the gate pins.
>
> Compare `Offline/` against cTrader for accuracy. Compare either against itself across a change for
> regression.
>
> **`Online/*/net.csv` predates the 2026-09-11 `generate_net_report` fix** and still carries the four
> defects recorded below — aggregation disabled, holding time collapsed, the wrong drawdown denominator.
> Regenerating it needs a cTrader session, and `net.csv` is outside the gate, so the files stand as the
> evidence that found the defects rather than as corrected output. `Offline/*/net.csv` is post-fix, and was regenerated on 2026-09-17 for the redefinition of "Net Return (%)" as Σ NetPnL / opening balance (13 return and ratio rows changed; the four byte-gated exports replayed identically), and again the same day when every equity row moved onto per-column curves (Buy and Sell equity drawdown, volatility and ratios; the per-bar ratios and `Risk-free Rate (%)` rows added, 90 rows in all). No number below depends on those rows.

# The `Test` goldens — the cTrader session, 2026-09-29

The five folders under `Online/` and `Offline/` are now the `Test` strategy's; the `Trend` goldens
retired with this session and everything after this section records them (git history keeps their files). Each
`Online/Golden N` is the cTrader backtest as run (its `Run.json`, the parameters and contract terms it recorded, its
exports); each `Offline/Golden N` is `BacktestingAPI` on the same parameters and terms, and is what the gate replays.

| # | Symbol | TF | Window | Account | Balance |
|---|---|---|---|---|---|
| 1 | EURUSD | H1 | 2023 | EUR | 10 000 |
| 2 | EURUSD | H1 | 2023 | USD | 10 000 |
| 3 | GBPJPY | H1 | 2023 | CHF | 10 000 |
| 4 | AUDUSD | D1 | 2015-2025 | EUR | 10 000 |
| 5 | US500 | H1 | 2023 | EUR | 10 000 |

**How they were run, to run them again.** cTrader's Backtesting tab · the Connector cBot · strategy `Test` ·
leverage 1:100 · accurate commission on · swap on · "download historical data for additional symbols" on · the
description `Golden N`, which names the run folder. The live runs: Automate · EURUSD m1 · 30-40 minutes each,
market open, on the EUR netted and the EUR hedged demo account, with the override
`Overrides/Spotware(cTrader)/Forex(Major)/EURUSD/M1/Realtime.yml` (volume 10 000, wider stops and targets, SMA 5).
Rebuild both Connectors with cTrader's Build first whenever `Enum.cs` changes. Afterwards: re-run each CLI twin
with the run's own `Input/Parameters.yml` and `Input/Contract.yml`, and replay each live account's mirrored fills
through `ReplayAPI.book` against the broker's closing deals.

**The protocol has two rules the Trend runs never needed.** The offline twin starts on the cBot's first bar and
stops at its last bar's close (`Phase Warmup: First Bar` and `Phase Execution: Last Bar` in the online `Run.log`):
the cBot activates on its first *full* bar, one bar after the window's first, and ATR is a Wilder mean seeded
from the first bar loaded, so a one-bar offset left about 23 % of the seed gap at the first trade and moved the
first volumes (47 000 against 48 000 on run 1). Aligned, the first twelve entries of run 1 equal cTrader's stop
distance and volume exactly. And cTrader's "To" is inclusive: its last bar is the window's last day.

**The data are equal.** Every bar the cBot sent over the wire equals the tape's on every bar of all five runs,
eleven years of AUDUSD D1 included (open, high, low and close to half a point). The account currencies were
confirmed from each run's own report.

**Result, on the engine as it stands** (positions matched on open time and side; net P&L in the account currency):

| # | Positions | Same close | Trades identical (open, close, side, volume) | cTrader net | Offline net | Δ |
|---|---|---|---|---|---|---|
| 1 | 908 / 908 | 846 | 925 / 1 201 | −3 543.65 | −3 558.12 | −14.48 |
| 2 | 908 / 908 | 845 | 885 / 1 201 | −3 483.67 | −3 567.31 | −83.64 |
| 3 | 953 / 953 | 949 | 1 192 / 1 226 | −6 289.88 | −6 309.67 | −19.80 |
| 4 | 476 / 476 | 467 | 609 / 620 | −3 815.19 | −3 814.24 | +0.95 |
| 5 | 494 / 494 | 483 | 303 / 643 | −2 548.86 | −5 099.42 | −2 550.56, the minimum commission (finding 3) |

The engine rounds commission half up per deal like the live broker (decided 2026-09-29, Live 2 below), where the
backtester truncates: that moved run 1's commission from −19.48 to −29.80 against cTrader and is by design. Before
the change the net gaps were −5.26, −66.46, −12.10, −1.05.

Every position opens at the same time on the same side in both engines. Net is closed trades only.

**Findings.**
1. **Closes take the oldest fills first (fixed 2026-09-29).** cTrader books each closing deal against the lots
   that opened the position in time order — one trade per closing deal, its entry price the volume-weighted price
   of the lots it consumed and its entry time the first of them — while the position's own entry price stays the
   average of every fill (break-even after a scale-out moved the stop to 1.0567 on run 1, the average of three
   lots, not 1.056715, the remaining two). The engine had booked every close at the position's average: position
   totals were equal, the split between trades was not (run 4's position 64: 7 000 at 0.76003 then 6 000 at
   0.757805 in cTrader, both legs at 0.759 before the fix). Identical trades rose on every run (run 1 895 → 920,
   run 3 1 173 → 1 198). The live broker books the same way (Live 1 below).
2. **The average entry is exact (fixed 2026-09-29).** The engine rounded a position's average to five digits
   after every increase; the broker keeps it exact (Live 1: 1.137063 for 10 M at 1.13706 and 5 M at 1.13707, 50 USD
   on one deal).
3. **US500's minimum commission — cTrader's backtester omits it, the live server charges it; the engine keeps
   it.** The backtester charged 0.72 EUR per contract round trip (0.01 % of value, two sides, no floor); a
   one-contract round trip on the live demo server cost 7.04 EUR, 2 × 4 USD. Spotware's own forum answers say
   backtesting takes only a commission per million and, at the time, no percentage commission at all; nothing
   documents a minimum in backtesting. Without the minimum the offline twin lands 31.44 from cTrader's net and
   630 of 643 trades are identical; with it, the committed golden, −5 093.07.
4. **A strict stop trigger is not cTrader's rule.** Half the stops cTrader fired a tick later than we did fit
   "strictly beyond the level", but firing only then moved every run away from cTrader (run 3's equal closes
   947 → 835). `≤`/`≥` stays.
5. **Bounded: trigger-boundary exits.** 2-7 % of closes differ by a tick or a trailing step: cTrader's trigger level
   sits a few millionths below ours where both are known exactly (run 1, 2023-01-03 08:31:53.256: ask 1.05582,
   our trailing trigger 1.055822, cTrader moved at 08:31:54.139), and once a trailing path differs the position's
   later P&L and every later volume follow. Investigated on 2026-09-29 and closed as not fixable from the exports:
   every one of cTrader's 3 070 exit fills equals the tape's price at its millisecond, the cBot checks every tick
   with the same `≤`/`≥`, the stop distances agree to the tenth of a pip cTrader prints, and neither a strict
   trigger (run 3's equal closes 947 → 835) nor an unrounded opening stop (run 1's 846 → 813) comes closer — the
   level cTrader held lies in a band of a few millionths that no rounding rule produces.
6. **By design: commission follows the broker, not cTrader's backtester.** Before the broker rounding, cTrader's commission was a cent under ours where the exact value lands on a cent. 48 000 units: 4.32
   exact, cTrader 4.30; 46 000: 4.14 against 4.12; but 43 000 (1.935 a side) truncates to 3.86 in both. No
   candidate rule — the base route, the documented USD route on either side of the spread — matches more than
   half the single-leg positions; about −21 EUR of 3 912 on run 1.
7. **Swap is charged at 20:59 UTC all year, each night rounded half up (fixed 2026-09-29).** `SwapTime` 1259 is
   minutes after 00:00 UTC (the Open API's definition), not 16:59 New York: in winter the engine rolled an hour late,
   which positions closed at 21:00 UTC showed on every run (run 1, 2023-11-16 18:00 → 21:00:00.173: cTrader −7.21,
   ours 0). Each night's charge is rounded half up to the cent. Positions whose swap equals cTrader's to the cent,
   before → after: run 1 86/103 → 92/99, run 2 79/87 → 82/83, run 3 129/151 → 135/145, run 4 348/441 → 400/441,
   run 5 without the minimum 102/121 → 114/121. **What remains is cTrader's partial-close split**: the closed part
   books the remaining fraction of the swap and the remainder keeps it too (run 4, a 7 000 position closing 4 000:
   3/7 of the accrued swap on the close where 4/7 was accrued), so cTrader's trades do not sum to the swap it
   charged; the engine keeps the pro-rata split, as it keeps the minimum commission (finding 3).

**Speed** (cTrader: the time Python was attached to its backtest, a lower bound on cTrader's own; offline: a new
process, the database read included):

| # | cTrader | Offline | Faster | Trading loop only |
|---|---|---|---|---|
| 1 | 41 s | 6.1 s | 6.7× | 39.9 → 1.2 s (33×) |
| 2 | 40 s | 6.0 s | 6.7× | 38.9 → 1.1 s (34×) |
| 3 | 2 min 50 s | 9.0 s | 19× | 167 → 1.2 s (140×) |
| 4 | 11 min 43 s | 20.3 s | 35× | 701 → 1.0 s (730×) |
| 5 | 46 s | 5.0 s | 9× | 44.7 → 0.7 s (68×) |

**The live check — Live 1, the EUR netted demo account, 2026-09-28.** Fifteen closing deals before the cBot
stopped, every one reproduced to the cent from the broker's own fills: an exact volume-weighted average for
increases, a reduce closing at that average, gross converted at 1 / ask at the close. The run stopped on a
refused amendment (`InvalidRequest`): M1 at night gave a 0.27-pip ATR, so risk sizing hit the 10 M maximum with
stops inside the spread that the broker dropped, a scale-out filled at or above entry so break-even was skipped
and the armed target fired three more partial closes, and the second break-even repeated the first. Fixed: the
live override trades 10 000 units with 4 × ATR stops, and the scale-out target is disarmed with the partial close
(`NNFXStrategyAPI`, byte-neutral on every offline golden).

**Live 2, the EUR hedged demo account, 2026-09-29.** 41 minutes on both fixes, ten entries, no error and no refused
amendment: **12 of 12 closing deals equal the oldest-first replay of the broker's fills in volume, entry price and
gross to the cent**, through eight increases, six partial closes, four take-profit changes, fourteen stop moves,
a take profit and a stop loss. Two findings: the live server **rounds each deal's commission half up** (5 000 units:
0.225 → 0.23, the opening fee split 0.23 + 0.22 across two partial closes; a 20 000 position opened in three fills
paid 1.81, not 1.80) where the backtester truncates — the engine follows the broker since the same day; and the mirror stamps a closing deal with its position's open time,
not its lot's (the prices are the lots'). **Not exercised:** two positions open at once — on M1 with SMA 5 the bar
after every fourth entry brought a reversal that closed the hedge scenario's primary before its first step; Live 1
exercised the same-side add and the opposite reduce on the netted account, and every backtest exercised both.

**DDPG was re-baselined** for findings 1 and 2: it increases and partly closes positions constantly and its
observation reads the realised P&L, so its path moved (net 3 600.07 → 3 950.62). It is a self-consistency golden.

---

The five `Trend` runs defined in `PLAN.md` §0.1, their artifacts, and the measured residual against cTrader.
This file exists so the runs never have to be repeated. Each folder holds `Run.json`,
`Parameters.yml` and the five exports; `trades`, `positions`, `orders` and `deals` are the gated
files, `net.csv` is excluded from the gate by design.

Engine determinism is established: run 1 was executed twice on 2026-09-10 (19:03 and 19:10) and
reproduced to the cent on every aggregate.

## Protocol

Connector cBot inside cTrader's own Backtesting tab, strategy `Trend`, both Spotware demo accounts in
**Hedging** mode. Leverage 30, accurate commission, swap left on, and cTrader's "download historical
data for additional symbols to convert profit/margin" enabled. `--resolution` unset so auto-resolution
runs. The cBot's `Description` parameter carries the label into `Run.json`.

| # | Symbol | Timeframe | From | To | Account | Balance | Label |
|---|---|---|---|---|---|---|---|
| 1 | EURUSD | h1 | 2023-01-01 | 2024-01-01 | EUR | 10 000 | `Golden 1` |
| 2 | USDJPY | h1 | 2023-01-01 | 2024-01-01 | EUR | 10 000 | `Golden 2` |
| 3 | EURUSD | h1 | 2023-01-01 | 2024-01-01 | USD | 10 000 | `Golden 3` |
| 4 | USDJPY | h1 | 2023-01-01 | 2024-01-01 | EUR | 1 000 000 | `Golden 4` |
| 5 | EURUSD | Daily | 2015-01-01 | 2026-01-01 | EUR | 10 000 | `Golden 5` |

**Counting convention.** cTrader closes any position still open at the stop date and counts it, so its
"Total trades" is our closed trades plus the open one. Run 1: 1024 rows in `trades.csv` plus 1 row in
`positions.csv` equals the 1025 both sides report. `net.csv` already reconciles the two, which is why
its totals — not `trades.csv` alone — are what compare against cTrader.

## Run 1 — EURUSD h1 2023, EUR 10 000

Folder `Golden 1`, executed 2026-09-10T19:10:07, run uid `f05cfd64`.

Trade logic agrees with cTrader **exactly**. Every count, streak and extreme is identical:

| Metric | Ours | cTrader | Δ |
|---|---|---|---|
| Total trades | 1025 | 1025 | — |
| Long / Short | 513 / 512 | 513 / 512 | — |
| Winning trades | 514 | 514 | — |
| Losing trades | 511 | 511 | — |
| Max consecutive winning | 8 | 8 | — |
| Max consecutive losing | 12 | 12 | — |
| Largest winning trade | 366.53 | 366.53 | — |
| Largest losing trade | -135.28 | -135.28 | — |
| Max equity drawdown | 32.51% | 32.52% | 0.01pp |

Identical trade counts, streaks and extremes mean entries, exits, ordering and sizing all agree. The
residual is confined to money:

| Component | Ours | cTrader | Δ | Δ as % |
|---|---|---|---|---|
| Gross | 341.42 | 365.53 | **+24.11** | 6.6% of gross |
| Commission | -2 814.63 | -2 815.90 | -1.27 | 0.045% |
| Swap | -466.03 | -466.56 | -0.53 | 0.11% |
| **Net** | **-2 939.24** | **-2 916.93** | **+22.31** | 0.22% of opening balance |

cTrader's gross is derived as `net - commission - swap`; it is not reported directly.

**Gross, +24.11 — this is the open position, not a per-trade residual.** Read on its own it looks like
0.0235 EUR a trade, or 0.008 pips, and it was first recorded here as exactly that. The directional
decomposition in run 3 disproves it: the long side reconciles to the cent, the whole gap is short-side,
and it equals the open Sell position's mark-to-market gap precisely. See "The residual is one position,
not a per-trade bias" below.

**Commission, -1.27.** Accounted for: cTrader closes the final open position and charges the closing
side, 28 000 units at 45 per million is 1.26. Our export carries only that position's opening
commission. The agreement is therefore to about a cent over 31.4 M units of volume.

The naive figure — 31.409 M × 45 × 2 sides — is 2 826.81, and **both** engines come in below it
(2 814.63 and 2 815.90). cTrader quantises commission to the cent exactly as `truncate(x, 2)` at
`Backtesting.py:599` does. The `truncate` call is faithful, not a defect. It is worth re-checking on
run 2, where minimum-volume trades make the quantisation proportionally largest.

**Swap, -0.53.** Same cause as commission: cTrader carries the final position further.

## Defects found, both in `net.csv`

`net.csv` is outside the golden gate, so neither of these would ever be caught by it.

**1. `Max Balance Drawdown (%)` is wrong — 44.24% against cTrader's 31.64%**, and exceeds its own
equity drawdown (32.51%), which is impossible. **Root cause found, one line:**
`generate_net_report` sets `initial_balance = account.Balance`, which at report time is the *closing*
balance, not the opening one. `calculate_excursion` is correct — given the opening balance it returns
31.6415%, cTrader's figure exactly; given the closing balance it returns 44.2376%, which is what
`net.csv` prints. Fixed 2026-09-11 (`PLAN.md` §2.6.1 before the 2026-09-18 renumbering).

**2. Holding time is wrong whenever a position is open at the stop date.** `net.csv` reports avg 181.64
days for an H1 strategy inside one year where `trades.csv` gives avg 4.85 hours.
`calculate_holding_times` is correct; the report path hands it a frame with **no `ExitTimestamp`
column**, so every exit fills with the run stop. Reconstructed exactly. Fixed 2026-09-11 (§2.6.3 before the renumbering).

**3. The Aggregated half of `net.csv` silently degrades to a copy of Individual** whenever a position is
open — 85 of 85 rows identical in run 1, where the correct Aggregated trade count is 697 not 1025. The
concat takes the **intersection** of the trades and positions columns, `Position` is not declared on
`PositionAPI`, and `aggregate_items` returns its input unchanged without it. Fixed 2026-09-11 (§2.6 before the renumbering).

None of the three affects the gated files, so all are reporting defects rather than engine defects, and
the run 1 artifacts remain valid as a baseline.

## Run 2 — USDJPY h1 2023, EUR 10 000

Folder `Golden 2`, run uid `c9c939f3`. Window 2023-01-03 09:00:00 → 2023-12-29 09:15:08.

**All 709 trades sit at `VolumeMin` 1 000 — one distinct size, 100% at the floor.** Run 2 therefore
proves both engines clamp; it cannot validate raw sizing. `trades` equals `deals` at 709, so there are
no partial closes either and the scale-out path is untouched. Both facts are why run 4 exists.

| Metric | Ours | cTrader | Δ |
|---|---|---|---|
| Total trades | 710 | 710 | — |
| Long / Short | 355 / 355 | 355 / 355 | — |
| Winning trades | 313 | 312 | **1** |
| Losing trades | 397 | 398 | **1** |
| Max consecutive winning | 12 | 12 | — |
| Max consecutive losing | 13 | 13 | — |
| Largest winning trade | 4.19 | 4.19 | — |
| Largest losing trade | -4.83 | -4.83 | — |
| Average trade | -0.0855 | -0.08 | — |
| Profit factor | 0.8808 | 0.88 | — |
| Max balance drawdown | 0.83% | 0.82% | 0.01pp |
| Max equity drawdown | 0.83% | 0.84% | 0.01pp |

| Component | Ours | cTrader | Δ |
|---|---|---|---|
| Gross | 2.63 | 1.33 | **-1.30** |
| Commission | -56.76 | -56.79 | -0.03 |
| Swap | -6.58 | -6.88 | -0.30 |
| **Net** | **-60.71** | **-62.34** | **-1.63** |

**The gross residual changes sign.** Run 1 had cTrader higher by 24.11; here it is lower by 1.30. A
systematic error would keep its sign, so this is the sub-pip exit residual behaving as noise. Per
trade: 1.30 / 710 = 0.0018 EUR, and at 1 000 units a USDJPY pip is about 0.065 EUR, so **0.028 pips**
— larger than run 1's 0.008 pips, as expected on the 3-digit contract, and still well under a pip.

**The one-trade classification gap is the same residual.** No trade has a net of exactly zero, and our
smallest absolute net is -0.01. One trade sits inside the sub-pip band and lands on opposite sides of
zero in the two engines, moving it between the winning and losing counts. Not a logic difference.

**Commission settles the `truncate` question — it is faithful.** At 1 000 units a side is
`1000 × 45/1e6 = 0.045`, which `truncate(x, 2)` makes 0.04, an 11% reduction, and the naive figure for
the run would be 63.81. Ours is 56.76, which is exactly `709 × 2 × 0.04` plus the open position's
0.04 opening side. cTrader reports 56.79 against `710 × 2 × 0.04 = 56.80`. **cTrader quantises to the
cent identically.** `Backtesting.py:599` reproduces the platform and must not be changed.

**`Max Balance Drawdown (%)` is correct here.** 0.83% against cTrader's 0.82%, and correctly below the
equity drawdown. Run 1 had it at 44.24% against 31.64% and *above* its own equity drawdown. The
difference between the two runs is partial closes: run 1 has them (1024 trades over 696 deals), run 2
has none (709 over 709). **The balance-series defect is in how a partial close is recorded**, which is
a far narrower lead than run 1 alone gave.

## Run 3 — EURUSD h1 2023, USD 10 000

Folder `Golden 3`, run uid `29a2dc35`. The `account == quote` branch, which no golden had ever reached.

Same 1024 trades and the same window as run 1, so the trade logic is currency-independent as it should
be. Every count, streak and extreme matches cTrader, including the long/short split of the extremes
(largest win 381.12 long and 297.90 short; largest loss -115.82 long and -146.85 short).

| Component | Ours | cTrader | Δ |
|---|---|---|---|
| Gross | 300.73 | 326.38 | -25.65 |
| Commission | -3 003.98 | -3 005.32 | 1.34 |
| Swap | -493.92 | -494.48 | 0.56 |
| **Net** | **-3 197.17** | **-3 173.42** | **-23.75** |

**`account == quote` is correct.** The long side reconciles to the cent in USD — gross 333.06,
commission -1 499.18, swap -471.37, net -1 637.49, all exact. The conversion topology this run exists
to test passes.

## The residual is one position, not a per-trade bias

Decomposing all three runs by direction settles it. **The long side matches cTrader to the cent on
gross, commission, swap and net, in every run.** The entire discrepancy is short-side:

| Run | Long net (ours / cTrader) | Short net (ours / cTrader) | Short Δ |
|---|---|---|---|
| 1 | -1 525.35 / -1 525.34 | -1 413.89 / -1 391.59 | -22.30 |
| 2 | -11.25 / -11.25 | -49.46 / -51.09 | 1.63 |
| 3 | -1 637.49 / -1 637.49 | -1 559.68 / -1 535.92 | -23.76 |

The cause is the single position left open at the stop date, which is a **Sell** in all three runs, so
it lands entirely in the short column:

| Run | Open position | Our mark (gross) | cTrader implied | Δ | Short gross Δ |
|---|---|---|---|---|---|
| 1 | Sell 28 000 @ 1.10473 | 2.53 | 26.64 | 24.11 | 24.11 |
| 2 | Sell 1 000 @ 141.001 | 0.53 | -0.77 | -1.30 | -1.30 |
| 3 | Sell 27 000 @ 1.10473 | 2.70 | 28.35 | 25.65 | 25.65 |

The open position's discrepancy equals the short gross discrepancy **exactly**, in all three runs. So
every closed trade, long and short, agrees with cTrader to the cent, and the only thing that differs in
the entire comparison is how the still-open position is valued.

**Cause.** All three positions were entered 2023-12-29T16:00:00 while the backtest window runs to
2024-01-01. cTrader closes an open position at the final tick of the window; we mark it earlier. Run 1
implies cTrader marks about 9.5 pips further along than we do. The short commission Δ (1.27, 0.03,
1.34) and swap Δ (0.54, 0.30, 0.55) have the same cause — cTrader charges the position's closing side
and carries its swap to the end of the window.

**This supersedes the sub-pip reading recorded for runs 1 and 2.** Aggregate gross differences of
24.11 and 1.30 looked like a per-trade residual that changed sign; the directional decomposition shows
they are one position each. There is no measurable per-trade exit residual in these runs.

Item for Phase 2: value the position open at the stop date at the final tick of the window, and charge
its closing commission and full swap, so the two engines agree on the last mark as well.

## Balance drawdown, three runs in

| Run | Ours | cTrader | Partial closes? |
|---|---|---|---|
| 1 | 44.24% | 31.64% | yes — 1024 trades / 696 deals |
| 2 | 0.83% | 0.82% | no — 709 / 709 |
| 3 | 49.59% | 34.26% | yes — 1024 / 696 |

The defect appears only where partial closes exist, and where it appears the value also exceeds our own
equity drawdown, which is impossible. Equity drawdown matches cTrader in all three runs (32.51/32.52,
0.83/0.84, 35.18/35.18), so the equity series is right and the balance series is not. **The defect is
in how a partial close is written to the balance series.**

## Run 4 — USDJPY h1 2023, EUR 1 000 000

Folder `Golden 4`, run uid `dd8cd8e3`. The run that decides item 2.2.

**Run 4 does not decide item 2.2, and it corroborates the defect rather than clearing it.** In
`Simulation` the volume is computed by *our* sizer and sent to cTrader to execute, so agreement on
volumes is tautological exactly as it is for fees — cTrader executes what it is given. What run 4 does
show is the distribution: at a million the `VolumeMin` clamp stops binding and **68 distinct volumes
from 5 000 to 81 000 appear, only 4 of 1017 at the floor**, against run 2's single clamped size.

Those magnitudes are consistent with §5.2's diagnosis. At `RiskPercentage` 1.0 on a 1 000 000 balance,
a genuine 1% risk with a stop of roughly 50 pips on USDJPY implies volumes in the millions of units;
the sizer produced tens of thousands, two orders of magnitude smaller, which is the `1/price` factor
§5.2 predicts. **Item 5.2 still stands and still needs fixing.** Deciding it requires a
`BacktestingAPI` run where our sizer's output can be checked against intended risk directly, not a
`Simulation` run where cTrader merely executes our number.

| Metric | Ours | cTrader |
|---|---|---|
| Total trades | 1018 | 1018 |
| Long / Short | 514 / 504 | 514 / 504 |
| Max consecutive winning / losing | 12 / 14 | 12 / 14 |
| Largest winning trade | 162.46 | 162.46 |
| Largest losing trade | -104.66 | -104.66 |
| Profit factor | 0.7872 | 0.79 |

| Side | Component | Ours | cTrader | Δ |
|---|---|---|---|---|
| long | gross | -38.74 | -38.74 | — |
| long | commission | -986.72 | -986.72 | — |
| long | swap | -61.51 | -61.51 | — |
| long | **net** | **-1 086.97** | **-1 086.97** | **—** |
| short | gross | -1 099.98 | -1 129.52 | -29.54 |
| short | commission | -1 011.90 | -1 012.84 | 0.94 |
| short | swap | -179.52 | -186.29 | 6.77 |
| short | net | -2 291.39 | -2 328.65 | 37.26 |

The long side reconciles exactly for the fourth time. The open position is again a Sell — 23 000 @
141.001 — and our mark values its gross at 12.11 against cTrader's implied 41.65, a gap of **29.54 that
equals the short gross gap exactly**. The pattern from runs 1-3 holds without exception.

## Balance drawdown — the partial-close hypothesis was wrong

Run 4 has partial closes (1017 trades over 709 deals) and its balance drawdown is **correct**. The real
cause is the denominator, and it is now pinned:

| Run | Absolute DD | Initial | Peak balance | abs / peak | Ours % | cTrader |
|---|---|---|---|---|---|---|
| 1 | 3 267.67 | 10 000 | 10 327.15 | **31.64%** | 44.24% | 31.64% |
| 2 | 82.26 | 10 000 | 10 016.37 | **0.82%** | 0.83% | 0.82% |
| 3 | 3 544.35 | 10 000 | 10 345.82 | **34.26%** | 49.59% | 34.26% |
| 4 | 3 637.23 | 1 000 000 | 1 000 064.26 | **0.36%** | 0.36% | 0.36% |

**`absolute / peak balance` reproduces cTrader exactly in all four runs.** Our absolute figure is
therefore right and only the percentage is wrong — it divides by something else. The error scales with
the ratio of drawdown to balance, so it vanishes when the drawdown is small (runs 2 and 4, both under
1%) and reaches 40% relative error when the drawdown is large (runs 1 and 3, both over 30%). That is
why it looked like a partial-close effect: runs 1 and 3 happen to have both properties.

Equity drawdown matches cTrader in all four runs, so only the balance percentage is affected.

## Holding time — the function is correct, the reporting path is not

`calculate_holding_times` at `Portfolio/Statistic.py:348` computes `exit - entry` per row and, called
directly on run 1's `trades.csv`, returns **max 3.67 days, avg 0.20 days, min 0** — which matches a
manual computation exactly and is right for an H1 strategy.

`net.csv` for the same run reports **max 360.71, avg 181.64**. So the defect is in what reaches the
function in the report path, not in the function itself. The `fill_null(stop_dt)` branch on
`ExitTimestamp` is the obvious suspect, since filling every exit with the stop date would produce
durations of exactly this shape, but `trades.csv` has zero nulls in that column, so the frame the
report passes is not the one exported. **The earlier note that holding time is "measured from a fixed
origin" was a guess and is withdrawn** — the mechanism is unconfirmed, the symptom is not.

## Run 5 — EURUSD Daily 2015-2026, EUR 10 000

Folder `Golden 5`, run uid `77dd4367`, executed labelled `Golden 4`. Window 2015-02-12 → 2025-12-17,
510 trades over 359 deals, volumes 1 000-14 000 across 14 distinct sizes.

**`positions.csv` is empty — no position was open at the stop date.** That makes run 5 the control for
every hypothesis the other four runs raised, and it is an exact match on every figure:

| Component | Ours | cTrader | Δ |
|---|---|---|---|
| Gross | -546.35 | -546.35 | — |
| Commission | -235.12 | -235.12 | — |
| Swap | **-1 198.88** | **-1 198.87** | — |
| **Net** | **-1 980.35** | **-1 980.34** | **—** |
| Long net | -1 653.40 | -1 653.40 | — |
| Short net | -326.95 | -326.94 | — |

Counts and extremes match as in every other run: 510 trades, 258/252 long/short, 242/268 winning and
losing, streaks 6 and 10, largest win 123.66, largest loss -101.22, and the same long/short split of
each. Profit factor 0.7685 against 0.77.

### What run 5 proves

**The residual in runs 1-4 was entirely the open position.** Remove it and the two engines agree to the
cent on gross, commission, swap and net, long and short, over eleven years.

**The old accuracy floor is unverified, not disproven.** Swap is the dominant cost here — -1 198.88
against -235.12 of commission — and it matches to the cent over eleven years, as does gross across 510
trades. But both figures arrive over the wire from cTrader, so the match measures the bookkeeping that
carries them, not a fill or fee computation. The "sub-pip intrabar exit residual, ~0.5%/y swap
residual" note can only be tested against `BacktestingAPI`, which none of these runs exercise.

**Holding time is correct here** — 5.4848 days reported against 5.485 measured — which is what pinned
the defect below.

## The two `net.csv` defects, both now diagnosed

**Holding time — confirmed mechanism.** `calculate_holding_times` is correct; the report path passes it
a frame with **no `ExitTimestamp` column** whenever an open position exists, so `exits` becomes the run
stop date for every row and holding time collapses to `stop - entry`. Proven by reconstruction on run 1:
dropping the column yields max 363.71 / avg 184.82 against the 2024-01-01 argument, and using the run's
real stop of 2023-12-29 gives **max 360.71, avg 181.64, min 0** — exactly what `net.csv` reports,
including the zero minimum, which arises because the last entry is later than the stop and clips.
Run 5 has no open position and reports correctly. Runs 1-4 each have one and report wrongly.

**Balance drawdown — confirmed denominator.** `absolute / peak balance` reproduces cTrader on every run:

| Run | Absolute DD | Peak balance | abs / peak | Ours % | cTrader |
|---|---|---|---|---|---|
| 1 | 3 267.67 | 10 327.15 | 31.64% | 44.24% | 31.64% |
| 2 | 82.26 | 10 016.37 | 0.82% | 0.83% | 0.82% |
| 3 | 3 544.35 | 10 345.82 | 34.26% | 49.59% | 34.26% |
| 4 | 3 637.23 | 1 000 064.26 | 0.36% | 0.36% | 0.36% |
| 5 | — | — | — | 26.63% | 21.43% |

The absolute figure is right; only the percentage divides by the wrong quantity. Equity drawdown
matches everywhere (run 5: 21.84% against 21.92%).

## Contract terms are a hidden input — freeze them

`Universe.Contract` holds `SwapLong`/`SwapShort` as **current** broker values, and they drift. Worse,
`UpdatedBy` on the EURUSD and USDJPY rows reads **`Autosave`** with timestamps matching the start of
runs 4 and 5 — **every cBot run overwrites the row**, so the values a golden used are not recoverable
from the database afterwards.

This is not confined to the swap column. Sizing is `SizingMode: Risk` at `RiskPercentage: 1.0`, a
percentage of **balance**, and swap feeds balance. A changed swap rate therefore moves every volume and
every number downstream, not just `SwapPnL`. Runs 1 and 3 demonstrate the mechanism: identical trades
in different account currencies produced different volumes (59 against 61 distinct) purely because the
balance differed.

The terms in force were frozen in `Contract.json` until 2026-09-17, when each golden folder took its
own `Contract.yml` and the gate began replaying with `--contract`. A golden replayed against a drifted
`Universe.Contract` row without that pin will not reproduce.
---

# The offline half — `BacktestingAPI` against cTrader

Run 2026-09-11, five `Backtesting` runs on the same configurations, `--resolution` unset so
auto-resolution runs, fees left on `Auto` so they resolve to `Accurate` against the contract terms in
`Contract.json` (verified unchanged from the online half before running).

**This is the first measurement of the offline engine against cTrader that has ever been taken.**

| Run | Offline net | cTrader net | Δ | Δ as % of net |
|---|---|---|---|---|
| 1 EURUSD H1 EUR 10k | -2 815.54 | -2 916.93 | +101.39 | 3.5% |
| 2 USDJPY H1 EUR 10k | -58.40 | -62.34 | +3.94 | 6.3% |
| 3 EURUSD H1 **USD** 10k | -2 299.58 | -3 173.42 | **+873.84** | **27.5%** |
| 4 USDJPY H1 EUR 1M | -3 313.99 | -3 415.62 | +101.63 | 3.0% |
| 5 EURUSD D1 EUR 11y | **-1 981.27** | **-1 980.34** | **-0.93** | **0.05%** |

## Re-baselined 2026-09-15 — the engine was reading Float32 prices

**The table above was measured on corrupted inputs, and the `Offline/` exports now hold the corrected
run.** `DataframeAPI.frame` ended with `shrink_dtype()` on every column, which silently downcast
`Float64` to `Float32` and integers to `Int8`. Every database read goes through it, and the preload
tape cache stored its intra-bar frames that way (`intra_H1.parquet`, `intra_M1.parquet`: every tick
price and conversion `Float32`). Proven both ways: restoring the downcast reproduces the old exports
byte for byte, and removing it plus a cache format bump (`BacktestingAPI._CACHE_FORMAT_`, so stale
tapes are rebuilt instead of read) produces the new ones, which a warm rerun reproduces byte for byte.

A pip size of `1e-05` became `9.99999974737875e-06`, which is why `Points` read `151.000003814571` for a
151-point move. On USDJPY it went further: a price near 134.718 carries too few significant digits in
`Float32` to resolve a 0.001 tick, so intra-bar targets were compared against the wrong price and
exits moved — golden 4 now closes 1 017 trades, not 1 018.

| Run | Offline net (Float32) | Offline net (Float64) | cTrader net | Δ before | Δ now |
|---|---|---|---|---|---|
| 1 EURUSD H1 EUR 10k | -2 815.54 | -2 814.49 | -2 916.93 | 101.39 | 102.44 |
| 2 USDJPY H1 EUR 10k | -58.40 | **-62.10** | -62.34 | 3.94 | **0.24** |
| 3 EURUSD H1 **USD** 10k | -2 299.58 | -2 293.90 | -3 173.42 | 873.84 | 879.52 |
| 4 USDJPY H1 EUR 1M | -3 313.99 | **-3 402.28** | -3 415.62 | 101.63 | **13.34** |
| 5 EURUSD D1 EUR 11y | -1 981.27 | -1 981.27 | -1 980.34 | -0.93 | -0.93 |

**Both USDJPY runs moved toward cTrader, by 16× and 7.6×.** Runs 1 and 3 did not move materially:
their gaps are the open position, the descend gate and the account-currency conversion diagnosed
below, none of which a dtype touches. Run 5 is Daily and moves only in the fifth decimal
(-1 981.271972 → -1 981.272019). The Δ columns are offline minus cTrader, so run 5's is negative where
runs 1-4 are positive: it is the only run that lands below cTrader. The sections below were written
against the `Float32` runs; their mechanisms stand, but any tick count or exit count they quote belongs
to the old exports. The old exports are preserved in git at commit `578c9a5`.

`Offline/Golden 1-5/Run.json` still carries `StartedAt` 2026-09-11: the manifests and `Parameters.yml`
are from the original runs, while the five exports are from the 2026-09-15 rerun with identical
parameters.

**Run 5 is the result to read first.** Eleven years, 512 trades, swap the dominant cost, and the
offline engine lands **0.93 EUR** from cTrader — 0.009% of the opening balance. Its components:
gross -531.52 against -546.35, commission -235.98 against -235.12, swap **-1 213.78 against
-1 198.87**. The swap gap is 1.24% over eleven years, about **0.11% a year**, which is the first
honest measurement of the figure the old note put at ~0.5%/y.

## The divergence has one shape: entries agree, exits do not

Every first divergence, in all five runs, is on `ExitTimestamp` and `ExitPrice` with
`EntryTimestamp`, `Direction`, `Volume` and `EntryPrice` identical.

**Run 2 isolates it** because every volume is clamped at `VolumeMin`, so sizing cannot drift with
balance and the two paths stay aligned:

| | |
|---|---|
| Identical entry timestamps | **709 / 709** |
| Identical exit timestamps | **703 / 709** |
| Identical exit prices | **703 / 709** |
| Exit price gap | median **0.000 pips**, mean 0.078 |
| Trades off by more than 5 pips | **1** |

**99.2% of exits are exact.** Six differ, one badly, and that single trade carries essentially the
whole gross gap (5.96 against 2.10).

**The other runs are not like-for-like comparisons.** The divergence is path-dependent: one different
exit changes the balance, which changes the next volume, which changes every subsequent decision. Run 1
keeps only 473 of 1024 identical entry timestamps after diverging at trade 2. Only run 2 stays aligned,
and only because clamping makes sizing balance-independent.

## The failing case, diagnosed

Run 2, trade 236. Sell USDJPY entered 2023-05-10 14:00:00.217 at 134.397.

| | |
|---|---|
| cTrader exit | 14:35:11.798 at **134.724** |
| Offline exit | 18:40:09.578 at 134.178 |
| Difference | 4h05m late, 54.6 pips |

The hour 14:00-15:00 holds **9 337 ticks** with a maximum bid of **134.718**. A Sell exits at the ask,
and 134.718 plus the spread is 134.724 — exactly cTrader's exit. So cTrader stopped the position out at
the intrabar high, the offline engine did not, and it rode the position to a profit four hours later.

**The tick is in the tape.** This is not missing data. The stop comparison itself is correct —
`Backtesting.py:799` tests a Sell stop against the **ask**. The fault is upstream, in the
auto-resolution gate.

`_intrabar_source_` (`Backtesting.py:1007`) only walks a bar's interior when
`_should_descend_(bids, asks)` passes; otherwise the bar is **skipped whole** and none of its ticks are
examined. `_should_descend_` decides from the bar's four OHLC bid and ask values plus a spread pad. A
bar whose stored high ask under-represents the true maximum ask inside it therefore fails the test, and
an armed stop that the tape could have triggered is never checked.

Next step is to instrument the gate on this exact bar: log the bar's `HighTick.Ask`, the pad, and the
position's armed stop, and compare against the maximum ask over the 9 337 ticks. Do not change the gate
before that measurement — it is also the mechanism that makes auto-resolution fast.

## Run 3 is the outlier, and it is the account currency

27.5% off, far worse than any other run, on the `account == quote` branch. Its volumes run 6.3% above
the online half (32.926M against 30.967M) where run 4's match to 0.01%.

`_conversions_` (`Backtesting.py:494`) reads `tick.BidBaseConversion` and `tick.BidQuoteConversion`
**unconditionally**, falling back to a computed value only when they are null. Those stored columns are
**EUR-denominated**. A USD account therefore reads EUR conversions and scales its P&L and its sizing by
the wrong factor.

This is direct empirical support for dropping the hardcoded conversion columns from the `Tick` table
(`PLAN.md` §3.6) and for the generic account currency work (§5.4). It is the largest single accuracy defect
the golden set has found.

## Structural notes

**Runs 1, 3, 4 and 5 each produce one or two more closed trades offline than online**; run 2 produces
exactly the same number. Run 2 is the only run with no partial closes (709 trades over 709 deals), so
the extra split is in the scale-out path.

**Run 5's volumes** are 2.6460M against 2.6400M with 14 distinct sizes on both sides — 0.23% apart over
eleven years, which is the closest sizing agreement in the set.

## The switch — 2026-09-25

The engine moved to the UTC tape (`PLAN.md`, Done log, Phase 3), and the offline goldens tripped, as rule 2
of the plan expects. Every number below is from a fresh run of the switched code with each golden's own
`Parameters.yml` and `Contract.yml`, compared with cTrader's own result for the same run
(`Online/Golden N/trades.csv`, closed trades only, so the open position of 5.6 is outside all three columns).

| Run | cTrader | Before | After | Gap before | Gap after | Trades matching cTrader, before → after |
|---|---|---|---|---|---|---|
| 1 EURUSD H1 EUR | -2 940.52 | -2 836.06 | **-2 946.19** | +104.46 | **-5.67** | 584 → **924** of 1 024 |
| 3 EURUSD H1 USD | -3 198.53 | -2 317.01 | **-3 187.25** | +881.52 | **+11.28** | 154 → **905** of 1 024 |
| 5 EURUSD D1 EUR | -1 980.35 | -1 981.27 | -1 999.51 | -0.92 | -19.16 | 482 → 484 of 510 |
| 2 USDJPY H1 EUR | -61.20 | -61.12 | **-61.17** | +0.08 | **+0.03** | 704 → 702 of 709 |
| 4 USDJPY H1 EUR 1 000 000 | -3 389.54 | -3 379.80 | **-3 386.28** | +9.74 | **+3.26** | 1 010 → 1 006 of 1 017 |
| DDPG consistency | | +3 344.09 | +4 387.29 | | | self-consistency only |

"Matching" is by direction, entry price, exit price and volume in order — timestamps cannot be compared,
because the online files carry the London-local stamps of the pre-2026-09-11 decoder. Trade counts now
equal cTrader's on all three runs (1 024, 1 024, 510), where the old engine closed one or two more.

**What moved them, in the order it was found.**

1. **The two-sided bar.** The gate that decides whether to walk a bar's ticks, and the equity marks, read
   `HighTick.Ask` — the ask at the tick where the bid peaked, not the highest ask. The bar now carries both
   (`HighPoint.AskTick`, `HighPoint.BidTick`), and the gate reads the true bounds with no pad: `Auto` and
   `Tick` give byte-identical exports on runs 1, 3 and 5. This is the run 2 trade-236 defect above, fixed
   by construction. It moved runs 1 and 3 most.
2. **Swap at the 17:00 New York roll.** The rollover hours (`SwapSummerTime` 22, `SwapWinterTime` 21 with
   European daylight saving) were tuned while every stamp was London time. Read in UTC they charged an
   extra night on trades opened just after 17:00 New York — the first switched run 5 read -1 329.40 of
   swap against cTrader's -1 198.88. Counting New York rolls brought it to -1 213.65, the same
   -14.8 residual as before (each night is converted at the exit rate, not the night's own).
3. **Run 5's old agreement was a cancellation.** Before, gross was +14.83 off and swap -14.90; now gross is
   -4.33 off and swap -14.77. The net moved away from cTrader while both components got better or stayed.
4. **Run 3's 27.5 % gap is gone.** The section above traced it to EUR-denominated conversion columns read
   by a USD account; the switch dropped those columns and rebuilds conversions at run time from the pair's
   own quotes.
5. **UTC stamps and the platform's labels** move every summer timestamp by an hour and every bar label to
   the bar's own open. They change no price path on these runs.

**Runs 2 and 4, measured 2026-09-28** once the refill put EURJPY on the tape: both replay, and both moved
closer to cTrader (gross 2.35 against 2.10 and -1 152.54 against -1 150.83; commission -56.71 against -56.72 and
-1 989.09 against -1 997.68; swap -6.81 against -6.58 and -244.65 against -241.03). Run 1 replayed the same day
at -2 946.19, exactly the figure above, so nothing in the engine moved between the two measurements.

**Carry to 6.13.** Re-baseline all five pairs of runs in one cTrader session. The run 1 and 3 remainders (-5.67 and +11.28) and run 5's swap residual are the
expected starting points.

## Phase 6 — the offline half re-baselined, 2026-09-28

The engine changes of Phase 6 are in, and the offline goldens, the DDPG self-consistency golden and a new
**Golden 6** were regenerated on them, each with its own pinned `Parameters.yml` and `Contract.yml`.
`pytest Tests/Golden --golden` replays all seven byte for byte again (with the in-process sequence test and
the account-currency matrix, 10 passed). **The online half is not regenerated:** the cBot runs the same Python
strategies, so its sizing moved with this change too, and the pairs are re-run together in the cTrader
session (2026-09-29, above). Until then, compare a closed trade with cTrader only on run 3, whose sizing did not
move. "Before" below is a fresh run of the code as it stood this morning.

| Run | Trades | Closed-trade net | Open position net | `net.csv` net | Max equity drawdown % | Distinct volumes | Swap |
|---|---|---|---|---|---|---|---|
| 1 EURUSD H1 EUR | 1024 → 1024 | -2 946.19 → -3 200.55 | 25.38 → 25.27 | -2 920.81 → -3 175.28 | 33.37 → 35.23 | 60 → 65 | -461.21 → -491.59 |
| 2 USDJPY H1 EUR | 709 → 1017 | -61.17 → -4 173.69 | -0.80 → -23.80 | -61.96 → -4 197.49 | 0.88 → 43.88 | 1 → 69 | -6.81 → -291.03 |
| 3 EURUSD H1 USD | 1024 → 1024 | -3 187.25 → -3 187.25 | 27.01 → 25.10 | -3 160.24 → -3 162.14 | 35.84 → 35.11 | 59 → 59 | -490.19 → -490.75 |
| 4 USDJPY H1 EUR 1 000 000 | 1017 → 1017 | -3 386.28 → -420 938.00 | -18.36 → -2 410.48 | -3 404.63 → -423 348.48 | 0.37 → 44.25 | 68 → 786 | -244.65 → -29 507.85 |
| 5 EURUSD D1 EUR | 510 → 510 | -2 000.00 → -2 244.25 | -0.54 → -1.18 | -2 000.54 → -2 245.43 | 22.05 → 25.07 | 14 → 14 | -1 213.65 → -1 358.77 |
| 6 GBPJPY H1 **CHF** (new) | 1052 | -5 224.66 | 22.37 | -5 202.29 | 54.82 | 41 | -275.78 |
| DDPG consistency | 1076 → 1051 | +4 327.32 → +3 600.07 | -4.16 → -5.30 | +4 323.16 → +3 594.77 | 24.53 → 34.35 | 53 → 60 | 0 |

**What moved each run, and why.**

1. **Risk sizing through the quote conversion (6.2)** moved every account that is not the quote currency — runs
   1, 2, 4, 5, 6. The risk amount is in the account currency and the stop distance in the quote currency; the
   volume is now `amount / (stop × pip × quote-to-account rate)`, so a trade risks the configured 1 % on every
   pair. On USDJPY with a EUR account the old sizing risked 0.0067 %: run 2 traded the 1 000-unit floor 709
   times with one distinct volume and lost 0.6 % of the account; at a true 1 % the same Trend strategy loses
   42 %, and run 4 has the full volume distribution (786 distinct volumes) that it exists to cover. Run 3 (USD
   account, the quote) is the control: its closed trades are identical, so its gap to cTrader stays **+11.28**.
2. **The open position is settled at the stop (6.6).** It was already marked at the final tick offline (run 1's
   gross 26.64 is cTrader's implied 26.64); it now also pays its closing commission and the swap of every roll
   up to `--stop`. Run 3: commission -1.34 → -2.68 and swap 0 → -0.57, where cTrader charged 1.34 and 0.55 more than we did.
3. **Swap is accrued at each roll (6.15, 6.17)**, from the contract's schedule and at the roll's own rate, and a
   close takes its share. Per trade on run 5's volumes (the baseline's, which are cTrader's), each night at its
   own rate equals cTrader's swap to the cent on **245 of 438** swapped trades, against **187** for one rate at
   exit; the total moves only -1 213.65 → -1 212.73 against cTrader's -1 198.88. Truncating each night to the
   cent would put the total at -1 202.05 but matches only 105 trades, so it is not cTrader's rule; the -13.9
   residual stays open for 6.13.
4. **Intrabar segmentation (6.16)** moved every excursion column and the curve's drawdown rows, never a fill.
   Checked against the tape tick by tick, run 3's trades went from **483 of 1 024** equal to the tick truth
   (worst gap 855 points) to **1 024 of 1 024**, and every run is exact (1 024, 1 017, 1 024, 1 017, 510 and
   the live-contract twin of run 1, whose 16:59 New York roll falls inside an H1 bar). Feeding the exports back
   through the mirror's `ReplayAPI` reproduces every excursion price and entry balance, and the drawdown P&L
   to a cent (runs 1, 3, 5).
5. **`SpreadPnL`** is a new column on every export and a new `net.csv` row (Spreads Profit/Loss), between gross
   and commission. It is part of gross — never add it to net.
6. **DDPG** moved because its exposure feature is now normalised by the order sizer's own reference volume
   (6.3): the weights are stale by design and the golden only proves determinism until Phase 7 retrains.

**Golden 6** is the cross-currency case: a CHF account on GBPJPY, where neither side of the pair is the account
— profit converts through CHFJPY and the commission's base through GBPCHF, both direct pairs on the tape. It
has no cTrader twin yet: a CHF demo account now exists, so it joins the 6.13 session.
