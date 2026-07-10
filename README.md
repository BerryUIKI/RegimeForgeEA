# RegimeForgeEA

RegimeForgeEA is a modular, regime-aware algorithmic trading framework with an
MQL5 Expert Advisor and a Python research backtester. It is instrument-agnostic:
the first included strategy is configured for an aggressive XAUUSD M5 trend
breakout, but the execution and risk architecture does not depend on gold.

Chinese documentation: [README_zh-CN.md](README_zh-CN.md)

> [!WARNING]
> This software is for research and educational use. Trading involves
> substantial risk. Validate symbol specifications, costs, and strategy
> behavior before enabling live trading.

## Features

- Regime classification: trend, range, high volatility, and unknown
- Pluggable strategy modules with a shared signal interface
- Centralized risk sizing, order execution, and position management
- ATR stop loss, take profit, and trailing stop
- Spread, daily-loss, and peak-drawdown entry locks
- Closed-bar signals to avoid look-ahead behavior
- Python event backtester aligned with the EA's first strategy

The current EA opens trades only in the trend regime. Range and high-volatility
regimes remain inactive until dedicated strategy modules are added.

## Latest public-data backtest

The unoptimized default strategy was tested on 375,413 weekday-only
`PAXGUSDT` M5 bars from 2021–2025. Monthly Binance Data Vision archives were
verified against publisher-provided SHA-256 checksums.

| Metric | Risk-managed run | Continuous diagnostic |
|---|---:|---:|
| Total return | -11.55% | -98.87% |
| Maximum drawdown | 12.35% | 98.90% |
| Trades | 44 | 2,054 |
| Win rate | 22.73% | 24.49% |
| Profit factor | 0.47 | 0.28 |

The risk-managed run stopped opening positions on January 11, 2021 after its
peak-drawdown lock fired. The continuous diagnostic shows that the underlying
strategy is not viable with the current defaults. PAXGUSDT is a gold-linked
public proxy, not an XAUUSD broker feed; these results must not be presented as
live-trading validation.

Read the [full report](reports/PAXGUSDT_2021_2025.md) and inspect the
[data manifest](reports/PAXGUSDT_2021_2025_data_manifest.json).

## MQL5 layout

```text
MQL5/
├── Experts/RegimeForgeEA.mq5
└── Include/RegimeForge/
    ├── StrategyTypes.mqh
    └── TrendBreakoutStrategy.mqh
```

Copy the files into the corresponding folders under the MT5 `MQL5` data
directory and compile `Experts/RegimeForgeEA.mq5` in MetaEditor. Attach it to
the chart and symbol that should be traded; the EA uses `_Symbol`.

## Python backtest

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python backtest/regime_forge_backtest.py data/XAUUSD_M5.csv \
  --output outputs/run_001
```

The input CSV must contain:

```text
time,open,high,low,close
```

Optional columns are `tick_volume`, `real_volume`, and `spread`. The `spread`
column is interpreted as broker points. Column names are case-insensitive.
Common MT5 exports with separate `Date` and `Time` columns are also accepted.

Useful overrides:

```bash
python backtest/regime_forge_backtest.py data/XAUUSD_M5.csv \
  --initial-equity 10000 \
  --risk-percent 1.0 \
  --spread-points 35 \
  --point 0.01 \
  --contract-size 100 \
  --output outputs/aggressive
```

Each run writes:

- `summary.json`: performance and run parameters
- `trades.csv`: complete trade ledger
- `equity.csv`: bar-by-bar equity and regime

Signals are calculated on a closed bar and executed at the next bar open with
spread. Since OHLC data does not reveal intrabar event order, a bar touching
both stop loss and take profit is resolved stop-first. Trailing stops are
updated at bar close. Tick-level MT5 Strategy Tester results will therefore
not be identical.

To reproduce the public-data benchmark, use the commands in the
[backtest report](reports/PAXGUSDT_2021_2025.md). Raw market data and generated
run outputs are intentionally excluded from Git; the downloader rebuilds them
from verified public archives.

## Main parameters

- `InpRiskPerTradePct`: equity risk per trade; default `1.00%`
- `InpMaxDailyLossPct`: daily equity entry lock
- `InpMaxDrawdownPct`: peak-equity entry lock
- `InpMaxSpreadPoints`: maximum entry spread in broker points
- `InpBreakoutBars`: breakout lookback
- `InpFastMAPeriod` / `InpSlowMAPeriod`: trend direction
- `InpADXTrendLevel`: trend strength threshold
- `InpStopATR` / `InpTakeProfitATR`: ATR stop and target multipliers

The defaults are intentionally aggressive. They are not a profit expectation
and should not be used with real funds without broker-specific validation.

## Adding strategies

Add strategy modules under `Include/RegimeForge/` and have each module produce
the shared `TradeSignal` structure. The main EA remains responsible for risk,
orders, protective stops, and position management.

Planned strategy families:

1. Range regime: Bollinger-band or statistical mean reversion
2. High-volatility regime: false-breakout filter or post-event momentum
3. Low-volatility regime: compression breakout
4. Portfolio layer: regime-based strategy allocation under one risk engine

## Development

```bash
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for strategy, data, and validation
requirements. Report vulnerabilities through the process in
[SECURITY.md](SECURITY.md), not a public issue.

## License

[MIT](LICENSE)
