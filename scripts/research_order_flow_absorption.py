"""Order-level validation for the pre-specified M5 order-flow absorption factor."""

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
from scripts.explore_order_flow_factors import QUANTILE_WINDOW_BARS, add_features


SPREAD_PRICE = 0.35
LOT_SIZE = 0.10
CONTRACT_SIZE = 100.0


def run_strategy(frame: pd.DataFrame, hold_bars: int, side: str, session_hours: tuple[int, ...]) -> pd.DataFrame:
    """Trade non-overlapping long absorption events at next-bar bid/ask prices."""
    if side == "long":
        signal = (frame["ret_3"] <= frame["return_lower"]) & (frame["ofi_3"] >= frame["ofi_3_upper"])
    else:
        signal = (frame["ret_3"] >= frame["return_upper"]) & (frame["ofi_3"] <= frame["ofi_3_lower"])
    signal = (signal & frame.index.hour.isin(session_hours)).fillna(False).to_numpy()
    rows: list[dict[str, object]] = []
    index = 0
    while index + hold_bars < len(frame):
        if not signal[index]:
            index += 1
            continue
        entry_index = index + 1
        # The factor's forecast horizon is close(t) to close(t + hold_bars).
        # Entering happens at t + 1 open, so the executable exit is that
        # forecast bar's close rather than an extra M5 bar later.
        exit_index = index + hold_bars
        if side == "long":
            entry_price = float(frame["open"].iloc[entry_index]) + SPREAD_PRICE / 2.0
            exit_price = float(frame["close"].iloc[exit_index]) - SPREAD_PRICE / 2.0
            price_change = exit_price - entry_price
        else:
            entry_price = float(frame["open"].iloc[entry_index]) - SPREAD_PRICE / 2.0
            exit_price = float(frame["close"].iloc[exit_index]) + SPREAD_PRICE / 2.0
            price_change = entry_price - exit_price
        pnl = price_change * LOT_SIZE * CONTRACT_SIZE
        rows.append(
            {
                "signal_time": frame.index[index],
                "entry_time": frame.index[entry_index],
                "exit_time": frame.index[exit_index],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "net_pnl": pnl,
                "net_bps": 10_000.0 * price_change / entry_price,
            }
        )
        index = exit_index + 1
    return pd.DataFrame(rows)


def summarize(trades: pd.DataFrame) -> dict[str, float | int]:
    if trades.empty:
        return {"trades": 0, "net_pnl": 0.0, "profit_factor": 0.0, "win_rate_percent": 0.0, "net_mean_bps": 0.0, "max_drawdown": 0.0}
    gains = float(trades.loc[trades["net_pnl"] > 0, "net_pnl"].sum())
    losses = float(-trades.loc[trades["net_pnl"] < 0, "net_pnl"].sum())
    equity = trades["net_pnl"].cumsum()
    drawdown = equity - equity.cummax()
    return {
        "trades": len(trades),
        "net_pnl": float(trades["net_pnl"].sum()),
        "profit_factor": gains / losses if losses else float("inf"),
        "win_rate_percent": 100.0 * float((trades["net_pnl"] > 0).mean()),
        "net_mean_bps": float(trades["net_bps"].mean()),
        "max_drawdown": float(drawdown.min()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ohlc_csv", type=Path)
    parser.add_argument("flow_csv", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    parser.add_argument("--bar-minutes", type=int, default=5)
    parser.add_argument("--hold-bars", type=int, default=6)
    parser.add_argument("--side", choices=("long", "short"), default="long")
    parser.add_argument("--session-hours", default="0-23", help="UTC hours, for example 13-20.")
    args = parser.parse_args()
    ohlc = load_bars(args.ohlc_csv, default_spread_points=35.0)
    flow = pd.read_csv(args.flow_csv, parse_dates=["time"]).set_index("time")
    if flow.index.tz is None:
        flow.index = flow.index.tz_localize("UTC")
    if args.bar_minutes <= 0 or 60 % args.bar_minutes or args.hold_bars <= 0:
        raise ValueError("bar-minutes and hold-bars must be positive, and bar-minutes must divide 60")
    start_hour, end_hour = (int(value) for value in args.session_hours.split("-", maxsplit=1))
    if not 0 <= start_hour <= end_hour <= 23:
        raise ValueError("session-hours must be an inclusive UTC range such as 13-20")
    features = add_features(ohlc, flow, 20 * 24 * 60 // args.bar_minutes)
    periods = {
        "training_2021_2023": features.loc["2021-01-01":"2023-12-31"],
        "validation_2024": features.loc["2024-01-01":"2024-12-31"],
        "holdout_2025": features.loc["2025-01-01":"2025-12-31"],
    }
    all_trades: list[pd.DataFrame] = []
    summaries: dict[str, dict[str, float | int]] = {}
    for name, sample in periods.items():
        trades = run_strategy(sample, args.hold_bars, args.side, tuple(range(start_hour, end_hour + 1)))
        if not trades.empty:
            trades.insert(0, "sample", name)
            all_trades.append(trades)
        summaries[name] = summarize(trades)
    output = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    args.trades.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.trades, index=False)
    lines = [
        "# Order-flow absorption order-level backtest",
        "",
        "## Pre-specified rule",
        "",
        f"This test fixes the rule before evaluating 2025: use the `ofi_price_absorption` {args.side} factor during UTC {start_hour:02d}:00–{end_hour:02d}:59 and hold for {args.hold_bars} {args.bar_minutes}-minute bars. The choice must be made from training statistics only, not from 2025 data.",
        "",
        f"At close t, an absorption signal combines a three-bar price extreme with an opposite three-bar OFI extreme. Both thresholds are shifted by one {args.bar_minutes}-minute bar. Enter at the next bar's bid/ask and exit at the close of bar t+{args.hold_bars}, charging a 0.35 USD round-trip spread. Positions do not overlap. Results use 0.10 lot and a 100 oz contract only to express PnL; factor metrics are independent of size.",
        "",
        "## Results",
        "",
        "| Sample | Trades | Net PnL (USD) | Profit factor | Win rate | Mean net bps | Maximum drawdown (USD) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in summaries.items():
        lines.append(f"| {name} | {values['trades']} | {values['net_pnl']:.2f} | {values['profit_factor']:.3f} | {values['win_rate_percent']:.2f}% | {values['net_mean_bps']:.3f} | {values['max_drawdown']:.2f} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The 2025 result is a one-time holdout check. Passing this proxy-data test does not establish deployable XAUUSD profitability: the source is PAXGUSDT aggregate trades, and it omits the MT5 broker's bid/ask feed, fill latency, slippage, commissions, and trading-session constraints.",
    ])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(pd.DataFrame(summaries).T.to_string())


if __name__ == "__main__":
    main()
