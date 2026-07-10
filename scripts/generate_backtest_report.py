"""Generate a Markdown report and equity chart from backtest output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def money(value: float) -> str:
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def percent(value: float) -> str:
    return f"{value:.2f}%"


def value_or_na(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None or not np.isfinite(value) else f"{value:.{digits}f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--data-metadata", type=Path, required=True)
    parser.add_argument("--diagnostic-run", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--chart", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads((args.run / "summary.json").read_text(encoding="utf-8"))
    metadata = json.loads(args.data_metadata.read_text(encoding="utf-8"))
    trades = pd.read_csv(args.run / "trades.csv")
    equity = pd.read_csv(args.run / "equity.csv", parse_dates=["time"])
    equity["year"] = equity["time"].dt.year

    annual_rows: list[dict] = []
    for year, group in equity.groupby("year"):
        start_equity = float(group["equity"].iloc[0])
        end_equity = float(group["equity"].iloc[-1])
        year_trades = trades[
            pd.to_datetime(trades["exit_time"], utc=True).dt.year == year
        ]
        annual_rows.append(
            {
                "year": int(year),
                "return": 100.0 * (end_equity / start_equity - 1.0),
                "trades": len(year_trades),
                "win_rate": (
                    100.0 * (year_trades["net_pnl"] > 0).mean()
                    if len(year_trades)
                    else 0.0
                ),
                "net_pnl": float(year_trades["net_pnl"].sum()) if len(year_trades) else 0.0,
            }
        )

    average_trade = float(trades["net_pnl"].mean()) if len(trades) else 0.0
    median_trade = float(trades["net_pnl"].median()) if len(trades) else 0.0
    average_r = float(trades["r_multiple"].mean()) if len(trades) else 0.0
    long_count = int((trades["direction"] == "long").sum()) if len(trades) else 0
    short_count = int((trades["direction"] == "short").sum()) if len(trades) else 0
    exposure = 100.0 * (equity["position"] != 0).mean()

    args.chart.parent.mkdir(parents=True, exist_ok=True)
    figure, axes = plt.subplots(
        2,
        1,
        figsize=(12, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    axes[0].plot(equity["time"], equity["equity"], color="#d89b22", linewidth=1.1)
    axes[0].set_title("RegimeForgeEA public-data backtest")
    axes[0].set_ylabel("Equity (USD)")
    axes[0].grid(alpha=0.25)
    axes[1].fill_between(
        equity["time"],
        100.0 * equity["drawdown"],
        0,
        color="#b13b3b",
        alpha=0.7,
    )
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(args.chart, dpi=160)
    plt.close(figure)

    annual_table = "\n".join(
        f"| {row['year']} | {percent(row['return'])} | {row['trades']} | "
        f"{percent(row['win_rate'])} | {money(row['net_pnl'])} |"
        for row in annual_rows
    )
    chart_relative = args.chart.name
    parameters = summary["parameters"]
    last_trade_time = trades["exit_time"].iloc[-1] if len(trades) else "N/A"
    diagnostic_section = ""
    if args.diagnostic_run:
        diagnostic = json.loads(
            (args.diagnostic_run / "summary.json").read_text(encoding="utf-8")
        )
        diagnostic_section = f"""
## Continuous-strategy diagnostic

The primary run stopped opening positions after its peak-drawdown safety lock
was triggered; its last trade closed at `{last_trade_time}`. This lock is
deliberately persistent during one EA session. A second diagnostic run raised
both entry-lock thresholds to 100% while leaving the signal and trade parameters
unchanged:

| Metric | Risk-managed run | Continuous diagnostic |
|---|---:|---:|
| Total return | {percent(summary['total_return_percent'])} | {percent(diagnostic['total_return_percent'])} |
| Maximum drawdown | {percent(summary['max_drawdown_percent'])} | {percent(diagnostic['max_drawdown_percent'])} |
| Trades | {summary['trades']} | {diagnostic['trades']} |
| Win rate | {percent(summary['win_rate_percent'])} | {percent(diagnostic['win_rate_percent'])} |
| Profit factor | {value_or_na(summary['profit_factor'])} | {value_or_na(diagnostic['profit_factor'])} |

The diagnostic is not a deployable configuration. It exists to distinguish
strategy behavior from the safety lock's behavior.
"""
    report = f"""# Public-data backtest report

## Scope

This report evaluates the first RegimeForgeEA trend-breakout strategy on
`PAXGUSDT` 5-minute public market data from Binance Data Vision. PAXG represents
one fine troy ounce of vaulted physical gold, but PAXGUSDT is a 24/7 crypto
venue and is **not** an XAUUSD broker feed. Weekend UTC bars were removed to
reduce, not eliminate, the market-hours mismatch.

