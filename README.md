# RegimeForgeEA

[![Python tests](https://github.com/BerryUIKI/RegimeForgeEA/actions/workflows/python-tests.yml/badge.svg)](https://github.com/BerryUIKI/RegimeForgeEA/actions/workflows/python-tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![MQL5](https://img.shields.io/badge/Execution-MQL5-167AC6)
![Research status](https://img.shields.io/badge/M5%20candidate-Proxy%20validated-0A8F72)

RegimeForgeEA is a modular, regime-aware algorithmic trading framework with an
MQL5 Expert Advisor and a Python research backtester. It is instrument-agnostic:
the first included strategy is an XAUUSD M5 trend-breakout research candidate,
but the execution and risk architecture does not depend on gold.

Chinese documentation: [README_zh-CN.md](README_zh-CN.md)

> [!WARNING]
> This software is for research and educational use. Trading involves
> substantial risk. Validate symbol specifications, costs, and strategy
> behavior before enabling live trading.

## Current research candidate: M5 volume-confirmed reversal

The current research candidate is a long-only M5 reversal rule. It passed the
fixed training, validation, and holdout protocol on a public gold-linked proxy;
it still requires broker-native XAUUSD Bid/Ask testing before any deployment.

$$r_3(t)=\frac{C_t}{C_{t-3}}-1$$

$$q_{20}(t)=Q_{0.20}(\{r_3(s):s<t\}),\qquad VR(t)=\frac{V_t}{SMA_{60}(V)_t}$$

Enter long at the next M5 open when:

$$r_3(t)\le q_{20}(t)\quad\land\quad VR(t)\ge1.5$$

Exit after 24 M5 bars (120 minutes). The threshold uses the prior 5,760 M5
bars and is shifted one bar to avoid look-ahead. See the
[full Markdown report](reports/M5_Volume_Reversal_Research_Report.md) and
[PDF report](reports/M5_Volume_Reversal_Research_Report.pdf).

## Features

- Regime classification: trend, range, high volatility, and unknown
- Pluggable strategy modules with a shared signal interface
- Centralized risk sizing, order execution, and position management
- ATR stop loss, take profit, and trailing stop
- Spread, daily-loss, and peak-drawdown entry locks
- Closed-bar signals to avoid look-ahead behavior
- Python event backtester aligned with the EA's first strategy
- Research-only Bollinger/RSI range model for candidate evaluation

The current EA manages only the trend-breakout research candidate. New entries
are disabled by default (`InpEnableNewEntries=false`) because the current public
research has not qualified any strategy for deployment. Range and
high-volatility regimes remain inactive in the EA.

## Research status

Multiple pre-defined strategy families were tested with 2021–2023 training,
2024 validation, and a 2025 final holdout. Most candidates were rejected. One
M5 volume-confirmed reversal candidate passed all three splits on the public
PAXGUSDT proxy; it is not a live-profit claim and is not enabled by default.

- [Trend candidate research](reports/Trend_Candidate_Research.md): eight
  M15/M30/H1 EMA/ADX/Donchian candidates; all failed training gates.
- [Range candidate research](reports/Range_Candidate_Research.md): eight
  M15/M30/H1 Bollinger/RSI range candidates; all failed training gates.
- [High-frequency candidate research](reports/High_Frequency_Candidate_Research.md):
  M5 pullback candidates with a closed H1/H4 trend filter; all failed at the
  order level.
- [Intraday factor screen](reports/Intraday_Factor_Screen.md): cost-adjusted
  M5 factor screen; order-level conversion of the initial reversal rule failed.
- [Volume-reversal order research](reports/Volume_Reversal_Candidate_Research.md):
  fixed-time M5 exits and ATR stops; all candidates failed training gates.
- [M5 order-flow factor screen](reports/Order_Flow_Factor_Screen.md) and
  [order-level result](reports/Order_Flow_Absorption_Backtest.md): the apparent
  event-level absorption effect failed once next-bar execution and non-overlap
  were imposed.
- [M1 order-flow factor screen](reports/Order_Flow_Factor_Screen_1m.md) and
  [order-level result](reports/Order_Flow_Absorption_Backtest_1m.md): a
  one-minute, 1,542,455-bar screen produced positive event means in training
  and validation, but its pre-specified executable rule failed in all three
  samples. It is therefore rejected, not integrated into the EA.
- [M5 executable factor grid](reports/M5_Executable_Factor_Grid.md) and
  [pre-specified holdout](reports/M5_Volume_Reversal_Holdout.md): the
  volume-confirmed three-bar reversal candidate passed the 2021–2023 training,
  2024 validation, and 2025 holdout on the public PAXGUSDT proxy. It remains
  research-only until it passes broker-native XAUUSD bid/ask validation.
  The [formal research report](reports/M5_Volume_Reversal_Research_Report.md)
  is also available as a PDF in the repository.

The Python range model is research-only and is not yet implemented in MQL5.
Broker-native XAUUSD bid/ask data, walk-forward validation, and demo forward
testing are required before enabling EA entries.

Reproduce the fixed candidate studies after downloading the public-data set:

```bash
python scripts/research_trend_candidates.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  --output-json outputs/trend_candidate_research.json \
  --report reports/Trend_Candidate_Research.md

python scripts/research_range_candidates.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  --output-json outputs/range_candidate_research.json \
  --report reports/Range_Candidate_Research.md

python scripts/download_binance_aggtrades.py \
  --symbol PAXGUSDT --start 2021-01 --end 2025-12 \
  --bar-interval 1min --weekdays-only \
  --output data/derived/PAXGUSDT_order_flow_1m_2021_2025_weekdays.csv

python scripts/explore_order_flow_factors.py \
  data/derived/PAXGUSDT_order_flow_1m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_1m_2021_2025_weekdays.csv \
  --bar-minutes 1 --horizons 5,10,20,30 \
  --output outputs/order_flow_factor_screen_1m.csv \
  --report reports/Order_Flow_Factor_Screen_1m.md

python scripts/research_m5_order_flow_grid.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_5m_2021_2025.csv \
  --output outputs/m5_executable_factor_grid.csv \
  --report reports/M5_Executable_Factor_Grid.md

python scripts/research_order_flow_absorption.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_5m_2021_2025.csv \
  --factor volume_return_3_reversal --bar-minutes 5 --hold-bars 24 \
  --side long --session-hours 0-23 \
  --trades outputs/m5_volume_reversal_holdout_trades.csv \
  --report reports/M5_Volume_Reversal_Holdout.md
```

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
├── Experts/RegimeForgeVolumeReversalEA.mq5
└── Include/RegimeForge/
    ├── StrategyTypes.mqh
    └── TrendBreakoutStrategy.mqh
```

Copy the files into the corresponding folders under the MT5 `MQL5` data
directory and compile `Experts/RegimeForgeEA.mq5` in MetaEditor. Attach it to
the chart and symbol that should be traded; the EA uses `_Symbol`.

### M5 volume-reversal test EA

`Experts/RegimeForgeVolumeReversalEA.mq5` is a separate implementation of the
proxy-data research candidate. In MT5 Strategy Tester, attach it to an XAUUSD
M5 chart, use the broker's actual spread/tick settings, and set
`InpEnableNewEntries=true` only for the test. Its key candidate settings are
`InpReturnLookbackBars=3`, `InpQuantileBars=5760`,
`InpMinimumVolumeRatio=1.50`, and `InpHoldBars=24`. It uses MT5 tick volume,
which differs from the proxy's exchange-traded volume; this is intentional for
the broker-native validation and makes the test result authoritative over the
proxy result.

The conservative adaptive test profile is enabled by default: `InpFixedLots=0.02`,
a completed-H1 `EMA(20) > EMA(50)` filter, a 2% daily realized-loss lock, and
a 12-bar cooldown after four consecutive losing exits. Its proxy-data
[adaptive backtest](reports/M5_Adaptive_Volume_Reversal_Backtest.md) reduced
2025 maximum drawdown versus the original candidate, but did not improve every
historical sample; validate this profile independently in MT5. The detailed
[adaptive research paper](reports/M5_Adaptive_Volume_Reversal_Research_Paper.md)
and [PDF](reports/M5_Adaptive_Volume_Reversal_Research_Paper.pdf) document the
selection caveat, risk analysis, and professional-test protocol.

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
and should not be used with real funds without broker-specific validation. New
EA entries are disabled by default until a strategy passes the documented gates.

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
