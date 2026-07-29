# Research campaign — DDPG on EURUSD H1

A chronological record of the hypotheses tested, what each returned, and how each result
redirected the work. Written so the research process itself can be narrated in the thesis.

Canonical evaluation unless stated: **10 000 EUR · accurate (tick-derived) spread ·
2015-01-01 → 2026-01-01 · netting · EURUSD**.

---

# EXECUTIVE SUMMARY

## The result

On EURUSD H1 bars with **daily (D1) decisions**, a 20% rebalance filter, IC Markets 3.5-point
commission and a **swap-free** account, a DDPG agent trained under a mirrored, exposure-gated
LogReturn reward returns **+34.02% over eleven years** against EURUSD buy-and-hold **−2.93%**
(Sharpe 0.275, maxDD 23.5%, 1 586 trades).

Its defining behaviour is **regime-following**: a **67.0% regime score** against a 50% coin-flip
baseline, holding **274 days long through the 2017 rally**, with **192 long and 200 short**
directional runs.

## What is established, and how strongly

| claim | evidence | verdict |
|---|---|---|
| follows regimes | z = +2.05 vs a rotation null (p = 0.025, before selection adjustment) | **supported ≈2σ** |
| regime accuracy pays | regime-correct years +8.06% vs wrong −5.54% | **supported** |
| return is alpha, not drift | **β = 0.130** ⇒ α = +3.11%/y | **supported** |
| not one lucky year | drop-one-year jackknife: worst case +10.19% | **supported** |
| more than a moving average | **+44pp over an SMA120 rule at identical sizing** | **supported** |
| the return is > 0 | t = 1.07, p = 0.156, CI [−2.47%, +8.48%] | **NOT resolved** |

The last row is the honest limit: at Sharpe 0.275, roughly **53 years** of data would be needed for
2σ. Eleven years of one pair cannot resolve it. **The behaviour is statistically detectable; the
profit is a point estimate.** That asymmetry is precisely why the primary objective was behavioural —
with n = 11, ranking on return is ranking on noise, which is how P2's +19.8% and P6's `hi_t1` were
manufactured and then lost.

## The five findings worth taking away

1. **The reward sign, not market efficiency, was the binding constraint.** `NeutralizeReward`
   over-subtracted and made the reward anti-correlated with direction (Phase 1-3).
2. **Behaviour and profit are different skills.** Regime score is a **screen against beta traps, never
   a maximand** — an SMA120 rule scores *higher* (68.1%) and loses money, and across 16 seeds the
   regime score correlates **+0.05** with return (Phases 13, 16).
3. **The policy is interpretable**: a ~120-day trend follower keyed to its own `MAEpoch` feature,
   agreeing with a naive SMA120 rule 71.3% of the time — yet **all of its edge lives in the 28.7% of
   bars where it disagrees** (Phase 13).
4. **The model is robust; the procedure that finds it is not.** Emergence is **~12.5%** (2 of 16
   seeds); **nothing measurable at selection time identifies the good seed** (held-out return
   correlates −0.08), and **ensembling cannot rescue it either** — averaging regresses to the modal
   collapsed-short seed and destroys two-sidedness (Phases 14, 16, 17).
5. **Costs shape design, not viability.** A 20% rebalance filter recovers **+11.94pp** of commission
   drag while slightly *reducing* drawdown (Phase 9, README 2×2).

## Conclusions that were overturned — the actual research path

This record deliberately keeps the wrong turns, because most of the learning is in them.

| claimed | overturned by |
|---|---|
| "+19.8% chained OOS — the thesis result" (P2) | true chained replay gave −1.32%/y; **pure NNFX rules scored −1.44%/y** |
| "EURUSD H1 has no tradeable alpha; the collapse is the data" (P7) | correct about *next-bar prediction*, wrong about **regime-following behaviour**, which Part II shows is achievable |
| "`hi_t1` +31.54% is the best model" (P6) | ≈10× leverage on a −2.92% drift — a beta trap; the origin of the regime score |
| "gross edge exists under spread" (Phase 5) | a zero-spread test made results *worse* |
| "leverage/vol-drag explains the shortfall" (Phase 4) | measured leverage 0.36-0.55×, drag 0.1%/y |
| "emergence is 3/16 = 18.8%" (Phase 14) | one "success" was a **degenerate no-trade model** (silent zero) and another was the worst full-range seed ⇒ **2/16 = 12.5%** |
| "the test-fold metric is inverted" (Phase 16, mid-scan) | with all 16 seeds the correlation is **−0.075** — it is **noise**, not an inverted signal |
| "longer training collapses seed variance (F = 6.13, p = 0.011)" (Phase 15) | the arms are **paired**, not independent; done correctly there is **no significant effect** |
| "+42.48% is the canonical result" (README) | that is the **zero-commission, no-hysteresis** cell; canonical is **+34.02%** |

## Reading guide

- **Part I (P0-P7)** — three prior weeks: the dead-feature bug, the DDPG-versus-SAC saturation
  diagnosis, the selection-bias reckoning, the metrics rebuild, and the no-alpha verdict.
- **Part II, Phases 1-10** — the regime campaign: reward-sign diagnosis, the regime metric, action
  repeat and calendar decisions, hysteresis, frictions, permutation test.
- **Phases 11-13** — where the return comes from: per-year decomposition, beta, jackknife, and the
  black-box interpretation with the SMA120 ablation.
- **Phases 14-16** — reproducibility and selection: emergence rate, episode-budget dose-response,
  determinism at `threads=1`, and the measured impossibility of selecting the good seed.

---

# PART I — Prior campaigns (2026-07-02 → 2026-07-23)

Three weeks of work preceded the campaign in Part II. It is reported here because most of it
consists of **negative results and instrument-building**, and because several conclusions reached in
this period were later overturned — which is itself part of the story.

## P0 (07-02) — Validation gate, and a dead feature nobody had noticed

Before committing to an 11-year walk-forward, a 15-check audit re-derived every observation feature,
the action decoder and the reward from scratch over 3 119 bars. All 15 passed (max relative error
5.9e-8 = float32 rounding).

**The audit also found a real bug: `PortfolioAPI.InitialBalance` was `None` for entire runs.** Only
`init_data` seeded it and nothing in the backtest path called that, so the account observation
features (balance and equity as returns from initial capital) were **always exactly 0**, and the
Learning fitness fallback returned 0. **Every DRL run before this date carried the defect.** Fixed by
seeding from the `Account` setter; 6 goldens byte-identical, 450 tests green.

*Lesson carried forward:* audit inputs before trusting results, and prefer re-deriving a quantity
independently over reading the code that produces it.

## P1 (07-03) — DDPG saturates by construction; SAC does not

Three-year probes were run as a gate before the full walk-forward.

- **SAC:** healthy learner. Train fitness climbed −20% → +28…+35% in every fold and seed; the
  promoted policy had rich actions (std 0.59, 3.5% saturated) and 785 trades per 6 months.
- **DDPG:** the promoted greedy policy was **a ≡ +1.0000 on all 3 097 test bars** (std 0.0000) — one
  trade, i.e. buy-and-hold.

**Follow-up diagnosis, instrumented rather than inferred.** The reward was verified bit-exact against
Moody and Saffell (agreement 7.76e-06 versus the numerical derivative) — not a bug. The deterministic
actor tanh-**saturates to a constant ±1 within episode 1**; tanh saturation is an absorbing state
with dead gradient and no restoring force. Gradient clipping delayed it (~step 6000 versus ~3000) but
could not prevent it. Exploration was measured adequate (OU stationary std ≈ 0.36), so it was **not**
an exploration-magnitude problem. SAC stayed plastic on the identical environment and reward.

**⇒ The collapse is DDPG-specific and algorithmic** — observation, action, reward and strategy were
all sound. This framing became the mechanistic spine of the thesis and was re-confirmed repeatedly.

## P2 (07-04 → 07-06) — The hybrid detour, and the selection-bias reckoning

Continuous-action arms were probed and all failed structurally: DDPG constant-long, RDDPG
constant-long, TD3 constant-short, SAC plastic but churny. A **hybrid** design followed — model
signal wrapped in NNFX-style risk management (stops, scale-out, trailing).

**First result, fleet v4: HybridRDDPG chained out-of-sample +19.8% mean, 5/5 seeds positive.**
Recorded at the time as "THE thesis result".

