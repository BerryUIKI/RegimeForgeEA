# H4 EMA crossover quality audit

## Decision

**Not high quality for deployment.** The selected candidate remains a useful
research artifact, but it fails this stricter quality audit because independent
samples are small, short-only validation is negative, and modestly adverse
costs eliminate validation profitability. No live or demo activation should be
inferred from the original proxy-screen pass.

## Cost sensitivity

The 35-point baseline is the original fixed proxy assumption. Higher-cost rows
remove the entry-spread lock only to isolate the effect of cost; they are not
recommended operating settings.

| Spread points | Sample | Return | Max drawdown | Trades | PF |
|---|---|---:|---:|---:|---:|
| 35 | Training | 3.79% | 2.08% | 63 | 1.46 |
| 35 | Validation | 0.60% | 2.17% | 24 | 1.18 |
| 35 | Holdout | 0.40% | 1.03% | 8 | 1.29 |
| 70 | Training | 3.62% | 2.11% | 63 | 1.44 |
| 70 | Validation | 0.53% | 2.20% | 24 | 1.15 |
| 70 | Holdout | 0.39% | 1.04% | 8 | 1.28 |
| 105 | Training | 3.06% | 2.21% | 63 | 1.36 |
| 105 | Validation | -0.09% | 2.24% | 24 | 0.98 |
| 105 | Holdout | 0.37% | 1.05% | 8 | 1.27 |
| 140 | Training | 2.89% | 2.31% | 63 | 1.34 |
| 140 | Validation | -0.16% | 2.28% | 24 | 0.96 |
| 140 | Holdout | -0.44% | 1.62% | 8 | 0.69 |

## Long/short decomposition at the original cost

| Side | Sample | Return | Max drawdown | Trades | PF |
|---|---|---:|---:|---:|---:|
| Long only | Training | 2.82% | 1.70% | 35 | 1.65 |
| Long only | Validation | 0.77% | 0.88% | 15 | 1.40 |
| Long only | Holdout | 0.68% | 0.67% | 4 | 2.66 |
| Short only | Training | 1.52% | 1.74% | 34 | 1.34 |
| Short only | Validation | -0.29% | 1.52% | 11 | 0.82 |
| Short only | Holdout | 0.36% | 0.83% | 5 | 1.38 |

## Calendar-year stability at the original cost

| Year | Return | Max drawdown | Trades | PF |
|---:|---:|---:|---:|---:|
| 2021 | -0.28% | 1.72% | 18 | 0.89 |
| 2022 | 0.59% | 2.07% | 23 | 1.17 |
| 2023 | 3.73% | 0.65% | 20 | 3.18 |
| 2024 | 0.60% | 2.17% | 24 | 1.18 |
| 2025 | 0.40% | 1.03% | 8 | 1.29 |

## Quality assessment

The original chronological screen is valid as a preliminary hypothesis test:
the rule uses completed bars, takes both directions, defines exits before the
holdout, and has positive aggregate results at the baseline proxy cost. It is
not a sufficient basis for a high-quality classification. The 2024 validation
contains 24 trades and the 2025 holdout only 8. Calendar results are uneven,
with a negative 2021 and most profit concentrated in 2023. Most importantly,
the short-only sleeve loses in validation (PF below 1.0), so the evidence for
the requested short-selling component is not stable.

At 105 fixed spread points, validation turns negative; at 140 points, both
validation and holdout are negative. Broker-native XAUUSD costs can be variable
and can include spread, commission, swap, slippage, and gap risk, none of which
are captured by the baseline model. Therefore the candidate does not clear a
reasonable robustness threshold for deployment.

## Required evidence before reconsideration

1. MT5 backtests on broker-native XAUUSD bid/ask data with commission, swap,
   realistic variable spread, and the broker's actual contract specification.
2. A pre-registered, untouched out-of-sample period with a materially larger
   trade count than the present eight-trade holdout.
3. Side-specific evidence showing that both long and short components are
   robust, or an explicit redesign to remove the unsupported side.
4. Demo forward testing with order-level reconciliation against the EA log.
5. A new quality audit using the same adverse-cost and stability criteria.
