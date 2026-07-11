"""Evaluate price-only H1/H4 long/short moving-average crossover candidates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import Config, load_bars, resample_bars, run_backtest
from scripts.research_trend_candidates import split_bars


@dataclass(frozen=True)
class Candidate:
    name: str
    interval: str
    fast: int
    slow: int
    stop_atr: float
    target_atr: float
    trailing_atr: float
    time_exit_bars: int

    def config(self) -> Config:
        return Config(
            strategy="ma_crossover",
            fast_ma_period=self.fast,
            slow_ma_period=self.slow,
            stop_atr=self.stop_atr,
            take_profit_atr=self.target_atr,
            trailing_atr=self.trailing_atr,
            time_exit_bars=self.time_exit_bars,
            initial_equity=10_000.0,
            risk_percent=0.5,
            max_daily_loss_percent=2.0,
            max_drawdown_percent=20.0,
            allow_long=True,
            allow_short=True,
        )


CANDIDATES = (
    Candidate("MA01_H1_10_30_2x3", "1h", 10, 30, 2.0, 3.0, 2.0, 72),
    Candidate("MA02_H1_20_50_2x3", "1h", 20, 50, 2.0, 3.0, 2.0, 96),
    Candidate("MA03_H1_20_100_2p5x4", "1h", 20, 100, 2.5, 4.0, 2.5, 120),
    Candidate("MA04_H4_10_30_2x3", "4h", 10, 30, 2.0, 3.0, 2.0, 30),
    Candidate("MA05_H4_20_50_2p5x4", "4h", 20, 50, 2.5, 4.0, 2.5, 42),
    Candidate("MA06_H4_50_100_3x5", "4h", 50, 100, 3.0, 5.0, 3.0, 60),
)


def metric(summary: dict) -> dict:
    return {"return_percent": round(float(summary["total_return_percent"]), 4), "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4), "trades": int(summary["trades"]), "win_rate_percent": round(float(summary["win_rate_percent"]), 4), "profit_factor": summary["profit_factor"]}


def passes(row: dict, minimum_trades: int) -> bool:
    return row["trades"] >= minimum_trades and row["profit_factor"] is not None and row["profit_factor"] >= 1.10 and row["return_percent"] > 0 and row["max_drawdown_percent"] <= 15.0


def rows(items: list[dict]) -> str:
    text = []
    for item in items:
        pf = "N/A" if item["profit_factor"] is None else f"{item['profit_factor']:.2f}"
        text.append(f"| {item['name']} | {item['interval']} | {item['return_percent']:.2f}% | {item['max_drawdown_percent']:.2f}% | {item['trades']} | {item['win_rate_percent']:.2f}% | {pf} |")
    return "\n".join(text) or "| None | - | - | - | - | - | - |"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = load_bars(args.csv, default_spread_points=35.0)
    data_by_interval = {interval: resample_bars(source, interval) for interval in {candidate.interval for candidate in CANDIDATES}}
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    train_rows = []
    for candidate in CANDIDATES:
        train = split_bars(data_by_interval[candidate.interval], "2021-01-01", "2024-01-01")
        train_rows.append({"name": candidate.name, "interval": candidate.interval, **metric(run_backtest(train, candidate.config())[0])})
    validation_rows = []
    for row in train_rows:
        if passes(row, 50 if row["interval"] == "1h" else 20):
            candidate = by_name[row["name"]]
            validation = split_bars(data_by_interval[candidate.interval], "2024-01-01", "2025-01-01")
            validation_rows.append({"name": candidate.name, "interval": candidate.interval, **metric(run_backtest(validation, candidate.config())[0])})
    approved = [row for row in validation_rows if passes(row, 15 if row["interval"] == "1h" else 6)]
    selected = max(approved, key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]), default=None)
    holdout_row = None
    if selected:
        candidate = by_name[selected["name"]]
        holdout = split_bars(data_by_interval[candidate.interval], "2025-01-01", "2026-01-01")
        holdout_row = {"name": candidate.name, "interval": candidate.interval, **metric(run_backtest(holdout, candidate.config())[0])}
    payload = {"train": train_rows, "validation": validation_rows, "selected": selected, "holdout": holdout_row}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = f"""# Moving-average crossover swing candidate research

## Method

This volume-free study uses completed H1/H4 EMA crossover signals, symmetric long and short entries, next-bar bid/ask execution, ATR stop loss, ATR take profit, trailing stop, time exit, 0.5% equity risk, 2% daily loss lock, and 20% peak drawdown lock.

## Training: 2021-2023

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|---:|
{rows(train_rows)}

## Validation: 2024

| Candidate | Bars | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|---:|
{rows(validation_rows)}

## Decision

{'No candidate passed training and validation, so 2025 was not evaluated.' if selected is None else f'{selected["name"]} was selected before its 2025 holdout run.'}
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
