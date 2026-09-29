# Campaigns

The record of the deep-reinforcement-learning campaigns run on this framework: what was set up, what was
measured, what failed and what the next campaign must do differently. Written on 2026-09-25, when the
`Research/` folder that held the campaigns' harnesses, write-ups and result files was deleted ahead of a
new, deeper campaign. Everything worth keeping from it is here; section 0 says where the artifacts went.

Two campaigns, one method:

- **July 2026 — the thesis.** DDPG on EURUSD H1 with daily decisions: **+34.02 % over 2015-2025 against
  buy-and-hold −2.93 %**, Sharpe 0.275, max drawdown 23.5 %, regime score 67.0 % (p 0.025).
- **August 2026 — the seven majors.** The locked recipe retrained on AUDUSD · EURUSD · GBPUSD · NZDUSD ·
  USDCAD · USDCHF · USDJPY, about 1 600 seeds: six pairs profitable, two-sided and robust across start
  balances; USDJPY a documented negative result.

Every number below was measured on the engine **as it was then**. Section 12 lists what has changed since;
no number here replays byte for byte on the current engine, and the next campaign must re-measure before
it compares.

---

## 0. Where the artifacts are

| What | Where |
|---|---|
| **The thesis champion's weights** (`DDPG THESIS 2026-07-27 [S1000s0 regime67 sharpe0.46]`) | `Tests/Golden/Consistency/DDPG/Weights`, SHA-256 identical, with its `Observation.json`. Actor `ffcbbf6c3e62d719…`, critic `1a89cf282f017e50…`, target actor `e584d610b1863ee9…`, target critic `45d7bf9784dda7f5…` |
| The champion and replication folders (weights, the 1 269-line phase-by-phase `CAMPAIGN.md`, `README.md`, `FRICTIONS.md`, the training manifest) | git history, commit `5d0f2f9d` and earlier, under `Library/Parameter/Spotware(cTrader)/Forex(Major)/EURUSD/Hour/` |
| The July lock kit — `REPRODUCE.md`, the training harness `sweep_campaign.py`, the evaluator `robust_eval.py`, `verify_lock.py`, `baseline.json`, the eight analysis scripts | git history, commit `5d0f2f9d`, under `Research/DDPG-EURUSD-H1/` |
| Everything never committed — the 1 822-line seven-pair write-up `CAMPAIGN-7PAIR.md`, its drivers (`campaign.py`, `pair.py`, `score.py`, `champion_override.py`, `publish.py`, `consolidate.py`, `evaluate_seeds.py`, `memory_guard.py`), the per-pair `Learning.yml` files and every result JSON | `%LOCALAPPDATA%\cAlgo\Data\Archive\Research 2026-09-25.zip`, outside the repository |
| The seven-pair seed weights | `%LOCALAPPDATA%\cAlgo\Data\Models\WAVE <PAIR> H1 seeds<a>-<b> champion\Seed N\DDPG` — the only copies of the seven winners |
| The published runs (the web Journal) | `%LOCALAPPDATA%\cAlgo\Data\Runs`, run ids in section 1.2 |
| **Live parameter overrides the campaign installed** | `%LOCALAPPDATA%\cAlgo\Data\Overrides\Spotware(cTrader)\Forex(Major)\<pair>\H1\{Learning,Backtesting}.yml`, provenance `DDPG: Champion`. They applied to every DDPG H1 run on the seven pairs; USDJPY's carried the research-only `RiskPercentage 119.1994` and `ExposureReference 2591`. Archived in `inspect_persistent("Archive")/Overrides 2026-09-28.zip` and deleted with Phase 6's sizing fix, 2026-09-28 |

The champion **cannot be retrained** (section 11) and **no longer replays at its published numbers** on the
current engine (section 12). It survives as an archived artifact; the method is what carries forward.

---

## 1. Results

### 1.1 The thesis champion — EURUSD, EUR 10 000, 2015-01-01 → 2026-01-01

| Metric | Value |
|---|---|
| Return | **+34.02 %** (equity 13 401.55) against buy-and-hold **−2.93 %** |
| Sharpe · max drawdown | 0.275 · 23.5 % |
| Regime score | **67.0 %** — permutation null 50.16 ± 8.22, z +2.05, **p 0.025** (2 000 rotations) |
| Beta · alpha | β +0.130, correlation +0.115, **α +3.11 % a year** (drift explains ≈ 0.01 % a year) |
| Exposure | long 66.6 % · short 32.0 % · flat 1.4 % of bars; 392 directional runs (192 long, 200 short) |
| Holds | median 2 days, mean 7.1 days; longest long 274 days (2017); runs ≥ 90 days are 0.8 % of runs and 22.5 % of held time |
| Rebalances | 1 586 (144 a year); the published Journal run reports 1 069 trades, and the two sources disagree |
| Leverage | gross mean 1.50×, median 1.02×, p95 4.17×, max 7.96× |
| Stability | regime 67.5 % over 2015-2023 and 67.4 % over 2024-2025; the regime score is unchanged across risk 1-8 % and balances 2 500-100 000 |

**Per year** — 8 of 11 positive, mean +3.12 %, median +1.55 %:

| Year | EURUSD | Model | Long % | Year | EURUSD | Model | Long % |
|---|---|---|---|---|---|---|---|
| 2015 | −10.05 % | +5.60 % | 41.2 | 2021 | −7.18 % | +0.22 % | 53.2 |
| 2016 | −3.21 % | −2.41 % | 75.9 | 2022 | −5.95 % | **+21.52 %** | 33.7 |
| 2017 | +14.24 % | +1.55 % | 86.7 | 2023 | +3.16 % | +8.16 % | 89.6 |
| 2018 | −4.58 % | −2.66 % | 57.4 | 2024 | −6.17 % | **−17.29 %** | 80.9 |
| 2019 | −2.21 % | +9.56 % | 48.5 | 2025 | +13.49 % | +8.98 % | 83.3 |
| 2020 | +9.08 % | +1.06 % | 93.7 | | | | |

Regime-correct years average +8.06 %, wrong years −5.54 %. **Dropping 2022 leaves +10.19 %** (2022 is about
two thirds of the total); dropping 2024 gives +61.90 %. 2024 is a structural whipsaw: a 120-day trend
follower cannot turn within a month (October: market −2.21 %, model −7.39 % at 100 % long).

**What the policy learned** (Phase 13): exposure correlates most with the trailing **120-day** return
(+0.591; 1 day +0.048, 20 days +0.230, 250 days +0.447) and agrees 71.3 % with the sign of price against a
120-day SMA. It is **not** that rule: with sizing held identical, the SMA120 sign loses −8.33 % where the
model makes +36.02 % (simulator), always-short makes +11.46 %, always-long −26.49 %. Almost the whole edge
(+3 692 of +4 529 EUR gross) comes from the 28.7 % of bars where the model disagrees with the rule.

**Statistical power** (Phase 12): annual returns give t +1.07, one-sided p 0.156; bootstrap 95 % interval on
the mean annual return [−2.47 %, +8.48 %]. At Sharpe 0.275, reaching t = 2 needs about **53 years** of data.
**The behavior is detectable; the profit is a point estimate.**

**Frictions on the same weights:**

| Commission (swap-free) | Return | Sharpe | Max DD |
|---|---|---|---|
| spread only | +40.03 % | 0.307 | 23.0 % |
| 2 points | +35.52 % | 0.283 | 23.0 % |
| **3.5 points (canonical)** | **+34.02 %** | 0.275 | 23.5 % |
| 7 points | +18.35 % | 0.185 | 25.3 % |
| 14 points | +14.72 % | 0.162 | 26.3 % |

| Swap per lot per night, long / short (3.5 pt commission) | With hysteresis 0.20 | Without |
|---|---|---|
| 0 / 0 | +34.02 % | +22.08 % |
| −0.2 / −0.02 | +28.72 % | +4.87 % |
| −0.5 / −0.05 | +14.97 % | −15.32 % |
| −1.0 / −0.10 | −8.97 % | −40.24 % |
| −2.445 / −0.105 (Spotware demo) | −42.20 % | −88.82 % |

**Swap is the binding friction**: holds of months need a swap-free (swing or Islamic) account. The cost
model is deliberately pessimistic — a standard account's spread charged together with a raw account's
commission, which no broker does at once.

**The replication** — `DDPG REPLICATION 2026-07-28 [E15s3 regime62 short-tilted]`, seed 3 of a 16-seed,
15-episode arm: +28.28 % (five-balance mean +21.97 %, 5/5 positive), **34 % long**, regime 61.6 %, but max
drawdown 62.5 % and regime decaying 64.6 % → 52.6 % from the training era to 2024-2025; −47.88 % at 4×
commission. It reaches the same regime behavior from the **opposite tilt**, which supports timing over
beta, and it was not the deliverable because of its drawdown and decay.

### 1.2 The seven majors — 2015-01-01 → 2026-01-01, 10 000 in the account currency

| Pair (account) | Model | Risk | Return | 5-balance mean (sd) | Sharpe | Max DD | Long % | Regime (null) | p | β | α a year | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USDCAD (USD) | Seed 149 | 1.0 | +220.98 % | 226.56 (10.81) | 0.603 | 49.1 % | 67.7 | 64.2 | 0.0015 | +2.395 | +10.03 % | `d0c461c8eb0e484cbee1210fc89f28fd` |
| GBPUSD (USD) | Seed 77 | 1.0 | +129.05 % | 124.10 (5.11) | 0.397 | 50.4 % | 46.0 | 65.2 | 0.0015 | −0.056 | **+11.64 %** | `e9161d8ecc9e4068b6f3ecc9247410af` |
| AUDUSD (USD) | Seed 153 | 1.0 | +87.17 % | 102.48 (10.58) | 0.348 | 41.1 % | 19.6 | 68.8 (57.7) | 0.041 | −2.008 | +4.95 % | `1e6fbd1f88004072a4c44570ca5b06d3` |
| EURUSD (EUR) | Seed 117 | 1.0 | +70.58 % | 73.90 (3.27) | 0.387 | 46.8 % | 49.0 | 60.4 (49.95) | 0.0055 | +0.265 | +6.61 % | `0337b55c582149ba87a38eb013290783` |
| NZDUSD (USD) | Seed 69 | 1.5 | +60.05 % | 56.39 (3.76) | 0.368 | 23.3 % | — | 72.2 (69.82) | 0.056 | −0.710 | +2.78 % | `faaec4b6be174562971646f85155c96c` |
| USDCHF (USD) | Seed 83 | 1.0 | +54.82 % | 50.55 (5.16) | 0.802 | 8.2 % | 24.2 | 81.0 (60.40) | 0.005 | −0.083 | +3.91 % | `11310f1c1fc340258785c7a1933b4911` |
| USDJPY (USD) | Seed 26 | 23.8 | +16.22 % | 15.74 (0.69) | 0.251 | 24.0 % | **100** | 73.9 | — | +1.012 | **−1.07 %** | `e6dfead07652404492962c57c23764f5` |

