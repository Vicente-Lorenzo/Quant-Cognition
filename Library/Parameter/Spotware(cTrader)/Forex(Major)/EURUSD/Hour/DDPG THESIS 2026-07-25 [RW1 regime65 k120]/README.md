# DDPG EURUSD H1 — thesis deliverable (2026-07-25)

Weights: `DDPG/{actor,critic,target_actor,target_critic}`

## Training recipe
- reward **DifferentialSortino, NeutralizeReward = FALSE** (neutralize inverts the directional signal)
- mirror augmentation, ratio 0.50
- observation: **market-only** (`AccountFeatures: [false]`, 34 features) + slow regime indicators
  `MOMRegime[ROC,1440] MOMEpoch[ROC,2880] MARegime[SMA,1440] MAEpoch[SMA,2880] MACycle[SMA,4320] MAEra[SMA,5040]`
- gamma 0.9995 · net 64x32 · lambda 0.001 · warmup 3000 · threshold 0 · Calmar fitness · exposure gate 300/0.30
- 30 episodes, single seed, frictionless training (accurate spread, no commission/swap)

## Deployment
- **DecisionInterval (action repeat) k = 120** — decide every 120 bars, hold in between
- RiskPercentage selectable; behaviour invariant, only size changes

## Results (canonical: 10 000 EUR, accurate spread, 2015-01-01 -> 2026-01-01)
| risk | return | maxDD | Sharpe | Sortino | long% | regime |
|---|---|---|---|---|---|---|
| 1 | +4.47% | 6.4% | 0.171 | 0.247 | 42.2% | 65.3% |
| 2 | +11.33% | 12.3% | 0.225 | 0.326 | 43.4% | 65.4% |
| 4 | +22.55% | 22.1% | 0.240 | 0.347 | 45.0% | 64.4% |
| 6 | +37.04% | 27.9% | 0.271 | 0.392 | 43.1% | 65.1% |

- **Regime score 65.3%, all 11/11 years aligned** (50% = coin flip, trivial SMA5040 rule = 72.8%)
- Benchmarks: EURUSD buy-and-hold **-2.93%** · S&P500 daily Sharpe 0.674
- Initial-balance invariance: +4.22..+4.71% across 9 900-10 200 (sd 0.17); +2.76..+4.53% across 2 500-100 000 (6/6 positive)
- Sustained holds: 151 directional segments, **140 days continuous long through the 2017 rally**

## Caveat
Single seed. Replication at n=3 (`r_RW7`) collapsed on all three seeds, so this is an
**existence proof**, not a reproducible recipe. Emergence rate under study (`r_RW8`, n=8).
