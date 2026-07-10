"""Screen pre-defined intraday gold factors before converting them into strategies."""

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


SPREAD_PRICE = 0.35
HORIZONS = (3, 6, 12, 24)
QUANTILE_WINDOW_BARS = 20 * 24 * 12
SESSIONS = {
    "all": tuple(range(24)),
    "asia_00_06": tuple(range(0, 7)),
    "london_07_12": tuple(range(7, 13)),
    "new_york_13_20": tuple(range(13, 21)),
}


def t_statistic(values: pd.Series) -> float:
    values = values.dropna()
    if len(values) < 2 or values.std(ddof=1) == 0:
        return 0.0
    return float(values.mean() / (values.std(ddof=1) / np.sqrt(len(values))))


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["ret_1"] = result["close"].pct_change(1)
    result["ret_3"] = result["close"].pct_change(3)
    result["ret_6"] = result["close"].pct_change(6)
    result["ret_3_high"] = result["ret_3"].shift(1).rolling(QUANTILE_WINDOW_BARS).quantile(0.8)
    result["ret_3_low"] = result["ret_3"].shift(1).rolling(QUANTILE_WINDOW_BARS).quantile(0.2)
    result["ret_6_high"] = result["ret_6"].shift(1).rolling(QUANTILE_WINDOW_BARS).quantile(0.8)
    result["ret_6_low"] = result["ret_6"].shift(1).rolling(QUANTILE_WINDOW_BARS).quantile(0.2)
    result["high_12"] = result["high"].shift(1).rolling(12).max()
    result["low_12"] = result["low"].shift(1).rolling(12).min()
    result["volume_ratio"] = result["volume"] / result["volume"].rolling(60).mean()
    result["hour"] = result.index.hour
    return result


def factor_masks(frame: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    return {
        "mom_3_quantile": (frame["ret_3"] >= frame["ret_3_high"], frame["ret_3"] <= frame["ret_3_low"]),
        "mom_6_quantile": (frame["ret_6"] >= frame["ret_6_high"], frame["ret_6"] <= frame["ret_6_low"]),
        "mom_3_reversal": (frame["ret_3"] <= frame["ret_3_low"], frame["ret_3"] >= frame["ret_3_high"]),
        "mom_6_reversal": (frame["ret_6"] <= frame["ret_6_low"], frame["ret_6"] >= frame["ret_6_high"]),
        "breakout_12": (frame["close"] > frame["high_12"], frame["close"] < frame["low_12"]),
        "breakout_12_reversal": (frame["close"] < frame["low_12"], frame["close"] > frame["high_12"]),
        "volume_confirmed_mom": (
            (frame["ret_3"] >= frame["ret_3_high"]) & (frame["volume_ratio"] >= 1.5),
            (frame["ret_3"] <= frame["ret_3_low"]) & (frame["volume_ratio"] >= 1.5),
        ),
        "volume_confirmed_reversal": (
            (frame["ret_3"] <= frame["ret_3_low"]) & (frame["volume_ratio"] >= 1.5),
            (frame["ret_3"] >= frame["ret_3_high"]) & (frame["volume_ratio"] >= 1.5),
        ),
    }


def evaluate(frame: pd.DataFrame) -> pd.DataFrame:
    factors = factor_masks(frame)
    rows: list[dict] = []
    for horizon in HORIZONS:
        forward_return = frame["close"].shift(-horizon) / frame["close"] - 1.0
        spread_return = SPREAD_PRICE / frame["close"]
        for session_name, hours in SESSIONS.items():
            session_mask = frame["hour"].isin(hours)
            for factor_name, (long_mask, short_mask) in factors.items():
                long_values = (forward_return - spread_return).where(long_mask & session_mask)
                short_values = (-forward_return - spread_return).where(short_mask & session_mask)
                for side, values in (("long", long_values), ("short", short_values)):
                    usable = values.dropna()
                    rows.append(
                        {
                            "factor": factor_name,
                            "side": side,
                            "session": session_name,
                            "horizon_bars": horizon,
                            "observations": len(usable),
                            "net_mean_bps": 10_000.0 * float(usable.mean()) if len(usable) else np.nan,
                            "t_stat": t_statistic(usable),
                            "win_rate_percent": 100.0 * float((usable > 0).mean()) if len(usable) else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = add_features(load_bars(args.csv, default_spread_points=35.0))
    train = evaluate(source.loc["2021-01-01":"2023-12-31"])
    validation = evaluate(source.loc["2024-01-01":"2024-12-31"])
    merged = train.merge(
        validation,
        on=["factor", "side", "session", "horizon_bars"],
        suffixes=("_train", "_validation"),
    )
    robust = merged.loc[
        (merged["observations_train"] >= 100)
        & (merged["observations_validation"] >= 30)
        & (merged["net_mean_bps_train"] > 0)
        & (merged["net_mean_bps_validation"] > 0)
        & (merged["t_stat_train"] >= 1.5)
        & (merged["t_stat_validation"] >= 1.0)
    ].sort_values(["net_mean_bps_validation", "t_stat_validation"], ascending=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)
    lines = [
        "# Intraday factor screen",
        "",
        "## Method",
        "",
        "The screen evaluates fixed M5 factors on 2021–2023 training and 2024 validation data. Each observation assumes entry at the next tradable price and subtracts one 0.35 USD spread. The 2025 holdout is not used. Extreme-return thresholds are rolling 20-trading-day 20/80 quantiles, shifted one bar so they use only information known at the signal time.",
        "",
        "Factors: 3-bar and 6-bar momentum quantiles, 12-bar breakouts, and volume-confirmed 3-bar momentum. Sessions are Asia (00–06 UTC), London (07–12 UTC), New York (13–20 UTC), and all hours. Horizons are 3, 6, 12, and 24 M5 bars.",
        "",
        "A factor is retained only when it has positive net mean return in both periods, at least 100 training and 30 validation observations, training t-statistic >= 1.5, and validation t-statistic >= 1.0.",
        "",
        "## Factors passing both periods",
        "",
        "| Factor | Side | Session | Horizon | Train net bps | Train t | Validation net bps | Validation t |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in robust.iterrows():
        lines.append(
            f"| {row['factor']} | {row['side']} | {row['session']} | {int(row['horizon_bars'])} | "
            f"{row['net_mean_bps_train']:.3f} | {row['t_stat_train']:.2f} | "
            f"{row['net_mean_bps_validation']:.3f} | {row['t_stat_validation']:.2f} |"
        )
    if robust.empty:
        lines.append("| None | - | - | - | - | - | - | - |")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Only the retained rows are eligible to become full trade rules and to be tested on 2025. Rows absent from this table must not be promoted to an EA factor.",
        ]
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(robust.to_string(index=False))


if __name__ == "__main__":
    main()
