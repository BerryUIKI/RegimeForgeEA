# Volume-confirmed reversal order research

## Factor formula

Let r_3(t) = Close(t) / Close(t-3) - 1. Let q_20(t), q_80(t) be the trailing 20-trading-day 20th and 80th percentiles of r_3, shifted one M5 bar. Let V_ratio(t) = Volume(t) / SMA_60(Volume)(t).

- Long if r_3(t) crosses below q_20(t) and V_ratio(t) >= 1.5.
- Short if r_3(t) crosses above q_80(t) and V_ratio(t) >= 1.5.
- Enter at the next M5 open; exit after the configured number of M5 bars or at the ATR protective stop.

Candidates are fixed before the 2025 holdout. Training requires 500+ trades, validation requires 150+ trades, plus positive return, PF >= 1.05, and maximum drawdown <= 20%.

### Training: 2021–2023

| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|
| VR01_exit_6_stop_3 | -45.38% | 57.36% | 9413 | 47.12% | 0.90 |
| VR02_exit_12_stop_3 | -34.70% | 47.86% | 7701 | 48.19% | 0.93 |
| VR03_exit_24_stop_3 | -41.34% | 49.70% | 5919 | 45.95% | 0.90 |
| VR04_exit_12_stop_2 | -72.97% | 78.04% | 8263 | 43.13% | 0.88 |

### Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|


## Selection

No candidate passed the training and validation gates.

No final-holdout run was authorized.

## Decision

Only a candidate with a positive final holdout may be considered for MQL5 implementation and broker-native cost validation.
