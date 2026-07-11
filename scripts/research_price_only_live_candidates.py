"""Evaluate price-only, long/short M5 candidates with protective exits."""

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
    quantile: float
    lookback: int
    stop_atr: float
    target_atr: float
    trailing_atr: float
    time_exit_bars: int

    def config(self) -> Config:
        return Config(
            strategy="price_reversal",
            higher_timeframe=self.higher_timeframe,
            higher_fast_ma_period=self.higher_fast,
            higher_slow_ma_period=self.higher_slow,
            reversal_lookback_bars=self.lookback,
            reversal_quantile= self.quantile,
            reversal_require_cross=True,
            time_exit_bars=self.time_exit_bars,
            initial_equity=10_000.0,
            risk_percent=0.25,
            max_daily_loss_percent=2.0,
            max_drawdown_percent=20.0,
            stop_atr=self.stop_atr,
            take_profit_atr=self.target_atr,
            trailing_atr=self.trailing_atr,
            commission_per_lot_round_turn=0.0,
            allow_long=True,
            allow_short=True,
        )


CANDIDATES = (
    Candidate("PR01_H1_q20_r3_1p5x2_24", "1h", 20, 50, 0.20, 3, 1.5, 2.0, 1.2, 24),
    Candidate("PR02_H1_q10_r3_1p5x2_24", "1h", 20, 50, 0.10, 3, 1.5, 2.0, 1.2, 24),
    Candidate("PR03_H1_q20_r3_2x3_48", "1h", 20, 50, 0.20, 3, 2.0, 3.0, 1.5, 48),
    Candidate("PR04_H1slow_q20_r6_2x3_48", "1h", 20, 100, 0.20, 6, 2.0, 3.0, 1.5, 48),
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
    return (
        result["trades"] >= minimum_trades
        and result["profit_factor"] is not None
        and result["profit_factor"] >= 1.10
        and result["return_percent"] > 0.0
        and result["max_drawdown_percent"] <= 15.0
    )


def run_period(frame, candidate: Candidate) -> dict:
    summary, _, _ = run_backtest(frame, candidate.config())
    return metric(summary)


def table(rows: list[dict], title: str) -> str:
    lines = []
    for row in rows:
        pf = "N/A" if row["profit_factor"] is None else f"{row['profit_factor']:.2f}"
        lines.append(
            f"| {row['name']} | {row['return_percent']:.2f}% | {row['max_drawdown_percent']:.2f}% | {row['trades']} | {row['win_rate_percent']:.2f}% | {pf} |"
        )
    body = "\n".join(lines) if lines else "| None | - | - | - | - | - |"
    return f"### {title}\n\n| Candidate | Return | Max drawdown | Trades | Win rate | Profit factor |\n|---|---:|---:|---:|---:|---:|\n{body}\n"


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
        for row in train if passes(row, 150)
    ]
    approved = [row for row in validation if passes(row, 50)]
    selected = max(
        approved,
        key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]),
        default=None,
    )
    holdout = None if selected is None else {"name": selected["name"], **run_period(holdout_data, by_name[selected["name"]])}
    payload = {"protocol": "price-only long/short ATR stop/target candidates", "train": train, "validation": validation, "selected": selected, "holdout": holdout}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    decision = "No candidate passed training and validation; 2025 was not evaluated." if selected is None else f"`{selected['name']}` was selected from 2024 validation before the single 2025 holdout run."
    report = f"""# Price-only live-strategy candidate research

## Live-trading controls

This study excludes all volume inputs. Each candidate uses symmetric long and short entries, next-bar bid/ask execution, ATR stop loss, ATR take profit, trailing stop, fixed maximum holding time, 0.25% risk per trade, 2% daily loss lock, and a 20% peak-drawdown entry lock. Signals use only completed M5 and completed H1/H4 information.

## Formula

Long when the completed higher-timeframe EMA fast value exceeds the slow value and the M5 return is at or below its shifted trailing lower quantile. Short when the completed higher-timeframe fast EMA is below the slow EMA and the M5 return is at or above its shifted trailing upper quantile. Stops and targets are ATR multiples specified per candidate.

{table(train, 'Training: 2021-2023')}
{table(validation, 'Validation: 2024')}
## Selection

{decision}

{table([holdout], 'Final holdout: 2025') if holdout else 'No final holdout run was authorized.\n'}
## Decision

Do not enable a candidate in MQL5 unless it passes all three periods and subsequently passes broker-native XAUUSD Bid/Ask testing with actual costs.
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
