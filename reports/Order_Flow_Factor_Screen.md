# Order-flow factor screen

## Formula

For a window n, OFI_n(t) = sum(BuyTakerQty - SellTakerQty) / sum(BuyTakerQty + SellTakerQty). Extreme thresholds are rolling 20-trading-day 20/80 quantiles shifted one M5 bar. Momentum trades with OFI; reversal trades against it. The absorption factor buys when price is at a negative return extreme while OFI is positive extreme, and sells the symmetric condition.

Each event subtracts one 0.35 USD spread. Training is 2021–2023; validation is 2024; 2025 is excluded.

## Factors passing both periods

| Factor | Side | Session | Horizon | Train net bps | Train t | Validation net bps | Validation t |
|---|---|---|---:|---:|---:|---:|---:|
| ofi_price_absorption | long | asia_00_06 | 24 | 2.188 | 1.68 | 2.885 | 2.09 |
| ofi_price_absorption | long | all | 12 | 1.127 | 2.35 | 1.576 | 2.03 |
| ofi_price_absorption | long | all | 24 | 1.042 | 1.56 | 1.409 | 1.40 |
| ofi_price_absorption | long | all | 6 | 1.028 | 2.72 | 1.053 | 1.85 |
| ofi_price_absorption | long | new_york_13_20 | 3 | 0.901 | 1.78 | 0.916 | 1.13 |
