# Price-only live-strategy candidate research

## Live-trading controls

This study excludes all volume inputs. Each candidate uses symmetric long and short entries, next-bar bid/ask execution, ATR stop loss, ATR take profit, trailing stop, fixed maximum holding time, 0.25% risk per trade, 2% daily loss lock, and a 20% peak-drawdown entry lock. Signals use only completed M5 and completed H1/H4 information.

## Formula

Long when the completed higher-timeframe EMA fast value exceeds the slow value and the M5 return is at or below its shifted trailing lower quantile. Short when the completed higher-timeframe fast EMA is below the slow EMA and the M5 return is at or above its shifted trailing upper quantile. Stops and targets are ATR multiples specified per candidate.

### Training: 2021-2023

| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|
| PR01_H1_q20_r3_1p5x2_24 | -16.58% | 20.10% | 2871 | 36.29% | 0.93 |
| PR02_H1_q10_r3_1p5x2_24 | -0.10% | 20.06% | 3740 | 37.83% | 1.00 |
| PR03_H1_q20_r3_2x3_48 | -18.68% | 20.15% | 2322 | 35.57% | 0.88 |
| PR04_H1slow_q20_r6_2x3_48 | -19.74% | 20.02% | 2255 | 35.70% | 0.87 |

### Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|
| None | - | - | - | - | - |

## Selection

No candidate passed training and validation; 2025 was not evaluated.

No final holdout run was authorized.

## Decision

Do not enable a candidate in MQL5 unless it passes all three periods and subsequently passes broker-native XAUUSD Bid/Ask testing with actual costs.
