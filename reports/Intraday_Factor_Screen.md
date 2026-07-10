# Intraday factor screen

## Method

The screen evaluates fixed M5 factors on 2021–2023 training and 2024 validation data. Each observation assumes entry at the next tradable price and subtracts one 0.35 USD spread. The 2025 holdout is not used. Extreme-return thresholds are rolling 20-trading-day 20/80 quantiles, shifted one bar so they use only information known at the signal time.

Factors: 3-bar and 6-bar momentum quantiles, 12-bar breakouts, and volume-confirmed 3-bar momentum. Sessions are Asia (00–06 UTC), London (07–12 UTC), New York (13–20 UTC), and all hours. Horizons are 3, 6, 12, and 24 M5 bars.

A factor is retained only when it has positive net mean return in both periods, at least 100 training and 30 validation observations, training t-statistic >= 1.5, and validation t-statistic >= 1.0.

## Factors passing both periods

| Factor | Side | Session | Horizon | Train net bps | Train t | Validation net bps | Validation t |
|---|---|---|---:|---:|---:|---:|---:|
| volume_confirmed_reversal | short | asia_00_06 | 24 | 2.096 | 3.55 | 5.644 | 5.53 |
| breakout_12_reversal | short | asia_00_06 | 24 | 3.518 | 5.50 | 4.191 | 4.20 |
| volume_confirmed_reversal | short | london_07_12 | 24 | 2.472 | 3.98 | 3.572 | 4.29 |
| volume_confirmed_reversal | short | london_07_12 | 12 | 2.314 | 5.01 | 3.501 | 5.56 |
| volume_confirmed_reversal | short | all | 24 | 1.706 | 5.38 | 3.474 | 6.11 |
| volume_confirmed_reversal | short | london_07_12 | 6 | 1.194 | 3.40 | 3.272 | 6.66 |
| breakout_12_reversal | long | asia_00_06 | 12 | 3.287 | 8.08 | 3.214 | 4.09 |
| breakout_12_reversal | short | london_07_12 | 24 | 2.849 | 3.56 | 3.187 | 2.84 |
| volume_confirmed_reversal | short | all | 12 | 1.742 | 6.99 | 3.043 | 6.59 |
| breakout_12_reversal | long | asia_00_06 | 24 | 3.731 | 7.15 | 2.874 | 2.74 |
| breakout_12_reversal | short | london_07_12 | 12 | 2.647 | 4.48 | 2.817 | 3.48 |
| breakout_12_reversal | long | asia_00_06 | 6 | 2.020 | 6.12 | 2.740 | 4.58 |
| volume_confirmed_reversal | long | london_07_12 | 24 | 1.816 | 3.02 | 2.591 | 2.84 |
| mom_6_reversal | short | asia_00_06 | 24 | 1.675 | 6.70 | 2.519 | 5.72 |
| breakout_12_reversal | short | all | 24 | 2.612 | 6.75 | 2.502 | 3.76 |
| mom_3_reversal | short | asia_00_06 | 24 | 1.237 | 5.11 | 2.449 | 5.16 |
| volume_confirmed_reversal | long | all | 24 | 2.540 | 8.24 | 2.414 | 4.49 |
| breakout_12_reversal | short | london_07_12 | 6 | 1.405 | 3.19 | 2.406 | 3.74 |
| volume_confirmed_reversal | long | all | 12 | 2.153 | 9.17 | 2.370 | 6.00 |
| volume_confirmed_reversal | short | all | 6 | 1.076 | 5.68 | 2.366 | 6.83 |
| volume_confirmed_reversal | long | london_07_12 | 6 | 0.598 | 1.68 | 2.357 | 4.70 |
| mom_3_reversal | long | asia_00_06 | 24 | 2.442 | 10.39 | 2.285 | 5.33 |
| volume_confirmed_reversal | long | london_07_12 | 12 | 1.426 | 3.14 | 2.253 | 3.52 |
| volume_confirmed_reversal | long | new_york_13_20 | 12 | 1.408 | 3.31 | 2.213 | 2.95 |
| breakout_12_reversal | short | london_07_12 | 3 | 0.814 | 2.51 | 2.167 | 4.15 |
| volume_confirmed_reversal | long | all | 6 | 1.663 | 9.00 | 2.144 | 6.92 |
| breakout_12_reversal | short | all | 12 | 2.672 | 9.00 | 2.045 | 3.77 |
| breakout_12_reversal | long | all | 6 | 1.898 | 8.16 | 2.016 | 4.88 |
| breakout_12_reversal | long | london_07_12 | 12 | 2.403 | 4.47 | 2.010 | 2.04 |
| breakout_12_reversal | long | all | 12 | 2.765 | 9.66 | 1.938 | 3.67 |
| mom_3_reversal | short | london_07_12 | 12 | 0.899 | 3.96 | 1.931 | 5.55 |
| mom_3_reversal | short | london_07_12 | 6 | 0.272 | 1.62 | 1.918 | 7.27 |
| mom_3_reversal | long | all | 24 | 1.227 | 8.43 | 1.897 | 7.41 |
| mom_3_reversal | short | london_07_12 | 24 | 0.840 | 2.58 | 1.896 | 3.82 |
| mom_6_reversal | long | all | 24 | 1.533 | 10.26 | 1.855 | 7.14 |
| mom_3_reversal | long | all | 12 | 0.970 | 8.78 | 1.810 | 9.66 |
| mom_3_reversal | short | all | 12 | 0.964 | 8.70 | 1.799 | 9.01 |
| mom_3_reversal | long | london_07_12 | 12 | 0.506 | 2.22 | 1.795 | 5.09 |
| mom_3_reversal | long | asia_00_06 | 12 | 1.940 | 10.59 | 1.778 | 5.50 |
| mom_6_reversal | long | all | 12 | 1.237 | 10.93 | 1.768 | 9.27 |
| volume_confirmed_reversal | short | asia_00_06 | 12 | 2.202 | 4.54 | 1.764 | 1.80 |
| breakout_12_reversal | long | london_07_12 | 3 | 0.736 | 2.05 | 1.759 | 2.88 |
| mom_6_reversal | short | all | 12 | 1.115 | 9.78 | 1.758 | 9.01 |
| volume_confirmed_reversal | long | asia_00_06 | 12 | 2.750 | 7.51 | 1.746 | 2.45 |
| breakout_12_reversal | short | all | 6 | 1.629 | 7.09 | 1.743 | 4.38 |
| volume_confirmed_reversal | long | asia_00_06 | 24 | 3.866 | 7.67 | 1.741 | 1.92 |
| volume_confirmed_reversal | long | new_york_13_20 | 6 | 1.447 | 4.50 | 1.739 | 2.97 |
| volume_confirmed_reversal | short | asia_00_06 | 6 | 1.385 | 3.93 | 1.714 | 2.52 |
| breakout_12_reversal | long | all | 24 | 3.018 | 8.01 | 1.712 | 2.39 |
| mom_3_reversal | short | all | 24 | 0.965 | 6.61 | 1.690 | 6.40 |
| breakout_12_reversal | long | asia_00_06 | 3 | 1.188 | 4.19 | 1.684 | 3.46 |
| mom_6_reversal | short | all | 24 | 1.244 | 8.27 | 1.628 | 6.27 |
| mom_6_reversal | long | asia_00_06 | 24 | 2.891 | 12.19 | 1.626 | 3.69 |
| breakout_12_reversal | long | london_07_12 | 6 | 1.102 | 2.36 | 1.619 | 2.11 |
| mom_3_reversal | short | all | 6 | 0.587 | 6.96 | 1.617 | 10.60 |
| volume_confirmed_reversal | short | all | 3 | 0.516 | 3.52 | 1.585 | 6.11 |
| mom_6_reversal | short | london_07_12 | 24 | 1.353 | 4.05 | 1.583 | 3.43 |
| volume_confirmed_reversal | long | asia_00_06 | 6 | 2.155 | 6.79 | 1.564 | 2.89 |
| breakout_12_reversal | short | all | 3 | 0.827 | 4.71 | 1.560 | 5.21 |
| mom_6_reversal | short | london_07_12 | 12 | 1.027 | 4.40 | 1.555 | 4.78 |
| breakout_12_reversal | short | new_york_13_20 | 12 | 1.304 | 2.38 | 1.520 | 1.44 |
| mom_6_reversal | short | new_york_13_20 | 12 | 0.462 | 2.35 | 1.510 | 4.19 |
| volume_confirmed_reversal | long | new_york_13_20 | 24 | 1.100 | 2.02 | 1.500 | 1.48 |
| mom_3_reversal | short | asia_00_06 | 12 | 1.064 | 5.43 | 1.486 | 3.84 |
| mom_3_reversal | short | new_york_13_20 | 12 | 0.573 | 2.99 | 1.472 | 4.14 |
| mom_6_reversal | short | asia_00_06 | 12 | 1.131 | 5.50 | 1.467 | 4.10 |
| breakout_12_reversal | long | all | 3 | 1.256 | 6.91 | 1.461 | 4.69 |
| mom_6_reversal | long | all | 6 | 0.696 | 8.12 | 1.391 | 9.52 |
| mom_3_reversal | long | all | 6 | 0.618 | 7.30 | 1.390 | 9.74 |
| mom_6_reversal | short | all | 6 | 0.616 | 7.04 | 1.374 | 9.23 |
| mom_6_reversal | long | london_07_12 | 12 | 0.793 | 3.36 | 1.348 | 3.66 |
| mom_6_reversal | short | london_07_12 | 6 | 0.312 | 1.81 | 1.312 | 5.22 |
| mom_3_reversal | long | asia_00_06 | 6 | 1.081 | 7.59 | 1.307 | 5.22 |
| volume_confirmed_reversal | long | all | 3 | 0.798 | 5.66 | 1.285 | 5.21 |
| volume_confirmed_reversal | short | asia_00_06 | 3 | 0.862 | 3.12 | 1.280 | 2.57 |
| breakout_12_reversal | short | asia_00_06 | 6 | 2.031 | 5.07 | 1.279 | 1.82 |
| mom_3_reversal | short | asia_00_06 | 6 | 0.647 | 4.28 | 1.251 | 4.40 |
| mom_3_reversal | short | all | 3 | 0.250 | 3.90 | 1.249 | 10.59 |
| mom_3_reversal | short | new_york_13_20 | 6 | 0.405 | 2.75 | 1.177 | 4.39 |
| breakout_12_reversal | short | asia_00_06 | 3 | 1.178 | 3.74 | 1.169 | 2.25 |
| mom_6_reversal | long | london_07_12 | 6 | 0.381 | 2.13 | 1.165 | 4.31 |
| volume_confirmed_reversal | long | new_york_13_20 | 3 | 0.559 | 2.23 | 1.121 | 2.45 |
| mom_6_reversal | long | asia_00_06 | 12 | 2.315 | 12.50 | 1.111 | 3.39 |
| mom_3_reversal | short | asia_00_06 | 3 | 0.307 | 2.63 | 1.099 | 5.01 |
| mom_6_reversal | long | asia_00_06 | 6 | 1.176 | 8.32 | 1.059 | 4.05 |
| mom_6_reversal | short | asia_00_06 | 6 | 0.658 | 3.92 | 1.056 | 4.07 |
| mom_3_reversal | long | all | 3 | 0.236 | 3.67 | 1.038 | 9.36 |
| mom_3_reversal | long | asia_00_06 | 3 | 0.577 | 5.18 | 0.975 | 5.14 |
| mom_3_reversal | long | london_07_12 | 24 | 0.931 | 2.95 | 0.971 | 1.84 |
| mom_6_reversal | short | new_york_13_20 | 6 | 0.280 | 1.89 | 0.907 | 3.32 |
| mom_6_reversal | short | all | 3 | 0.140 | 2.11 | 0.904 | 7.86 |
| mom_6_reversal | long | all | 3 | 0.210 | 3.17 | 0.902 | 7.94 |
| mom_6_reversal | short | asia_00_06 | 3 | 0.226 | 1.81 | 0.752 | 3.82 |
| mom_3_reversal | short | new_york_13_20 | 24 | 0.542 | 2.18 | 0.722 | 1.56 |
| mom_6_reversal | long | london_07_12 | 24 | 1.236 | 3.84 | 0.675 | 1.21 |
| mom_6_reversal | long | asia_00_06 | 3 | 0.417 | 3.73 | 0.641 | 3.14 |
| volume_confirmed_reversal | long | asia_00_06 | 3 | 1.057 | 4.40 | 0.519 | 1.27 |

## Decision

Only the retained rows are eligible to become full trade rules and to be tested on 2025. Rows absent from this table must not be promoted to an EA factor.
