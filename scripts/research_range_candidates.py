"""Run a fixed, time-split range mean-reversion candidate study."""

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
from scripts.research_trend_candidates import qualifies, split_bars


@dataclass(frozen=True)
class Candidate:
    name: str
    interval: str
    bollinger_period: int
    bollinger_deviation: float
    rsi_lower: float
    rsi_upper: float
    adx_trend_level: float
    stop_atr: float
    take_profit_atr: float
    trailing_atr: float

    def config(self) -> Config:
        return Config(
            strategy="range_mean_reversion",
            risk_percent=0.5,
            max_daily_loss_percent=100.0,
            max_drawdown_percent=100.0,
            bollinger_period=self.bollinger_period,
            bollinger_deviation=self.bollinger_deviation,
            rsi_lower=self.rsi_lower,
            rsi_upper=self.rsi_upper,
            adx_trend_level=self.adx_trend_level,
            stop_atr=self.stop_atr,
            take_profit_atr=self.take_profit_atr,
            trailing_atr=self.trailing_atr,
        )


CANDIDATES = (
    Candidate("R01_M15_standard", "15min", 20, 2.0, 30.0, 70.0, 20.0, 1.6, 1.6, 1.0),
    Candidate("R02_M15_strict", "15min", 20, 2.25, 25.0, 75.0, 18.0, 2.0, 2.0, 1.2),
    Candidate("R03_M15_long", "15min", 30, 2.0, 30.0, 70.0, 18.0, 2.0, 1.8, 1.2),
    Candidate("R04_M30_standard", "30min", 20, 2.0, 30.0, 70.0, 20.0, 1.6, 1.6, 1.0),
    Candidate("R05_M30_strict", "30min", 25, 2.25, 25.0, 75.0, 18.0, 2.0, 2.0, 1.2),
    Candidate("R06_H1_standard", "1h", 20, 2.0, 30.0, 70.0, 20.0, 1.6, 1.6, 1.0),
    Candidate("R07_H1_strict", "1h", 25, 2.25, 25.0, 75.0, 18.0, 2.0, 2.0, 1.2),
    Candidate("R08_H1_long", "1h", 30, 2.0, 30.0, 70.0, 18.0, 2.0, 1.8, 1.2),
)


def metrics(summary: dict) -> dict:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def run_period(frame, candidate: Candidate) -> dict:
    summary, _, _ = run_backtest(frame, candidate.config())
    return metrics(summary)


def table(rows: list[dict], title: str) -> str:
    table_rows = []
    for row in rows:
        profit_factor = (
            "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        )
        table_rows.append(
            f"| {row['name']} | {row['interval']} | {row['return_percent']:.2f}% | "
            f"{row['max_drawdown_percent']:.2f}% | {row['trades']} | "
            f"{row['win_rate_percent']:.2f}% | {profit_factor} |"
        )
    body = "\n".join(table_rows)
    return f"### {title}\n\n| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |\n|---|---:|---:|---:|---:|---:|---:|\n{body}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    source = load_bars(args.csv, default_spread_points=35.0)
    by_interval = {interval: resample_bars(source, interval) for interval in {c.interval for c in CANDIDATES}}
    candidate_by_name = {candidate.name: candidate for candidate in CANDIDATES}
    train = []
    for candidate in CANDIDATES:
        result = run_period(split_bars(by_interval[candidate.interval], "2021-01-01", "2024-01-01"), candidate)
        train.append({"name": candidate.name, "interval": candidate.interval, **result})
    validation = []
    for row in filter(qualifies, train):
        candidate = candidate_by_name[row["name"]]
        result = run_period(split_bars(by_interval[candidate.interval], "2024-01-01", "2025-01-01"), candidate)
        validation.append({"name": candidate.name, "interval": candidate.interval, **result})
    approved = [row for row in validation if qualifies(row)]
    selected = max(
        approved,
        key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]),
        default=None,
    )
    holdout = None
    if selected:
        candidate = candidate_by_name[selected["name"]]
        result = run_period(split_bars(by_interval[candidate.interval], "2025-01-01", "2026-01-01"), candidate)
        holdout = {"name": candidate.name, "interval": candidate.interval, **result}
    payload = {
        "methodology": {
            "data_split": "2021-2023 train, 2024 validation, 2025 final holdout",
            "selection_rule": "same fixed gates as trend research",
            "strategy": "range-only Bollinger/RSI mean reversion",
            "candidates": len(CANDIDATES),
        },
        "train": train,
        "validation": validation,
        "selected": selected,
        "holdout": holdout,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    decision = (
        "No candidate passed the pre-defined training and validation gates. The EA defaults were not changed."
        if selected is None
        else f"Selected `{selected['name']}` before final-holdout evaluation."
    )
    holdout_table = table([holdout], "Final holdout: 2025") if holdout else "No final-holdout run was authorized by the selection gate.\n"
    report = f"""# Range candidate research\n\n## Method\n\nEight pre-defined range-only Bollinger/RSI mean-reversion candidates were evaluated. The test uses 2021–2023 for training, 2024 for validation, and 2025 as final holdout. The holdout is not used for candidate selection. Research uses 0.5% fixed-fractional risk and disables safety locks to reveal full-period behavior.\n\n{table(train, 'Training: 2021–2023')}\n{table(validation, 'Validation: 2024')}\n## Selection\n\n{decision}\n\n{holdout_table}\n## Decision\n\nDo not change the MQL5 EA unless a selected candidate passes the final holdout with positive return, profit factor above 1.05, and maximum drawdown no greater than 20%. PAXGUSDT remains a gold-linked public proxy, not broker-native XAUUSD data.\n"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
