# DDPG on EURUSD H1 — experimental record

Everything below is measured on the canonical configuration unless stated:
**10 000 EUR · accurate (real) spread · zero commission/swap · 2015-01-01 → 2026-01-01 · netting.**

---

## 1. Benchmarks

| series | window | total | CAGR | Sharpe (daily) |
|---|---|---|---|---|
| EURUSD buy-and-hold (H1, model window) | 11.0y | **−2.93%** | −0.27% | — |
| EURUSD buy-and-hold (D1) | 11.0y | −1.92% | −0.18% | −0.022 |
| S&P 500 (US500) | 10.0y | +235.47% | +12.81% | **+0.674** |

Yearly EURUSD moves (the regime ground truth):
2015 −10.16 · 2016 −3.21 · **2017 +14.24** · 2018 −4.58 · 2019 −2.21 · **2020 +9.08** ·
2021 −7.18 · 2022 −5.95 · **2023 +3.16** · 2024 −6.17 · **2025 +13.49**
Up-total 39.97 · down-total 39.46 · **Σ|move| = 79.4% = the gross prize of perfect regime timing.**

## 2. The regime score (primary metric)

For each year, `aligned = long% if the year rose, else 1 − long%`, weighted by |year move|.
Because up- and down-move totals are nearly equal, **a one-sided collapse scores ~50% by construction**:

| policy | regime score |
|---|---|
| always long | 50.3% |
| always short | 49.7% |
| coin flip | 50% |
| **trivial SMA5040 (210d) cross** | **72.8%** |
| perfect foresight | 100% |

**Return alone is not evidence of skill.** Two of the highest-returning models produced in this
campaign scored at chance: **+38.12% @ regime 37.3%** and **+49.76% @ regime 49.4%** — both are
leveraged shorts riding EURUSD's drift straight through every rally.

## 3. Trivial-rule reference (the target exists and is reachable)

Slow SMA cross, vol-targeted, real spread:

| rule | regime | return | maxDD | long% |
|---|---|---|---|---|
| SMA 480 (20d) | 60.4% | — | — | — |
| SMA 1440 (60d) | 66.3% | −14.68% | 17.6% | 47.3% |
| SMA 2880 (120d) | 69.9% | −8.40% | 11.5% | 45.8% |
| SMA 4320 (180d) | 72.0% | −0.33% | 8.2% | 46.1% |
| **SMA 5040 (210d)** | **72.8%** | **+1.00%** | 6.5% | 45.3% |

Caveat: the *window* was selected by scanning 28 configurations, so **+1.00% is selection-sensitive**
(windows span −8.4%…+1.0%); the **regime score is robust** (69-73% for every window 120d-360d).

## 4. Why the standard DDPG configuration cannot work

### 4.1 `NeutralizeReward` inverts the learning signal
`hedge = held_exposure × market_log_return` is subtracted from the equity log-return — but the
strategy's equity change *is* essentially that product. Measured over 68 153 bars:

| quantity | value |
|---|---|
| corr(raw reward, hedge) | **+0.9989** |
| reward magnitude removed | **87.4%** (σ 4.57e-4 → 5.76e-5) |
| corr(raw, direction·market) | +0.8949 |
| corr(neutralized, direction·market) | **−0.7860** |
| σ(hedge) vs σ(raw) | 5.10e-4 > 4.57e-4 ⇒ **over-subtraction** |

It does not merely remove directional signal — it **inverts** it, penalising the agent for holding
the correct side of a regime.

### 4.2 Confirmed on trained models (dose-response)

| arm | features | γ | long% | return | regime |
|---|---|---|---|---|---|
| MO1 | 20-day | 0.998 | 86.3% | −9.78% | 50.8% |
| GA | 20-day | 0.9995 | 64.2% | −6.93% | 50.8% |
| GB | 20-day | 0.9998 | 0.1% | −0.25% | 49.6% |
| XA | SMA4320/5040 | 0.998 | 13.6% | −24.07% | **40.1%** |
| XB | SMA4320/5040 | 0.9995 | 56.2% | −4.07% | **30.2%** |

With no regime features the score pins at ~50% (nothing to align with). **Given regime-scale features
under the inverted reward it falls *below* chance — 40.1%, then 30.2% as the horizon lengthens** —
i.e. the better the model can see regimes, the more strongly it anti-aligns. XB missed 10 of 11 years.
Features and γ are *enablers*; the reward sign decides the direction.

### 4.3 Two further structural blindnesses
- **Credit horizon:** γ=0.998 ⇒ ~500 bars ≈ 1 month, against regimes lasting 2-12 months.
- **Feature horizon:** the slowest input was 480 bars (~20 days) — no input described a multi-month regime.

## 4bis. The reward must also be SCALE-SENSITIVE (best model)

`DifferentialSortino` is **scale-invariant in position size**: doubling exposure doubles both the
return and the downside, leaving the ratio unchanged. It therefore has **no gradient pushing the
position larger**, while the actor regularizer λ pulls the pre-tanh activation toward zero. The
equilibrium is a tiny position — the model trades at a **median 2.7% of available size and never
exceeds 26%**.

Replacing it with a **scale-sensitive** reward (`LogReturn`, `RewardScale 1000`) removes the ceiling:

| | DifferentialSortino | LogReturn ×1000 |
|---|---|---|
| actor output range | −0.113 … +0.258 | **−0.798 … +0.731** |
| median \|signal\| | 0.027 | **0.200** |
| bars beyond \|0.5\| | 0.00% | **21.34%** |

**This single change produced the best model of the campaign** (`m_S1000` seed 0), identical to §5 in
every other respect:

| metric | §5 model (DiffSortino) | **best model (LogReturn ×1000)** |
|---|---|---|
| regime score | 65.3% | **67.5%** |
| return (mean of 5 initial balances) | +4.51% (sd 0.17) | **+73.79%** (sd 0.37, 5/5 positive) |
| Sharpe / Sortino | 0.171 / 0.247 | **0.457 / 0.665** |
| maxDD | 6.4% | 28.5% |
| long share | 42.2% | 64.3% |
| regime, train-era → recent | 65.7 → 63.9 (−1.8pp) | **67.5 → 67.4 (−0.1pp)** |
| directional segments / longest hold | 151 / 140d | **104 / 255d** |

Per-year: it captures **all four up-years strongly** (long 81.4% in 2017, 78.9% in 2020, 86.5% in 2023,
90.3% in 2025) and both large declines (2015, 2022), missing only the four *small* down-years.
Longest holds: **255 days continuously long through the 2020-06→2021-06 rally** and **220 days through
the 2025 rally**.

**Anti-beta argument.** The model is **64.3% long on an instrument that fell 2.93%** over the period and
still returns +73.79%. Drift-capture cannot produce this — profiting while net long a declining market
requires genuine timing. Contrast the campaign's rejected beta traps: +38.12% at regime 37.3% and
+49.76% at regime 49.4%, both of which shorted straight through every rally.

**Trade-off to state:** the scale-sensitive reward also raises drawdown (28.5% vs 6.4%) and turnover
(21 580 vs 2 336 trades), because LogReturn rewards holding the drift and therefore re-admits some of the
directional-collapse pressure that DifferentialSortino suppresses. Two of the three seeds in this arm
collapsed.

## 5. The corrected configuration (DifferentialSortino variant)

`raw DifferentialSortino (neutralize OFF) + mirror 0.50 + SMA4320/5040 regime features +
γ 0.9995 + market-only observation (34 features) + 64×32 + λ 0.001 + Calmar fitness +
exposure gate (300 bars / 0.30 ratio)`, deployed with **action repeat k = 120**.

Removing the inversion alone moved the regime score **30.2% → 66.2%** at otherwise identical settings.

### 5.1 Action repeat (deployment)
Decide every k bars, hold in between. Churn was the entire remaining gap:

| k | return | trades | regime |
|---|---|---|---|
| 1 | −4.62% | 8 351 | 66.2% |
| 8 | −2.39% | 6 084 | 67.1% |
| 24 | +0.18% | 3 580 | 68.7% |
| **120** | **+4.47%** | **2 336** | 65.3% |

It also removed the P&L path-chaos: return spread across initial balances fell from **24pp to 0.49pp**.
Training *with* action repeat is worse (it divides gradient updates by k) — **train at k=1, deploy at k=120.**

### 5.2 Final results

| risk | return | maxDD | Sharpe | Sortino | long% | regime |
|---|---|---|---|---|---|---|
| 1 | +4.47% | 6.4% | 0.171 | 0.247 | 42.2% | 65.3% |
| 2 | +11.33% | 12.3% | 0.225 | 0.326 | 43.4% | 65.4% |
| 4 | +22.55% | 22.1% | 0.240 | 0.347 | 45.0% | 64.4% |
| **6** | **+37.04%** | 27.9% | 0.271 | 0.392 | 43.1% | 65.1% |
| 8 | +31.07% | 36.5% | 0.271 | — | 42.9% | 65.3% |

**Regime score 65.3%, all 11/11 years aligned.** Per-year long share: 74.0% in 2017 (+14.24),
69.4% in 2020 (+9.08), 69.4% in 2023 (+3.16), 61.8% in 2025 (+13.49); 16.7% in 2022 (−5.95),
31.4% in 2024 (−6.17). Sustained holds: 151 directional segments (vs 2 276 before action repeat),
**140 days continuously long through the 2017 rally**.

### 5.3 Invariance (generalisation evidence)
- **Position size:** regime 64.4-65.4% and long-share 42-45% are unchanged from risk 1 to risk 8 —
  sizing is orthogonal to the learned policy. Efficiency peaks near risk 6; risk 8 is past the drag knee.
- **Account size:** positive at all six sizes over a **40× range** (2 500 → 100 000): +2.76%…+4.53%,
  DD 5.6-7.6%, Sharpe 0.11-0.17. Execution granularity is *not* invariant (243 → 24 118 trades) because
  `VolumeMin` lets larger accounts express finer position deltas — a property of discrete lot sizing.
- **Time:** regime 65.7% (2015-2023) vs 63.9% (2024-2025) — 1.8pp decay.

### 5.4 Signal characteristics
Actor output spans **−0.113 … +0.258**, median |signal| 0.027 — this variant trades at a small fraction of
available size, for the scale-invariance reason set out in §4bis (resolved there by LogReturn).
The **long side reaches 2.3× further than the short side**, matching the market: up-years are fewer but
~2× larger (mean |move| 10.0% vs 5.6%). The agent sizes to expected regime magnitude.

## 6. Limitations (state plainly)
1. **Reproducibility is the open question.** The result is currently an **existence proof**. Replication
   attempts at n=3/8/24 seeds collapsed, but those runs were later found to have been executed with the
   **exposure gate silently disabled** by a parameter-passing defect in the multi-seed worker, so they did
   *not* replicate the configuration. A corrected replication is in progress.
2. Action repeat k=120 is applied at inference to a model trained at k=1 (standard practice — frame-skip,
   Mnih et al. 2015 — but it should be stated).
3. Selection of the trivial-rule benchmark window was in-sample.
4. Full-range results are ~90% in-sample by construction (training 2015-2024).
5. Sharpe (0.171-0.271) remains well below the S&P 500's 0.674 over the same decade. Leverage cannot
   close that gap — Sharpe is scale-invariant. Higher regime accuracy is the only route.
