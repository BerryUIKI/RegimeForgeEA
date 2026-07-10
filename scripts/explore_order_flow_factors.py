"""Screen order-flow imbalance factors with no-future-data rolling thresholds."""

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
QUANTILE_WINDOW_BARS = 20 * 24 * 12
HORIZONS = (3, 6, 12, 24)
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


def add_features(ohlc: pd.DataFrame, flow: pd.DataFrame, quantile_window: int = QUANTILE_WINDOW_BARS) -> pd.DataFrame:
    # Keep OHLC fields as canonical. This also supports a single derived file
    # that already contains both price and order-flow columns.
    flow_columns = flow.drop(columns=["trade_count"], errors="ignore")
    missing_columns = flow_columns.columns.difference(ohlc.columns)
    result = ohlc.join(flow_columns.loc[:, missing_columns], how="inner")
    result["hour"] = result.index.hour
    result["ret_3"] = result["close"].pct_change(3)
    for period in (3, 6, 12):
        signed = (result["buy_taker_quantity"] - result["sell_taker_quantity"]).rolling(period).sum()
        total = result["total_taker_quantity"].rolling(period).sum()
        feature = f"ofi_{period}"
        result[feature] = signed / total.replace(0.0, np.nan)
        result[f"{feature}_upper"] = result[feature].shift(1).rolling(quantile_window).quantile(0.8)
        result[f"{feature}_lower"] = result[feature].shift(1).rolling(quantile_window).quantile(0.2)
    result["return_upper"] = result["ret_3"].shift(1).rolling(quantile_window).quantile(0.8)
    result["return_lower"] = result["ret_3"].shift(1).rolling(quantile_window).quantile(0.2)
    return result


def masks(frame: pd.DataFrame) -> dict[str, tuple[pd.Series, pd.Series]]:
    result: dict[str, tuple[pd.Series, pd.Series]] = {}
    for period in (3, 6, 12):
        feature = f"ofi_{period}"
        high = frame[feature] >= frame[f"{feature}_upper"]
        low = frame[feature] <= frame[f"{feature}_lower"]
        result[f"ofi_{period}_momentum"] = (high, low)
        result[f"ofi_{period}_reversal"] = (low, high)
    absorption_long = (frame["ret_3"] <= frame["return_lower"]) & (frame["ofi_3"] >= frame["ofi_3_upper"])
    absorption_short = (frame["ret_3"] >= frame["return_upper"]) & (frame["ofi_3"] <= frame["ofi_3_lower"])
    result["ofi_price_absorption"] = (absorption_long, absorption_short)
    return result


def evaluate(frame: pd.DataFrame, horizons: tuple[int, ...]) -> pd.DataFrame:
    rows: list[dict] = []
    for horizon in horizons:
        future_return = frame["close"].shift(-horizon) / frame["close"] - 1.0
        cost = SPREAD_PRICE / frame["close"]
        for session, hours in SESSIONS.items():
            session_mask = frame["hour"].isin(hours)
            for factor, (long_mask, short_mask) in masks(frame).items():
                for side, condition, signed_return in (
                    ("long", long_mask, future_return - cost),
                    ("short", short_mask, -future_return - cost),
                ):
                    values = signed_return.where(condition & session_mask).dropna()
                    rows.append(
                        {
                            "factor": factor,
                            "side": side,
                            "session": session,
                            "horizon_bars": horizon,
                            "observations": len(values),
                            "net_mean_bps": 10_000.0 * float(values.mean()) if len(values) else np.nan,
                            "t_stat": t_statistic(values),
                            "win_rate_percent": 100.0 * float((values > 0).mean()) if len(values) else np.nan,
                        }
                    )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ohlc_csv", type=Path)
    parser.add_argument("flow_csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--bar-minutes", type=int, default=5)
    parser.add_argument("--horizons", default="3,6,12,24", help="Comma-separated forecast horizons in bars.")
    args = parser.parse_args()
    ohlc = load_bars(args.ohlc_csv, default_spread_points=35.0)
    flow = pd.read_csv(args.flow_csv, parse_dates=["time"]).set_index("time")
    if flow.index.tz is None:
        flow.index = flow.index.tz_localize("UTC")
    if args.bar_minutes <= 0 or 60 % args.bar_minutes:
        raise ValueError("bar-minutes must be a positive divisor of 60")
    horizons = tuple(int(value) for value in args.horizons.split(",") if value)
    if not horizons or any(value <= 0 for value in horizons):
        raise ValueError("horizons must contain positive integers")
    quantile_window = 20 * 24 * 60 // args.bar_minutes
    features = add_features(ohlc, flow, quantile_window)
    train = evaluate(features.loc["2021-01-01":"2023-12-31"], horizons)
    validation = evaluate(features.loc["2024-01-01":"2024-12-31"], horizons)
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
    report_lines = [
        "# Order-flow factor screen",
        "",
        "## Formula",
        "",
        f"For a window n, OFI_n(t) = sum(BuyTakerQty - SellTakerQty) / sum(BuyTakerQty + SellTakerQty). Extreme thresholds are rolling 20-trading-day 20/80 quantiles shifted one {args.bar_minutes}-minute bar. Momentum trades with OFI; reversal trades against it. The absorption factor buys when price is at a negative return extreme while OFI is positive extreme, and sells the symmetric condition.",
        "",
        "Each event subtracts one 0.35 USD spread. Training is 2021–2023; validation is 2024; 2025 is excluded.",
        "",
        "## Factors passing both periods",
        "",
        "| Factor | Side | Session | Horizon | Train net bps | Train t | Validation net bps | Validation t |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in robust.iterrows():
        report_lines.append(
            f"| {row['factor']} | {row['side']} | {row['session']} | {int(row['horizon_bars'])} | {row['net_mean_bps_train']:.3f} | {row['t_stat_train']:.2f} | {row['net_mean_bps_validation']:.3f} | {row['t_stat_validation']:.2f} |"
        )
    if robust.empty:
        report_lines.append("| None | - | - | - | - | - | - | - |")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(robust.to_string(index=False))


if __name__ == "__main__":
    main()
