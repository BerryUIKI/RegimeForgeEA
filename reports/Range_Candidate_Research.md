# Range candidate research

## Method

Eight pre-defined range-only Bollinger/RSI mean-reversion candidates were evaluated. The test uses 2021–2023 for training, 2024 for validation, and 2025 as final holdout. The holdout is not used for candidate selection. Research uses 0.5% fixed-fractional risk and disables safety locks to reveal full-period behavior.

### Training: 2021–2023

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| R01_M15_standard | 15min | -10.27% | 13.23% | 197 | 35.53% | 0.72 |
| R02_M15_strict | 15min | -2.06% | 3.14% | 23 | 26.09% | 0.57 |
| R03_M15_long | 15min | -6.06% | 9.25% | 118 | 31.36% | 0.70 |
| R04_M30_standard | 30min | -5.21% | 5.55% | 111 | 34.23% | 0.74 |
| R05_M30_strict | 30min | -0.07% | 0.74% | 16 | 25.00% | 0.95 |
| R06_H1_standard | 1h | -1.33% | 4.05% | 86 | 39.53% | 0.91 |
| R07_H1_strict | 1h | -0.31% | 1.48% | 14 | 28.57% | 0.85 |
| R08_H1_long | 1h | -3.58% | 5.85% | 57 | 31.58% | 0.60 |

### Validation: 2024

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|


## Selection

No candidate passed the pre-defined training and validation gates. The EA defaults were not changed.

No final-holdout run was authorized by the selection gate.

## Decision

Do not change the MQL5 EA unless a selected candidate passes the final holdout with positive return, profit factor above 1.05, and maximum drawdown no greater than 20%. PAXGUSDT remains a gold-linked public proxy, not broker-native XAUUSD data.
