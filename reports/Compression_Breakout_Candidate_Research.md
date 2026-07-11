# ATR-compression breakout candidate research

## Method

This study is entirely price-based. It trades long when a completed H1/H4 EMA trend is up, M5 ATR is compressed relative to its 56-bar ATR, and price breaks the prior M5 range high; it trades short symmetrically. Each candidate has ATR stop loss, take profit, trailing stop, maximum holding time, 0.25% risk sizing, 2% daily loss lock, 20% peak drawdown lock, and next-bar bid/ask execution. Volume is not used.

## Training: 2021-2023

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
| CB01_H1_c80_b12_1p5x2 | -20.09% | 20.09% | 222 | 20.27% | 0.31 |
| CB02_H1_c65_b18_1p5x2 | -2.52% | 3.01% | 55 | 29.09% | 0.64 |
| CB03_H1slow_c80_b12_2x3 | -20.02% | 20.02% | 281 | 20.64% | 0.37 |
| CB04_H4_c80_b12_2x3 | -20.06% | 20.06% | 272 | 21.32% | 0.35 |

## Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
| None | - | - | - | - | - |

## Decision

No candidate passed training and validation, so 2025 was not evaluated.
