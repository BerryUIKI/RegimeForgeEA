---
title: "Adaptive M5 Volume-Confirmed Reversal: Detailed Research Paper"
author: "RegimeForgeEA"
date: "2026-07-10"
geometry: margin=0.70in
fontsize: 10pt
---

# Abstract

This paper documents an M5 long reversal candidate and a subsequent
risk-adaptive overlay. The base rule was selected with a 2021-2023 training
set, validated on 2024, and evaluated once on a 2025 holdout using public
PAXGUSDT data as a gold-linked proxy. The adaptive overlay adds a completed H1
trend filter, a daily realized-loss lock, and a loss-streak cooldown. It reduces
the observed 2025 drawdown, but it was designed after inspecting the original
holdout result; consequently it is exploratory and requires a new independent
broker-native XAUUSD test before any deployment decision.

# 1. Research question

The base candidate has positive proxy-data performance but an unacceptable 2025
drawdown at the original 0.10 lot reference size. The purpose of the adaptive
overlay is to avoid mean-reversion entries during broader downtrends and to
limit repeated losses during adverse intraday conditions, without modifying the
underlying alpha signal.

# 2. Data and execution assumptions

The research uses weekday-only PAXGUSDT five-minute bars from 2021 through
2025. PAXGUSDT is a public gold-linked proxy and is not an XAUUSD broker feed.
Aggregate-trade-derived volume is used for the proxy factor. The backtest enters
at the next M5 open, charges a fixed 0.35 USD round-trip spread, exits at a
fixed horizon, and prohibits position overlap. Dollar PnL is expressed with a
0.10 lot and 100 oz contract reference solely for comparability.

The following are outside scope: broker Bid/Ask history, slippage, commissions,
swaps, fill latency, stop-level rules, symbol suffixes, weekend gaps, and order
rejections. Any performance result in this paper is therefore research evidence
rather than an XAUUSD or live-trading claim.

# 3. Base factor specification

Let $C_t$ and $V_t$ denote the close and volume of the closed M5 bar $t$.

$$r_3(t)=\frac{C_t}{C_{t-3}}-1$$

Let $q_{20}(t)$ be the 20th percentile of the preceding 5,760 three-bar returns
(20 trading days), calculated with a one-bar shift. The shift ensures that the
threshold at $t$ excludes the current signal return.

$$q_{20}(t)=Q_{0.20}(\{r_3(s):s<t\})$$

Define the volume ratio:

$$VR(t)=\frac{V_t}{SMA_{60}(V)_t}$$

The base long signal is:

$$r_3(t)\le q_{20}(t)\quad\land\quad VR(t)\ge1.5$$

At the signal close, the strategy submits a long order at the next M5 opening
price. It exits after 24 M5 bars (120 minutes). Entry and exit each include half
of the fixed 0.35 USD round-trip spread.

# 4. Base-rule selection protocol

The original grid used direct, non-overlapping order-level simulations. It
considered order-flow, return reversal, breakout reversal, and volume-confirmed
reversal families; long and short directions; Asia, London, New York, and all
UTC sessions; and holding periods from 5 to 120 minutes.

The training candidate gate required at least 100 trades, profit factor (PF)
at least 1.10, and mean net return at least 0.50 bps. The selected candidate
then required at least 30 validation trades, PF at least 1.05, and mean net
return at least 0.25 bps. The 2025 sample was inspected only after the base
candidate passed 2024 validation.

# 5. Drawdown diagnosis

The base rule is a long mean-reversion strategy. Its adverse periods are
concentrated in persistent downtrends and elevated volatility, where repeated
oversold readings do not revert promptly. In the 2025 proxy holdout, the worst
monthly results occurred in May, October, and December, and the maximum
drawdown trough occurred on 21 November 2025. The 0.10 lot reference drawdown
was 4,927.40 USD, compared with 6,707.20 USD total holdout PnL.

# 6. Adaptive overlay

The overlay does not change the base alpha condition. It controls when new
signals may be traded.

## 6.1 Completed H1 trend filter

Only trade when the prior completed H1 bar has a positive EMA trend:

$$EMA_{20}^{H1}(t-1)>EMA_{50}^{H1}(t-1)$$

The completed-bar shift prevents use of an unfinished H1 candle.

## 6.2 Daily realized-loss lock

Let $B_d$ be the account balance at the start of broker day $d$, and let
$R_d$ be realized PnL accumulated during that day. Reject new entries when:

$$R_d\le-0.02B_d$$

The lock resets on the next broker day. It does not forcibly close an existing
position; it only stops subsequent entries.

## 6.3 Loss-streak cooldown

