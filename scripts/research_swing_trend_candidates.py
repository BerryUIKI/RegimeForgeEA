"""Evaluate price-only H4/D1 swing trend candidates with live-style exits."""

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
    adx_level: float
    breakout_bars: int
    stop_atr: float
    target_atr: float
    trailing_atr: float
    time_exit_bars: int

    def config(self) -> Config:
        return Config(
            strategy="trend_breakout",
            fast_ma_period=self.fast,
            slow_ma_period=self.slow,
            adx_trend_level=self.adx_level,
            breakout_bars=self.breakout_bars,
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
    Candidate("ST01_H4_20_50_adx20_br12", "4h", 20, 50, 20.0, 12, 1.5, 3.0, 2.0, 30),
    Candidate("ST02_H4_20_50_adx25_br18", "4h", 20, 50, 25.0, 18, 2.0, 4.0, 2.5, 42),
    Candidate("ST03_H4_50_100_adx20_br12", "4h", 50, 100, 20.0, 12, 2.0, 3.0, 2.0, 36),
    Candidate("ST04_H4_20_50_adx30_br24", "4h", 20, 50, 30.0, 24, 2.0, 4.0, 2.5, 48),
    Candidate("ST05_D1_20_50_adx20_br10", "1d", 20, 50, 20.0, 10, 2.0, 3.0, 2.0, 20),
    Candidate("ST06_D1_10_30_adx25_br20", "1d", 10, 30, 25.0, 20, 2.0, 4.0, 2.5, 30),
)


def metric(summary: dict) -> dict:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def passes(result: dict, minimum_trades: int) -> bool:
    return result["trades"] >= minimum_trades and result["profit_factor"] is not None and result["profit_factor"] >= 1.10 and result["return_percent"] > 0 and result["max_drawdown_percent"] <= 15.0


def rows(items: list[dict]) -> str:
    output = []
    for item in items:
        pf = "N/A" if item["profit_factor"] is None else f"{item['profit_factor']:.2f}"
        output.append(f"| {item['name']} | {item['interval']} | {item['return_percent']:.2f}% | {item['max_drawdown_percent']:.2f}% | {item['trades']} | {item['win_rate_percent']:.2f}% | {pf} |")
    return "\n".join(output) or "| None | - | - | - | - | - | - |"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = load_bars(args.csv, default_spread_points=35.0)
    interval_data = {interval: resample_bars(source, interval) for interval in {candidate.interval for candidate in CANDIDATES}}
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    train_rows = []
    for candidate in CANDIDATES:
        data = split_bars(interval_data[candidate.interval], "2021-01-01", "2024-01-01")
        train_rows.append({"name": candidate.name, "interval": candidate.interval, **metric(run_backtest(data, candidate.config())[0])})
    validation_rows = []
    for row in train_rows:
        minimum = 30 if row["interval"] == "4h" else 8
        if passes(row, minimum):
            candidate = by_name[row["name"]]
            data = split_bars(interval_data[candidate.interval], "2024-01-01", "2025-01-01")
            validation_rows.append({"name": candidate.name, "interval": candidate.interval, **metric(run_backtest(data, candidate.config())[0])})
    approved = [row for row in validation_rows if passes(row, 10 if row["interval"] == "4h" else 3)]
    selected = max(approved, key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]), default=None)
    holdout_row = None
    if selected is not None:
        candidate = by_name[selected["name"]]
        data = split_bars(interval_data[candidate.interval], "2025-01-01", "2026-01-01")
        holdout_row = {"name": candidate.name, "interval": candidate.interval, **metric(run_backtest(data, candidate.config())[0])}
    payload = {"train": train_rows, "validation": validation_rows, "selected": selected, "holdout": holdout_row}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = f"""# H4/D1 swing trend candidate research

## Method

This study is price-only and non-ultra-high-frequency. It uses H4 or D1 EMA/ADX/Donchian-style trend breakouts, symmetric long and short signals, next-bar bid/ask execution, ATR stop loss, ATR take profit, trailing stop, time exit, 0.5% equity risk, 2% daily loss lock, and a 20% peak-drawdown entry lock. Volume is not used.

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