**It did not survive scrutiny.** Adding per-fold checkpoint archiving enabled a *true* chained
out-of-sample test — fold-k weights replayed on year k+1. Under that test **all 10 seeds were
negative**, and a faithful replica of the v4 recipe gave **−1.32%/y with 3/10 seeds positive**. The
+19.8% had been **selection bias**.

**The control that settled it:** pure NNFX rules, with no learning at all, scored **−1.44%/y** on the
same window — statistically indistinguishable from every hybrid. **The market, not the model, was the
binding constraint** for single-pair D1 trend following at retail costs.

Also from this period: a λ dose-response (λ=1e-2 best at −0.14%/y); H1 stops behave like noise, so
hybrids are D1 strategies; and a striking result — a **10-seed ensemble took zero trades**, because
the seeds' signals mutually cancelled. They were noise, not a shared pattern.

## P3 (07-07) — Rebuilding the measurements

Two instrument problems were fixed before further searching.

1. **Risk ratios were trade-based and pathological.** A few winning trades with no losers drove the
   downside deviation to a floor, producing enormous Sharpe/Sortino values. Replaced with textbook
   **bar-based equity-curve ratios**, all annualized, with intra-bar-accurate drawdown. That removed
   the crude "fewer than 6 trades" fitness guard which had been masking the problem.
2. **A fitness artifact was distorting selection.** Under Sortino fitness with that guard, a no-trade
   model (fitness 0) beat any negative-Sortino trader, so **selection actively preferred doing
   nothing** — one reason so many arms appeared to "collapse".

The DDPG implementation was **certified paper-faithful** against Lillicrap et al. 2015 line by line,
including the commonly-missed critic L2 weight decay, with deviations documented (LayerNorm instead
of BatchNorm, γ, network width). *The algorithm was not the confound.*

A D1 net-size sweep found **no robust alpha at any capacity** — shrinking the network did not help,
so capacity was not binding — but showed **frame-stacking matters** (window 16 kept policies alive
where window 8 collapsed to 0-1 trades). H1 produced the hunt's only positive true-OOS result
(+2.31%), attributed to data volume: ~56 000 H1 bars against ~2 900 D1 bars.

## P4 (07-20) — The threshold that silenced the model

A measured root cause for the one-sided collapse under the threshold architecture:
`EntryThreshold [-0.4, +0.4]` did not *filter* the model, it **silenced** it — **4 trades in 11
years, zero buys**. The model's positive excursions peaked near **+0.27**, so +0.4 was unreachable on
the long side while −0.4 was trivially reached on the short side: **the threshold manufactured the
asymmetry.** Worse, every action inside the band produced an identical outcome, so Q(s,a) was **flat
across the band** and the actor received no gradient to distinguish +0.1 from +0.39.

A/B on identical weights, without retraining:

| arm | trades | buys | sells | return | maxDD |
|---|---|---|---|---|---|
| threshold + risk | 4 | **0** | 4 | +0.23% | 1.8% |
| sign + risk | 16 823 | 4 145 | 12 678 | −99.67% | 99.7% |
| sign, no risk | 1 416 | **708** | **708** | −1.81% | 2.6% |

Two lessons: stops are incompatible with signal-following re-entry (a churn death spiral), and
two-sided trading was reachable **without retraining** once the wrapper stopped silencing the model.

## P5 (07-21) — The netting rewrite

The architecture was rebuilt around a **netting** position model: a single net position with
continuous target exposure `target = action × full_size`, deltas quantised, and deliberately **no
artificial deadband** — a deadband would have rebuilt the flat-Q plateau. Hedging behaviour was left
untouched and all 6 goldens stayed byte-identical.

Fixed along the way: an **ATR-sizing bug** where `SizingMode: Risk` with risk management disabled
silently produced **zero volume**; and a **leverage mis-calibration** — removing stops while keeping
ATR sizing turned "2% risk" into **4-29× leverage**, because the 1.5×ATR stop had been the bound.

## P6 (07-21) — The no-alpha verdict, and the evaluation protocol

The netting rewrite **worked structurally and produced no alpha.** Frictionless replay, with all
costs removed, of three independently trained models:

| model | gross | Sharpe | maxDD | buys/sells |
|---|---|---|---|---|
| lo_t1 | +4.17% | **+0.21** | 3.6% | 2558/2164 balanced |
| clip5 | −12.59% | −0.17 | 29.1% | 844/5099 |
| hi_t1 | **+31.54%** | +0.11 | 66.6% | 39/17955 one-sided |

**Mean gross Sharpe ≈ 0.05 with 100% of transaction costs removed.** Costs were real (15.5pp drag)
but **not** the binding constraint.

**`hi_t1` is the selection trap, caught.** Its +31.54% — the best raw return — was a permanent short
at roughly 10× leverage capturing EURUSD's −2.92% drift: 10 × 2.92% ≈ +29% of the +31.54%, fully
explained. **Ranking on return alone would have shipped it.** This is the empirical justification for
treating two-sidedness as a prerequisite rather than a preference, and the direct ancestor of the
regime score built in Part II.

Three methodology findings from this period shaped everything after:

- **Training is not reproducible at fixed seed** (same config and seed: −3.1 versus −26.3), because
  float-level divergence is amplified by RL chaos *and* by promoted-checkpoint selection.
  ⇒ **never compare arms on a single promoted model; compare per-seed distributions.**
- **Seed σ ≈ 20-25 points**, so n=2-4 can resolve only structural outcomes or catastrophes, never a
  10-point mean difference.
- **`balance=N` does not enforce two-sidedness** — the gate `min(buys, sells) ≥ N` passes a
  41-buy / 1891-sell model trivially. It needed to be a *ratio*. (Acted on in Part II.)

## P7 (07-23) — Measuring the ceiling

Finally the predictability itself was measured. Next-bar direction AUC on honest 70/30 time splits:
technicals 0.514 · session 0.522 · microstructure 0.519 · cross-FX 0.519 · US500 0.507 · calendar
0.500 · **combined 0.530**, against a tradeable threshold of roughly 0.53-0.55. A supervised
classifier given the *full* feature set and traded with realistic spread lost money in every
out-of-sample configuration while trading balanced and two-sided — so the 0.53 edge did not survive
costs.

**Conclusion recorded at the time:** EURUSD H1 has no tradeable directional alpha; the DDPG collapse
is the data, not the model.

**That conclusion was half right, and Part II overturns the other half.** It is correct about
*next-bar prediction* and about *out-of-sample profit*. It is wrong about **regime-following
behaviour**, which Part II shows is both achievable and easy — the prior campaigns had simply never
measured behaviour separately from profit.

---

# PART II — The regime campaign (2026-07-24 → 2026-07-27)

**Objective at the start of this part:** a model that follows regimes (holds long through up-regimes,
short through down-regimes), trades both sides without collapsing, ends the full range positive, and
beats EURUSD buy-and-hold.

---

## Phase 1 — The measurement was wrong

**Hypothesis.** The existing models were "two-sided" because their buy/sell *trade counts* were
balanced (e.g. 3078 buys / 5630 sells).

**Test.** Measure time-weighted exposure instead of trade counts.

**Result.** The flagship "balanced" model spent **91% of its directional time short**. Under a
netting engine, closing a short *is* a buy, so buy-to-cover inflated the buy count and disguised a
one-sided policy.

**Effect on direction.** Replaced the trade-count balance gate with a time-weighted exposure gate
(`_long_bars_` / `_short_bars_` counted every bar). Every subsequent claim about "two-sidedness"
uses exposure time, never trade counts.

---

## Phase 2 — Building an instrument that cannot be fooled

**Problem.** Return alone cannot distinguish regime-following from leveraged drift capture, and
exposure balance alone cannot distinguish skill from indifference.

**Method.** Defined the **regime score**: for each calendar year,
`aligned = long% if the year rose else 1 − long%`, weighted by |year move|.

**Calibration (the property that makes it trustworthy).** EURUSD's up-moves (39.97%) and
down-moves (39.46%) over 2015-2026 are nearly equal, so:

| policy | regime score |
|---|---|
| always long | 50.3% |
| always short | 49.7% |
| coin flip | 50% |
| perfect foresight | 100% |

**A one-sided collapse scores ~50% by construction and cannot fake skill.**

**Effect on direction.** This became the primary ranking metric; return became secondary. It
immediately rejected several apparent successes — e.g. **+38.12% at regime 37.3%**, **+49.76% at
49.4%**, and later **+273.56% at 57.5% with 14.3% long** — all leveraged shorts riding the drift
straight through every rally.

---

## Phase 3 — Establishing that the target is reachable