After four consecutive losing exits, do not open a new position for 12 M5 bars
(one hour). A profitable exit resets the loss counter. The cooldown is intended
to avoid clustered entries when the short-horizon reversal premise is failing.

# 7. Results

| Sample | Base PF | Adaptive PF | Base net PnL | Adaptive net PnL | Base max DD | Adaptive max DD |
|---|---:|---:|---:|---:|---:|---:|
| Training 2021-2023 | 1.156 | 1.162 | 11,644.50 | 6,063.90 | -2,111.00 | -2,251.00 |
| Validation 2024 | 1.257 | 1.334 | 7,832.00 | 5,565.00 | -1,847.00 | -946.00 |
| Holdout 2025 | 1.119 | 1.221 | 6,707.20 | 7,151.00 | -4,927.40 | -3,134.50 |

![Base and adaptive comparison](assets/adaptive_factor_comparison.png)

The overlay improves PF in every displayed sample. However, training drawdown
is slightly worse, so the overlay must not be presented as universally superior.
It is a risk-oriented adaptation that materially improves the observed 2024 and
2025 drawdowns, not an optimized global solution.

![2025 holdout equity comparison](assets/adaptive_factor_holdout_equity.png)

![Adaptive monthly PnL](assets/adaptive_factor_monthly_pnl.png)

# 8. Position sizing interpretation

The 0.10 lot reference is too aggressive for a 10,000 USD account. With a
linear approximation, the adaptive 2025 maximum drawdown of 3,134.50 USD at
0.10 lot becomes approximately 626.90 USD at 0.02 lot, or about 6.3% of a
10,000 USD account. This is an illustration, not a risk guarantee: real XAUUSD
spread, slippage, contract size, and gap behavior can break linear scaling.

The provided EA therefore defaults to `InpFixedLots=0.02`. The professional
tester should use the broker's contract specification and an account-level risk
budget rather than copying this illustration mechanically.

# 9. MQL5 implementation mapping

`Experts/RegimeForgeVolumeReversalEA.mq5` implements the following semantics:

1. Evaluate the volume-confirmed reversal signal on the last completed M5 bar.
2. Calculate the threshold from prior bars only.
3. Require the previous completed H1 EMA20/EMA50 trend condition.
4. Block new entries after the daily realized-loss limit or a loss-streak
   cooldown.
5. Use the EA magic number to isolate positions and exit the managed position
   after the configured holding interval.

The EA intentionally defaults to `InpEnableNewEntries=false`. A tester must
explicitly enable entries in MT5 Strategy Tester.

# 10. Professional XAUUSD test protocol

The professional tester should use real ticks or the best available broker
Bid/Ask model, fixed symbol specifications, and a full commission/swap setup.
At minimum, record:

1. PF, expectancy, maximum drawdown, recovery factor, and trade count.
2. Sensitivity to spread expansion, slippage, and execution delay.
3. Performance across at least three non-overlapping calendar periods.
4. Results with the base rule and adaptive overlay separately.
5. Risk at 0.01, 0.02, and a broker-appropriate risk-sized volume.
6. Behaviour around news, rollover, and sessions with poor liquidity.

The adaptive configuration should be considered accepted only if its XAUUSD
result remains positive after realistic costs and its drawdown stays inside the
tester-defined risk budget.

# 11. Reproduction

```powershell
python scripts/research_order_flow_absorption.py \
  data/derived/PAXGUSDT_5m_2021_2025_weekdays.csv \
  data/derived/PAXGUSDT_order_flow_5m_2021_2025.csv \
  --factor volume_return_3_reversal --bar-minutes 5 --hold-bars 24 \
  --side long --session-hours 0-23 --use-higher-trend-filter \
  --max-daily-loss-percent 2 --initial-equity 10000 \
  --max-consecutive-losses 4 --cooldown-bars 12 \
  --trades outputs/m5_adaptive_volume_reversal_trades.csv \
  --report reports/M5_Adaptive_Volume_Reversal_Backtest.md

python scripts/generate_adaptive_factor_paper_charts.py \
  outputs/m5_volume_reversal_holdout_trades.csv \
  outputs/m5_adaptive_volume_reversal_trades.csv \
  --assets reports/assets
```

# 12. Conclusion

The base M5 volume-confirmed reversal factor is a credible proxy-data research
candidate with positive training, validation, and original holdout results. The
adaptive overlay improves observed recent-sample risk but is exploratory because
it was formulated after inspecting the original holdout drawdown. Broker-native
XAUUSD Bid/Ask testing is the next decision gate; no live-profit conclusion is
warranted before that test is complete.