The test covers {metadata['first_bar']} through {metadata['last_bar']} and uses
{metadata['bars']:,} bars. Results are a research proxy, not live-trading
validation.

![Equity curve and drawdown]({chart_relative})

## Headline results

| Metric | Result |
|---|---:|
| Initial equity | {money(summary['initial_equity'])} |
| Final equity | {money(summary['final_equity'])} |
| Net profit | {money(summary['net_profit'])} |
| Total return | {percent(summary['total_return_percent'])} |
| Maximum drawdown | {percent(summary['max_drawdown_percent'])} |
| Trades | {summary['trades']} |
| Win rate | {percent(summary['win_rate_percent'])} |
| Profit factor | {value_or_na(summary['profit_factor'])} |
| Average trade | {money(average_trade)} |
| Median trade | {money(median_trade)} |
| Average R multiple | {value_or_na(average_r)} |
| Long / short trades | {long_count} / {short_count} |
| Bar exposure | {percent(exposure)} |

{diagnostic_section}

## Annual breakdown

| Year | Equity return | Closed trades | Win rate | Realized P&L |
|---:|---:|---:|---:|---:|
{annual_table}

## Strategy and execution assumptions

- Closed-bar M5 breakout signals with EMA({parameters['fast_ma_period']}) /
  EMA({parameters['slow_ma_period']}) direction and ADX({parameters['adx_period']})
  >= {parameters['adx_trend_level']:.1f}.
- High-volatility bars are excluded when ATR({parameters['atr_period']}) divided
  by ATR({parameters['atr_period'] * 4}) is at least
  {parameters['high_volatility_atr_ratio']:.2f}.
- Stop loss: {parameters['stop_atr']:.2f} ATR; take profit:
  {parameters['take_profit_atr']:.2f} ATR; trailing stop:
  {parameters['trailing_atr']:.2f} ATR.
- Risk per trade: {parameters['risk_percent']:.2f}% of marked equity.
- Synthetic spread: {parameters['default_spread_points']:.0f} points at a
  {parameters['point']:.2f} point size. No commission or swap was modeled.
- Signals execute at the next bar open. If stop and target are both touched
  within one OHLC bar, the stop is assumed to occur first.
- Position sizing uses a 100-unit contract to resemble a common XAUUSD CFD
  contract, not Binance spot execution.

## Data quality

| Check | Result |
|---|---:|
| Duplicate timestamps | {metadata['duplicate_timestamps']} |
| Non-positive OHLC rows | {metadata['non_positive_prices']} |
| Gaps over five minutes | {metadata['gaps_over_five_minutes']} |
| Missing monthly archives | {len(metadata['missing_months'])} |
| Archive verification | SHA-256 verified per monthly file |

Large gaps include scheduled weekend removal and exchange/data interruptions.
The downloader preserves UTC timestamps and verifies each archive against the
publisher-provided checksum.

## Interpretation

The result answers a narrow question: how the current rules behaved on a
gold-linked, high-frequency public proxy under explicit OHLC assumptions. It
does not establish expected profitability on XAUUSD. Before live use, the
strategy still requires:

1. Broker-native XAUUSD tick or M1 data with bid/ask prices.
2. MT5 Strategy Tester validation using real ticks.
3. Walk-forward parameter selection without tuning on the final test window.
4. Commission, swap, slippage, stop-level, and rejected-order modeling.
5. Demo forward testing through multiple volatility regimes.

## Reproduction

```bash
python scripts/download_binance_klines.py \\
  --symbol PAXGUSDT --interval 5m \\
  --start 2021-01 --end 2025-12 --weekdays-only \\
  --output data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \\
  --manifest-output reports/PAXGUSDT_2021_2025_data_manifest.json

python backtest/regime_forge_backtest.py \\
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \\
  --output outputs/paxgusdt_2021_2025

python backtest/regime_forge_backtest.py \\
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \\
  --max-daily-loss-percent 100 --max-drawdown-percent 100 \\
  --output outputs/paxgusdt_2021_2025_continuous

python scripts/generate_backtest_report.py \\
  --run outputs/paxgusdt_2021_2025 \\
  --diagnostic-run outputs/paxgusdt_2021_2025_continuous \\
  --data-metadata data/derived/PAXGUSDT_5m_2021_2025_weekdays.metadata.json \\
  --report reports/PAXGUSDT_2021_2025.md \\
  --chart reports/PAXGUSDT_2021_2025_equity.png
```

## Sources

- [Binance Spot Kline API and market-data endpoints](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market)
- [Binance Data Vision public archive](https://data.binance.vision/)
- [Paxos PAXG overview](https://docs.paxos.com/guides/stablecoin/paxg)
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(f"wrote {args.report}")
    print(f"wrote {args.chart}")


if __name__ == "__main__":
    main()