**Hypothesis.** Perhaps regime-following on EURUSD H1 is simply not achievable, in which case the
objective is ill-posed.

**Test.** Score trivial slow moving-average cross rules.

**Result.**

| rule | regime | return | maxDD | long% |
|---|---|---|---|---|
| SMA 480 (20d) | 60.4% | — | — | — |
| SMA 1440 (60d) | 66.3% | −14.68% | 17.6% | 47.3% |
| SMA 2880 (120d) | 69.9% | −8.40% | 11.5% | 45.8% |
| SMA 4320 (180d) | 72.0% | −0.33% | 8.2% | 46.1% |
| **SMA 5040 (210d)** | **72.8%** | **+1.00%** | 6.5% | 45.3% |

**Effect on direction.** Decisive reframing: regime-following is *easy* on this instrument. The
DDPG models' ~53% was therefore a **model failure, not an efficient-market wall** — overturning the
prior campaign's conclusion for the behavioural objective. Also corrected a long-standing error:
EURUSD buy-and-hold over the window is **−2.93%**, not the −7% previously assumed.

*Caveat retained for honesty:* the winning window was chosen by scanning 28 configurations, so the
+1.00% is selection-sensitive; the regime score is not (69-73% for every window 120d-360d).

---

## Phase 4 — Finding the root cause

**Observation.** Models given regime-scale features scored *below* chance.

**Hypothesis.** `NeutralizeReward` — intended to remove directional beta by subtracting
`held_exposure × market_return` — was interfering with the directional signal.

**Test.** Decompose the reward over 68 153 bars of a real trajectory.

| quantity | value |
|---|---|
| corr(raw reward, hedge term) | **+0.9989** |
| reward magnitude removed | **87.4%** |
| corr(raw, direction·market) | +0.8949 |
| corr(neutralized, direction·market) | **−0.7860** |
| σ(hedge) vs σ(raw) | 5.10e-4 > 4.57e-4 |

**Result.** The strategy's equity change *is* essentially `exposure × market return`, so the hedge
term nearly equals the reward. Worse, it **over-subtracts**, leaving a residual that is
*anti-correlated* with directional correctness. **The reward paid the agent to hold the wrong side.**

**Confirmation on trained models (dose-response):**

| arm | features | γ | long% | return | regime |
|---|---|---|---|---|---|
| MO1 | 20-day | 0.998 | 86.3% | −9.78% | 50.8% |
| GA | 20-day | 0.9995 | 64.2% | −6.93% | 50.8% |
| GB | 20-day | 0.9998 | 0.1% | −0.25% | 49.6% |
| XA | SMA4320/5040 | 0.998 | 13.6% | −24.07% | **40.1%** |
| XB | SMA4320/5040 | 0.9995 | 56.2% | −4.07% | **30.2%** |

With no regime features the score pins at ~50% (nothing to align with). **Given regime-scale
features under the inverted reward it falls below chance — 40.1%, then 30.2% as the horizon
lengthens.** The better the model could see regimes, the more strongly it anti-aligned; XB missed
10 of 11 years, almost the mirror image of the trivial rule.

**Effect on direction.** Features and discount factor are *enablers*; **the reward sign decides the
direction**. Removing neutralization alone moved the regime score **30.2% → 66.2%** at otherwise
identical settings. Beta-collapse should instead be prevented by **mirror augmentation**
(symmetrising the *data*), never by zeroing the *reward*.

**Secondary blindnesses identified.** γ=0.998 gives a ~1-month credit horizon and the slowest
feature was 480 bars (~20 days), against regimes lasting 2-12 months. Both were fixed
(γ=0.9995; SMA 1440/2880/4320/5040 added).

---

## Phase 5 — Churn, and the discovery that P&L was noise

**Observation.** Single-run returns were unstable.

**Test.** Re-run one trained model changing only the **initial balance** (economically meaningless).

**Result.** Returns spanned **+8.31% to −16.00%** (σ≈9pp) while exposure balance and turnover stayed
constant.

**Effect on direction.** Every single-run return ranking in the campaign was invalidated —
behaviour was reproducible, P&L was not. Evaluation protocol changed to report the **mean over five
initial balances**, and no model is promoted on one lucky run.

**Follow-up hypothesis.** The instability came from high-frequency churn (median 5-bar holds,
~17 000 trades).

**Test.** Action repeat — decide every *k* bars, hold in between.

| k | return | trades | regime |
|---|---|---|---|
| 1 | −4.62% | 8 351 | 66.2% |
| 8 | −2.39% | 6 084 | 67.1% |
| 24 | +0.18% | 3 580 | 68.7% |
| 120 | **+4.47%** | 2 336 | 65.3% |

**Result.** Monotonic: less churn, better return, regime score unchanged. It also **eliminated the
P&L chaos** — the initial-balance spread collapsed from **24pp to 0.49pp**.

**Also tested and rejected:** training *with* action repeat (divides gradient updates by k and
starves the learner — 0/3 seeds). Conclusion: **train at k=1, deploy slow.**

---

## Phase 6 — Why the model never used its full position range

**Observation (raised by the supervisor).** Directional signals never exceeded ±0.5.

**Measurement.** Actor output spanned **−0.113 … +0.258**, median |signal| **0.027** — the model
traded at ~3% of available size, never above 26%.

**Diagnosis.** `DifferentialSortino` is **scale-invariant in position size**: doubling exposure
doubles both return and downside, leaving the ratio unchanged. It therefore has *no gradient*
pushing position size up, while the actor regulariser λ pulls the pre-tanh activation toward zero.

**Test.** Replace it with a **scale-sensitive** reward (`LogReturn`, `RewardScale 1000`).

| | DifferentialSortino | LogReturn ×1000 |
|---|---|---|
| actor range | −0.113 … +0.258 | **−0.798 … +0.731** |
| median \|signal\| | 0.027 | **0.200** |
| bars beyond \|0.5\| | 0.00% | **21.34%** |

**Result.** The ceiling disappeared, and this single change produced the campaign's best model.

**Effect on direction.** LogReturn ×1000 became the reward of record. Trade-off noted: it also
re-admits some directional-collapse pressure, later countered with `mirror_ratio 0.65`.

---

## Phase 7 — Decision cadence

**Observation (raised by the supervisor).** Action repeat counted *bars*, which is irregular when
data is missing; calendar boundaries ("every Monday", "every 4 hours") would be better.

**Implementation.** `DecisionSchedule` — buckets derived from the bar timestamp (H4/H8/H12/D1/W1),
immune to gaps.

**Result.**

| schedule | return | regime | Sharpe | maxDD |
|---|---|---|---|---|
| H4 | −34.05% | 68.1% | −0.250 | 47.8% |
| H8 | −21.26% | 68.2% | −0.116 | 40.9% |
| H12 | +22.11% | 67.6% | 0.209 | 32.4% |
| **D1** | **+42.48%** | **68.1%** | **0.319** | **24.4%** |
| W1 | +0.92% | 67.5% | 0.065 | 38.9% |

**Two findings.** Calendar **D1 beats bar-count k=24** (+29.30%, Sharpe 0.250) — the gap-robustness
argument confirmed numerically. And **the regime score is 67.5-68.2% at every frequency from hourly
to weekly**: regime *identification* is independent of how often the agent acts; only costs change.

**Honesty note that changed the reported headline.** Bar-count k=120 showed +73.79% while calendar
W1 — the same ~weekly cadence — showed only +0.92%, revealing the k=120 figure as partly **phase
luck**. The reported configuration was therefore moved to **D1**.

**Effect on direction.** Canonical configuration fixed: **timeframe H1, decision D1.**

---

## Phase 8 — Frictions, and a structural inefficiency they exposed

**Request (supervisor).** Test commissions and swaps progressively, and consider frictions during
learning.

**Unit correction.** `CommissionType.Points` takes points, so the Spotware demo's contract value of
45 is **4.5 pips per side** — genuinely extreme. Realistic IC Markets / Pepperstone raw pricing is
**≈3.5 points**.

**Result at realistic costs.** The strategy survived commission comfortably, but **swap** — at
−0.5/night and worse — destroyed it. That is the arithmetic consequence of a strategy that is ~65%
long and holds for up to 265 days: negative carry compounds across the whole position.

**The unexpected discovery.** Trade counts under daily decisions were **20 146 against only ~2 860
daily decisions — 7× more trades than decisions**. Cause:
`target = reference_volume(ATR, balance) × action`, so ATR and balance drift move the target every
bar *even when the agent holds its action constant*. **The churn is generated in the sizing layer,
below the policy — the agent cannot learn to avoid it.**

