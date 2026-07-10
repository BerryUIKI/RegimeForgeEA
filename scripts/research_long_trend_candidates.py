"""Evaluate fixed long-only gold trend candidates with time-split validation."""

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
    breakout: int
    adx: float
    stop: float
    target: float
    trail: float

    def config(self) -> Config:
        return Config(
            strategy="trend_breakout",
            allow_short=False,
            risk_percent=0.5,
            max_daily_loss_percent=100.0,
            max_drawdown_percent=100.0,
            fast_ma_period=self.fast,
            slow_ma_period=self.slow,
            breakout_bars=self.breakout,
            adx_trend_level=self.adx,
            stop_atr=self.stop,
            take_profit_atr=self.target,
            trailing_atr=self.trail,
        )


CANDIDATES = (
    Candidate("L01_H1_20_100", "1h", 20, 100, 20, 25.0, 2.2, 5.0, 2.0),
    Candidate("L02_H1_30_150", "1h", 30, 150, 30, 25.0, 2.5, 6.0, 2.0),
    Candidate("L03_H4_10_50", "4h", 10, 50, 10, 20.0, 2.0, 5.0, 2.0),
    Candidate("L04_H4_20_100", "4h", 20, 100, 20, 25.0, 2.5, 6.0, 2.2),
    Candidate("L05_D1_10_50", "1D", 10, 50, 5, 20.0, 2.0, 4.0, 2.0),
    Candidate("L06_D1_20_100", "1D", 20, 100, 10, 25.0, 2.5, 5.0, 2.2),
)


def metrics(summary: dict) -> dict:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def passes_common_gates(result: dict) -> bool:
    profit_factor = result["profit_factor"]
    return (
        profit_factor is not None
        and profit_factor >= 1.05
        and result["max_drawdown_percent"] <= 20.0
        and result["return_percent"] > 0.0
    )


def passes_training_gates(result: dict) -> bool:
    return result["trades"] >= 30 and passes_common_gates(result)


def passes_validation_gates(result: dict) -> bool:
    return result["trades"] >= 12 and passes_common_gates(result)


def run_period(frame, candidate: Candidate) -> dict:
    summary, _, _ = run_backtest(frame, candidate.config())
    return metrics(summary)


def table(rows: list[dict], title: str) -> str:
    body = "\n".join(
        "| {name} | {interval} | {return_percent:.2f}% | {max_drawdown_percent:.2f}% | "
        "{trades} | {win_rate_percent:.2f}% | {profit_factor} |".format(
            **{**row, "profit_factor": "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"}
        )
        for row in rows
    )
    return f"### {title}\n\n| Candidate | Bars | Return | Max drawdown | Trades | Win rate | Profit factor |\n|---|---:|---:|---:|---:|---:|---:|\n{body}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = load_bars(args.csv, default_spread_points=35.0)
    bars = {interval: resample_bars(source, interval) for interval in {c.interval for c in CANDIDATES}}
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    train = []
    for candidate in CANDIDATES:
        result = run_period(split_bars(bars[candidate.interval], "2021-01-01", "2024-01-01"), candidate)
        train.append({"name": candidate.name, "interval": candidate.interval, **result})
    validation = []
    for row in filter(passes_training_gates, train):
        candidate = by_name[row["name"]]
        result = run_period(split_bars(bars[candidate.interval], "2024-01-01", "2025-01-01"), candidate)
        validation.append({"name": candidate.name, "interval": candidate.interval, **result})
    approved = [row for row in validation if passes_validation_gates(row)]
    selected = max(
        approved,
        key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]),
        default=None,
    )
    holdout = None
    if selected:
        candidate = by_name[selected["name"]]
        result = run_period(split_bars(bars[candidate.interval], "2025-01-01", "2026-01-01"), candidate)
        holdout = {"name": candidate.name, "interval": candidate.interval, **result}
    payload = {"train": train, "validation": validation, "selected": selected, "holdout": holdout}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    decision = "No candidate passed the training and validation gates." if selected is None else f"Selected `{selected['name']}` before holdout evaluation."
    holdout_table = table([holdout], "Final holdout: 2025") if holdout else "No holdout run was authorized.\n"
    report = f"""# Long-only trend candidate research\n\n## Factor\n\nTrade only when EMA(fast) exceeds EMA(slow), ADX exceeds its threshold, and the closed price breaks the prior N-bar high. The strategy does not short. Stop, target, and trailing distances are ATR multiples.\n\nThe fixed study uses 2021–2023 training, 2024 validation, and 2025 final holdout. A candidate must have positive return, profit factor >= 1.05, and maximum drawdown <= 20% in both training and validation. The low-frequency trend gate requires at least 30 training trades and 12 validation trades, approximately one validation trade per month.\n\n{table(train, 'Training: 2021–2023')}\n{table(validation, 'Validation: 2024')}\n## Selection\n\n{decision}\n\n{holdout_table}\n## Decision\n\nDo not enable this factor in the EA unless it passes the final holdout. PAXGUSDT is a gold-linked public proxy, not broker-native XAUUSD data.\n"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
