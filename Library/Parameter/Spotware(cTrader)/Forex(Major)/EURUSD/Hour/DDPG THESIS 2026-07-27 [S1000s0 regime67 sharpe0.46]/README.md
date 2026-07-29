# DDPG EURUSD H1 — deliverable model (2026-07-27)

Weights: `DDPG/{actor,critic,target_actor,target_critic}` (seed 0 of arm `m_S1000`). The arm's
PROMOTED model was a different, bad seed — validation fitness does not select the good seed
(measured in `CAMPAIGN.md` Phases 14 and 16).

Full research narrative: **`CAMPAIGN.md`** · friction detail: **`FRICTIONS.md`**.

## Recipe
- reward **LogReturn** with **RewardScale = 1000**, NeutralizeReward = FALSE
- mirror 0.50 · market-only observation (`AccountFeatures: false`) · slow regime indicators
  `MOM[ROC 1440/2880] MA[SMA 1440/2880/4320/5040]`
- gamma 0.9995 · net 64x32 · lambda 0.001 · warmup 3000 · threshold 0 · Calmar fitness
- exposure gate 300/0.30 · 30 episodes · frictionless training (real spread, no commission)
- deployed at **timeframe H1** with **DecisionSchedule = D1** (calendar daily; gap-robust, phase-free)
  and **RebalanceThreshold = 0.20**

## Headline result — CANONICAL DELIVERABLE
**10 000 EUR · accurate (tick-derived) spread · IC Markets commission 3.5 points · swap-free ·
2015-01-01 → 2026-01-01 · risk 1 · netting**

| metric | value |
|---|---|
| **return** | **+34.02%** (EURUSD buy-and-hold −2.93%) |
| Sharpe | 0.275 |
| maxDD | 23.5% |
| **regime score** | **67.0%** (50 = coin flip) |
| long / short bars | 66.6% / 32.0% |
| directional runs | 192 long · 200 short |
| trades | 1 586 (144/year) |
| beta to EURUSD | **0.130** ⇒ alpha +3.11%/y, not drift |

Sustained holds: **274 days long through the 2017 rally**, 22.5% of held time in runs ≥ 90 days.

## Costs and hysteresis — the matched 2×2
All four cells are the same weights over the same window; only costs and the rebalance filter differ.

| | no commission | **3.5-point commission** |
|---|---|---|
| **no hysteresis** | +42.48% · Sharpe 0.319 · DD 24.4% | +22.08% · Sharpe 0.207 · DD 25.7% |
| **hysteresis 0.20** | +40.03% · Sharpe 0.307 · DD 23.0% | **+34.02% · Sharpe 0.275 · DD 23.5%** |

- Commission alone costs **−20.40pp** without hysteresis, but only **−6.01pp** with it.
- **The 20% rebalance filter recovers +11.94pp** under realistic costs (34.02 versus 22.08) while
  slightly *reducing* drawdown. It costs 2.45pp when trading is free — a small price for the
  robustness.
- ⚠ **A previous version of this file reported +42.48% as "canonical".** That figure is the
  **zero-commission, no-hysteresis** cell and must not be quoted as the headline. It is retained
  above only as the top-left corner of the 2×2.

## Decision-frequency sweep
⚠ Measured at **zero commission and no hysteresis** (the top-left cell above), so the *levels* are
optimistic; the *comparison between schedules* is what matters.

| schedule | return | regime | Sharpe | maxDD |
|---|---|---|---|---|
| H4 | −34.05% | 68.1% | −0.250 | 47.8% |
| H8 | −21.26% | 68.2% | −0.116 | 40.9% |
| H12 | +22.11% | 67.6% | 0.209 | 32.4% |
| **D1** | **+42.48%** | **68.1%** | **0.319** | **24.4%** |
| W1 | +0.92% | 67.5% | 0.065 | 38.9% |

**The regime score is 67.5-68.2% at EVERY frequency from hourly to weekly** — regime identification is
independent of how often the model acts; only trading costs change. Calendar D1 beats bar-count k=24
(+29.30%, Sharpe 0.250): clock alignment is robust to missing bars, unlike a bar counter. Bar-count
k=120 showed +73.79% while calendar W1 shows only +0.92%, so that headline was partly **phase luck** —
D1 is the honest, reportable configuration.

Regime stability: **train-era 2015-2023 67.5% vs recent 2024-2025 67.4%** (0.1pp decay).

## Per-year decomposition (canonical deliverable configuration)
| year | EURUSD | model | long% | | year | EURUSD | model | long% |
|---|---|---|---|---|---|---|---|---|
| 2015 | −10.05% | +5.60% | 41.2% | | 2021 | −7.18% | +0.22% | 53.2% |
| 2016 | −3.21% | −2.41% | 75.9% | | 2022 | −5.95% | **+21.52%** | 33.7% |
| 2017 | +14.24% | +1.55% | 86.7% | | 2023 | +3.16% | +8.16% | 89.6% |
| 2018 | −4.58% | −2.66% | 57.4% | | 2024 | −6.17% | **−17.29%** | 80.9% |
| 2019 | −2.21% | +9.56% | 48.5% | | 2025 | +13.49% | +8.98% | 83.3% |
| 2020 | +9.08% | +1.06% | 93.7% | | | | | |

**8 of 11 years positive.** Regime-correct years average **+8.06%**, regime-wrong years **−5.54%**.
Survives the deletion of any single year (worst case: drop 2022 → +10.19%).

## Why LogReturn: it unlocks the full position range
DifferentialSortino is scale-invariant in position size, so it cannot prefer a larger position.
A scale-sensitive reward removes that ceiling:

| | DiffSortino (RW1) | LogReturn x1000 |
|---|---|---|
| actor output range | −0.113 .. +0.258 | **−0.798 .. +0.731** |
| median abs signal | 0.027 | **0.200** |
| bars above abs 0.5 | 0.00% | **21.34%** |

## Not a beta trap
Net long 66.6% of bars on an instrument that FELL 2.93%, yet positive overall — profiting while net
long a falling market requires timing, not drift capture. Confirmed by direct measurement:
**beta 0.130**, so the drift explains ≈0.01%/y of a +3.12%/y mean. Contrast the campaign's rejected
beta traps: +38.12% @ regime 37.3% and +49.76% @ regime 49.4%.

## Caveats
- **Emergence ~12.5%** (2 of 16 seeds positive and two-sided; pooled 4/28 ≈ 14%). The *model* is
  robust; the *procedure that finds it* is not.
- **Nothing available at selection time identifies a good seed** — across 16 seeds the regime score
  correlates +0.05 with full-range return and the held-out test return −0.08. Evaluate every seed on
  the target criterion; never trust a promoted model.
- **The return is not statistically significant** (t = 1.07, p = 0.156, bootstrap 95% CI
  [−2.47%, +8.48%]). At Sharpe 0.275 roughly 53 years would be needed for 2σ. The *behaviour* is
  significant (z = +2.05); the *return* is a point estimate.
- **Swap-free is required.** Ordinary overnight financing on 274-day holds is materially adverse.
- ~90% of the evaluation window overlaps training; this is a behavioural thesis, not a deployment
  claim.
- Known weaknesses: timing inside correct regimes (2017: right, only +1.55%) and regime misreads
  (2024: −17.29%, costs 28pp of the total).