**Fix.** `RebalanceThreshold`: require `|delta| ≥ max(VolumeMin, threshold × |reference_volume|)`.

| threshold | trades | return @3.5pt | Sharpe | maxDD |
|---|---|---|---|---|
| 0 | 20 146 | +22.08% | 0.207 | 25.7% |
| 0.05 | 7 784 | +27.62% | 0.239 | 24.9% |
| 0.10 | 3 548 | +32.24% | 0.265 | 25.5% |
| **0.20** | **1 586** | **+34.02%** | **0.275** | **23.5%** |

**13× fewer trades, +12pp return under real commission, drawdown and regime score unchanged.**

**Learning-time frictions — hypothesis disproven, with a mechanism.** Charging costs inside the
reward (`w_C35`, `w_C70`, `q_M65b`) produced **0/6, collapse, and 0/12** respectively, versus
**2/12** for the identical recipe trained cost-free. The reason is the same structural fact: the
churn being charged for is produced below the policy, so the cost arrives as noise the agent cannot
act on, degrading learning. **The economically-correct version of the idea was the strategy-layer
hysteresis**, which delivered precisely the intended effect.

---

## Phase 9 — Reproducibility

**Problem.** The best models were single seeds.

**First measurement.** 0/8 and 1/24 seeds reproduced regime-following — an emergence rate of ~7%.

**Bug found mid-measurement.** The multi-seed worker (`_learn_seed_`) reconstructed `LearningAPI`
with explicit keyword arguments and **silently dropped `ratio`, `mirror_ratio` and `final`**, so
every multi-seed run executed with the exposure gate disabled. The earlier "0/24" figure was
therefore **not a replication of the reference configuration** and was withdrawn.

**Levers tested against the low emergence rate, all exhausted:**

| lever | result |
|---|---|
| λ ∈ {0, 1e-4, 0.003} | all collapse; **λ=0.001 is the only working value** |
| network capacity (128×64, 256×128) | no help |
| more episodes (90, 100) | no help — models were bit-identical, since weights save only on validation improvement |
| final vs best checkpoint | final is worse (0/3) |
| short training (5, 12 episodes) | 0/8 — **saturation is near-immediate**, so the good policy is not an early transient |

**What did work.** Training **natively at the decision cadence** (D1) instead of hourly: ~6× faster
and a markedly higher rate of regime-skilled seeds. Combined with `mirror_ratio 0.65` — which
over-weights the mirrored (upward) world to cancel LogReturn's short lean — the recipe produced
**2/12 seeds meeting every objective under real frictions**.

---

## Current result

**EURUSD · timeframe H1 · decision D1 · swap-free account · IC Markets commission · 20% hysteresis**

| metric | value |
|---|---|
| return | **+34.02%** (buy-and-hold −2.93%) |
| Sharpe / Sortino | 0.275 / — |
| maxDD | 23.5% |
| regime score | **67.0%** (coin flip 50%, trivial rule 72.8%) |
| long share | 66.6% |
| trades | 1 586 over 11 years |
| longest hold | **274 days long through the 2017 rally** |
| robustness | positive at 4× real commission and at swap −0.5/night |
| invariance | position size (risk 1→8), account size (2 500→100 000), time-split (67.5% vs 67.4%) |

**Standing caveats.** Emergence ~17% of seeds; results are ~90% in-sample by construction
(training 2015-2024); action repeat is applied at deployment to a model trained per-bar; Sharpe
remains below the S&P 500's 0.674 over the same decade, and leverage cannot close that gap because
Sharpe is scale-invariant.

---

## Phase 10 — Statistical robustness

**Question.** Is a regime score of 67% distinguishable from luck?

**Method — permutation test with a matched null.** The model's own exposure series is rotated
circularly against the market (2 000 draws). Rotation preserves the policy's autocorrelation,
hold lengths and long/short mix *exactly*, and destroys only its alignment with the market. This is
a stricter null than random policies, because it holds every structural property constant.

| quantity | value |
|---|---|
| actual regime score | **67.05%** |
| null mean ± sd | **50.16% ± 8.22** |
| null 5th / 50th / 95th percentile | 38.29% / 48.16% / 66.30% |
| null maximum over 2 000 draws | 68.96% |
| z-score | **+2.05** |
| one-sided p-value | **0.025** (50 / 2 000 rotations matched or beat it) |

**Two readings, both worth reporting.**

1. **The null mean lands at 50.16%**, empirically confirming the analytical calibration that 50% is
   the coin-flip baseline. The metric's design is validated independently of any model.
2. **The evidence is ~2σ, not overwhelming.** Individual rotations reach 68.96%, above the actual
   score. With only 11 calendar years the year-weighted metric is coarse, so a rotated policy can
   align by chance; the null standard deviation is 8.22pp.

**Multiple-comparison caveat (state this explicitly).** The p-value is **not** corrected for the
search. On the order of 100 configurations were evaluated across the campaign, and the final model
was selected partly *on* the regime score. The defensible claim is therefore:
*"significant at approximately 2σ against a structure-matched null, before adjustment for model
selection"* — not *"p = 0.025, therefore real"*.

**What would strengthen it.** A permutation test on a period never used for selection, or a
pre-registered configuration evaluated once on held-out years. Both are natural extensions and are
noted as limitations rather than claimed.

---

## Phase 11 (07-27) — Where the return actually comes from

The permutation test asked whether the *behaviour* was real. This phase asks the complementary and
more searching question: **where does the money come from, and is it the regime-following that pays?**
A single full-range run of the champion was instrumented at bar level to capture the equity curve
alongside exposure, then decomposed by calendar year. Conditions are the deliverable's:
EURUSD H1 bars, D1 decisions, 20% rebalance hysteresis, IC Markets 3.5-point commission, swap-free.

### 11.1 The per-year table

| year | EURUSD | model | long% | trades | maxDD | equity end |
|---|---|---|---|---|---|---|
| 2015 | −10.05% | **+5.60%** | 41.2% | 205 | 12.5% | 10 560 |
| 2016 | −3.21% | −2.41% | 75.9% | 89 | 6.9% | 10 303 |
| 2017 | +14.24% | +1.55% | 86.7% | 146 | 13.5% | 10 463 |
| 2018 | −4.58% | −2.66% | 57.4% | 184 | 17.2% | 10 182 |
| 2019 | −2.21% | **+9.56%** | 48.5% | 138 | 9.4% | 11 155 |
| 2020 | +9.08% | +1.06% | 93.7% | 120 | 11.3% | 11 278 |
| 2021 | −7.18% | +0.22% | 53.2% | 162 | 9.3% | 11 309 |
| 2022 | −5.95% | **+21.52%** | 33.7% | 185 | 11.7% | 13 743 |
| 2023 | +3.16% | +8.16% | 89.6% | 120 | 8.2% | 14 874 |
| 2024 | −6.17% | **−17.29%** | 80.9% | 107 | 18.0% | 12 288 |
| 2025 | +13.49% | +8.98% | 83.3% | 130 | 9.1% | 13 390 |

**8 of 11 years positive**, mean +3.12%/y, median +1.55%, cross-year standard deviation 9.25pp. No
single year draws down more than 18.0%.

### 11.2 The return is not beta — the measurement that closes the P6 trap

This is the test that `hi_t1` failed in P6, run properly.

| quantity | value |
|---|---|
| correlation(model year return, EURUSD year move) | **+0.115** |
| beta to EURUSD | **+0.130** |
| **alpha** | **+3.11%/y** |

**Essentially all of the return is alpha.** In P6, `hi_t1`'s +31.54% was arithmetically explained by
roughly 10× leverage applied to EURUSD's −2.92% drift — a beta trap that ranking on return alone
would have shipped. Here the beta is 0.13, so the drift explains **0.13 × 0.06% ≈ 0.01%/y** of a
+3.12%/y mean. The two clearest illustrations sit in the table:

- **2022** — EURUSD −5.95%, the model **+21.52%** while only 33.7% long. Its best year by a wide
  margin, earned by being short through a decline.
- **2019** — EURUSD −2.21%, essentially flat, the model **+9.56%** with near-balanced exposure
  (48.5% long). There is no drift to harvest in that year at all; the return is trading.

### 11.3 The regime score is not decorative — it is the mechanism that pays

Classifying each year by whether the model's majority side matched the year's direction:

| | years | mean model return |
|---|---|---|
| regime-**correct** | 7 / 11 — 2015, 2017, 2019, 2020, 2022, 2023, 2025 | **+8.06%** |
| regime-**wrong** | 4 / 11 — 2016, 2018, 2021, 2024 | **−5.54%** |

