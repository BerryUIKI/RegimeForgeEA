# H4/D1 swing trend candidate research

## Method

This study is price-only and non-ultra-high-frequency. It uses H4 or D1 EMA/ADX/Donchian-style trend breakouts, symmetric long and short signals, next-bar bid/ask execution, ATR stop loss, ATR take profit, trailing stop, time exit, 0.5% equity risk, 2% daily loss lock, and a 20% peak-drawdown entry lock. Volume is not used.

## Training: 2021-2023

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|---:|
| ST01_H4_20_50_adx20_br12 | 4h | -3.74% | 5.96% | 109 | 28.44% | 0.84 |
| ST02_H4_20_50_adx25_br18 | 4h | -2.78% | 4.39% | 65 | 27.69% | 0.81 |
| ST03_H4_50_100_adx20_br12 | 4h | 0.65% | 4.08% | 73 | 38.36% | 1.06 |
| ST04_H4_20_50_adx30_br24 | 4h | -1.73% | 3.46% | 43 | 30.23% | 0.83 |
| ST05_D1_20_50_adx20_br10 | 1d | 1.15% | 1.18% | 7 | 42.86% | 1.98 |
| ST06_D1_10_30_adx25_br20 | 1d | 0.14% | 1.08% | 6 | 50.00% | 1.12 |

## Validation: 2024

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|---:|
| None | - | - | - | - | - | - |

## Decision

No candidate passed training and validation, so 2025 was not evaluated.
