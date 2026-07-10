"""Direct executable M5 grid for pre-defined order-flow factor families."""

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
HOLD_BARS = (1, 2, 3, 6, 12, 24)
SESSIONS = {
    "all": tuple(range(24)),
    "asia_00_06": tuple(range(0, 7)),
    "london_07_12": tuple(range(7, 13)),
    "new_york_13_20": tuple(range(13, 21)),
}
FAMILIES = (
    "ofi_momentum",
    "ofi_reversal",
    "ofi_absorption",
    "return_3_reversal",
    "return_6_reversal",
    "breakout_12_reversal",
    "volume_return_3_reversal",
)
SIDES = ("long", "short")


def signal_for(frame: pd.DataFrame, family: str, side: str, hours: tuple[int, ...]) -> np.ndarray:
    high = frame["ofi_3"] >= frame["ofi_3_upper"]
    low = frame["ofi_3"] <= frame["ofi_3_lower"]
    if family == "ofi_momentum":
        condition = high if side == "long" else low
    elif family == "ofi_reversal":
        condition = low if side == "long" else high
    elif family == "ofi_absorption":
        condition = ((frame["ret_3"] <= frame["return_lower"]) & high) if side == "long" else ((frame["ret_3"] >= frame["return_upper"]) & low)
    elif family == "return_3_reversal":
        condition = frame["ret_3"] <= frame["return_lower"] if side == "long" else frame["ret_3"] >= frame["return_upper"]
    elif family == "return_6_reversal":
        condition = frame["ret_6"] <= frame["return_6_lower"] if side == "long" else frame["ret_6"] >= frame["return_6_upper"]
    elif family == "breakout_12_reversal":
        condition = frame["close"] < frame["prior_low_12"] if side == "long" else frame["close"] > frame["prior_high_12"]
    elif family == "volume_return_3_reversal":
        base = frame["ret_3"] <= frame["return_lower"] if side == "long" else frame["ret_3"] >= frame["return_upper"]
        condition = base & (frame["volume_ratio"] >= 1.5)
    else:
        raise ValueError(f"unsupported family: {family}")
    return (condition & frame.index.hour.isin(hours)).fillna(False).to_numpy()


def net_returns(frame: pd.DataFrame, signal: np.ndarray, side: str, hold: int) -> np.ndarray:
    opens, closes = frame["open"].to_numpy(float), frame["close"].to_numpy(float)
    values: list[float] = []
    index = 0
    while index + hold < len(frame):
        if not signal[index]:
            index += 1
            continue
        entry_index, exit_index = index + 1, index + hold
        if side == "long":
            entry, exit_price = opens[entry_index] + SPREAD_PRICE / 2.0, closes[exit_index] - SPREAD_PRICE / 2.0
            values.append((exit_price - entry) / entry)
        else:
            entry, exit_price = opens[entry_index] - SPREAD_PRICE / 2.0, closes[exit_index] + SPREAD_PRICE / 2.0
            values.append((entry - exit_price) / entry)
        index = exit_index + 1
    return np.asarray(values, dtype=float)


def metric(values: np.ndarray) -> dict[str, float | int]:
    if not len(values):
        return {"trades": 0, "mean_bps": 0.0, "profit_factor": 0.0, "win_rate_percent": 0.0}
    gains, losses = float(values[values > 0].sum()), float(-values[values < 0].sum())
    return {"trades": len(values), "mean_bps": 10_000 * float(values.mean()), "profit_factor": gains / losses if losses else float("inf"), "win_rate_percent": 100 * float((values > 0).mean())}


