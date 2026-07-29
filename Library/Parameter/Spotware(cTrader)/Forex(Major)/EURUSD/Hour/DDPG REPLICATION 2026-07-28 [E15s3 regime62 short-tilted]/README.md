# DDPG EURUSD H1 — independent replication (2026-07-28)

**This is not the deliverable.** The deliverable is
`DDPG THESIS 2026-07-27 [S1000s0 regime67 sharpe0.46]`. This model is preserved because it is an
**independently trained second model that meets every campaign objective**, and therefore evidence
that the *finding* replicates even though the *procedure that produces it* is unreliable
(emergence ~12.5%, see `CAMPAIGN.md` Phases 14 and 16).

Weights: `DDPG/{actor,critic,target_actor,target_critic}` — **seed 3 of arm `r_E15`**
(champion recipe at a **15-episode** budget, 16 seeds). Discovered by scanning all sixteen seeds on
the target criterion; the pipeline's own promotion did not select it.

## Why it matters: the same behaviour with the opposite tilt

| | deliverable (`S1000s0`) | **this model (`E15s3`)** |
|---|---|---|
| episodes trained | 30 | **15** |
| return (11y) | **+34.02%** | +28.28% |
| long fraction | **66.6% (long-tilted)** | **34.0% (short-tilted)** |
| regime score | **67.0%** | 61.6% |
| Sharpe | 0.275 | 0.212 |
| maxDD | **23.5%** | 63.4% |
| regime decay (train-era → recent) | **0.1pp** | 12.0pp |

Two independently trained models reach positive, two-sided, regime-following behaviour from
**opposite directional tilts** — one net long 66.6% of bars, the other net short 66.0%. Since they
cannot both be harvesting the same directional drift, this is independent support for the Phase 11
conclusion that the return is **timing, not beta** (deliverable β = 0.130).

This model also lands inside the campaign's *original* target band (30-40% long) that the deliverable
overshoots.

## Evaluation
`10 000 EUR · accurate spread · commission 3.5 points · swap-free · D1 decisions ·
RebalanceThreshold 0.20 · 2015-01-01 → 2026-01-01`

- **5-balance robustness protocol: +21.97% mean · sd 4.93 · range +17.43% to +28.28% · positive 5/5**
- regime score **61.6%** · split: train-era 2015-2023 **64.6%** vs recent 2024-2025 **52.6%**
- long fraction 34.0% · maxDD 63.4% · Sharpe 0.212 · Sortino 0.302

## Why it is NOT the deliverable
- **maxDD 63.4%** against the deliverable's 23.5% — the dominant objection.
- **Regime decays 12.0pp** between the train era and recent years, where the deliverable decays
  0.1pp. Its regime skill is much less stable out toward the present.
- Lower return and lower Sharpe.
- At **4× commission (14 points) it collapses to −47.88%**, whereas the deliverable stays positive at
  the same stress (see `FRICTIONS.md`). Its edge is materially thinner.

## Provenance
Recovered from the sweep scratch directory under `%TEMP%`, which is wiped periodically — archived
here so the replication evidence is not lost. Training is bit-exactly reproducible at
`threads=1`/`worker_threads=1` (Phase 15), so this model can be regenerated from the recipe and
seed 3.
