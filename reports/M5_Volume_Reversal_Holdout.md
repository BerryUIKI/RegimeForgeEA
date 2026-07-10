# Order-level factor backtest

## Pre-specified rule

This test fixes the rule before evaluating 2025: use the `volume_return_3_reversal` long factor during UTC 00:00–23:59 and hold for 24 5-minute bars. The choice is fixed from training and validation before 2025 is examined.

At close t, the volume-reversal rule buys when the three-bar return is at or below its trailing 20-trading-day 20th percentile and current volume is at least 1.5 times its trailing 60-bar mean. Thresholds are shifted by one 5-minute bar. Enter at the next bar's bid/ask and exit at the close of bar t+24, charging a 0.35 USD round-trip spread. Positions do not overlap. Results use 0.10 lot and a 100 oz contract only to express PnL; factor metrics are independent of size.

## Results

| Sample | Trades | Net PnL (USD) | Profit factor | Win rate | Mean net bps | Maximum drawdown (USD) |
|---|---:|---:|---:|---:|---:|---:|
| training_2021_2023 | 4333 | 11644.50 | 1.156 | 51.63% | 1.512 | -2111.00 |
| validation_2024 | 1428 | 7832.00 | 1.257 | 55.04% | 2.447 | -1847.00 |
| holdout_2025 | 1350 | 6707.20 | 1.119 | 55.41% | 1.768 | -4927.40 |

## Interpretation

The 2025 result is a one-time holdout check. Passing this proxy-data test does not establish deployable XAUUSD profitability: the source is PAXGUSDT aggregate trades, and it omits the MT5 broker's bid/ask feed, fill latency, slippage, commissions, and trading-session constraints.