def evaluate(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for family in FAMILIES:
        for session, hours in SESSIONS.items():
            for side in SIDES:
                signal = signal_for(frame, family, side, hours)
                for hold in HOLD_BARS:
                    rows.append({"family": family, "session": session, "side": side, "hold_bars": hold, **metric(net_returns(frame, signal, side, hold))})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ohlc_csv", type=Path)
    parser.add_argument("flow_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    ohlc = load_bars(args.ohlc_csv, default_spread_points=35.0)
    flow = pd.read_csv(args.flow_csv, parse_dates=["time"]).set_index("time")
    if flow.index.tz is None:
        flow.index = flow.index.tz_localize("UTC")
    features = add_features(ohlc, flow, quantile_window=20 * 24 * 12)
    features["ret_6"] = features["close"].pct_change(6)
    features["return_6_lower"] = features["ret_6"].shift(1).rolling(20 * 24 * 12).quantile(0.2)
    features["return_6_upper"] = features["ret_6"].shift(1).rolling(20 * 24 * 12).quantile(0.8)
    features["prior_high_12"] = features["high"].shift(1).rolling(12).max()
    features["prior_low_12"] = features["low"].shift(1).rolling(12).min()
    features["volume_ratio"] = features["volume"] / features["volume"].rolling(60).mean()
    train, validation = evaluate(features.loc["2021-01-01":"2023-12-31"]), evaluate(features.loc["2024-01-01":"2024-12-31"])
    merged = train.merge(validation, on=["family", "session", "side", "hold_bars"], suffixes=("_train", "_validation"))
    training_gate = (merged["trades_train"] >= 100) & (merged["profit_factor_train"] >= 1.10) & (merged["mean_bps_train"] >= 0.50)
    shortlist = merged.loc[training_gate].copy()
    shortlist["selection_score"] = shortlist["mean_bps_train"] * np.sqrt(shortlist["trades_train"])
    shortlist = shortlist.sort_values("selection_score", ascending=False)
    selected = shortlist.head(1)
    validation_pass = bool(not selected.empty and selected.iloc[0]["trades_validation"] >= 30 and selected.iloc[0]["profit_factor_validation"] >= 1.05 and selected.iloc[0]["mean_bps_validation"] >= 0.25)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)
    lines = [
        "# M5 executable order-flow grid",
        "",
        "## Protocol",
        "",
        "This pre-defined grid tests OFI momentum/reversal/absorption and price-return, breakout, and volume-confirmed reversal factors; both directions; four UTC sessions; and 5/10/15/30/60/120 minute exits. Extreme thresholds use trailing 20-trading-day 20/80 quantiles shifted one M5 bar. Entries occur at the next M5 bid/ask, exits at the fixed-horizon close, a 0.35 USD round-trip spread is charged, and positions cannot overlap.",
        "",
        "Training is 2021–2023. A candidate needs 100 trades, PF >= 1.10, and >= 0.50 mean net bps before training-only selection by mean-bps-times-square-root-trades. The selected candidate then needs 30 validation trades, PF >= 1.05, and >= 0.25 mean net bps in 2024. The 2025 holdout is not examined unless it passes validation.",
        "",
        "## Training shortlist and 2024 validation",
        "",
        "| Family | Session | Side | Hold (min) | Train trades | Train PF | Train bps | Validation trades | Validation PF | Validation bps |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if shortlist.empty:
        lines.append("| None | - | - | - | - | - | - | - | - | - |")
    else:
        for _, row in shortlist.iterrows():
            lines.append(f"| {row['family']} | {row['session']} | {row['side']} | {int(row['hold_bars']) * 5} | {int(row['trades_train'])} | {row['profit_factor_train']:.3f} | {row['mean_bps_train']:.3f} | {int(row['trades_validation'])} | {row['profit_factor_validation']:.3f} | {row['mean_bps_validation']:.3f} |")
    lines.extend(["", "## Decision", "", "One training-selected candidate passed validation and is eligible for a separately recorded 2025 holdout test." if validation_pass else "No training-selected candidate passed validation. Do not inspect 2025 or integrate this grid into the EA."])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(shortlist.to_string(index=False))
    print(f"validation_pass={validation_pass}")


if __name__ == "__main__":
    main()
