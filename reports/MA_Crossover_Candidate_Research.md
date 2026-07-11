# Moving-average crossover swing candidate research

## Method

This volume-free study uses completed H1/H4 EMA crossover signals, symmetric long and short entries, next-bar bid/ask execution, ATR stop loss, ATR take profit, trailing stop, time exit, 0.5% equity risk, 2% daily loss lock, and 20% peak drawdown lock.

## Training: 2021-2023

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|---:|
| MA01_H1_10_30_2x3 | 1h | -18.57% | 20.02% | 424 | 31.13% | 0.76 |
| MA02_H1_20_50_2x3 | 1h | -16.29% | 19.09% | 327 | 30.89% | 0.75 |
| MA03_H1_20_100_2p5x4 | 1h | -9.03% | 10.36% | 191 | 29.84% | 0.75 |
| MA04_H4_10_30_2x3 | 4h | 1.27% | 6.48% | 107 | 37.38% | 1.07 |
| MA05_H4_20_50_2p5x4 | 4h | 3.79% | 2.08% | 63 | 42.86% | 1.46 |
| MA06_H4_50_100_3x5 | 4h | 2.16% | 2.00% | 35 | 42.86% | 1.49 |

## Validation: 2024

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|---:|
| MA05_H4_20_50_2p5x4 | 4h | 0.60% | 2.17% | 24 | 37.50% | 1.18 |
| MA06_H4_50_100_3x5 | 4h | 0.39% | 0.89% | 5 | 60.00% | 1.74 |

## Decision

MA05_H4_20_50_2p5x4 was selected before its 2025 holdout run.
