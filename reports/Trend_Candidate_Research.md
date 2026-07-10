# Trend candidate research

## Method

Eight pre-defined Donchian/EMA/ADX trend candidates were evaluated. The process uses 2021–2023 for training, 2024 for validation, and 2025 as a final holdout. The holdout is not used to select a candidate. Research uses 0.5% fixed-fractional risk and disables safety locks solely to reveal full-period strategy behavior.

A candidate must have positive return, profit factor at least 1.05, maximum drawdown no greater than 20%, and at least 30 trades in both training and validation to reach the holdout.

### Training: 2021–2023

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|
| T01_M15_baseline | 15min | -77.57% | 77.57% | 1345 | 25.43% | 0.47 |
| T02_M15_longer | 15min | -51.14% | 52.31% | 746 | 25.60% | 0.54 |
| T03_M15_slow | 15min | -48.85% | 50.57% | 798 | 27.57% | 0.57 |
| T04_M30_baseline | 30min | -42.37% | 42.67% | 696 | 28.74% | 0.62 |
| T05_M30_longer | 30min | -18.59% | 18.62% | 385 | 28.83% | 0.72 |
| T06_H1_baseline | 1h | -14.67% | 18.34% | 346 | 32.66% | 0.76 |
| T07_H1_slow | 1h | -7.28% | 10.45% | 185 | 29.19% | 0.78 |
| T08_H1_balanced | 1h | -9.25% | 14.26% | 256 | 30.08% | 0.79 |

### Validation: 2024

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|


## Selection

No candidate passed the pre-defined training and validation gates. The EA defaults were not changed.

No final-holdout run was authorized by the selection gate.

## Decision

Do not change EA defaults unless a selected candidate also has positive final-holdout return, profit factor above 1.05, and maximum drawdown no greater than 20%. This study uses PAXGUSDT as a gold-linked public proxy, not broker-native XAUUSD data.
