"""Select M1 order-flow absorption candidates using executable order-level metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import load_bars
from scripts.explore_order_flow_factors import add_features


SPREAD_PRICE = 0.35
SESSIONS = {
    "all": tuple(range(24)),
    "asia_00_06": tuple(range(0, 7)),
    "london_07_12": tuple(range(7, 13)),
    "new_york_13_20": tuple(range(13, 21)),
}
HOLD_BARS = (5, 10, 20, 30)
SIDES = ("long", "short")


def candidate_signal(frame: pd.DataFrame, side: str, hours: tuple[int, ...]) -> np.ndarray:
    if side == "long":
        condition = (frame["ret_3"] <= frame["return_lower"]) & (frame["ofi_3"] >= frame["ofi_3_upper"])
    else:
        condition = (frame["ret_3"] >= frame["return_upper"]) & (frame["ofi_3"] <= frame["ofi_3_lower"])
    return (condition & frame.index.hour.isin(hours)).fillna(False).to_numpy()


def executable_returns(frame: pd.DataFrame, signal: np.ndarray, side: str, hold_bars: int) -> np.ndarray:
    """Return non-overlapping net returns with next-bar bid/ask entry and close exit."""
    opens = frame["open"].to_numpy(dtype=float)
    closes = frame["close"].to_numpy(dtype=float)
    values: list[float] = []
    index = 0
    while index + hold_bars < len(frame):
        if not signal[index]:
            index += 1
            continue
        entry_index = index + 1
        exit_index = index + hold_bars
        if side == "long":
            entry = opens[entry_index] + SPREAD_PRICE / 2.0
            exit_price = closes[exit_index] - SPREAD_PRICE / 2.0
            values.append((exit_price - entry) / entry)
        else:
            entry = opens[entry_index] - SPREAD_PRICE / 2.0
            exit_price = closes[exit_index] + SPREAD_PRICE / 2.0
            values.append((entry - exit_price) / entry)
        index = exit_index + 1
    return np.asarray(values, dtype=float)


def metrics(values: np.ndarray) -> dict[str, float | int]:
    if not len(values):
        return {"trades": 0, "mean_bps": 0.0, "profit_factor": 0.0, "win_rate_percent": 0.0, "max_drawdown_bps": 0.0}
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    equity = np.cumsum(values)
    drawdown = equity - np.maximum.accumulate(equity)
    return {
        "trades": len(values),
        "mean_bps": 10_000.0 * float(values.mean()),
        "profit_factor": gains / losses if losses else float("inf"),
        "win_rate_percent": 100.0 * float((values > 0).mean()),
        "max_drawdown_bps": 10_000.0 * float(drawdown.min()),
    }


def evaluate(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for session, hours in SESSIONS.items():
        for side in SIDES:
            signal = candidate_signal(frame, side, hours)
            for hold_bars in HOLD_BARS:
                rows.append({"session": session, "side": side, "hold_bars": hold_bars, **metrics(executable_returns(frame, signal, side, hold_bars))})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bars_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    bars = load_bars(args.bars_csv, default_spread_points=35.0)
    features = add_features(bars, bars, quantile_window=20 * 24 * 60)
    train = evaluate(features.loc["2021-01-01":"2023-12-31"])
    validation = evaluate(features.loc["2024-01-01":"2024-12-31"])
    merged = train.merge(validation, on=["session", "side", "hold_bars"], suffixes=("_train", "_validation"))
    train_gate = (merged["trades_train"] >= 500) & (merged["profit_factor_train"] >= 1.10) & (merged["mean_bps_train"] >= 0.50)
    shortlist = merged.loc[train_gate].copy()
    shortlist["selection_score"] = shortlist["mean_bps_train"] * np.sqrt(shortlist["trades_train"])
    shortlist = shortlist.sort_values("selection_score", ascending=False)
    selected = shortlist.head(1)
    validation_pass = bool(
        not selected.empty
        and selected.iloc[0]["trades_validation"] >= 150
        and selected.iloc[0]["profit_factor_validation"] >= 1.05
        and selected.iloc[0]["mean_bps_validation"] >= 0.25
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)
    lines = [
        "# M1 executable order-flow grid",
        "",
        "## Protocol",
        "",
        "The grid evaluates the pre-defined price/OFI absorption formula for long and short sides, four UTC sessions, and 5/10/20/30 minute holding periods. At a closed one-minute bar, it uses a trailing 20-trading-day (28,800-bar) 20/80 quantile threshold shifted by one bar. A long signal combines a negative three-bar price extreme with a positive OFI extreme; a short signal is symmetric.",
        "",
        "Every evaluation enters at the next one-minute bar's bid/ask, exits at the specified close, charges a 0.35 USD round-trip spread, and prohibits overlap. Training (2021–2023) selects the one candidate with the largest mean-bps-times-square-root-trades score after the gates: at least 500 trades, PF >= 1.10, and mean net return >= 0.50 bps. Validation (2024) requires at least 150 trades, PF >= 1.05, and mean net return >= 0.25 bps. The 2025 holdout is not inspected here.",
        "",
        "## Training shortlist and 2024 validation",
        "",
        "| Session | Side | Hold (min) | Train trades | Train PF | Train bps | Validation trades | Validation PF | Validation bps |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if shortlist.empty:
        lines.append("| None | - | - | - | - | - | - | - | - |")
    else:
        for _, row in shortlist.iterrows():
            lines.append(f"| {row['session']} | {row['side']} | {int(row['hold_bars'])} | {int(row['trades_train'])} | {row['profit_factor_train']:.3f} | {row['mean_bps_train']:.3f} | {int(row['trades_validation'])} | {row['profit_factor_validation']:.3f} | {row['mean_bps_validation']:.3f} |")
    lines.extend(["", "## Decision", "", "A candidate is eligible for the untouched 2025 holdout only when the selected row passes the stated validation gates." if validation_pass else "No training-selected candidate passed the stated validation gates. Do not inspect 2025 or integrate this grid into the EA."])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(shortlist.to_string(index=False))
    print(f"validation_pass={validation_pass}")


if __name__ == "__main__":
    main()
