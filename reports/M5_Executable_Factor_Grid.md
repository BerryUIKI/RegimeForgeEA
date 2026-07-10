# M5 executable order-flow grid

## Protocol

This pre-defined grid tests OFI momentum/reversal/absorption and price-return, breakout, and volume-confirmed reversal factors; both directions; four UTC sessions; and 5/10/15/30/60/120 minute exits. Extreme thresholds use trailing 20-trading-day 20/80 quantiles shifted one M5 bar. Entries occur at the next M5 bid/ask, exits at the fixed-horizon close, a 0.35 USD round-trip spread is charged, and positions cannot overlap.

Training is 2021–2023. A candidate needs 100 trades, PF >= 1.10, and >= 0.50 mean net bps before training-only selection by mean-bps-times-square-root-trades. The selected candidate then needs 30 validation trades, PF >= 1.05, and >= 0.25 mean net bps in 2024. The 2025 holdout is not examined unless it passes validation.

## Training shortlist and 2024 validation

| Family | Session | Side | Hold (min) | Train trades | Train PF | Train bps | Validation trades | Validation PF | Validation bps |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| volume_return_3_reversal | all | long | 120 | 4333 | 1.162 | 1.512 | 1428 | 1.276 | 2.447 |
| volume_return_3_reversal | all | long | 60 | 5833 | 1.165 | 1.189 | 1887 | 1.238 | 1.701 |
| breakout_12_reversal | all | short | 120 | 3711 | 1.152 | 1.446 | 1185 | 1.160 | 1.479 |
| breakout_12_reversal | all | short | 60 | 4595 | 1.170 | 1.245 | 1428 | 1.162 | 1.125 |
| breakout_12_reversal | asia_00_06 | short | 120 | 1164 | 1.295 | 2.300 | 400 | 1.220 | 1.919 |
| breakout_12_reversal | all | long | 60 | 4379 | 1.158 | 1.144 | 1296 | 1.260 | 1.745 |
| breakout_12_reversal | all | long | 120 | 3569 | 1.124 | 1.213 | 1080 | 1.178 | 1.594 |
| volume_return_3_reversal | all | short | 60 | 5788 | 1.127 | 0.937 | 1842 | 1.212 | 1.481 |
| volume_return_3_reversal | asia_00_06 | long | 120 | 1288 | 1.245 | 1.895 | 405 | 0.992 | -0.073 |
| volume_return_3_reversal | all | short | 120 | 4305 | 1.101 | 0.967 | 1389 | 1.099 | 0.942 |
| breakout_12_reversal | asia_00_06 | long | 60 | 1255 | 1.321 | 1.767 | 383 | 1.293 | 1.729 |
| volume_return_3_reversal | asia_00_06 | long | 60 | 1608 | 1.256 | 1.479 | 497 | 1.232 | 1.461 |
| breakout_12_reversal | asia_00_06 | short | 60 | 1389 | 1.248 | 1.553 | 468 | 1.057 | 0.393 |
| volume_return_3_reversal | all | long | 30 | 7176 | 1.119 | 0.683 | 2316 | 1.260 | 1.399 |
| volume_return_3_reversal | asia_00_06 | long | 30 | 1886 | 1.275 | 1.293 | 575 | 1.124 | 0.638 |
| breakout_12_reversal | asia_00_06 | long | 120 | 1079 | 1.229 | 1.708 | 334 | 1.240 | 1.807 |
| volume_return_3_reversal | london_07_12 | short | 120 | 1346 | 1.117 | 1.278 | 432 | 1.110 | 0.918 |
| volume_return_3_reversal | asia_00_06 | short | 120 | 1300 | 1.138 | 1.099 | 425 | 1.184 | 1.521 |
| volume_return_3_reversal | asia_00_06 | short | 60 | 1610 | 1.160 | 0.987 | 523 | 1.161 | 1.071 |
| volume_return_3_reversal | london_07_12 | long | 60 | 1747 | 1.114 | 0.879 | 566 | 1.252 | 1.565 |
| return_6_reversal | asia_00_06 | long | 120 | 1836 | 1.105 | 0.843 | 640 | 1.126 | 1.032 |
| volume_return_3_reversal | new_york_13_20 | short | 30 | 2490 | 1.104 | 0.707 | 787 | 1.154 | 1.055 |
| return_6_reversal | asia_00_06 | long | 60 | 2572 | 1.105 | 0.643 | 915 | 1.135 | 0.815 |
| breakout_12_reversal | london_07_12 | short | 60 | 1249 | 1.113 | 0.888 | 379 | 1.131 | 0.843 |

## Decision

One training-selected candidate passed validation and is eligible for a separately recorded 2025 holdout test.
