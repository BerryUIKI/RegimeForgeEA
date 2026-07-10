# M1 executable order-flow grid

## Protocol

The grid evaluates the pre-defined price/OFI absorption formula for long and short sides, four UTC sessions, and 5/10/20/30 minute holding periods. At a closed one-minute bar, it uses a trailing 20-trading-day (28,800-bar) 20/80 quantile threshold shifted by one bar. A long signal combines a negative three-bar price extreme with a positive OFI extreme; a short signal is symmetric.

Every evaluation enters at the next one-minute bar's bid/ask, exits at the specified close, charges a 0.35 USD round-trip spread, and prohibits overlap. Training (2021–2023) selects the one candidate with the largest mean-bps-times-square-root-trades score after the gates: at least 500 trades, PF >= 1.10, and mean net return >= 0.50 bps. Validation (2024) requires at least 150 trades, PF >= 1.05, and mean net return >= 0.25 bps. The 2025 holdout is not inspected here.

## Training shortlist and 2024 validation

| Session | Side | Hold (min) | Train trades | Train PF | Train bps | Validation trades | Validation PF | Validation bps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| None | - | - | - | - | - | - | - | - |

## Decision

No training-selected candidate passed the stated validation gates. Do not inspect 2025 or integrate this grid into the EA.
