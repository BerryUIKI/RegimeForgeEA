# High-frequency pullback candidate research

## Factor formula

At M5 close t, let B_lower(t), B_upper(t) be Bollinger bands and RSI(t) be the M5 RSI. Let EMA_fast^H(t-1), EMA_slow^H(t-1) be the higher-timeframe EMAs calculated only through the last completed higher-timeframe bar.

- Long if EMA_fast^H(t-1) > EMA_slow^H(t-1), Close(t) < B_lower(t), and RSI(t) <= L.
- Short if EMA_fast^H(t-1) < EMA_slow^H(t-1), Close(t) > B_upper(t), and RSI(t) >= U.
- The order is placed at the next M5 open; stops, targets, and trailing stops are ATR multiples.

This is high-frequency in execution: all entries are M5, while H1/H4 is a delayed direction filter. The fixed protocol uses 2021–2023 training, 2024 validation, and 2025 holdout. Gates require positive return, PF >= 1.05, maximum drawdown <= 20%, 150+ training trades, and 50+ validation trades.

### Training: 2021–2023

| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|
| HF01_H1_bb15_rsi40 | -96.12% | 97.10% | 7842 | 32.76% | 0.82 |
| HF02_H1_bb20_rsi35 | -64.54% | 67.64% | 3498 | 35.93% | 0.74 |
| HF03_H1_bb20_rsi30 | -34.93% | 37.33% | 1555 | 34.60% | 0.70 |
| HF04_H1_slow | -96.09% | 97.08% | 7796 | 32.80% | 0.82 |
| HF05_H1_longbb | -70.10% | 73.35% | 4376 | 36.11% | 0.77 |
| HF06_H4_bb15 | -96.16% | 97.07% | 7602 | 32.44% | 0.80 |
| HF07_H4_bb20 | -66.99% | 70.85% | 3526 | 35.54% | 0.73 |
| HF08_H4_slow | -74.22% | 77.80% | 4531 | 35.60% | 0.76 |

### Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|


## Selection

No candidate passed training and validation.

No final-holdout run was authorized.

## Decision

Do not enable the factor in MQL5 unless it passes the final holdout and then broker-native XAUUSD bid/ask testing.
