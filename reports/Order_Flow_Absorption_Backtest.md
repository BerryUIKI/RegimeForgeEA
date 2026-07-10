# Order-flow absorption order-level backtest

## Pre-specified rule

This test fixes the rule before evaluating 2025: use the `ofi_price_absorption` long factor over all sessions and hold for six M5 bars. The choice is based on its highest training t-statistic among the all-session absorption horizons in the prior factor screen, not on 2025 data.

At close t, signal when the three-bar price return is at or below its trailing 20-trading-day 20th percentile and the three-bar order-flow imbalance is at or above its trailing 80th percentile. Both thresholds are shifted by one M5 bar. Enter long at the next M5 open plus half a 0.35 USD spread; exit at the close of bar t+6 minus half spread, matching the factor's fixed six-bar forecast horizon. Positions do not overlap. Results use 0.10 lot and a 100 oz contract only to express PnL; factor metrics are independent of size.

## Results

| Sample | Trades | Net PnL (USD) | Profit factor | Win rate | Mean net bps | Maximum drawdown (USD) |
|---|---:|---:|---:|---:|---:|---:|
| training_2021_2023 | 1381 | -4221.10 | 0.712 | 39.17% | -1.667 | -4440.80 |
| validation_2024 | 588 | 182.00 | 1.024 | 51.53% | 0.183 | -739.00 |
| holdout_2025 | 441 | -2048.80 | 0.828 | 46.49% | -1.146 | -3384.00 |

## Interpretation

The 2025 result is a one-time holdout check. Passing this proxy-data test does not establish deployable XAUUSD profitability: the source is PAXGUSDT aggregate trades, and it omits the MT5 broker's bid/ask feed, fill latency, slippage, commissions, and trading-session constraints.
