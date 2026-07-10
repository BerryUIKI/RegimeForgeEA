# Order-flow factor screen

## Formula

For a window n, OFI_n(t) = sum(BuyTakerQty - SellTakerQty) / sum(BuyTakerQty + SellTakerQty). Extreme thresholds are rolling 20-trading-day 20/80 quantiles shifted one 1-minute bar. Momentum trades with OFI; reversal trades against it. The absorption factor buys when price is at a negative return extreme while OFI is positive extreme, and sells the symmetric condition.

Each event subtracts one 0.35 USD spread. Training is 2021–2023; validation is 2024; 2025 is excluded.

## Factors passing both periods

| Factor | Side | Session | Horizon | Train net bps | Train t | Validation net bps | Validation t |
|---|---|---|---:|---:|---:|---:|---:|
| ofi_price_absorption | short | new_york_13_20 | 10 | 1.404 | 6.44 | 1.495 | 4.49 |
| ofi_price_absorption | long | london_07_12 | 30 | 1.343 | 3.32 | 1.357 | 2.89 |
| ofi_price_absorption | short | new_york_13_20 | 5 | 1.314 | 8.10 | 1.230 | 4.66 |
| ofi_price_absorption | long | all | 30 | 1.242 | 5.20 | 1.183 | 4.47 |
| ofi_price_absorption | long | london_07_12 | 20 | 1.264 | 3.73 | 1.171 | 3.00 |
| ofi_price_absorption | short | asia_00_06 | 5 | 0.870 | 5.28 | 1.159 | 4.44 |
| ofi_price_absorption | short | new_york_13_20 | 20 | 1.649 | 5.66 | 1.155 | 2.57 |
| ofi_price_absorption | short | new_york_13_20 | 30 | 1.533 | 4.34 | 1.106 | 1.97 |
| ofi_price_absorption | short | all | 5 | 1.019 | 9.51 | 1.059 | 7.75 |
| ofi_price_absorption | long | london_07_12 | 10 | 1.110 | 4.51 | 1.016 | 3.19 |
| ofi_price_absorption | long | all | 20 | 1.266 | 6.65 | 1.009 | 4.64 |
| ofi_price_absorption | long | asia_00_06 | 10 | 0.943 | 3.70 | 0.872 | 2.94 |
| ofi_price_absorption | short | all | 10 | 1.142 | 8.64 | 0.860 | 5.00 |
| ofi_price_absorption | long | all | 10 | 1.025 | 7.59 | 0.856 | 4.90 |
| ofi_price_absorption | long | new_york_13_20 | 20 | 1.037 | 3.14 | 0.791 | 1.84 |
| ofi_price_absorption | long | new_york_13_20 | 30 | 0.653 | 1.71 | 0.790 | 1.54 |
| ofi_price_absorption | long | all | 5 | 1.025 | 9.81 | 0.767 | 5.79 |
| ofi_price_absorption | long | new_york_13_20 | 5 | 0.896 | 5.17 | 0.728 | 2.83 |
| ofi_price_absorption | short | asia_00_06 | 10 | 0.796 | 3.76 | 0.677 | 2.08 |
| ofi_price_absorption | long | london_07_12 | 5 | 0.960 | 5.30 | 0.624 | 2.57 |
| ofi_price_absorption | long | asia_00_06 | 20 | 0.952 | 2.73 | 0.610 | 1.70 |
| ofi_price_absorption | short | asia_00_06 | 30 | 0.759 | 2.27 | 0.571 | 1.25 |
| ofi_price_absorption | long | asia_00_06 | 30 | 0.628 | 1.53 | 0.551 | 1.19 |
| ofi_price_absorption | short | london_07_12 | 5 | 0.923 | 4.85 | 0.497 | 2.03 |
| ofi_price_absorption | long | asia_00_06 | 5 | 0.934 | 4.77 | 0.497 | 2.24 |
| ofi_price_absorption | long | new_york_13_20 | 10 | 0.707 | 3.04 | 0.484 | 1.45 |
| ofi_price_absorption | short | all | 20 | 1.123 | 6.40 | 0.224 | 1.00 |
