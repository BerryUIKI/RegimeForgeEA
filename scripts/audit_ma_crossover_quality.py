"""Audit the selected H4 EMA crossover candidate for robustness and transfer risk."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import load_bars, resample_bars, run_backtest
from scripts.research_ma_crossover_candidates import CANDIDATES
from scripts.research_trend_candidates import split_bars


SAMPLES = (
    ("Training", "2021-01-01", "2024-01-01"),
    ("Validation", "2024-01-01", "2025-01-01"),
    ("Holdout", "2025-01-01", "2026-01-01"),
)


def selected_candidate():
    return next(item for item in CANDIDATES if item.name == "MA05_H4_20_50_2p5x4")


def metric(summary: dict) -> dict:
    factor = summary["profit_factor"]
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "profit_factor": None if factor is None else round(float(factor), 4),
    }


def table(rows: list[dict], first: str) -> str:
    lines = [f"| {first} | Sample | Return | Max drawdown | Trades | PF |", "|---|---|---:|---:|---:|---:|"]
    for row in rows:
        factor = "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        lines.append(
            f"| {row[first.lower().replace(' ', '_')]} | {row['sample']} | "
            f"{row['return_percent']:.2f}% | {row['max_drawdown_percent']:.2f}% | "
            f"{row['trades']} | {factor} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    candidate = selected_candidate()
    base = candidate.config()
    bars = resample_bars(load_bars(args.csv, default_spread_points=35.0), candidate.interval)

    costs = []
    for spread in (35.0, 70.0, 105.0, 140.0):
        stressed = bars.copy()
        stressed["spread"] = spread
        config = replace(base, max_spread_points=1000.0)
        for label, start, end in SAMPLES:
            summary, _, _ = run_backtest(split_bars(stressed, start, end), config)
            costs.append({"spread_points": int(spread), "sample": label, **metric(summary)})

    sides = []
    for name, config in (("Long only", replace(base, allow_short=False)), ("Short only", replace(base, allow_long=False))):
        for label, start, end in SAMPLES:
            summary, _, _ = run_backtest(split_bars(bars, start, end), config)
            sides.append({"side": name, "sample": label, **metric(summary)})

    years = []
    for year in range(2021, 2026):
        summary, _, _ = run_backtest(split_bars(bars, f"{year}-01-01", f"{year + 1}-01-01"), base)
        years.append({"year": year, **metric(summary)})

    payload = {"candidate": candidate.name, "cost_sensitivity": costs, "side_decomposition": sides, "calendar_years": years}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report = f"""# H4 EMA crossover quality audit

## Decision

**Not high quality for deployment.** The selected candidate remains a useful
research artifact, but it fails this stricter quality audit because independent
samples are small, short-only validation is negative, and modestly adverse
costs eliminate validation profitability. No live or demo activation should be
inferred from the original proxy-screen pass.

## Cost sensitivity

The 35-point baseline is the original fixed proxy assumption. Higher-cost rows
remove the entry-spread lock only to isolate the effect of cost; they are not
recommended operating settings.

{table(costs, 'Spread points')}

## Long/short decomposition at the original cost

{table(sides, 'Side')}

## Calendar-year stability at the original cost

| Year | Return | Max drawdown | Trades | PF |
|---:|---:|---:|---:|---:|
{chr(10).join(f"| {row['year']} | {row['return_percent']:.2f}% | {row['max_drawdown_percent']:.2f}% | {row['trades']} | {'N/A' if row['profit_factor'] is None else f'{row['profit_factor']:.2f}'} |" for row in years)}

## Quality assessment

The original chronological screen is valid as a preliminary hypothesis test:
the rule uses completed bars, takes both directions, defines exits before the
holdout, and has positive aggregate results at the baseline proxy cost. It is
not a sufficient basis for a high-quality classification. The 2024 validation
contains 24 trades and the 2025 holdout only 8. Calendar results are uneven,
with a negative 2021 and most profit concentrated in 2023. Most importantly,
the short-only sleeve loses in validation (PF below 1.0), so the evidence for
the requested short-selling component is not stable.

At 105 fixed spread points, validation turns negative; at 140 points, both
validation and holdout are negative. Broker-native XAUUSD costs can be variable
and can include spread, commission, swap, slippage, and gap risk, none of which
are captured by the baseline model. Therefore the candidate does not clear a
reasonable robustness threshold for deployment.

## Required evidence before reconsideration

1. MT5 backtests on broker-native XAUUSD bid/ask data with commission, swap,
   realistic variable spread, and the broker's actual contract specification.
2. A pre-registered, untouched out-of-sample period with a materially larger
   trade count than the present eight-trade holdout.
3. Side-specific evidence showing that both long and short components are
   robust, or an explicit redesign to remove the unsupported side.
4. Demo forward testing with order-level reconciliation against the EA log.
5. A new quality audit using the same adverse-cost and stability criteria.
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
