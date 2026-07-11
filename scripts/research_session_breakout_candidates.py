"""Evaluate price-only, long/short session-range breakout candidates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backtest.regime_forge_backtest import ema, load_bars, wilder_average
from scripts.research_trend_candidates import split_bars


SPREAD_PRICE = 0.35
CONTRACT_SIZE = 100.0
VOLUME_STEP = 0.01


@dataclass(frozen=True)
class Candidate:
    name: str
    session_start_hour: int
    range_bars: int
    trade_end_hour: int
    stop_atr: float
    target_atr: float
    trailing_atr: float
    max_hold_bars: int


CANDIDATES = (
    Candidate("SB01_London60_1p5x2", 7, 12, 13, 1.5, 2.0, 1.2, 48),
    Candidate("SB02_London30_1p5x2", 7, 6, 13, 1.5, 2.0, 1.2, 48),
    Candidate("SB03_NY60_1p5x2", 13, 12, 20, 1.5, 2.0, 1.2, 48),
    Candidate("SB04_NY30_2x3", 13, 6, 20, 2.0, 3.0, 1.5, 60),
)


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    previous_close = result["close"].shift(1)
    true_range = pd.concat(
        [result["high"] - result["low"], (result["high"] - previous_close).abs(), (result["low"] - previous_close).abs()],
        axis=1,
    ).max(axis=1)
    result["atr"] = wilder_average(true_range, 14)
    higher = result.resample("1h", label="left", closed="left").agg(close=("close", "last")).dropna()
    higher_fast = ema(higher["close"], 20).shift(1)
    higher_slow = ema(higher["close"], 50).shift(1)
    result["h1_up"] = (higher_fast > higher_slow).reindex(result.index, method="ffill")
    result["h1_down"] = (higher_fast < higher_slow).reindex(result.index, method="ffill")
    result["day"] = result.index.date
    return result


def session_ranges(frame: pd.DataFrame, candidate: Candidate) -> tuple[pd.Series, pd.Series, pd.Series]:
    hour = frame.index.hour
    minute = frame.index.minute
    start = candidate.session_start_hour
    range_end_minutes = start * 60 + candidate.range_bars * 5
    minute_of_day = hour * 60 + minute
    range_mask = (minute_of_day >= start * 60) & (minute_of_day < range_end_minutes)
    range_bars = frame.loc[range_mask].groupby("day", observed=True).agg(range_high=("high", "max"), range_low=("low", "min"))
    high = frame["day"].map(range_bars["range_high"])
    low = frame["day"].map(range_bars["range_low"])
    trade_mask = (minute_of_day >= range_end_minutes) & (hour < candidate.trade_end_hour)
    return high, low, pd.Series(trade_mask, index=frame.index)


def normalize_volume(raw: float) -> float:
    return max(0.0, np.floor(raw / VOLUME_STEP) * VOLUME_STEP)


def simulate(frame: pd.DataFrame, candidate: Candidate) -> dict:
    high_range, low_range, trade_window = session_ranges(frame, candidate)
    cash = 10_000.0
    peak = cash
    day_start = cash
    current_day = None
    position = None
    pending = 0
    pending_atr = 0.0
    traded_days: set[object] = set()
    trades: list[dict] = []
    equity_rows: list[float] = []
    for index, (timestamp, row) in enumerate(frame.iterrows()):
        day = row["day"]
        bid_open, bid_high, bid_low, bid_close = (float(row[key]) for key in ("open", "high", "low", "close"))
        ask_open, ask_high, ask_low, ask_close = (bid_open + SPREAD_PRICE, bid_high + SPREAD_PRICE, bid_low + SPREAD_PRICE, bid_close + SPREAD_PRICE)
        if day != current_day:
            current_day = day
            day_start = cash if position is None else cash + position["direction"] * ((bid_open if position["direction"] == 1 else ask_open) - position["entry"]) * position["volume"] * CONTRACT_SIZE
        equity_open = cash if position is None else cash + position["direction"] * ((bid_open if position["direction"] == 1 else ask_open) - position["entry"]) * position["volume"] * CONTRACT_SIZE
        daily_lock = equity_open <= day_start * 0.98
        drawdown_lock = equity_open <= peak * 0.80
        if position is None and pending and not daily_lock and not drawdown_lock:
            entry = ask_open if pending == 1 else bid_open
            stop_distance = candidate.stop_atr * pending_atr
            volume = normalize_volume((equity_open * 0.0025) / (stop_distance * CONTRACT_SIZE)) if stop_distance > 0 else 0.0
            if volume >= 0.01:
                position = {"direction": pending, "entry": entry, "stop": entry - pending * stop_distance, "target": entry + pending * candidate.target_atr * pending_atr, "volume": volume, "entry_index": index, "entry_time": timestamp}
                traded_days.add(day)
        pending = 0
        if position is not None:
            direction = position["direction"]
            stop_hit = bid_low <= position["stop"] if direction == 1 else ask_high >= position["stop"]
            target_hit = bid_high >= position["target"] if direction == 1 else ask_low <= position["target"]
            reason = None
            if stop_hit:
                exit_price = min(bid_open, position["stop"]) if direction == 1 else max(ask_open, position["stop"])
                reason = "stop"
            elif target_hit:
                exit_price = max(bid_open, position["target"]) if direction == 1 else min(ask_open, position["target"])
                reason = "take_profit"
            elif index - position["entry_index"] >= candidate.max_hold_bars:
                exit_price = bid_close if direction == 1 else ask_close
                reason = "time_exit"
            if reason is not None:
                pnl = direction * (exit_price - position["entry"]) * position["volume"] * CONTRACT_SIZE
                cash += pnl
                trades.append({"entry_time": position["entry_time"], "exit_time": timestamp, "direction": "long" if direction == 1 else "short", "net_pnl": pnl, "exit_reason": reason})
                position = None
            elif pd.notna(row["atr"]):
                trail = candidate.trailing_atr * float(row["atr"])
                position["stop"] = max(position["stop"], bid_close - trail) if direction == 1 else min(position["stop"], ask_close + trail)
        if position is None and pd.notna(row["atr"]) and day not in traded_days and bool(trade_window.loc[timestamp]):
            if bool(row["h1_up"]) and bid_close > high_range.loc[timestamp]:
                pending, pending_atr = 1, float(row["atr"])
            elif bool(row["h1_down"]) and bid_close < low_range.loc[timestamp]:
                pending, pending_atr = -1, float(row["atr"])
        marked = cash if position is None else cash + position["direction"] * ((bid_close if position["direction"] == 1 else ask_close) - position["entry"]) * position["volume"] * CONTRACT_SIZE
        peak = max(peak, marked)
        equity_rows.append(marked)
    trades_frame = pd.DataFrame(trades)
    pnl = trades_frame["net_pnl"] if not trades_frame.empty else pd.Series(dtype=float)
    gains, losses = float(pnl[pnl > 0].sum()), float(-pnl[pnl < 0].sum())
    equity = np.asarray(equity_rows)
    drawdown = equity / np.maximum.accumulate(equity) - 1.0 if len(equity) else np.array([0.0])
    return {"return_percent": 100.0 * (cash - 10_000.0) / 10_000.0, "max_drawdown_percent": -100.0 * float(drawdown.min()), "trades": len(trades_frame), "win_rate_percent": 100.0 * float((pnl > 0).mean()) if len(pnl) else 0.0, "profit_factor": gains / losses if losses else None}


def passes(result: dict, minimum_trades: int) -> bool:
    return result["trades"] >= minimum_trades and result["profit_factor"] is not None and result["profit_factor"] >= 1.10 and result["return_percent"] > 0 and result["max_drawdown_percent"] <= 15.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    source = add_features(load_bars(args.csv, default_spread_points=35.0))
    train, validation, holdout = (split_bars(source, start, end) for start, end in (("2021-01-01", "2024-01-01"), ("2024-01-01", "2025-01-01"), ("2025-01-01", "2026-01-01")))
    train_rows = [{"name": candidate.name, **simulate(train, candidate)} for candidate in CANDIDATES]
    by_name = {candidate.name: candidate for candidate in CANDIDATES}
    validation_rows = [{"name": row["name"], **simulate(validation, by_name[row["name"]])} for row in train_rows if passes(row, 100)]
    approved = [row for row in validation_rows if passes(row, 40)]
    selected = max(approved, key=lambda row: (row["return_percent"] / max(row["max_drawdown_percent"], 0.01), row["profit_factor"]), default=None)
    holdout_row = None if selected is None else {"name": selected["name"], **simulate(holdout, by_name[selected["name"]])}
    payload = {"train": train_rows, "validation": validation_rows, "selected": selected, "holdout": holdout_row}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    def rows(items: list[dict]) -> str:
        output = []
        for item in items:
            pf = "N/A" if item["profit_factor"] is None else f"{item['profit_factor']:.2f}"
            output.append(f"| {item['name']} | {item['return_percent']:.2f}% | {item['max_drawdown_percent']:.2f}% | {item['trades']} | {item['win_rate_percent']:.2f}% | {pf} |")
        return "\n".join(output) or "| None | - | - | - | - | - |"
    report = f"""# Session breakout live-strategy candidate research

## Method

This price-only study uses London or New York opening ranges, completed H1 EMA20/EMA50 trend confirmation, and symmetric long/short breakouts. Every trade has an ATR stop, ATR target, trailing stop, maximum holding time, next-bar bid/ask execution, 0.25% equity risk, 2% daily loss lock, 20% peak drawdown lock, and one trade per session day. Volume is not used.

## Training: 2021-2023

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
{rows(train_rows)}

## Validation: 2024

| Candidate | Return | Max drawdown | Trades | Win rate | PF |
|---|---:|---:|---:|---:|---:|
{rows(validation_rows)}

## Decision

{'No candidate passed training and validation, so 2025 was not evaluated.' if selected is None else f'{selected["name"]} was selected before its 2025 holdout run.'}
"""
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report, encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
