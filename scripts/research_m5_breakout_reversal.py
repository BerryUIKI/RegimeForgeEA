"""Evaluate price-only M5 breakout-reversal rules with live-style exits."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import Config, load_bars, run_backtest
from scripts.research_trend_candidates import split_bars


@dataclass(frozen=True)
class Candidate:
    name: str
    breakout_bars: int
    stop_atr: float
    target_atr: float
    trailing_atr: float
    time_exit_bars: int
    allow_long: bool
    allow_short: bool

    def config(self) -> Config:
        return Config(
            strategy="breakout_reversal",
            breakout_bars=self.breakout_bars,
            stop_atr=self.stop_atr,
            take_profit_atr=self.target_atr,
            trailing_atr=self.trailing_atr,
            time_exit_bars=self.time_exit_bars,
            initial_equity=10_000.0,
            risk_percent=0.25,
            max_daily_loss_percent=2.0,
            max_drawdown_percent=20.0,
            allow_long=self.allow_long,
            allow_short=self.allow_short,
        )


CANDIDATES = (
    Candidate("BR01_12_both_1p5x2_24", 12, 1.5, 2.0, 1.5, 24, True, True),
    Candidate("BR02_12_short_1p5x2_24", 12, 1.5, 2.0, 1.5, 24, False, True),
    Candidate("BR03_12_short_2x3_24", 12, 2.0, 3.0, 2.0, 24, False, True),
    Candidate("BR04_12_short_2x3_12", 12, 2.0, 3.0, 2.0, 12, False, True),
    Candidate("BR05_12_short_2p5x4_24", 12, 2.5, 4.0, 2.5, 24, False, True),
    Candidate("BR06_18_short_2x3_24", 18, 2.0, 3.0, 2.0, 24, False, True),
    Candidate("BR07_24_short_2x3_24", 24, 2.0, 3.0, 2.0, 24, False, True),
    Candidate("BR08_12_both_2x3_24", 12, 2.0, 3.0, 2.0, 24, True, True),
)


def metric(summary: dict) -> dict:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def passes(row: dict, minimum_trades: int) -> bool:
    return (
        row["trades"] >= minimum_trades
        and row["profit_factor"] is not None
        and row["profit_factor"] >= 1.10
        and row["return_percent"] > 0
        and row["max_drawdown_percent"] <= 15.0
    )


def table(rows: list[dict]) -> str:
    output = []
    for row in rows:
        pf = "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        output.append(f"| {row['name']} | {row['return_percent']:.2f}% | {row['max_drawdown_percent']:.2f}% | {row['trades']} | {row['win_rate_percent']:.2f}% | {pf} |")
    return "\n".join(output) or "| None | - | - | - | - | - |"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    bars = load_bars(args.csv, default_spread_points=35.0)
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    train = split_bars(bars, "2021-01-01", "2024-01-01")
    training = [{"name": candidate.name, **metric(run_backtest(train, candidate.config())[0])} for candidate in CANDIDATES]
    validation = []
    for row in training:
        if passes(row, 500):
            candidate = by_name[row["name"]]
            validation.append({"name": candidate.name, **metric(run_backtest(split_bars(bars, "2024-01-01", "2025-01-01"), candidate.config())[0])})
    approved = [row for row in validation if passes(row, 150)]
    selected = max(approved, key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]), default=None)
    holdout = None
    if selected:
        candidate = by_name[selected["name"]]
        holdout = {"name": candidate.name, **metric(run_backtest(split_bars(bars, "2025-01-01", "2026-01-01"), candidate.config())[0])}
    payload = {"training": training, "validation": validation, "selected": selected, "holdout": holdout}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = f"""# M5 price-action breakout reversal research

This study excludes volume and order-flow inputs. Signals use completed M5 price
only: long below the previous N-bar low and short above the previous N-bar high.
Orders execute on the next bar bid/ask and use ATR stop loss, take profit,
trailing stop, time exit, 0.25% equity risk, 2% daily lock, and 20% peak-drawdown lock.

## Training: 2021-2023

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
{table(training)}

## Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
{table(validation)}

## Decision

{'No candidate passed training and validation; 2025 was not inspected.' if selected is None else f'{selected["name"]} was selected before evaluating the 2025 holdout.'}
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