- **Every pair is robust-positive** across the five start balances (9 900 / 10 000 / 10 050 / 10 100 /
  10 200), relative sd 4-10 %. Lead with the five-balance mean: two headlines differ from it (USDCAD 220.98
  against 226.56, AUDUSD 87.17 against 102.48).
- **GBPUSD is the cleanest result** (β −0.056, α +11.64 % a year). USDCAD was named the flagship, but its β
  of +2.4 rests on eleven yearly points.
- **USDJPY is a negative result**, published as "directional, not two-sided": 100 % long, β 1.01, no alpha,
  underperforming simply holding the pair (≈ 120 → 150). It first failed through sizing (section 5.3), then
  through market structure — the yen fell almost continuously, so always-long was locally optimal.
- **p is not corrected for selection.** Each winner is the best of 128-256 seeds; strictly, none survives a
  Bonferroni correction at 0.05. The alpha/beta decomposition is the claim to lead with; the permutation
  test is a supporting screen.
- The Journal runs' "Net Return (%)" values (EURUSD 81.47, USDCAD 276.19, GBPUSD 207.62 …) use the old
  per-trade compounding definition, not the equity return (section 12).

**Emergence** — the share of seeds that produce a qualifying model — depends on the pair **and** the seed
range: GBPUSD 18.8 %, EURUSD 4-6 % (2 of 32 on the first wave, 4 of 96 over seeds 0-95), AUDUSD 3.1 % on seeds 0-63 but
14 of 64 on 64-127, USDCHF 0 of 64 on its first wave. The July estimate of 12.5-18 % described EURUSD only
and did not transfer.

---

## 2. The setup

| Item | Value |
|---|---|
| Instrument · bars · decisions | Spotware (cTrader) majors · **H1 bars** for observation and stepping · **daily decisions** (`DecisionSchedule D1`: a new action only when the calendar day of the bar stamp changes; held in between) |
| Period | 2015-01-01 → 2026-01-01, about 68 150 H1 bars |
| Split | `--training 0 --validation 12 --testing 12`: **one fold** — train 2015-01 → 2024-01, validate 2024, test 2025. Not walk-forward, not continuous, and evaluation covered the whole window, training years included |
| Account | 10 000, leverage 30, netting, `RiskPercentage 1.0`, `ATRScale 1.5`. EURUSD on a EUR account; the other six on USD, so the account is always the pair's base or quote currency |
| Training costs | Accurate (tick-derived) spread, **commission 0, swap 0** — costs taught cost avoidance, not direction |
| Canonical evaluation | Accurate spread · **commission 3.5 points** (IC Markets raw) · **swap-free** · netting · D1 decisions · `RebalanceThreshold 0.20` · bar-level resolution · five start balances, or one (10 000) for screening |
| Seeds · threads | `--threads 1` and one thread per worker — required for bit-exact training |

Cost units: the Spotware demo contract's commission of 45 means 4.5 pips a side — extreme; realistic raw
pricing is about 3.5 points (≈ 3.5 USD a lot a side).

---

## 3. The agent — DDPG

Certified against Lillicrap et al. (2015) line by line, critic L2 weight decay included. Deliberate
deviations: LayerNorm instead of BatchNorm, gradient-norm clipping, an actor pre-activation regularizer, a
uniform warmup, and the width and discount below.

