# Long-only trend candidate research

## Factor

Trade only when EMA(fast) exceeds EMA(slow), ADX exceeds its threshold, and the closed price breaks the prior N-bar high. The strategy does not short. Stop, target, and trailing distances are ATR multiples.

The fixed study uses 2021–2023 training, 2024 validation, and 2025 final holdout. A candidate must have positive return, profit factor >= 1.05, maximum drawdown <= 20%, and at least 30 trades in both training and validation.

### Training: 2021–2023

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| L01_H1_20_100 | 1h | -1.74% | 6.87% | 88 | 29.55% | 0.90 |
| L02_H1_30_150 | 1h | -3.70% | 6.16% | 79 | 27.85% | 0.76 |
| L03_H4_10_50 | 4h | 1.86% | 2.55% | 52 | 34.62% | 1.22 |
| L04_H4_20_100 | 4h | 1.38% | 2.09% | 23 | 39.13% | 1.42 |
| L05_D1_10_50 | 1D | 0.95% | 0.90% | 5 | 40.00% | 2.08 |
| L06_D1_20_100 | 1D | 0.00% | -0.00% | 0 | 0.00% | N/A |

### Validation: 2024

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| L03_H4_10_50 | 4h | 3.00% | 0.92% | 16 | 62.50% | 3.10 |

## Selection

No candidate passed the training and validation gates.

No holdout run was authorized.

## Decision

Do not enable this factor in the EA unless it passes the final holdout. PAXGUSDT is a gold-linked public proxy, not broker-native XAUUSD data.