**A 13.6-point spread between the two groups.** This retroactively justifies the entire
behavioural detour of the campaign. The regime score was introduced in Phase 2 as a *defensive*
instrument — a way to reject beta traps that return alone would accept. It turns out to be
**predictive of profit**: the years the model reads correctly are the years it is paid, and the
years it misreads are the years it loses. Optimizing behaviour was not a substitute for optimizing
return; on this problem it was a **cleaner-signal route to it**.

The honest counterweight is **2017**: regime-correct, 86.7% long through a +14.24% rally, and it
earned only **+1.55%**. Being directionally right is necessary but far from sufficient — the entry
and exit timing inside the regime still governs how much of the move is captured. This is the same
timing bottleneck identified in Phase 6 and it remains the model's principal inefficiency.

### 11.4 Drop-one-year jackknife — is it one lucky year?

Each year was removed in turn and the remainder recompounded.

| dropped | remaining total | | dropped | remaining total |
|---|---|---|---|---|
| — (all) | +33.91% | | 2021 | +33.61% |
| 2015 | +26.81% | | **2022** | **+10.19%** |
| 2016 | +37.22% | | 2023 | +23.80% |
| 2017 | +31.86% | | 2024 | +61.90% |
| 2018 | +37.56% | | 2025 | +22.88% |
| 2019 | +22.23% | | | |
| 2020 | +32.50% | | | |

**The result survives the removal of any single year.** The worst case — dropping 2022, the largest
contributor at +21.52% — still leaves **+10.19%** over the remaining ten years. The result is
therefore not one lucky year, although it is fair to say 2022 is load-bearing: it supplies roughly
two-thirds of the total.

The mirror-image observation is that **2024 alone costs 28pp** (removing it lifts the total from
+33.91% to +61.90%). That single regime misread — 80.9% long through a −6.17% year — is the largest
identifiable inefficiency in the model, and a more informative target for future work than any
hyperparameter.

### 11.5 What this phase establishes

- The return is **alpha, not drift** (β = 0.13) — the P6 selection trap is closed by measurement,
  not by assertion.
- Regime accuracy **causes** the return (+8.06% versus −5.54%, a 13.6-point spread), which validates
  the campaign's decision to optimize behaviour rather than profit directly.
- The result is **not carried by a single year**, surviving any one-year deletion.
- The two named weaknesses are **timing inside correct regimes** (2017: right, but only +1.55%) and
  **regime misreads** (2024: −17.29%), not leverage, not costs, and not beta.

---

## Phase 12 (07-27) — Statistical power, and why the primary objective was behavioural

Phase 11 established *where* the return comes from. This phase asks the question a thesis examiner
will ask next: **is the return statistically distinguishable from zero?** The answer is the most
important honest limitation in the document, and it retroactively justifies the campaign's choice of
primary objective.

### 12.1 The return is positive but underpowered

Treating the 11 calendar-year returns as the sample:

| quantity | value |
|---|---|
| mean annual return | **+3.12%** |
| sample standard deviation | 9.70pp |
| standard error | 2.93pp |
| **t-statistic** | **+1.07** (df 10) |
| one-sided p-value | **0.156** |
| bootstrap 95% CI on the mean (20 000 resamples) | **[−2.47%, +8.48%]** |
| P(mean annual return > 0) | 87.0% |
| bootstrap 11-year total | median +35.0%, 95% CI [−28.2%, +138.9%], P(>0) 83.6% |

**The confidence interval contains zero.** The point estimate is positive and the bootstrap puts
roughly 87% of its mass above zero, but by the conventional 5% threshold the return is **not
significant**. The same conclusion follows directly from the Sharpe ratio:

    t = Sharpe × √years = 0.275 × √11 = 0.91   (one-sided p = 0.192)

### 12.2 This is a sample-size limit, not a defect of the model

The relation `t = SR × √y` can be inverted to ask how much data a Sharpe of 0.275 *needs*:

| target | years required |
|---|---|
| t = 1.0 | ≈ 13 years |
| t = 1.65 (p = 0.05) | ≈ 36 years |
| **t = 2.0** | **≈ 53 years** |

**Eleven years of a single currency pair cannot resolve a Sharpe of 0.275, no matter how good the
model is.** This is a property of the measurement problem, not of the strategy. Any paper reporting
statistical significance for a low-Sharpe single-pair strategy on a decade of data is either using a
much higher Sharpe, pooling many instruments, or has not run the calculation.

### 12.3 Why the primary objective was behavioural — the argument in full

This is the methodological spine of the thesis, and Phase 12 is what makes it defensible.

| claim | instrument | evidence | verdict |
|---|---|---|---|
| the model **follows regimes** | regime score vs rotation null | z = +2.05, p = 0.025 | **supported at ≈2σ** |
| regime accuracy **pays** | correct vs wrong year grouping | +8.06% vs −5.54%, 13.6pp spread | **supported** |
| the return is **not beta** | β to EURUSD | β = 0.130, α = +3.11%/y | **supported** |
| the return is **not one year** | drop-one-year jackknife | worst case +10.19% | **supported** |
| the return is **> 0** | t-test on 11 annual returns | t = 1.07, p = 0.156 | **not resolved** |

The behavioural claim is testable at this sample size; the profitability claim is not. Choosing the
regime score as the primary objective was therefore not a way of avoiding a hard target — it was the
**only objective the available data can actually adjudicate**. Ranking on return with n = 11 would
have been ranking on noise, which is precisely how `hi_t1` (P6) and the +19.8% hybrid (P2) were
produced and then lost.

### 12.4 The defensible summary claim

Stated so that every clause is backed by a measurement in this document:

> On EURUSD H1 with daily decisions and realistic swap-free retail costs, a DDPG agent trained
> under a mirrored, exposure-gated reward learns **statistically detectable regime-following
> behaviour** (regime score 67.0%, z = +2.05 against a structure-matched rotation null, before
> adjustment for model selection). That behaviour is **economically meaningful in-sample** —
> +34.02% over 11 years against −2.93% buy-and-hold, with beta 0.13 so the return is alpha rather
> than drift, positive in 8 of 11 years, and robust to deleting any single year. The return is
> **not statistically significant** (t = 1.07, p = 0.156); at a Sharpe of 0.275 roughly 53 years of
> data would be required to establish it at 2σ, so the profitability result is reported as a point
> estimate with its confidence interval, not as a claim of edge.

### 12.5 Limitations, stated rather than discovered by a reader

- **In-sample.** Roughly 90% of the evaluation window overlaps training. This was an explicit
  scoping decision for a behavioural thesis, not an oversight.
- **Selection.** On the order of 100 configurations were evaluated; no p-value in this document is
  corrected for that search.
- **Emergence rate.** The recipe produces the target behaviour in a minority of seeds
  (2 of 12 measured under full frictions), so the *procedure* is far less robust than the *model*.
- **Swap-free.** The result depends on a swap-free account; ordinary overnight financing on 274-day
  holds is materially adverse (quantified in `FRICTIONS.md`).
- **Single pair, single regime era.** 2015-2026 contains one major dollar cycle; the 2024 misread
  shows what happens when the model reads that cycle wrong.

---

## Phase 13 (07-27) — Opening the black box, and the benchmark that matters

Phases 11-12 established that the return is alpha, that regime accuracy pays, and that the return is
not statistically resolvable at n = 11. One question remained, and it is the one an examiner asks
first: **the model is a trend follower — is it anything more than a moving average?**

To answer it, the champion's bar-level exposure was dumped to CSV (68 156 rows: timestamp, equity,
exposure, close, rebalance size), so the policy could be interrogated without re-running the engine.

### 13.1 What lookback did the policy learn?

Correlating net exposure against the trailing return over various horizons:

| lookback | 1d | 5d | 20d | 45d | 90d | **120d** | 180d | 250d |
|---|---|---|---|---|---|---|---|---|
| correlation | +0.048 | +0.117 | +0.230 | +0.362 | +0.494 | **+0.591** | +0.511 | +0.447 |

**The policy is a ~120-day trend follower.** The correlation is near zero at daily horizons and peaks
sharply at 120 days. That number is not arbitrary: **120 days is exactly `MAEpoch` (SMA over 2 880 H1
bars)**, one of the six technical features in the observation. The agent selected a mid-horizon
feature and built its behaviour around it — a rare case of a DRL policy being directly interpretable
in terms of its own inputs.

