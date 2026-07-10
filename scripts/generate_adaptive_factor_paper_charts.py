"""Generate comparison charts for the detailed adaptive M5 factor paper."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


SAMPLES = ["training_2021_2023", "validation_2024", "holdout_2025"]
LABELS = ["Training\n2021-2023", "Validation\n2024", "Holdout\n2025"]
COLORS = {"baseline": "#6c7a89", "adaptive": "#0a8f72"}


def metrics(frame: pd.DataFrame) -> dict[str, float]:
    pnl = frame["net_pnl"]
    equity = pnl.cumsum()
    gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    return {"net": float(pnl.sum()), "pf": float(gains / losses), "dd": float((equity - equity.cummax()).min())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_csv", type=Path)
    parser.add_argument("adaptive_csv", type=Path)
    parser.add_argument("--assets", type=Path, required=True)
    args = parser.parse_args()
    baseline = pd.read_csv(args.baseline_csv, parse_dates=["exit_time"])
    adaptive = pd.read_csv(args.adaptive_csv, parse_dates=["exit_time"])
    args.assets.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), constrained_layout=True)
    x = list(range(len(SAMPLES))); width = 0.36
    base_metrics = [metrics(baseline.loc[baseline["sample"] == sample]) for sample in SAMPLES]
    adapt_metrics = [metrics(adaptive.loc[adaptive["sample"] == sample]) for sample in SAMPLES]
    axes[0].bar([value - width / 2 for value in x], [value["pf"] for value in base_metrics], width, label="Baseline", color=COLORS["baseline"])
    axes[0].bar([value + width / 2 for value in x], [value["pf"] for value in adapt_metrics], width, label="Adaptive", color=COLORS["adaptive"])
    axes[0].axhline(1, color="#333333", linewidth=0.8, linestyle="--"); axes[0].set(title="Profit Factor", xticks=x, xticklabels=LABELS, ylim=(0.9, 1.42)); axes[0].grid(axis="y", alpha=0.2); axes[0].legend(frameon=False)
    axes[1].bar([value - width / 2 for value in x], [-value["dd"] for value in base_metrics], width, label="Baseline", color=COLORS["baseline"])
    axes[1].bar([value + width / 2 for value in x], [-value["dd"] for value in adapt_metrics], width, label="Adaptive", color=COLORS["adaptive"])
    axes[1].set(title="Maximum Drawdown", ylabel="USD (0.10 lot reference)", xticks=x, xticklabels=LABELS); axes[1].grid(axis="y", alpha=0.2)
    fig.savefig(args.assets / "adaptive_factor_comparison.png", dpi=180); plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 5.1), constrained_layout=True)
    for name, frame, color in [("Baseline", baseline, COLORS["baseline"]), ("Adaptive", adaptive, COLORS["adaptive"])]:
        holdout = frame.loc[frame["sample"] == "holdout_2025"].sort_values("exit_time")
        axis.plot(holdout["exit_time"], holdout["net_pnl"].cumsum(), label=name, color=color, linewidth=1.25)
    axis.axhline(0, color="#333333", linewidth=0.8); axis.set(title="2025 Holdout: Cumulative PnL", xlabel="Exit time (UTC)", ylabel="Net PnL (USD, 0.10 lot reference)"); axis.grid(alpha=0.2); axis.legend(frameon=False)
    fig.savefig(args.assets / "adaptive_factor_holdout_equity.png", dpi=180); plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 5.1), constrained_layout=True)
    adaptive = adaptive.copy(); adaptive["month"] = adaptive["exit_time"].dt.to_period("M").dt.to_timestamp()
    for sample, frame in adaptive.groupby("sample", sort=False):
        monthly = frame.groupby("month")["net_pnl"].sum()
        axis.plot(monthly.index, monthly.values, marker="o", markersize=2.5, linewidth=1.0, label=sample.replace("_", " "))
    axis.axhline(0, color="#333333", linewidth=0.8); axis.set(title="Adaptive Strategy: Monthly PnL", xlabel="Month", ylabel="Net PnL (USD, 0.10 lot reference)"); axis.grid(alpha=0.2); axis.legend(frameon=False, ncol=3, loc="upper left")
    fig.savefig(args.assets / "adaptive_factor_monthly_pnl.png", dpi=180); plt.close(fig)


if __name__ == "__main__":
    main()
