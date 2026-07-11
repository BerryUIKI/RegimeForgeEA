"""Create reproducible charts and trade extracts for the H4 EMA study."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import load_bars, resample_bars, run_backtest
from scripts.research_ma_crossover_candidates import CANDIDATES
from scripts.research_trend_candidates import split_bars


def select_candidate():
    return next(item for item in CANDIDATES if item.name == "MA05_H4_20_50_2p5x4")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--trades", type=Path, required=True)
    args = parser.parse_args()

    candidate = select_candidate()
    source = load_bars(args.csv, default_spread_points=35.0)
    bars = resample_bars(source, candidate.interval)
    periods = {
        "Training (2021-2023)": ("2021-01-01", "2024-01-01"),
        "Validation (2024)": ("2024-01-01", "2025-01-01"),
        "Holdout (2025)": ("2025-01-01", "2026-01-01"),
    }
    runs = {}
    trade_rows = []
    for label, (start, end) in periods.items():
        summary, trades, equity = run_backtest(split_bars(bars, start, end), candidate.config())
        runs[label] = (summary, equity)
        if not trades.empty:
            copy = trades.copy()
            copy.insert(0, "sample", label)
            trade_rows.append(copy)

    args.assets.mkdir(parents=True, exist_ok=True)
    args.trades.parent.mkdir(parents=True, exist_ok=True)
    pd.concat(trade_rows, ignore_index=True).to_csv(args.trades, index=False)

    fig, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    palette = ["#1f6aa5", "#0a8f72", "#8c5a14"]
    for (label, (_, equity)), color in zip(runs.items(), palette):
        normalized = equity["equity"] / 10_000.0 * 100.0
        axis.plot(equity["time"], normalized, label=label, color=color, linewidth=1.1)
    axis.axhline(100, color="#333333", linewidth=0.8)
    axis.set(title="H4 EMA(20/50) Crossover: Equity by Fixed Sample", ylabel="Equity index (start = 100)")
    axis.grid(alpha=0.22)
    axis.legend()
    fig.savefig(args.assets / "ma_crossover_equity.png", dpi=180)
    plt.close(fig)

    labels = list(runs)
    returns = [runs[label][0]["total_return_percent"] for label in labels]
    drawdowns = [runs[label][0]["max_drawdown_percent"] for label in labels]
    factors = [runs[label][0]["profit_factor"] or 0.0 for label in labels]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
    positions = range(len(labels))
    short_labels = ["Train", "Validation", "Holdout"]
    axes[0].bar(positions, returns, color="#0a8f72")
    axes[0].bar(positions, [-value for value in drawdowns], color="#ba3d3d")
    axes[0].axhline(0, color="#333333", linewidth=0.8)
    axes[0].set(title="Return and maximum drawdown", ylabel="Percent", xticks=list(positions), xticklabels=short_labels)
    axes[0].legend(["Return", "Drawdown (negative)"])
    axes[0].grid(axis="y", alpha=0.22)
    axes[1].bar(positions, factors, color="#1f6aa5")
    axes[1].axhline(1.0, color="#333333", linewidth=0.8, linestyle="--")
    axes[1].set(title="Profit factor", ylim=(0, max(1.8, max(factors) + 0.2)), xticks=list(positions), xticklabels=short_labels)
    axes[1].grid(axis="y", alpha=0.22)
    fig.savefig(args.assets / "ma_crossover_metrics.png", dpi=180)
    plt.close(fig)

    all_trades = pd.concat(trade_rows, ignore_index=True)
    counts = all_trades.groupby(["sample", "exit_reason"]).size().unstack(fill_value=0).reindex(labels, fill_value=0)
    fig, axis = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    bottom = pd.Series(0, index=counts.index, dtype=float)
    colors = {"stop": "#ba3d3d", "take_profit": "#0a8f72", "trailing_stop": "#6c7a89", "time_exit": "#8c5a14"}
    for reason in counts.columns:
        axis.bar(counts.index, counts[reason], bottom=bottom, label=reason.replace("_", " "), color=colors.get(reason, "#555555"))
        bottom += counts[reason]
    axis.set(title="Exit reasons by sample", ylabel="Closed trades")
    axis.legend(ncol=2)
    axis.grid(axis="y", alpha=0.22)
    fig.savefig(args.assets / "ma_crossover_exit_reasons.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