Agreement between the policy's side and a naive price-versus-SMA rule confirms it:

| rule | SMA20 | SMA30 | SMA60 | SMA90 | **SMA120** |
|---|---|---|---|---|---|
| agreement | 61.5% | 64.1% | 67.9% | 69.6% | **71.3%** |

### 13.2 The sign-swap ablation

The decisive test. The model's **sizing is held fixed** — the exact per-bar `|exposure|` it chose —
and only the **direction** is replaced. Any difference is therefore attributable to direction alone.
A simplified accounting was used, first **calibrated against ground truth**: with a round-trip cost
of 0.000035 per unit it reproduces **+36.02%** against the engine's actual **+34.02%** (2.0pp error),
so relative comparisons below are trustworthy while absolute levels carry that error bar.

| arm (identical sizing) | total | Sharpe | maxDD | long% | regime |
|---|---|---|---|---|---|
| **model direction (champion)** | **+36.02%** | **0.285** | **22.7%** | 67.6% | 67.0% |
| SMA120 rule direction | −8.33% | 0.030 | 36.9% | 47.3% | **68.1%** |
| model magnitude, rule sign | −4.56% | 0.052 | 41.6% | 45.7% | 70.3% |
| always long, model magnitude | −26.49% | −0.060 | 55.5% | 100.0% | 50.4% |
| always short, model magnitude | +11.46% | 0.139 | 36.2% | 0.0% | 49.6% |

**The model beats the moving-average rule by 44.35 percentage points using the same position sizes.**
It also beats always-short — the drift-harvesting arm that trapped `hi_t1` in P6 — by 24.6pp.

**The most important row is the second one, and it corrects Phase 11.3.** The SMA120 rule scores a
*higher* regime score than the model (68.1% versus 67.0%) and still **loses money**. So:

> **Regime accuracy is necessary but not sufficient.** Within a single policy, reading the regime
> correctly is what pays (Phase 11.3: +8.06% versus −5.54%). Across policies, a higher regime score
> does not imply a higher return — the rule proves that identifying the regime and *monetizing* it
> are different skills.

This is the sharpest statement the campaign can make about its own primary metric, and it must be
reported alongside Phase 11.3 rather than instead of it. The regime score did its job: it is a
**screen** that rejects beta traps, not a **maximand**.

### 13.3 Where the edge actually lives

Bucketing every bar by whether the model agreed with SMA120 (P&L at bar *i* attributed to the
position held at *i*−1):

| bucket | bars | share | model P&L | rule P&L |
|---|---|---|---|---|
| agrees with SMA120 | 45 886 | 71.3% | **+2 204** | +2 204 |
| disagrees with SMA120 | 18 456 | 28.7% | **+1 846** | −1 846 |
| **model gross, all bars** | | | **+4 529 EUR** | |

**The 28.7% of bars where the model departs from the rule produce 40.8% of its gross profit**, and
because the rule loses exactly what the model gains there, the swing is **+3 692 EUR — essentially
the model's entire edge**. In the 71.3% of bars where they agree the two are identical by
construction, so *all* of the model's economic contribution is concentrated in its disagreements.

**The edge is not a cost artifact.** The rule is not even cheaper to run: turnover is **38.0M units
for the rule against 27.5M for the model**, so the model wins on gross P&L *and* pays less to trade.

### 13.4 The mechanism behind the 2024 misread

The 120-day interpretation also explains the worst year, month by month:

| 2024 | EURUSD | model | long% |
|---|---|---|---|
| Jan | −2.07% | −4.02% | 100.0% |
| Jun | −1.07% | −2.65% | 25.7% |
| Jul | +0.73% | −2.00% | 34.1% |
| Aug | +2.03% | +2.53% | 92.8% |
| Sep | +0.82% | +3.16% | 100.0% |
| **Oct** | **−2.21%** | **−7.39%** | **100.0%** |
| Nov | −2.92% | −2.76% | 90.8% |

The model correctly turned long through the August-September rally, then held **100% long into
October's reversal**, losing 7.39% in that month alone. This is the canonical trend-follower
whipsaw at a turning point, and it is *structural*: a 120-day filter cannot turn in under a month.
2024's −17.29% is therefore not a training failure but the known cost of the horizon the policy
learned — which is the honest way to report it.

### 13.5 Behavioural statistics

| quantity | value |
|---|---|
| directional runs | 392 — **192 long · 200 short** |
| median / mean hold | 2.0 days / 7.1 days |
| longest long / short | 274 days / 74 days |
| runs ≥ 30 days | 4.8% of runs but **52.6% of time held** |
| runs ≥ 90 days | 0.8% of runs but 22.5% of time held |
| mean / median gross leverage | 1.50× / 1.02× (p95 4.17×, max 7.96×) |
| bars long / short / flat | 66.6% / 32.0% / 1.4% |
| rebalances | 1 586 (144/year) |

Two observations worth keeping. **Run counts are near-perfectly balanced (192 long, 200 short)** even
though 66.6% of *time* is spent long — the model takes both sides equally often and simply holds
longs longer, which is exactly what regime-following in a market with large up-regimes should look
like, and a much stronger two-sidedness statement than the time-weighted split alone. And **leverage
is modest** (median 1.02×), confirming by direct measurement that this is not a leveraged-drift
result.

### 13.6 What Phase 13 establishes

- The policy is **interpretable**: a ~120-day trend follower keyed to its own `MAEpoch` feature,
  agreeing with a naive SMA120 rule 71.3% of the time.
- It is nonetheless **not** that rule: +36.02% versus −8.33% at identical sizing, with the entire
  edge (+3 692 EUR) concentrated in the 28.7% of bars where it disagrees, and with *lower* turnover.
- **Regime score is a screen, not a maximand** — the rule scores higher on it and still loses money.
- The 2024 failure has a **structural mechanism** (120-day horizon cannot turn inside a month)
  rather than an unexplained one.

---

## Phase 14 (07-27) — Emergence rate, and the selection criterion that does not work

The campaign's weakest claim throughout has been **reproducibility**: the champion is one model, and
earlier work put the emergence rate at roughly 2 in 12. Sixteen fresh seeds of the exact champion
recipe were run to tighten that estimate. The run answered the question — and exposed a larger
problem in the process.

### 14.1 The emergence rate

Sixteen seeds, identical configuration, test-fold account return of each seed's own promoted
checkpoint:

| quantity | value |
|---|---|
| mean | **−21.35%** |
| standard deviation | 17.30pp |
| min / max | −54.35% / **+15.21%** |
| quartiles | −30.69 / −23.43 / −10.10 |
| **positive seeds** | **3 / 16** (+15.21, +5.47, +0.01) |
| emergence rate | **18.8%**, Wilson 95% CI [6.6%, 43.0%] |

Pooled with the earlier 2-of-12 measurement: **5 / 28 = 17.9%**, CI [7.9%, 35.6%]. The two
independent estimates agree closely, so ~18% is a solid figure.

The practical consequence, stated plainly for anyone reproducing this work:

| goal | seeds required |
|---|---|
| ≥1 success with 90% probability | **12 seeds** |
| ≥1 success with 95% probability | **16 seeds** |

The seed standard deviation of 17.3pp also confirms the σ ≈ 20-25 estimate from P6 — small seed
counts (n = 2-4) can resolve only structural outcomes, never a mean difference.

### 14.2 The finding that matters more: validation fitness does not select the good seed

This is the uncomfortable part, and it is worth more than the emergence rate.

The harness promotes one seed per configuration using **CalmarRatio on the validation fold**. Across
these 16 seeds it promoted a model whose **frictionless full-range return is −45.90%** — while a seed
in the very same batch reached **+15.21%** on the test fold. Best validation fitness was 0.436.

> **The automated selection criterion did not merely add noise — it picked a badly negative model
> when a positive one was available in the same batch.**

This retroactively explains a great deal of the campaign:

- It is why the champion was **not** found by the pipeline's own promotion, but by scanning every
  seed with an independent evaluator on the regime-plus-return criterion.
- It is a second, independent instance of the P3 lesson (*a fitness artifact was distorting
  selection*) and of the P6 lesson (*never compare arms on a single promoted model*). The same class
  of error recurred in a different guise after both had supposedly been fixed.
- It means the honest unit of reproduction is **"run N seeds and evaluate all of them on the target
  criterion"**, never "run the pipeline and take what it promotes".

### 14.3 Model robustness versus procedure robustness

The distinction the campaign has been careful about since Phase 8, now quantified on both sides:

| | evidence | verdict |
|---|---|---|
| **the model** | β = 0.13 · 8/11 positive years · survives dropping any year · beats SMA120 by 44pp at identical sizing · 192 long / 200 short runs | **robust** |
| **the procedure** | 18% emergence · validation fitness promoted −45.90% over an available +15.21% · training not reproducible at fixed seed (P6) | **not robust** |

Both statements are true simultaneously and neither cancels the other. The trained artifact does what
it is claimed to do, under measurement, repeatedly, and against benchmarks. The *pipeline that
produced it* finds such an artifact roughly one time in six and cannot reliably recognise it when it
does. For a thesis this is a legitimate and interesting result about DRL practice rather than a
disclaimer — the literature very rarely reports emergence rates at all, and this campaign can report
one with a confidence interval.

### 14.4 What would fix it (not attempted, stated as future work)

- **Select on the target criterion directly.** Validation Calmar is a proxy that demonstrably
  disagrees with regime-plus-return; the evaluator used to find the champion should *be* the
  selection rule.
- **Select on a seed ensemble rather than a seed.** P2 showed a naive 10-seed ensemble cancels to
  zero trades, so this needs a regime-level vote rather than a signal-level average.
- **Report the whole seed distribution as the result**, as done here, instead of a promoted model.

---

## Phase 15 (07-28) — Does longer training help? And a discovery about determinism

The last open question was whether the ~18% emergence rate could be raised simply by training longer.
Three arms were run on the identical champion recipe, varying only the episode budget: **15, 30 and
100 episodes**. The answer is no — but the experiment produced a more valuable by-product.

### 15.1 The by-product: training is deterministic at `threads=1`

Comparing the 15-episode and 30-episode arms seed by seed, **9 of 16 seeds returned bit-identical
results** — not close, identical to full float precision. Between 30 and 100 episodes, 3 of 8 matched
identically.

This is only possible if **the same seed produces the same trajectory**, and it **corrects a
long-standing assumption in this project.** P6 recorded that *"training is not reproducible at fixed
seed (same config and seed: −3.1 versus −26.3)"*, and that caveat has shaped evaluation practice ever
since. It is now clear that the earlier observation was **conditional on multi-threaded execution** —
float reduction order varies with thread scheduling. With `SWEEP_THREADS=1` and
`SWEEP_WORKER_THREADS=1`, as used throughout this campaign, training is exactly reproducible.

Two consequences:

- **Every arm in this campaign is exactly reproducible**, which is a far stronger claim than the
  thesis previously assumed it could make.
- **The arms are paired, not independent.** Comparing episode budgets as independent samples is
  invalid when more than half the seeds are literally the same run.

Why identical rather than merely similar: for those seeds the **best-validation checkpoint occurred
within the first 15 episodes**, so extending the budget never promoted a different checkpoint. That is
itself the practical finding — see 15.3.

### 15.2 The comparison, done paired

| arm | n | mean | sd | max | positive |
|---|---|---|---|---|---|
| 15 episodes | 16 | −20.95% | 17.58 | **+15.21%** | **3/16** |
| 30 episodes | 16 | −21.35% | 17.30 | **+15.21%** | **3/16** |
| 100 episodes | 8 | −27.09% | 6.99 | −10.10% | 0/8 |

Paired by seed:

| comparison | mean change | better | worse | unchanged | paired t | verdict |
|---|---|---|---|---|---|---|
| 15 → 30 episodes | −0.40pp | 4 | 3 | **9** | −0.35 | **no effect** |
| 30 → 100 episodes | −2.79pp | 2 | 3 | **3** | −0.42 | **no effect** |

**Episode budget between 15 and 100 has no detectable effect.** Emergence is identical at 15 and 30
(3/16 both), and 0/8 at 100 episodes is unsurprising under an 18% rate (P = 0.189).

**A correction to an intermediate claim.** An earlier pass through this data compared the 30- and
100-episode arms as *independent* groups and reported a significant variance collapse
(F = 6.13, p = 0.011), with a tidy mechanism attached: longer training drives seeds into the
tanh-saturation absorbing state, destroying the right tail the search depends on. **That test was
invalid** — the seeds are paired and three of the eight are the same run. Done correctly the paired
comparison shows no significant effect, and the apparent narrowing rests on n = 8 with a single
dramatic seed (seed 1: +15.21% at 15 and 30 episodes, −28.08% at 100). The mechanism may well be
real — it is consistent with P1 — but **this experiment does not establish it**, and it is recorded
here as an untested hypothesis rather than a result.

### 15.3 What is actually actionable

- **Train short.** For 9 of 16 seeds the promoted checkpoint was already fixed by episode 15;
  doubling the budget changed nothing while costing 3.4× the wall time (6 089s versus 1 774s).
  The 100-episode arm cost 5 896s for eight seeds and produced no positive one.
- **Spend the compute on seeds, not episodes.** Emergence is ~18% per seed and flat in episode
  budget, so **16 seeds × 15 episodes dominates 8 seeds × 100 episodes** on every axis: more
  chances at the tail, one third of the wall time.
- **Reproducibility is available when wanted** — pin `threads=1` and any result in this campaign can
  be regenerated exactly. Multi-threaded runs lose it.

### 15.4 Where this leaves the emergence problem

Longer training is not the lever. Combined with Phase 14 — where validation Calmar promoted a
−45.90% model over an available +15.21% — the constraint is **selection, not optimization**. The good
seed already exists inside a 15-episode budget; the pipeline simply cannot tell which one it is. That
is the single most promising direction for future work, and it is a search-and-selection problem
rather than a reinforcement-learning one.

---

## Phase 16 (07-28) — Can any rule pick the good seed? The selection problem, measured

Phase 14 showed the pipeline promoted a −45.90% model while a +15.21% one sat in the same batch, and
Phase 15 narrowed the constraint to **selection rather than optimization**. This phase tests the
proposition directly. All sixteen seed weight sets from the 15-episode arm were retained, so each was
evaluated independently under the deliverable's conditions (D1 decisions, 20% hysteresis, 3.5-point
commission, swap-free) and every candidate selection rule was scored against the outcome.

### 16.1 The full seed population

| seed | full-range | regime | long% | maxDD | Sharpe | test fold |
|---|---|---|---|---|---|---|
| **3** | **+28.28%** | 61.6% | 34.0% | 62.5% | **0.227** | **−54.35%** |
| **9** | **+25.81%** | 57.3% | 63.0% | 53.3% | 0.225 | +5.47% |
| 7 | +5.43% | 49.1% | 4.3% | 37.1% | 0.102 | −10.10% |
| 11 | +0.00% | 49.6% | **0.0%** | **0.0%** | 0.000 | +0.01% |
| 8 | −9.35% | 51.4% | 5.8% | 54.2% | 0.052 | −13.97% |
| 5 | −20.43% | 57.4% | 7.3% | 69.0% | 0.100 | −28.78% |
| 14 | −26.82% | 49.6% | 0.0% | 60.7% | 0.058 | −29.47% |
| 2 | −27.68% | 58.8% | 6.4% | 71.8% | 0.076 | −30.27% |
| 10 | −29.77% | 51.4% | 1.1% | 62.9% | 0.070 | −33.46% |
| 0 | −30.73% | **64.8%** | 15.8% | 67.7% | 0.055 | −23.90% |
| 13 | −32.06% | 48.6% | 4.1% | 64.5% | 0.047 | −26.47% |
| 6 | −32.71% | 61.7% | 26.9% | 77.3% | 0.055 | −14.32% |
| 15 | −37.36% | 49.6% | 0.0% | 68.5% | 0.044 | −32.83% |
| 12 | −40.04% | 50.7% | 22.2% | 58.0% | −0.013 | −19.61% |
| 4 | −42.85% | 57.1% | 6.1% | 67.7% | 0.004 | −38.39% |
| **1** | **−67.55%** | 56.7% | 46.0% | 80.6% | −0.158 | **+15.21%** |

### 16.2 The emergence rate was contaminated — corrected

Phase 14 reported **3/16** emergence from the count of positive *test-fold* returns. That population
was **seeds 1, 9 and 11**, and inspecting them individually shows the count was wrong:

- **Seed 11 is a degenerate no-trade model** — 0.0% long, 0.0% maxDD, Sharpe exactly 0.000. Its
  "+0.01%" is a **silent zero**, not a success. The evaluation protocol warns about exactly this trap
  and it was still counted.
- **Seed 1 is the worst model in the population** (−67.55% full range, Sharpe −0.158), despite having
  the best test-fold return of the whole arm.

