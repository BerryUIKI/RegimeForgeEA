# M5 price-action breakout reversal research

This study excludes volume and order-flow inputs. Signals use completed M5 price
only: long below the previous N-bar low and short above the previous N-bar high.
Orders execute on the next bar bid/ask and use ATR stop loss, take profit,
trailing stop, time exit, 0.25% equity risk, 2% daily lock, and 20% peak-drawdown lock.

## Training: 2021-2023

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
| BR01_12_both_1p5x2_24 | 48.34% | 20.13% | 5616 | 39.89% | 1.05 |
| BR02_12_short_1p5x2_24 | 11.46% | 20.04% | 3838 | 39.13% | 1.02 |
| BR03_12_short_2x3_24 | 5.67% | 20.07% | 3756 | 38.84% | 1.01 |
| BR04_12_short_2x3_12 | 16.57% | 20.12% | 3816 | 43.58% | 1.04 |
| BR05_12_short_2p5x4_24 | -12.67% | 20.07% | 3687 | 39.87% | 0.96 |
| BR06_18_short_2x3_24 | 9.99% | 20.03% | 3019 | 39.22% | 1.03 |
| BR07_24_short_2x3_24 | 15.47% | 20.17% | 2539 | 39.19% | 1.05 |
| BR08_12_both_2x3_24 | 21.38% | 20.13% | 5154 | 39.04% | 1.03 |

## Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
| None | - | - | - | - | - |

## Decision

No candidate passed training and validation; 2025 was not inspected.
