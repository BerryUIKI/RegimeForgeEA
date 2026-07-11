"""Evaluate volume-free long/short ATR-compression breakout candidates."""

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
    higher_timeframe: str
    higher_fast: int
    higher_slow: int
    compression_ratio: float
    breakout_bars: int
    stop_atr: float
    target_atr: float
    trailing_atr: float
    time_exit_bars: int

    def config(self) -> Config:
        return Config(
            strategy="compression_breakout",
            higher_timeframe=self.higher_timeframe,
            higher_fast_ma_period=self.higher_fast,
            higher_slow_ma_period=self.higher_slow,
            compression_max_atr_ratio=self.compression_ratio,
            breakout_bars=self.breakout_bars,
            stop_atr=self.stop_atr,
            take_profit_atr=self.target_atr,
            trailing_atr=self.trailing_atr,
            time_exit_bars=self.time_exit_bars,
            initial_equity=10_000.0,
            risk_percent=0.25,
            max_daily_loss_percent=2.0,
            max_drawdown_percent=20.0,
            allow_long=True,
            allow_short=True,
        )


CANDIDATES = (
    Candidate("CB01_H1_c80_b12_1p5x2", "1h", 20, 50, 0.80, 12, 1.5, 2.0, 1.2, 48),
    Candidate("CB02_H1_c65_b18_1p5x2", "1h", 20, 50, 0.65, 18, 1.5, 2.0, 1.2, 48),
    Candidate("CB03_H1slow_c80_b12_2x3", "1h", 20, 100, 0.80, 12, 2.0, 3.0, 1.5, 60),
    Candidate("CB04_H4_c80_b12_2x3", "4h", 20, 50, 0.80, 12, 2.0, 3.0, 1.5, 60),
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
        output.append(f"| {item['name']} | {item['return_percent']:.2f}% | {item['max_drawdown_percent']:.2f}% | {item['trades']} | {item['win_rate_percent']:.2f}% | {pf} |")
    return "\n".join(output) or "| None | - | - | - | - | - |"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = load_bars(args.csv, default_spread_points=35.0)
    train, validation, holdout = (split_bars(source, start, end) for start, end in (("2021-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01")))
    train_rows = [{"name": candidate.name, **metric(run_backtest(train, candidate.config())[0])} for candidate in CANDIDATES]
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    validation_rows = [{"name": row["name"], **metric(run_backtest(validation, by_name[row["name"]].config())[0])} for row in train_rows if passes(row, 100)]
    approved = [row for row in validation_rows if passes(row, 40)]
    selected = max(approved, key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]), default=None)
    holdout_row = None if selected is None else {"name": selected["name"], **metric(run_backtest(holdout, by_name[selected["name"]].config())[0])}
    payload = {"train": train_rows, "validation": validation_rows, "selected": selected, "holdout": holdout_row}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report = f"""# ATR-compression breakout candidate research

## Method

This study is entirely price-based. It trades long when a completed H1/H4 EMA trend is up, M5 ATR is compressed relative to its 56-bar ATR, and price breaks the prior M5 range high; it trades short symmetrically. Each candidate has ATR stop loss, take profit, trailing stop, maximum holding time, 0.25% risk sizing, 2% daily loss lock, 20% peak drawdown lock, and next-bar bid/ask execution. Volume is not used.

## Training: 2021-2023

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
{rows(train_rows)}

## Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
{rows(validation_rows)}

## Decision

{'No candidate passed training and validation, so 2025 was not evaluated.' if selected is None else f'{selected["name"]} was selected before its 2025 holdout run.'}
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
