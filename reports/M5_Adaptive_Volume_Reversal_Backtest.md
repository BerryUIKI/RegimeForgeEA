# Order-level factor backtest

## Pre-specified rule

This test fixes the rule before evaluating 2025: use the `volume_return_3_reversal` long factor during UTC 00:00–23:59 and hold for 24 5-minute bars. The choice is fixed from training and validation before 2025 is examined.

Overlays: completed-H1 trend filter=True; daily realized-loss lock=2.00% of start-of-day equity; consecutive-loss limit=4; cooldown=12 bars.

At close t, the volume-reversal rule buys when the three-bar return is at or below its trailing 20-trading-day 20th percentile and current volume is at least 1.5 times its trailing 60-bar mean. Thresholds are shifted by one 5-minute bar. Enter at the next bar's bid/ask and exit at the close of bar t+24, charging a 0.35 USD round-trip spread. Positions do not overlap. Results use 0.10 lot and a 100 oz contract only to express PnL; factor metrics are independent of size.

## Results

| Sample | Trades | Net PnL (USD) | Profit factor | Win rate | Mean net bps | Maximum drawdown (USD) |
|---|---:|---:|---:|---:|---:|---:|
| training_2021_2023 | 2029 | 6063.90 | 1.162 | 52.34% | 1.714 | -2251.00 |
| validation_2024 | 790 | 5565.00 | 1.334 | 56.58% | 3.131 | -946.00 |
| holdout_2025 | 828 | 7151.00 | 1.221 | 56.64% | 2.768 | -3134.50 |

## Interpretation

The 2025 result is a one-time holdout check. Passing this proxy-data test does not establish deployable XAUUSD profitability: the source is PAXGUSDT aggregate trades, and it omits the MT5 broker's bid/ask feed, fill latency, slippage, commissions, and trading-session constraints.
