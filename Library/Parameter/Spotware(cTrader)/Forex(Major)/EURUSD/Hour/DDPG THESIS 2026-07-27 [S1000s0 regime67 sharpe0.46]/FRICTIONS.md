# Friction analysis — EURUSD H1 timeframe, D1 decisions, 20% rebalance hysteresis

Accurate (real, tick-derived) spread is applied in EVERY row. Commission is quoted in points
(1 pt = 0.1 pip/side). IC Markets / Pepperstone raw ~= $3.5 per lot per side ~= 3.5 pts.
Swap is per lot per night (long/short).

## Commission sensitivity (swap-free)
| friction | return | Sharpe | maxDD | regime | trades |
|---|---|---|---|---|---|
| spread only | +40.03% | 0.307 | 23.0% | 66.6% | 1 595 |
| +2 pts (0.2 pip/side) | +35.52% | 0.283 | 23.0% | 66.7% | 1 600 |
| **+3.5 pts (IC Markets raw)** | **+34.02%** | **0.275** | 23.5% | 67.0% | 1 586 |
| +7 pts (2x IC Markets) | +18.35% | 0.185 | 25.3% | 66.6% | 1 589 |
| +14 pts (4x IC Markets) | +14.72% | 0.162 | 26.3% | 66.5% | 1 599 |

Positive at 4x real commission. Regime score 66.5-67.0% at every level - behaviour is
unaffected by cost; only P&L changes.

## Swap sensitivity (all rows include 3.5 pt commission)
| swap/night | with 20% hysteresis | without hysteresis |
|---|---|---|
| 0 (swap-free) | +34.02% | +22.08% |
| -0.2 / -0.02 | +28.72% | +4.87% |
| -0.5 / -0.05 | **+14.97%** | -15.32% |
| -1.0 / -0.10 | -8.97% | -40.24% |
| -2.445 / -0.105 (Spotware demo) | -42.20% | -88.82% |

Swap is the binding friction, as expected for a strategy that is ~65% long with holds up to
265 days: negative carry compounds across the whole position. With hysteresis the strategy
tolerates up to -0.5/night and degrades gracefully instead of collapsing.
**Recommended venue: a swap-free / swing / Islamic account** - wide spread (which we already
model), high commission tolerance (works to 4x raw), zero swap.

## Rebalance hysteresis - why it matters
At D1 the raw strategy made **20 146 trades against ~2 860 daily decisions** (7x more trades
than decisions). Cause: `target = reference_volume(ATR, balance) x action`, so ATR/balance drift
moves the target every bar even when the agent holds its action constant. The agent cannot learn
to avoid this - it is generated below the policy, in the sizing layer.
`RebalanceThreshold` requires `|delta| >= max(VolumeMin, threshold x |reference_volume|)`:

| threshold | trades | return @3.5pt | Sharpe | maxDD |
|---|---|---|---|---|
| 0 | 20 146 | +22.08% | 0.207 | 25.7% |
| 0.05 | 7 784 | +27.62% | 0.239 | 24.9% |
| 0.10 | 3 548 | +32.24% | 0.265 | 25.5% |
| **0.20** | **1 586** | **+34.02%** | **0.275** | **23.5%** |

13x fewer trades, +12pp return, drawdown and regime score unchanged.

## Methodological note (state this in the paper)
We apply standard-account (wide, accurate) spread AND raw-account commission simultaneously.
Real brokers charge one or the other: raw accounts have ~0.1 pip spreads *because* they charge
commission. Our numbers are therefore **conservative over-costing**, not optimistic.
