"""Run a fixed, time-split trend-strategy candidate study."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import Config, load_bars, resample_bars, run_backtest


@dataclass(frozen=True)
class Candidate:
    name: str
    interval: str
    fast_ma_period: int
    slow_ma_period: int
    breakout_bars: int
    adx_trend_level: float
    stop_atr: float
    take_profit_atr: float
    trailing_atr: float

    def config(self) -> Config:
        return Config(
            risk_percent=0.5,
            max_daily_loss_percent=100.0,
            max_drawdown_percent=100.0,
            fast_ma_period=self.fast_ma_period,
            slow_ma_period=self.slow_ma_period,
            breakout_bars=self.breakout_bars,
            adx_trend_level=self.adx_trend_level,
            stop_atr=self.stop_atr,
            take_profit_atr=self.take_profit_atr,
            trailing_atr=self.trailing_atr,
        )


CANDIDATES = (
    Candidate("T01_M15_baseline", "15min", 20, 50, 18, 20.0, 1.6, 3.0, 1.2),
    Candidate("T02_M15_longer", "15min", 20, 80, 30, 25.0, 2.0, 4.0, 1.5),
    Candidate("T03_M15_slow", "15min", 30, 100, 36, 22.0, 2.0, 4.0, 1.5),
    Candidate("T04_M30_baseline", "30min", 20, 50, 18, 20.0, 1.6, 3.0, 1.2),
    Candidate("T05_M30_longer", "30min", 20, 80, 24, 25.0, 2.0, 4.0, 1.5),
    Candidate("T06_H1_baseline", "1h", 20, 50, 12, 20.0, 2.0, 4.0, 1.5),
    Candidate("T07_H1_slow", "1h", 20, 100, 20, 25.0, 2.2, 4.5, 1.8),
    Candidate("T08_H1_balanced", "1h", 30, 100, 24, 20.0, 2.0, 3.5, 1.5),
)


def split_bars(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    result = frame.loc[(frame.index >= start) & (frame.index < end)].copy()
    if result.empty:
        raise ValueError(f"No data in requested range {start} to {end}")
    return result


def metrics(summary: dict) -> dict[str, float | int | None]:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def qualifies(result: dict) -> bool:
    profit_factor = result["profit_factor"]
    return (
        result["trades"] >= 30
        and profit_factor is not None
        and profit_factor >= 1.05
        and result["max_drawdown_percent"] <= 20.0
        and result["return_percent"] > 0.0
    )


def run_period(frame: pd.DataFrame, candidate: Candidate) -> dict:
    summary, _, _ = run_backtest(frame, candidate.config())
    return metrics(summary)


def markdown_table(rows: list[dict], period: str) -> str:
    table_rows = []
    for row in rows:
        display_row = dict(row)
        display_row["profit_factor"] = (
            "N/A"
            if row["profit_factor"] is None
            else f"{row['profit_factor']:.2f}"
        )
        table_rows.append(
            "| {name} | {interval} | {return_percent:.2f}% | {max_drawdown_percent:.2f}% | "
            "{trades} | {win_rate_percent:.2f}% | {profit_factor} |".format(**display_row)
        )
    body = "\n".join(table_rows)
    return (
        f"### {period}\n\n"
        "| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
        f"{body}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = load_bars(args.csv, default_spread_points=35.0)
    by_interval = {interval: resample_bars(source, interval) for interval in {c.interval for c in CANDIDATES}}
    train_rows: list[dict] = []
    candidates_by_name = {candidate.name: candidate for candidate in CANDIDATES}

    for candidate in CANDIDATES:
        result = run_period(split_bars(by_interval[candidate.interval], "2021-01-01", "2024-01-01"), candidate)
        train_rows.append({"name": candidate.name, "interval": candidate.interval, **result})

    survivors = [row for row in train_rows if qualifies(row)]
    validation_rows: list[dict] = []
    for row in survivors:
        candidate = candidates_by_name[row["name"]]
        result = run_period(split_bars(by_interval[candidate.interval], "2024-01-01", "2025-01-01"), candidate)
        validation_rows.append({"name": candidate.name, "interval": candidate.interval, **result})

    validated = [row for row in validation_rows if qualifies(row)]
    selected = max(
        validated,
        key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]),
        default=None,
    )
    test_result = None
    if selected:
        candidate = candidates_by_name[selected["name"]]
        result = run_period(split_bars(by_interval[candidate.interval], "2025-01-01", "2026-01-01"), candidate)
        test_result = {"name": candidate.name, "interval": candidate.interval, **result}

    payload = {
        "methodology": {
            "data_split": "2021-2023 train, 2024 validation, 2025 final holdout",
            "selection_rule": "train and validation require positive return, profit factor >= 1.05, max drawdown <= 20%, and at least 30 trades; the final holdout does not influence selection",
            "risk_model": "0.5% fixed-fractional risk with daily and drawdown locks disabled during strategy research",
            "candidates": len(CANDIDATES),
        },
        "train": train_rows,
        "validation": validation_rows,
        "selected": selected,
        "holdout": test_result,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    selection_text = (
        "No candidate passed the pre-defined training and validation gates. The EA defaults were not changed."
        if selected is None
        else (
            f"Selected `{selected['name']}` from training and validation only. "
            "Its final-holdout result is reported below and was not used for selection."
        )
    )
    holdout_table = (
        markdown_table([test_result], "Final holdout: 2025") if test_result else "No final-holdout run was authorized by the selection gate.\n"
    )
    report = f"""# Trend candidate research\n\n## Method\n\nEight pre-defined Donchian/EMA/ADX trend candidates were evaluated. The process uses 2021–2023 for training, 2024 for validation, and 2025 as a final holdout. The holdout is not used to select a candidate. Research uses 0.5% fixed-fractional risk and disables safety locks solely to reveal full-period strategy behavior.\n\nA candidate must have positive return, profit factor at least 1.05, maximum drawdown no greater than 20%, and at least 30 trades in both training and validation to reach the holdout.\n\n{markdown_table(train_rows, 'Training: 2021–2023')}\n{markdown_table(validation_rows, 'Validation: 2024')}\n## Selection\n\n{selection_text}\n\n{holdout_table}\n## Decision\n\nDo not change EA defaults unless a selected candidate also has positive final-holdout return, profit factor above 1.05, and maximum drawdown no greater than 20%. This study uses PAXGUSDT as a gold-linked public proxy, not broker-native XAUUSD data.\n"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
