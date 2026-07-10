"""Test high-frequency volume-confirmed reversal factors as tradable orders."""

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
    time_exit_bars: int
    stop_atr: float

    def config(self) -> Config:
        return Config(
            strategy="volume_reversal",
            risk_percent=0.25,
            max_daily_loss_percent=100.0,
            max_drawdown_percent=100.0,
            reversal_lookback_bars=3,
            reversal_quantile_window=20 * 24 * 12,
            reversal_quantile=0.2,
            reversal_volume_ratio=1.5,
            reversal_require_cross=True,
            time_exit_bars=self.time_exit_bars,
            stop_atr=self.stop_atr,
            take_profit_atr=0.0,
            trailing_atr=10.0,
        )


CANDIDATES = (
    Candidate("VR01_exit_6_stop_3", 6, 3.0),
    Candidate("VR02_exit_12_stop_3", 12, 3.0),
    Candidate("VR03_exit_24_stop_3", 24, 3.0),
    Candidate("VR04_exit_12_stop_2", 12, 2.0),
)


def metrics(summary: dict) -> dict:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def passes_common(row: dict) -> bool:
    return (
        row["profit_factor"] is not None
        and row["profit_factor"] >= 1.05
        and row["return_percent"] > 0
        and row["max_drawdown_percent"] <= 20.0
    )


def table(rows: list[dict], title: str) -> str:
    body = []
    for row in rows:
        pf = "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        body.append(
            f"| {row['name']} | {row['return_percent']:.2f}% | {row['max_drawdown_percent']:.2f}% | {row['trades']} | {row['win_rate_percent']:.2f}% | {pf} |"
        )
    return f"### {title}\n\n| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |\n|---|---:|---:|---:|---:|---:|\n{'\n'.join(body)}\n"


def run_period(frame, candidate: Candidate) -> dict:
    summary, _, _ = run_backtest(frame, candidate.config())
    return metrics(summary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = load_bars(args.csv, default_spread_points=35.0)
    train_data = split_bars(source, "2021-01-01", "2024-01-01")
    validation_data = split_bars(source, "2024-01-01", "2025-01-01")
    holdout_data = split_bars(source, "2025-01-01", "2026-01-01")
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    train = [{"name": candidate.name, **run_period(train_data, candidate)} for candidate in CANDIDATES]
    validation = [
        {"name": row["name"], **run_period(validation_data, by_name[row["name"]])}
        for row in train
        if row["trades"] >= 500 and passes_common(row)
    ]
    approved = [row for row in validation if row["trades"] >= 150 and passes_common(row)]
    selected = max(
        approved,
        key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]),
        default=None,
    )
    holdout = None
    if selected:
        holdout = {"name": selected["name"], **run_period(holdout_data, by_name[selected["name"]])}
    payload = {"train": train, "validation": validation, "selected": selected, "holdout": holdout}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    decision = "No candidate passed the training and validation gates." if selected is None else f"Selected `{selected['name']}` before final-holdout evaluation."
    holdout_table = table([holdout], "Final holdout: 2025") if holdout else "No final-holdout run was authorized.\n"
    report = f"""# Volume-confirmed reversal order research\n\n## Factor formula\n\nLet r_3(t) = Close(t) / Close(t-3) - 1. Let q_20(t), q_80(t) be the trailing 20-trading-day 20th and 80th percentiles of r_3, shifted one M5 bar. Let V_ratio(t) = Volume(t) / SMA_60(Volume)(t).\n\n- Long if r_3(t) crosses below q_20(t) and V_ratio(t) >= 1.5.\n- Short if r_3(t) crosses above q_80(t) and V_ratio(t) >= 1.5.\n- Enter at the next M5 open; exit after the configured number of M5 bars or at the ATR protective stop.\n\nCandidates are fixed before the 2025 holdout. Training requires 500+ trades, validation requires 150+ trades, plus positive return, PF >= 1.05, and maximum drawdown <= 20%.\n\n{table(train, 'Training: 2021–2023')}\n{table(validation, 'Validation: 2024')}\n## Selection\n\n{decision}\n\n{holdout_table}\n## Decision\n\nOnly a candidate with a positive final holdout may be considered for MQL5 implementation and broker-native cost validation.\n"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
