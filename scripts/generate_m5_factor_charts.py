"""Generate chart assets for the M5 volume-confirmed reversal report."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


LABELS = {"training_2021_2023": "Training (2021-2023)", "validation_2024": "Validation (2024)", "holdout_2025": "Holdout (2025)"}
COLORS = {"training_2021_2023": "#2455a4", "validation_2024": "#0a8f72", "holdout_2025": "#d67a14"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trades_csv", type=Path)
    parser.add_argument("--assets", type=Path, required=True)
    args = parser.parse_args()
    trades = pd.read_csv(args.trades_csv, parse_dates=["exit_time"])
    args.assets.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for sample, frame in trades.groupby("sample", sort=False):
        frame = frame.sort_values("exit_time")
        axis.plot(frame["exit_time"], frame["net_pnl"].cumsum(), label=LABELS[sample], color=COLORS[sample], linewidth=1.2)
    axis.axhline(0, color="#555555", linewidth=0.8); axis.set(title="Cumulative Net PnL by Independent Sample", xlabel="Exit time (UTC)", ylabel="Net PnL (USD, 0.10 lot reference)"); axis.grid(alpha=0.22); axis.legend(frameon=False, ncol=3, loc="upper left")
    fig.savefig(args.assets / "m5_volume_reversal_equity.png", dpi=180); plt.close(fig)
    rows = []
    for sample, frame in trades.groupby("sample", sort=False):
        pnl = frame["net_pnl"]; gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
        rows.append((sample, gains / losses, frame["net_bps"].mean()))
    metric = pd.DataFrame(rows, columns=["sample", "pf", "mean_bps"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), constrained_layout=True)
    x = range(len(metric)); colors = [COLORS[value] for value in metric["sample"]]
    axes[0].bar(x, metric["pf"], color=colors); axes[0].axhline(1, color="#555555", linestyle="--", linewidth=0.8); axes[0].set(title="Profit Factor", xticks=list(x), xticklabels=["Train", "Validation", "Holdout"], ylim=(0.9, 1.35)); axes[0].grid(axis="y", alpha=0.22)
    axes[1].bar(range(len(metric)), metric["mean_bps"], color=colors); axes[1].axhline(0, color="#555555", linewidth=0.8); axes[1].set(title="Mean Net Return per Trade", ylabel="Basis points", xticks=list(range(len(metric))), xticklabels=["Train", "Validation", "Holdout"]); axes[1].grid(axis="y", alpha=0.22)
    fig.savefig(args.assets / "m5_volume_reversal_metrics.png", dpi=180); plt.close(fig)
    trades["month"] = trades["exit_time"].dt.to_period("M").dt.to_timestamp()
    monthly = trades.groupby(["sample", "month"], observed=True)["net_pnl"].sum().reset_index()
    fig, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for sample, frame in monthly.groupby("sample", sort=False):
        axis.plot(frame["month"], frame["net_pnl"], marker="o", markersize=2.5, linewidth=1.0, color=COLORS[sample], label=LABELS[sample])
    axis.axhline(0, color="#555555", linewidth=0.8); axis.set(title="Monthly Net PnL Stability", xlabel="Month", ylabel="Net PnL (USD, 0.10 lot reference)"); axis.grid(alpha=0.22); axis.legend(frameon=False, ncol=3, loc="upper left")
    fig.savefig(args.assets / "m5_volume_reversal_monthly.png", dpi=180); plt.close(fig)


if __name__ == "__main__":
    main()