Scored properly on the campaign's own criteria — **positive full range and genuinely two-sided** —
emergence is **2/16 = 12.5%** (seeds 3 and 9). Seed 7 is positive but 4.3% long, i.e. one-sided, so it
fails the two-sidedness prerequisite established in P6. The revised pooled estimate across all
measured arms is **4/28 ≈ 14%**, below the 17.9% previously reported.

### 16.3 Which signals actually predict the outcome

| candidate signal | Pearson | Spearman | usable? |
|---|---|---|---|
| **regime score** | **+0.051** | **−0.009** | **no — uncorrelated** |
| train-era regime | +0.038 | +0.059 | no |
| **test-fold return** | **−0.075** | **+0.091** | **no — uncorrelated** |
| long fraction | +0.221 | −0.050 | no |
| maxDD | −0.524 | −0.638 | partly, mechanical |
| Sharpe | +0.849 | +0.750 | **mechanical — see below** |

Simulating each as a selection rule over the sixteen seeds:

| rule | picks | result | rank |
|---|---|---|---|
| highest Sharpe | seed 3 | **+28.28%** | **1 / 16** |
| lowest maxDD | seed 11 | +0.00% | 4 / 16 (the degenerate) |
| highest regime score | seed 0 | −30.73% | 10 / 16 |
| highest train-era regime | seed 0 | −30.73% | 10 / 16 |
| most two-sided (long% ≈ 50) | seed 1 | **−67.55%** | **16 / 16** |
| random seed | — | −21.11% | mean |

### 16.4 Reading this honestly

**The Sharpe result is mechanical, not a discovery.** Sharpe and total return are computed from the
same equity curve over the same window; a correlation of +0.85 between them is close to tautological.
It does **not** demonstrate that a *validation-window* Sharpe would select well, and it must not be
reported as a working selection rule. The same caveat applies to maxDD.

**The two genuinely informative numbers are the ones that are near zero.**

- **Regime score does not predict return across seeds** (Pearson +0.05, Spearman −0.01), and
  selecting on it lands in the bottom half. This is the third and most decisive confirmation of the
  qualification introduced in Phase 13.2: within a single policy, regime accuracy pays
  (Phase 11.3: +8.06% versus −5.54% across years); **across candidate policies it carries no
  information about profit at all.** The regime score is a **screen against beta traps and nothing
  more.** It must never be used as a maximand, and this campaign's practice of scanning seeds on
  regime *plus* return — never regime alone — is retrospectively the correct one.
- **The test-fold return — the only genuinely out-of-sample signal available at selection time — has
  no predictive power either** (Pearson −0.08). This is the heart of the matter.

**A correction to an earlier claim in this session.** Watching the first seeds arrive, I described the
test-fold metric as *"inverted"* on the strength of two data points (seed 1: best test / worst full
range; seed 3: worst test / best full range). With all sixteen in, the correlation is **−0.075** — the
metric is **noise, not an inverted signal.** Two anti-correlated seeds out of sixteen is what noise
looks like. The corrected statement is weaker but true, and the distinction matters: an inverted
metric would be usable by flipping it, whereas a noisy one is unusable in any direction.

### 16.5 What this establishes about the emergence problem

The good seed exists — seed 3 delivers **+28.28% with 34.0% long exposure and a 61.6% regime score**
inside a 15-episode budget. But **nothing measurable at selection time identifies it.** Held-out
performance is uninformative, behaviour is uninformative, and the only signals that "work" are
mechanically derived from the answer itself.

So the ~14% emergence rate is not a tuning deficiency to be optimized away. It reflects a real
property of this problem: **seed quality on an 11-year window is not predictable from a shorter
held-out slice.** The practical consequence for anyone reproducing this work is unchanged from
Phase 15 but now rests on direct measurement rather than inference — **train many short-budget seeds
and evaluate every one of them on the target criterion.** There is no shortcut, and a pipeline that
promotes a single model on validation fitness will, on this problem, usually promote a bad one.

---

## Phase 17 (07-28) — If you cannot select, can you combine?

Phase 16 established that nothing measurable at selection time identifies a good seed. That makes the
~12.5% emergence rate look like a hard wall — but only if a single model must be chosen. The
alternative is to **use every seed and never select at all.** All sixteen seed models from the
15-episode arm were replayed with their per-bar exposure captured, and four combination rules were
evaluated against the individuals.

**Accounting note, stated up front.** Exposure statistics (**long fraction, regime score, agreement**)
are computed directly from the exposure series and are **exact**. The return, Sharpe and drawdown
columns come from the simplified simulator of Phase 13, whose cost constant was calibrated on the
*champion's* turnover; applied to sixteen different models it carries a material error, so **levels
below are indicative and only the comparisons are trustworthy.** Seed 3 shows +53.47% here against
**+28.28% when measured properly through the engine** — a good illustration of the size of that error.

### 17.1 The combination rules

| arm | return* | Sharpe* | maxDD* | **long%** | **regime** |
|---|---|---|---|---|---|
| best individual (seed 3) | +53.47% | 0.276 | 57.5% | **34.0%** | **61.6%** |
| second best (seed 9) | +41.17% | 0.251 | 49.0% | 63.1% | 57.3% |
| **mean of all individuals** | **−12.51%** | — | — | — | — |
| ENSEMBLE mean exposure | −8.06% | 0.058 | 44.8% | **5.4%** | 57.6% |
| ENSEMBLE median exposure | −2.52% | 0.107 | 53.4% | **3.2%** | 55.3% |
| **ENSEMBLE majority vote × mean size** | **+13.29%** | 0.167 | 59.2% | **3.2%** | 55.3% |
| ENSEMBLE vote, ≥⅓ agreement | −5.92% | 0.100 | 56.1% | **0.4%** | 50.4% |

\* simulator levels — see the accounting note.

### 17.2 The ensemble regresses to the mode, and the value is in the tail

The majority vote does beat picking a seed at random by a wide margin (+13.29% against a −12.51%
average), so combination is **not worthless**. But it fails the campaign's objectives outright:

- **Two-sidedness collapses.** Every ensemble is **3.2-5.4% long** — far more one-sided than any
  target, and worse than most individuals. This number is exact, not simulator-derived.
- **Regime skill degrades to 55.3%** against the deliverable's **67.0%** and seed 3's 61.6%.
- It is beaten decisively by the single best seed on every axis.

The mechanism is simple and worth stating plainly. **Most seeds collapse to a permanent short**, so any
vote or average inherits that modal behaviour. The good models — seed 3 at 34.0% long, seed 9 at 63.1%
— are the **tail of the distribution, not its centre**. Averaging pulls toward the centre, which is
precisely where the failures live.

> **Ensembling regresses to the mode. This campaign harvests the tail. The two are in direct
> opposition.**

That also explains why ensembling *looks* attractive from the mean return (it lifts −12.51% to
+13.29%) while being useless for the actual objective: it improves the *average* outcome by diluting
catastrophes, and simultaneously destroys the *behavioural* property that the whole campaign exists to
demonstrate.

### 17.3 P2's cancellation finding, revisited

P2 recorded that a 10-seed ensemble took **zero trades** because the seeds' signals mutually
cancelled, which was read as proof that the seeds were noise rather than a shared pattern. Measured
directly on this population:

| quantity | value |
|---|---|
| mean cross-seed sign agreement | **63.9%** |
| bars where all sixteen seeds agree | **0.0%** |

Both halves of that old finding are now sharpened. The seeds **do** share structure — 63.9% agreement
is well above the 50% coin flip, so they are *not* pure noise, and the total cancellation seen in P2
does not recur under the corrected reward and netting architecture. But agreement is **never
unanimous on a single bar out of 68 156**, which is why averaging thins the net position so severely
and why the ≥⅓-agreement gate leaves the model flat 9% of the time.

### 17.4 Conclusion

Combination is not the escape route from the selection problem. The honest position remains the one
from Phases 15 and 16, now tested from the other direction as well:

- **you cannot predict which seed is good** (Phase 16: every available signal correlates ≈ 0), and
- **you cannot average your way around it** (Phase 17: averaging destroys the behaviour you want).

What is left is the brute-force procedure this campaign actually used, and it should be reported as
the method rather than as an embarrassment: **train many short-budget seeds, evaluate every one of
them on the target criterion, and keep the tail.** At ~12.5% emergence, sixteen seeds give a
roughly 88% chance of at least one qualifying model — which is exactly what happened here, twice
(seed 3 in this arm, and the deliverable in its own).
