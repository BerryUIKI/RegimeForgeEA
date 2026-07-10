# Order-flow absorption order-level backtest

## Pre-specified rule

This test fixes the rule before evaluating 2025: use the `ofi_price_absorption` long factor during UTC 00:00–23:59 and hold for 5 1-minute bars. The choice must be made from training statistics only, not from 2025 data.

At close t, an absorption signal combines a three-bar price extreme with an opposite three-bar OFI extreme. Both thresholds are shifted by one 1-minute bar. Enter at the next bar's bid/ask and exit at the close of bar t+5, charging a 0.35 USD round-trip spread. Positions do not overlap. Results use 0.10 lot and a 100 oz contract only to express PnL; factor metrics are independent of size.

## Results

| Sample | Trades | Net PnL (USD) | Profit factor | Win rate | Mean net bps | Maximum drawdown (USD) |
|---|---:|---:|---:|---:|---:|---:|
| training_2021_2023 | 5573 | -16405.70 | 0.567 | 33.45% | -1.612 | -16483.20 |
| validation_2024 | 2464 | -6934.00 | 0.643 | 34.38% | -1.166 | -6963.50 |
| holdout_2025 | 1761 | -6068.40 | 0.701 | 41.74% | -1.001 | -6173.10 |

## Interpretation

The 2025 result is a one-time holdout check. Passing this proxy-data test does not establish deployable XAUUSD profitability: the source is PAXGUSDT aggregate trades, and it omits the MT5 broker's bid/ask feed, fill latency, slippage, commissions, and trading-session constraints.
