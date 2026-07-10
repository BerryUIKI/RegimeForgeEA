"""Evaluate fixed M5 pullback candidates with a closed-bar higher-timeframe filter."""

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
    bollinger_period: int
    bollinger_deviation: float
    rsi_lower: float
    rsi_upper: float
    stop_atr: float
    target_atr: float
    trailing_atr: float

    def config(self) -> Config:
        return Config(
            strategy="trend_pullback",
            higher_timeframe=self.higher_timeframe,
            higher_fast_ma_period=self.higher_fast,
            higher_slow_ma_period=self.higher_slow,
            risk_percent=0.25,
            max_daily_loss_percent=100.0,
            max_drawdown_percent=100.0,
            bollinger_period=self.bollinger_period,
            bollinger_deviation=self.bollinger_deviation,
            rsi_lower=self.rsi_lower,
            rsi_upper=self.rsi_upper,
            stop_atr=self.stop_atr,
            take_profit_atr=self.target_atr,
            trailing_atr=self.trailing_atr,
        )


CANDIDATES = (
    Candidate("HF01_H1_bb15_rsi40", "1h", 20, 50, 20, 1.5, 40.0, 60.0, 1.2, 1.2, 0.8),
    Candidate("HF02_H1_bb20_rsi35", "1h", 20, 50, 20, 2.0, 35.0, 65.0, 1.5, 1.5, 1.0),
    Candidate("HF03_H1_bb20_rsi30", "1h", 20, 50, 20, 2.0, 30.0, 70.0, 1.8, 1.8, 1.0),
    Candidate("HF04_H1_slow", "1h", 20, 100, 20, 1.5, 40.0, 60.0, 1.2, 1.2, 0.8),
    Candidate("HF05_H1_longbb", "1h", 20, 50, 30, 1.75, 35.0, 65.0, 1.5, 1.5, 1.0),
    Candidate("HF06_H4_bb15", "4h", 20, 50, 20, 1.5, 40.0, 60.0, 1.2, 1.2, 0.8),
    Candidate("HF07_H4_bb20", "4h", 20, 50, 20, 2.0, 35.0, 65.0, 1.5, 1.5, 1.0),
    Candidate("HF08_H4_slow", "4h", 20, 100, 30, 1.75, 35.0, 65.0, 1.5, 1.5, 1.0),
)


def metrics(summary: dict) -> dict:
    return {
        "return_percent": round(float(summary["total_return_percent"]), 4),
        "max_drawdown_percent": round(float(summary["max_drawdown_percent"]), 4),
        "trades": int(summary["trades"]),
        "win_rate_percent": round(float(summary["win_rate_percent"]), 4),
        "profit_factor": summary["profit_factor"],
    }


def passes_common(result: dict) -> bool:
    return (
        result["profit_factor"] is not None
        and result["profit_factor"] >= 1.05
        and result["return_percent"] > 0.0
        and result["max_drawdown_percent"] <= 20.0
    )


def train_gate(result: dict) -> bool:
    return result["trades"] >= 150 and passes_common(result)


def validation_gate(result: dict) -> bool:
    return result["trades"] >= 50 and passes_common(result)


def run_period(frame, candidate: Candidate) -> dict:
    summary, _, _ = run_backtest(frame, candidate.config())
    return metrics(summary)


def table(rows: list[dict], title: str) -> str:
    rows_text = []
    for row in rows:
        pf = "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        rows_text.append(
            f"| {row['name']} | {row['return_percent']:.2f}% | {row['max_drawdown_percent']:.2f}% | "
            f"{row['trades']} | {row['win_rate_percent']:.2f}% | {pf} |"
        )
    return f"### {title}\n\n| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |\n|---|---:|---:|---:|---:|---:|\n{'\n'.join(rows_text)}\n"


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
    train = []
    for candidate in CANDIDATES:
        train.append({"name": candidate.name, **run_period(train_data, candidate)})
    validation = []
    for row in filter(train_gate, train):
        validation.append({"name": row["name"], **run_period(validation_data, by_name[row["name"]])})
    approved = [row for row in validation if validation_gate(row)]
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
    decision = "No candidate passed training and validation." if selected is None else f"Selected `{selected['name']}` before final-holdout evaluation."
    holdout_table = table([holdout], "Final holdout: 2025") if holdout else "No final-holdout run was authorized.\n"
    report = f"""# High-frequency pullback candidate research\n\n## Factor formula\n\nAt M5 close t, let B_lower(t), B_upper(t) be Bollinger bands and RSI(t) be the M5 RSI. Let EMA_fast^H(t-1), EMA_slow^H(t-1) be the higher-timeframe EMAs calculated only through the last completed higher-timeframe bar.\n\n- Long if EMA_fast^H(t-1) > EMA_slow^H(t-1), Close(t) < B_lower(t), and RSI(t) <= L.\n- Short if EMA_fast^H(t-1) < EMA_slow^H(t-1), Close(t) > B_upper(t), and RSI(t) >= U.\n- The order is placed at the next M5 open; stops, targets, and trailing stops are ATR multiples.\n\nThis is high-frequency in execution: all entries are M5, while H1/H4 is a delayed direction filter. The fixed protocol uses 2021–2023 training, 2024 validation, and 2025 holdout. Gates require positive return, PF >= 1.05, maximum drawdown <= 20%, 150+ training trades, and 50+ validation trades.\n\n{table(train, 'Training: 2021–2023')}\n{table(validation, 'Validation: 2024')}\n## Selection\n\n{decision}\n\n{holdout_table}\n## Decision\n\nDo not enable the factor in MQL5 unless it passes the final holdout and then broker-native XAUUSD bid/ask testing.\n"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
