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

## License

[MIT](LICENSE)