| Hyperparameter | Value |
|---|---|
| Hidden layers | **64 × 32** (the base file's 400 × 300 was overridden) |
| Actor · critic | actor fc1-LN-ReLU-fc2-LN-ReLU-μ-tanh; critic takes the action at the second layer, ReLU(state + action) → Q |
| Learning rates | actor 1e-4 · critic 1e-3 (Adam; critic weight decay 0.01) |
| Batch · replay memory | 64 · 1 000 000 |
| Soft update τ | 0.001 |
| Discount γ | **0.9995** (see section 13: its meaning changed at daily steps) |
| Gradient clip | 1.0, norm, both networks — bounds update size; it is **not** the anti-collapse mechanism |
| Actor regularization λ | **0.001** × mean(u²) on the actor's pre-tanh activation; 0, 1e-4 and 0.003 all collapsed |
| Warmup | **3 000** transitions of uniform [−1, 1] actions before any gradient step |
| Exploration | Ornstein-Uhlenbeck θ 0.15, σ 0.2 (stationary sd ≈ 0.36); greedy at evaluation |
| Initialization | final layers U[−3e-3, 3e-3], fan-in uniform elsewhere |
| Updates | one learning step per stored transition (epochs 1, train frequency 1, gradient steps 1) |
| Episodes · patience · checkpoint | **30** · 99 (off) · best, not final (final scored 0/3) |

**DDPG collapses.** In the first phase the greedy action was +1.0000 on all 3 097 test bars: tanh saturation
is an absorbing state reached within the first episode. Clipping only delayed it; SAC stayed plastic. What
prevents collapse is a **scale-sensitive reward** (section 6) together with λ = 0.001.

---

## 4. The observation — 38 features

`AccountFeatures false`, `ObservationWindow 1`. The indicator bank is 16 indicators **in this order** — order
is an input, since the observation is built by walking `TechnicalManagement` in dict order (one set of
weights scored +34.02 %, +31.46 % and −46.19 % under three orders; `Observation.json` now refuses a mismatched
layout):

| # | Key | Indicator | # | Key | Indicator |
|---|---|---|---|---|---|
| 1 | `ATR` | ATR 14 | 9 | `RVFast` | RV 16 |
| 2 | `ER` | Efficiency Ratio 120 | 10 | `RVSlow` | RV 480 |
| 3 | `MAFast` | SMA 24 | 11 | `MOMRegime` | ROC 1440 |
| 4 | `MAMedium` | SMA 120 | 12 | `MOMEpoch` | ROC 2880 |
| 5 | `MASlow` | SMA 480 | 13 | `MARegime` | SMA 1440 |
| 6 | `MOMFast` | ROC 24 | 14 | `MAEpoch` | SMA 2880 |
| 7 | `MOMMedium` | ROC 120 | 15 | `MACycle` | SMA 4320 |
| 8 | `MOMSlow` | ROC 480 | 16 | `MAEra` | SMA 5040 |

The last six are the slow regime indicators — about 60, 120, 180 and 210 days on H1 — and they define the
horizon the model can perceive. The base parameter file carried only the first ten; the six were appended
by the campaign's override.

| # | Feature | Encoding | z-scored |
|---|---|---|---|
| 1-8 | sin and cos of month, weekday, hour, minute | raw | no |
| 9 | signed position exposure | volume ÷ `ActionAPI.maximum_volume`, clipped to ±1 (**defective**, section 5.3) | no |
| 10-13 | gap/open, high, low, close | log move against the previous close ÷ fast RV | no |
| 14 | volume | ln(1 + volume) | yes |
| 15 | spread | (ask − bid) / bid at the close | yes |
| 16 | ATR / close | | yes |
| 17 | fast RV level | | yes |
| 18 | volatility regime | ln(fast RV / slow RV) | no |
| 19 | Efficiency Ratio | | no |
| 20-24 | momentum ×5 | ROC ÷ (fast RV · √lookback) | no |
| 25-38 | per moving average ×7 | distance (close − SMA) / ATR and slope (SMA − previous SMA) / ATR | yes |

Normalization is a causal EWMA z-score, α = 1/200 (`NormalizeWindow 200`), statistics up to the previous
step, 0 on the first step, `EPSILON` 1e-8 added to the variance — `EPSILON` is an input to this model and
must not change. The trained policy keys on `MAEpoch` (SMA 2880 ≈ 120 days). A 16-bar frame stack kept daily
policies alive where 8 collapsed, but the champion uses window 1 with the slow features instead.

---

## 5. Action, sizing and decisions

### 5.1 From action to order

- The actor emits a ∈ [−1, 1]. Target volume = reference volume × a, where the **reference volume** is the
  fixed-fractional size that loses `RiskPercentage` (1 %) of balance over 1.5 × ATR14 (≈ 83 333 units on
  EURUSD at 10 000). No stops, no take-profit, netting.
- An order is sent when |target − current| ≥ max(`VolumeMin`, `RebalanceThreshold` × |reference|), rounded to
  the volume step (1 000).
- **No entry threshold and no deadband.** A band of [−0.4, +0.4] silenced the model — 4 trades in eleven
  years, zero buys: positive actions peaked near +0.27, Q was flat across the band and the actor had no
  gradient. Any deadband rebuilds that plateau.

### 5.2 Decision cadence and hysteresis — the two largest levers

The same weights at different cadences (no commission, no hysteresis):

| Decisions | Return | Regime | Sharpe | Max DD |
|---|---|---|---|---|
| H4 | −34.05 % | 68.1 % | −0.250 | 47.8 % |
| H8 | −21.26 % | 68.2 % | −0.116 | 40.9 % |
| H12 | +22.11 % | 67.6 % | 0.209 | 32.4 % |
| **D1** | **+42.48 %** | 68.1 % | 0.319 | 24.4 % |
| W1 | +0.92 % | 67.5 % | 0.065 | 38.9 % |

The regime call is the same at every cadence; only the cost of acting on it changes. Hourly decisions on the
same weights give −38.57 %, and −64.70 % with commission: **the daily schedule is worth about 81 points**. A
bar-count repeat of 120 once gave +73.79 % against W1's +0.92 % — phase luck, which is why the calendar
schedule was chosen. Training at the daily cadence too was about 6× faster and gave more regime-skilled seeds
(Phase 9); a bar-count action repeat in training divided the gradient updates and gave 0/3 seeds.

**Rebalance hysteresis** — without it daily decisions produced 20 146 trades from about 2 860 decisions,
because ATR and balance drift move the reference volume every bar. That churn is generated **below the
policy**, so the agent cannot learn to avoid it; the filter belongs in the strategy layer:

| `RebalanceThreshold` | Trades | Return at 3.5 pt | Sharpe | Max DD |
|---|---|---|---|---|
| 0 | 20 146 | +22.08 % | 0.207 | 25.7 % |
| 0.05 | 7 784 | +27.62 % | 0.239 | 24.9 % |
| 0.10 | 3 548 | +32.24 % | 0.265 | 25.5 % |
| **0.20** | **1 586** | **+34.02 %** | **0.275** | **23.5 %** |

The cost 2×2 on the champion (commission × hysteresis): none/none **+42.48 %**, none/0.20 +40.03 %, 3.5/none
+22.08 %, 3.5/0.20 **+34.02 %**. Hysteresis recovers **+11.94 points** under costs. (+42.48 % is the
frictionless, unfiltered cell; it was once misreported as the canonical result.)

### 5.3 The sizing defects every campaign weight was trained under

Both were fixed in Phase 6 (2026-09-28) and both invalidate the weights, so everything is retrained in Phase 7.

1. **Risk sizing ignores the quote-to-account conversion.** `amount / (stop × PipSize)` mixes account and
   quote currency, so effective risk is `RiskPercentage / price`: EURUSD 0.909 % instead of 1 %, **USDJPY
   0.0067 %** — 133 units at 10 000, under `VolumeMin` 1 000, so no USDJPY trade could ever fire and the
   actor collapsed with no feedback (final-layer weights 0.0013 against GBPUSD's 0.12). The research
   workaround scaled `RiskPercentage` by the price (× 119.1994) and lives in the live overrides of section 0.
   P&L conversion itself was verified correct against cTrader.
2. **The exposure feature and the order sizer disagree.** Feature 9 divides by `balance / price` while orders
   size by risk: 9.2× on EURUSD (the feature saturates at |a| ≈ 0.11), 8.9× on GBPUSD, **238× on USDJPY**
   (saturates at 0.004 — the agent is blind to its own position). Consequence: **the account balance is a
   policy input.** One EURUSD model made +82.77 % at 10 000, +72.05 % at 11 226 and +43.59 % at 100 000; the
   "path robustness" of five nearby balances is therefore a real perturbation, not a rescaling.

**Risk is not a pure multiplier either**, for the same reason: USDCHF Seed 83's regime fell to about 53 %
above risk 1.0; AUDUSD Seed 146 went from 11 % to 27 % long at 1.5. Re-measure behavior at the delivered
risk. Risk headroom is pair-specific: EURUSD Seed 69 improved to 3.0 (+19.27 % → +82.77 %), GBPUSD and
AUDUSD degraded past 1.0-1.5.

---

## 6. The reward

**Of record:** `LogReturn`, `RewardScale 1000`, `NeutralizeReward false`, `RewardClip 1.0`. Per H1 bar,
r = clip(1000 · ln(Eₜ / Eₜ₋₁), ±1); at the daily cadence the stored transition's reward is the sum of the
hourly clipped rewards since the last decision; `done` is always false. The clip binds for hourly equity
moves above 0.1 %. (The champion's manifest reads `RewardScale 1.0` — a reporting bug; the applied value was
1000.)

| Tried | Result | Lesson |
|---|---|---|
| **DifferentialSortino** (Moody & Saffell; verified bit-exact) | the model traded at about 3 % of size | a scale-invariant reward gives no gradient toward size while λ pulls toward 0 |
| **NeutralizeReward** (subtract held exposure × market return) | removed 87.4 % of the reward; its correlation with direction × market was **−0.786** against +0.895 raw; regime fell to 30-40 %; removing it alone moved regime 30.2 % → 66.2 % | it paid the agent to hold the wrong side. Prevent beta collapse by **mirroring the data**, never by zeroing the reward |
| **Costs inside the reward** (3.5 and 7 points, a mirrored variant) | 0/6, collapse, 0/12 — against 2/12 cost-free | the charged churn comes from the sizing layer, so it reaches the agent as noise; hysteresis is the right tool |

`TurnoverCost` and `SignalSmoothing` exist as knobs; no delivered model used them.

---

## 7. The training protocol

- **Mirror augmentation, ratio 0.50:** every second episode trains on a mirrored tape — price p → p₀²/p, so
  trends invert, highs and lows swap, asks and bids swap, conversions nulled. It symmetrizes the data so
  neither direction is privileged. 0.65 (with gate ratio 0.35) was worse: 3 of 64 seeds qualified (4.7 %).
- **Exposure gate:** on the validation pass an episode is eligible when the weaker side holds at least 300
  bars and 30 % of the stronger (`--balance 300 --ratio 0.30`), with at least 10 trades (`--activity 10`).
  Bars are counted **time-weighted, never by trades** — under netting, closing a short is a buy, and the
  "balanced" flagship of 3 078 buys and 5 630 sells was 91 % short in time. The gate is a preference: the
  best validation Calmar wins among eligible episodes, and 42 % of episodes were eligible.
- **Fitness:** annualized Calmar on the validation fold.
- **Frictionless training** (spread only); frictions are an evaluation condition.
- **Seeds are the search budget, not episodes.** Emergence was flat from 15 to 100 episodes (paired test,
  no effect; 9 of 16 seeds identical between 15 and 30 episodes), and good checkpoints are often fixed within
  the first four episodes. Train many short seeds over **fresh** ranges.
- **Determinism:** bit-exact at one thread within one environment; the product CLI and the research harness
  are the same computation, hash for hash. Multi-threaded runs are not reproducible.
- Note: with 3 000 warmup transitions and about 2 300 daily transitions in the training years, the first
  episode is entirely random, and its validation pass scores an untrained actor — a likely source of
  degenerate no-trade "promotions".

---

## 8. The evaluation methods — rebuild these, precisely

1. **Regime score.** From the per-bar exposure xₜ and closes cₜ: for each calendar year with ≥ 100 bars and
   ≥ 100 active bars, move = c_last / c_first − 1, f = long bars / active bars, aligned = f in up years and
   1 − f in down years; **R = 100 · Σ aligned · |move| / Σ |move|**. 50 is a coin flip. Report it split
   by era (training years against recent) with a per-year table. Keep the active-bars guard: the old
   evaluator counted flat time as short, so a zero-trade model scored the down-years' weight.
2. **Matched-null permutation test.** Rotate the exposure series circularly by k ~ U{1 … n−1}, 2 000
   draws, seeded, market fixed; one-sided **p = (#{R_null ≥ R} + 1) / (2 000 + 1)** (floor 0.0005), z and
   the 5/50/95 percentiles. Rotation keeps the policy's own autocorrelation, hold lengths and long/short mix
   and destroys only its alignment with the market. **The null is per model and per pair** — EURUSD ≈ 50,
   GBPUSD 48.2, AUDUSD 52.4-57.7, USDCAD 57.9-60.7, USDCHF 57.7-60.4, NZDUSD 52.8-69.8 — so a fixed bar (the
   old "> 55 %") is meaningless: always-long scores 64.4 on USDCAD and 73.9 on USDJPY while doing nothing
   clever. Run it at the **delivered** risk and exposure.
3. **Regime ceiling.** Score trivial SMA-cross and ROC-sign rules at 20-360 days and a 30-day forward oracle:
   an SMA120 rule scores **68.1 %** while losing money, and SMA 5040 bars scores 72.8 %. **A regime score is a
   screen, never a quantity to maximize**; across 16 seeds it correlated +0.05 with return.
4. **Two-sidedness.** The weaker side's share of **active** time, min(long, short) / active; gate at 10-20 %.
   Never trade counts.
5. **Persistence.** Directional runs of sign(x), flat runs excluded: count, mean hold, longest, true flips,
   and the share of runs and of held time at or beyond 1, 7, 30 and 90 days. It tracks drawdown — the
   champion flips 2.6× less and holds 2.6× longer than a comparable short-tilted seed.
6. **Path robustness.** The five start balances 9 900 / 10 000 / 10 050 / 10 100 / 10 200: report mean, sd,
   min, max and the positive count; robust-positive = mean > 0 and ≥ 4 of 5 positive. Never promote on one run
   (a balance change alone once moved a result from +8.31 % to −16.00 %).
7. **Yearly beta and alpha.** rᵧ the model's yearly return, mᵧ the pair's: β = cov(r, m) / var(m), alpha a
   year = mean(r) − β · mean(m). Yearly, not daily — a daily recomputation disagreed in sign. Eleven points
   make large betas weak.
8. **Drop-one-year jackknife.** Compound the yearly returns with each year removed; report the worst case
   and each year's contribution. Keep the year-boundary step the old script dropped.
9. **Sign-swap ablation.** Hold the sizing |x| fixed and change only the direction — model, rule sign, model
   magnitude with the rule's sign, always long, always short — in a vectorized simulator first calibrated to
   the real backtest's return; attribute P&L to the bars where model and rule disagree.
10. **Learned lookback.** Correlate exposure with trailing N-day returns (1-250 days) and with SMA-cross
    agreement to name what the policy follows.
11. **Selection-signal validation.** Pearson and Spearman of every screen metric against the outcome across
    seeds, and the rank of each rule's pick — how "no available signal selects the good seed" was proven.
12. **Pool-relative composite** (the final selector): gates return > 0, weaker side ≥ 10 %, mean hold ≥ 24
    bars, regime above its own measured null (a missing null rejects); then the mean of three groups of
    within-pool percentile ranks — money (annual return, Calmar, Sterling), safety (Sharpe, Sortino, max
    drawdown and downside volatility inverted), behavior (balance = weaker side / 50, regime edge, hold,
    longest run). The composite shortlists; the permutation p decides.
13. **Cost decomposition.** Frictionless against canonical, and the cadence × commission 2×2: the ten-minute
    test that separates "no edge" from "edge destroyed by costs".
14. **A lock gate.** Fingerprint weights and golden exports, replay within tolerances (return 0.05, regime
    0.1, Sharpe 0.005), check the critical symbols exist, apply a test floor.

---

## 9. Selection — what failed and what works

- **The pipeline's promotion selects badly.** Validation Calmar promoted a −45.90 % model while a +15.21 %
  one sat in the same batch; the champion's own arm promoted a different seed on re-run. Seeds that never
  trade are "promoted" too. **Evaluate every seed** under canonical conditions.
- **Never judge an arm on its training manifest.** Its full-range figure is the hourly-cadence number: the
  champion's manifest reads −38.57 %, Sharpe −0.31, 20 631 trades.
- **No signal available at selection time predicts the good seed** (16 seeds): regime +0.05, test-fold return
  −0.08, long share +0.22; Sharpe (+0.85) and drawdown (−0.52) are mechanical — they are the return itself.
  Picking by highest regime gave rank 10 of 16; by most two-sided, 16 of 16.
- **Ensembles regress to the mode.** Every combination (mean, median, vote, vote with agreement) fell to
  3.2-5.4 % long — the collapsed-short mode; all 16 seeds agreed on 0 % of bars.
- **The highest-return candidate failed the permutation test on every pair checked:** USDCHF +341 % (p 0.865)
  and +464 % (p 0.973), GBPUSD +260 % (p 0.163), AUDUSD +247 % (p 0.146) and +143 % (p 0.987, published and
  withdrawn), NZDUSD +254 % (p 0.258), USDCAD +82 % (below its null). The modal failure is a one-sided drift
  rider: the July `hi_t1` made +31.54 % on 39 buys and 17 955 sells — about 10× leverage on the pair's drift.
- **Rank by return over drawdown, never raw return** (raw return once picked GBPUSD's +92.63 % at 67.6 %
  drawdown over +76.64 % at 42.8 %).
- **Acceptance, as it ended:** profitable; two-sided (weaker side ≥ 10-20 % of active time); regime above its
  own null with p < 0.10 as a screen; Sharpe and drawdown reported, never gated (an invented drawdown gate
  rejected models the protocol accepts); risk swept afterwards and behavior re-measured at the delivered
  risk; stop a pair after two consecutive waves fail to beat the incumbent.
- **What finds a model:** many short seeds over fresh ranges, every seed evaluated, keep the tail.

---

## 10. Dead ends — do not spend compute on these again

| Lever | Result |
|---|---|
| λ ∈ {0, 1e-4, 0.003} | all collapse; only 0.001 works |
| Wider networks (128 × 64, 256 × 128) | no help |
| More episodes (90-100) | no help; weights save only on improvement |
| Final instead of best checkpoint | 0/3 |
| Very short training (5, 12 episodes) | 0/8 |
| Mirror 0.65 with gate ratio 0.35 | worse than 0.50 / 0.30 |
| Entry thresholds or deadbands | silence the model |
| `NeutralizeReward` | inverts the direction signal |
| Costs in the reward | 0/6 and 0/12 |
| Selecting seeds on any available signal | no predictive power |
| Ensembling seeds | collapses to the short mode |
| A JPY account for USDJPY · scaling the balance · `ExposureReference` alone | byte-identical, or the pair stays 0 %/100 % long |
| Supervised next-bar direction (technical, session, microstructure, cross-FX, US500, calendar features) | best combined AUC 0.530, lost money out of sample in every configuration — right about next-bar prediction, wrong about regime behavior |
| Pure rule-based NNFX and the hybrid RDDPG | −1.44 % and −1.32 % a year; the hybrid's "+19.8 % chained out-of-sample" was selection bias |

**Overturned claims**, recorded so they are not restated: "+19.8 % is the thesis result"; "no alpha in the
data"; "`hi_t1` is best"; "a gross edge exists under spread" (a zero-spread test made results worse);
"leverage and volatility drag explain the shortfall" (measured leverage 0.36-0.55×, drag 0.1 % a year);
"emergence 18.8 %" (12.5 % once a silent zero and the worst full-range seed were counted correctly); "the test
metric is inverted"; "longer training collapses variance" (a paired test read as independent); "+42.48 % is
canonical"; "`--ratio` is inert" (17 of 32 seeds changed at 0.45); "risk does not move Sharpe, regime or
exposure".

---

## 11. Traps

**Engine and measurement**
- Before 2026-07-02 `PortfolioAPI.InitialBalance` was `None`, so every account feature and the fitness
  fallback were 0 in every run. Audit inputs by re-deriving them independently.
- The training manifest reports the hourly cadence; the promoted model is not the best seed (section 9).
- Per-seed weights are **not** exported with a run (only the promoted model), and the model store is shared
  per (security, timeframe, strategy): the next wave on a pair overwrites the last. Archive every seed under a
  label unique per configuration before the next wave (the seven USDJPY waves overwrote one another).
- Trade-based Sharpe and Sortino were pathological, and under Sortino fitness a model that never trades
  (fitness 0) beat any losing trader — selection preferred doing nothing. Use equity-curve ratios.
- Removing stops while keeping ATR sizing turned "2 % risk" into 4-29× leverage; `SizingMode Risk` with risk
  management off gave zero volume.
- **The champion cannot be retrained.** The torch upgrade 2.12.1 → 2.13.0 between 2026-07-27 and 07-28 is the
  only identified change; the 07-28 replication reproduces byte for byte, the 07-27 champion does not.

**Operations** (measured on the engine as it was; re-measure)
- Kill process-pool **children before parents**: fifteen orphans holding 26 GB silently broke two runs.
- Sixteen workers was the ceiling (twenty broke the pool while frames loaded); never evaluate while a wave
  trains — one overlap dropped free memory from 32 GB to 1.1 GB and killed 32 seeds of a USDCAD wave.
- "No workers left" does not mean finished: the parent replays the elected model afterwards (about 90
  minutes once). Detect completion on the run's own status, not on process presence.
- Judge health by CPU, not log staleness: the harness logged only a banner and one completion line.
- A memory guard (free-memory floor 3 GB, grace 4 polls, kill the heaviest campaign process children first)
  was the backstop; its first floor of 8 GB killed legitimate work.
- Temporary folders are pruned at 30 days: the July plots and several analysis inputs were lost that way.

**Tooling bugs found** — hard-coded EURUSD or a EUR 10 000 account in evaluation scripts (a silently wrong
pair), a hard-coded −2.93 % benchmark printed for every pair, two tools reading different `net.csv` columns
(Individual against Aggregated), an unmeasured null defaulting to 50 (it inflated NZDUSD's edge from +2.4 to
+22.2), and a class attribute set in the parent that never reached spawned workers.

---

## 12. What has changed since — re-check before comparing

1. **Market data (Phase 3, 2026-09-25).** The campaigns read the cBot's tables, stored in Europe/London local
   time with each bar labelled by the open of the bar before its content. Today there is one UTC tick tape,
   bars are built on demand on the New York 17:00 clock and labelled by their own open, and extremes are
   two-sided. The champion reads the clock three ways — sin/cos time features, the daily decision bucket (the
   calendar date of the bar stamp) and the bars themselves — so **the champion's golden moved +3 344.09 →
   +4 387.29 at the switch**. Decide deliberately which clock the daily decision should follow: UTC midnight,
   London midnight or the 17:00 New York session.
2. **Float32 prices** until 2026-09-15: every database read downcast prices; fills and features were
   computed on Float32. Now Float64.
3. **Timestamps** were local; now naive UTC.
4. **Bar volume** is now bid updates plus ask updates, which feeds the `ln(1 + volume)` feature.
5. **Statistics** were rebuilt on 2026-09-17: equity-curve ratios per bar and annualized with the risk-free
   rate deducted, intrabar marks on both sides, and "Net Return (%)" now Σ net P&L / opening balance (the
   champion read 38.29 % under the old compounding definition). July and August validation Calmars and
   composite scores are not comparable with today's.
6. **Swap** is charged at the 17:00 New York roll, Wednesday triple; the campaigns were swap-free, but the
   swap table in section 1.1 would move.
7. **Currency conversion** is rebuilt at run time from the direct pair, for any account currency, and a
   missing direct pair is refused. A EUR account on the six USD pairs needs the EUR crosses, which the tape
   does not hold yet.
8. **Sizing** was defective (section 5.3) until Phase 6 fixed it on 2026-09-28; the fix invalidates every
   campaign weight.
9. **Tape start**: 2014-01 today against 2012-11 then; 2016-01-11 → 2016-01-25 is missing in every pair and
   cannot be repaired — it sits inside the training window.
10. **Performance**: the 11-year tick tape reads in about 5 s, Optimization and Learning workers share the
    tapes and the warmup through shared memory (Optimization the bars too), and bar-level runs release the
    ticks — the 55 GB builds, the
    warm-first procedure and the account-currency memory hazard of section 11 belong to the old engine.
11. **Parameters** resolve through the ladder, and every run records the parameters and contract terms it
    used (`Input/Parameters.yml`, `Input/Contract.yml`); weights trained before 2026-09-17 carry no
    `Observation.json` and load as unverified, except the champion, which was backfilled.

---

## 13. For the next campaign

1. **Fix sizing first, then retrain everything** — the quote-to-account conversion in the order sizer and one
   formula for the exposure feature and the sizer (both done in Phase 6, 2026-09-28, and the USDJPY override removed). USDJPY is
   the first pair to re-test: whether it can learn a two-sided policy once it can trade at all is open.
2. **Earn the claims iteration one could not make** — walk-forward with `training > 0` and `--continuous`, an
   honest election rule (`Last` or `Mean`), and a window **never** used for selection (`PLAN.md` 7.1-7.4).
   Pre-register the configuration and correct p for the number of seeds and configurations tried.
3. **Measure behavior before profit**, time-weighted: two-sidedness over active bars and a per-model
   permutation null; regime is a screen. Lead with the alpha/beta decomposition and the five-balance mean.
4. **Keep what worked:** H1 bars with daily decisions, rebalance hysteresis 0.20, LogReturn × 1000 with a
   ±1 clip, mirror 0.50, a time-weighted exposure gate, λ 0.001, 64 × 32, the 16-indicator bank in its order,
   frictionless training with pessimistic evaluation costs, single-threaded training.
5. **Treat the balance, the risk and the account currency as policy inputs** until 5.3 lands; choose them
   before training and re-measure behavior at the delivered level. A risk sweep is pair-specific.
6. **Seeds over episodes**: many short seeds over fresh ranges, a per-pair budget (emergence 3-19 %), every
   seed evaluated and archived; stop a pair after two waves fail to beat the incumbent.
7. **Record costs explicitly** — the spread is about 42 % of the cost and invisible in Learning runs
   (`SpreadPnL` records it since Phase 6) — swap is charged at the contract's own roll, and keep the cost 2×2 as a standard pre-flight.
8. **Re-examine γ.** 0.9995 was chosen as a credit horizon of about 2 000 *hourly* steps; with daily
   transitions it is about eight years — a change of meaning nobody discussed.
9. **Worth one bounded test:** "train at low risk, deliver leveraged". The seven-pair write-up also lists
   "train natively at D1" as untried, but the recipe already trained on the daily schedule, and D1 *bars*
   were tried in the early phases and lost to H1 on data volume (about 2 900 bars against 56 000) — treat it
   as unresolved, not as a free win.
10. **Statistical honesty:** at a Sharpe near 0.3, eleven years cannot establish profit; say so, state the
    tape's sampling eras (tick density differs about thirty-fold across the span), and never claim "ten-plus
    years" as a differentiator — resolution over the span is the distinctive part.
