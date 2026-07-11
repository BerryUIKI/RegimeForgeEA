"""Generate charts for the price-only live-strategy rejection report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_json", type=Path)
    parser.add_argument("--assets", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.results_json.read_text(encoding="utf-8"))
    rows = payload["train"]
    names = [row["name"].replace("PR0", "PR") for row in rows]
    profits = [row["return_percent"] for row in rows]
    pfs = [row["profit_factor"] or 0.0 for row in rows]
    drawdowns = [row["max_drawdown_percent"] for row in rows]
    args.assets.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
    colors = ["#ba3d3d" if value < 0 else "#0a8f72" for value in profits]
    axes[0].bar(names, profits, color=colors)
    axes[0].axhline(0, color="#333333", linewidth=0.8)
    axes[0].set(title="Training Total Return", ylabel="Percent")
    axes[0].tick_params(axis="x", rotation=20)
    axes[0].grid(axis="y", alpha=0.2)
    axes[1].bar(names, pfs, color="#6c7a89")
    axes[1].axhline(1.0, color="#333333", linewidth=0.8, linestyle="--")
    axes[1].set(title="Training Profit Factor", ylim=(0.8, 1.1))
    axes[1].tick_params(axis="x", rotation=20)
    axes[1].grid(axis="y", alpha=0.2)
    fig.savefig(args.assets / "price_only_live_training_performance.png", dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 4.6), constrained_layout=True)
    axis.scatter(drawdowns, pfs, s=90, color="#ba3d3d")
    for name, dd, pf in zip(names, drawdowns, pfs):
        axis.annotate(name, (dd, pf), xytext=(4, 4), textcoords="offset points")
    axis.axhline(1.0, color="#333333", linewidth=0.8, linestyle="--")
    axis.axvline(15.0, color="#333333", linewidth=0.8, linestyle="--")
    axis.set(title="Training Risk/Return Gate", xlabel="Maximum drawdown (%)", ylabel="Profit factor", xlim=(0, 22), ylim=(0.8, 1.1))
    axis.grid(alpha=0.2)
    fig.savefig(args.assets / "price_only_live_training_gate.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
