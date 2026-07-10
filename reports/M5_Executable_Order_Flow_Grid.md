# M5 executable order-flow grid

## Protocol

This pre-defined grid tests OFI momentum, OFI reversal, and price/OFI absorption factors; both directions; four UTC sessions; and 5/10/15/30/60/120 minute exits. OFI uses the three-bar signed taker-volume ratio and trailing 20-trading-day 20/80 thresholds shifted one M5 bar. Entries occur at the next M5 bid/ask, exits at the fixed-horizon close, a 0.35 USD round-trip spread is charged, and positions cannot overlap.

Training is 2021–2023. A candidate needs 100 trades, PF >= 1.10, and >= 0.50 mean net bps before training-only selection by mean-bps-times-square-root-trades. The selected candidate then needs 30 validation trades, PF >= 1.05, and >= 0.25 mean net bps in 2024. The 2025 holdout is not examined unless it passes validation.

## Training shortlist and 2024 validation

| Family | Session | Side | Hold (min) | Train trades | Train PF | Train bps | Validation trades | Validation PF | Validation bps |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| None | - | - | - | - | - | - | - | - | - |

## Decision

No training-selected candidate passed validation. Do not inspect 2025 or integrate this grid into the EA.
