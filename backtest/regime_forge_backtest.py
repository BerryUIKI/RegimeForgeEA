"""Event-driven OHLC backtester for the RegimeForgeEA trend strategy."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Config:
    strategy: str = "trend_breakout"
    higher_timeframe: str | None = None
    higher_fast_ma_period: int = 20
    higher_slow_ma_period: int = 50
    reversal_lookback_bars: int = 3
    reversal_quantile_window: int = 20 * 24 * 12
    reversal_quantile: float = 0.2
    reversal_volume_ratio: float = 1.5
    reversal_require_cross: bool = False
    time_exit_bars: int = 0
    initial_equity: float = 10_000.0
    risk_percent: float = 1.0
    max_daily_loss_percent: float = 4.0
    max_drawdown_percent: float = 12.0
    max_spread_points: float = 80.0
    default_spread_points: float = 35.0
    point: float = 0.01
    contract_size: float = 100.0
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    commission_per_lot_round_turn: float = 0.0
    fast_ma_period: int = 20
    slow_ma_period: int = 50
    atr_period: int = 14
    adx_period: int = 14
    adx_trend_level: float = 20.0
    high_volatility_atr_ratio: float = 1.8
    compression_max_atr_ratio: float = 0.8
    breakout_bars: int = 18
    stop_atr: float = 1.6
    take_profit_atr: float = 3.0
    trailing_atr: float = 1.2
    bollinger_period: int = 20
    bollinger_deviation: float = 2.0
    rsi_period: int = 14
    rsi_lower: float = 30.0
    rsi_upper: float = 70.0
    allow_long: bool = True
    allow_short: bool = True

    def validate(self) -> None:
        if self.initial_equity <= 0:
            raise ValueError("initial_equity must be positive")
        if not 0 < self.risk_percent <= 10:
            raise ValueError("risk_percent must be in (0, 10]")
        if not 0 < self.max_daily_loss_percent <= 100:
            raise ValueError("max_daily_loss_percent must be in (0, 100]")
        if not 0 < self.max_drawdown_percent <= 100:
            raise ValueError("max_drawdown_percent must be in (0, 100]")
        if self.max_spread_points < 0 or self.default_spread_points < 0:
            raise ValueError("spread parameters must be non-negative")
        if self.fast_ma_period >= self.slow_ma_period:
            raise ValueError("fast_ma_period must be below slow_ma_period")
        if self.strategy not in {"trend_breakout", "range_mean_reversion", "trend_pullback", "volume_reversal", "price_reversal", "compression_breakout", "ma_crossover"}:
            raise ValueError("unsupported strategy")
        if min(
            self.fast_ma_period,
            self.slow_ma_period,
            self.atr_period,
            self.adx_period,
            self.breakout_bars,
            self.bollinger_period,
            self.rsi_period,
            self.higher_fast_ma_period,
            self.higher_slow_ma_period,
            self.reversal_lookback_bars,
            self.reversal_quantile_window,
        ) <= 0:
            raise ValueError("indicator and breakout periods must be positive")
        positive = (
            self.point,
            self.contract_size,
            self.volume_min,
            self.volume_max,
            self.volume_step,
            self.trailing_atr,
            self.high_volatility_atr_ratio,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("price, volume, and trailing parameters must be positive")
        if self.volume_max < self.volume_min:
            raise ValueError("volume_max must be at least volume_min")
        if self.bollinger_deviation <= 0:
            raise ValueError("bollinger_deviation must be positive")
        if not 0 < self.rsi_lower < self.rsi_upper < 100:
            raise ValueError("RSI thresholds must satisfy 0 < lower < upper < 100")
        if not 0 < self.reversal_quantile < 0.5:
            raise ValueError("reversal_quantile must be in (0, 0.5)")
        if self.reversal_volume_ratio <= 0 or self.time_exit_bars < 0:
            raise ValueError("reversal volume and time-exit parameters are invalid")
        if self.stop_atr <= 0:
            raise ValueError("stop_atr must be positive")
        if self.take_profit_atr < 0:
            raise ValueError("take_profit_atr must be non-negative")
        if self.strategy != "volume_reversal" and self.take_profit_atr <= 0:
            raise ValueError("take_profit_atr must be positive for non-time-exit strategies")
        if self.strategy in {"trend_pullback", "price_reversal", "compression_breakout"} and not self.higher_timeframe:
            raise ValueError("trend_pullback, price_reversal, and compression_breakout require higher_timeframe")
        if self.higher_fast_ma_period >= self.higher_slow_ma_period:
            raise ValueError("higher_fast_ma_period must be below higher_slow_ma_period")
        if self.compression_max_atr_ratio <= 0:
            raise ValueError("compression_max_atr_ratio must be positive")


@dataclass
class Position:
    direction: int
    entry_time: pd.Timestamp
    entry_price: float
    stop: float
    take_profit: float
    volume: float
    initial_risk: float
    entry_bar: int


def load_bars(path: Path, default_spread_points: float) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame.columns = [str(column).strip().lower().strip("<>") for column in frame.columns]

    if "time" not in frame.columns and {"date", "time"}.issubset(frame.columns):
        frame["timestamp"] = frame["date"].astype(str) + " " + frame["time"].astype(str)
    elif "time" in frame.columns and "date" in frame.columns:
        frame["timestamp"] = frame["date"].astype(str) + " " + frame["time"].astype(str)
    elif "time" in frame.columns:
        frame["timestamp"] = frame["time"]
    elif "datetime" in frame.columns:
        frame["timestamp"] = frame["datetime"]
    else:
        raise ValueError("CSV requires time, datetime, or date/time columns")

    required = {"open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if "spread" not in frame.columns:
        frame["spread"] = default_spread_points
    else:
        frame["spread"] = pd.to_numeric(frame["spread"], errors="coerce").fillna(
            default_spread_points
        )

    frame = (
        frame.sort_values("timestamp")
        .drop_duplicates("timestamp", keep="last")
        .set_index("timestamp")
    )
    if (frame["high"] < frame[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("Invalid OHLC row: high is below another price")
    if (frame["low"] > frame[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("Invalid OHLC row: low is above another price")
    if not np.isfinite(frame[["open", "high", "low", "close", "spread"]].to_numpy()).all():
        raise ValueError("OHLC and spread values must be finite")
    if (frame[["open", "high", "low", "close"]] <= 0).any(axis=None):
        raise ValueError("OHLC values must be positive")
    if (frame["spread"] < 0).any():
        raise ValueError("spread values must be non-negative")
    return frame


def resample_bars(frame: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Aggregate UTC OHLC bars without changing the configured spread model."""
    if not interval:
        return frame.copy()
    aggregations = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "spread": "last",
    }
    optional_sums = ("tick_volume", "real_volume", "volume", "quote_volume", "trade_count")
    aggregations.update(
        {column: "sum" for column in optional_sums if column in frame.columns}
    )
    result = frame.resample(interval, label="left", closed="left").agg(aggregations)
    result = result.dropna(subset=["open", "high", "low", "close"])
    if result.empty:
        raise ValueError(f"No bars remain after resampling to {interval}")
    return result


def seeded_average(values: pd.Series, period: int, alpha: float) -> pd.Series:
    """Return an SMA-seeded recursive average matching terminal indicators."""
    source = values.astype(float).to_numpy()
    output = np.full(len(source), np.nan, dtype=float)
    valid_count = 0
    seed_values: list[float] = []
    previous = math.nan

    for index, value in enumerate(source):
        if math.isnan(value):
            continue
        if valid_count < period:
            seed_values.append(value)
            valid_count += 1
            if valid_count == period:
                previous = float(np.mean(seed_values))
                output[index] = previous
            continue
        previous = alpha * value + (1.0 - alpha) * previous
        output[index] = previous
    return pd.Series(output, index=values.index)


def ema(values: pd.Series, period: int) -> pd.Series:
    return seeded_average(values, period, 2.0 / (period + 1.0))


def wilder_average(values: pd.Series, period: int) -> pd.Series:
    return seeded_average(values, period, 1.0 / period)


def add_indicators(frame: pd.DataFrame, config: Config) -> pd.DataFrame:
    result = frame.copy()
    previous_close = result["close"].shift(1)
    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["fast_ma"] = ema(result["close"], config.fast_ma_period)
    result["slow_ma"] = ema(result["close"], config.slow_ma_period)
    result["previous_fast_ma"] = result["fast_ma"].shift(1)
    result["previous_slow_ma"] = result["slow_ma"].shift(1)
    result["atr"] = wilder_average(true_range, config.atr_period)
    result["atr_slow"] = wilder_average(true_range, config.atr_period * 4)

    up_move = result["high"].diff()
    down_move = -result["low"].diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=result.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=result.index,
    )
    smoothed_tr = wilder_average(true_range, config.adx_period)
    plus_di = 100.0 * wilder_average(plus_dm, config.adx_period) / smoothed_tr
    minus_di = 100.0 * wilder_average(minus_dm, config.adx_period) / smoothed_tr
    denominator = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / denominator
    result["adx"] = wilder_average(dx.fillna(0.0), config.adx_period)

    result["prior_high"] = (
        result["high"].shift(1).rolling(config.breakout_bars).max()
    )
    result["prior_low"] = (
        result["low"].shift(1).rolling(config.breakout_bars).min()
    )
    result["bollinger_mid"] = result["close"].rolling(config.bollinger_period).mean()
    bollinger_std = result["close"].rolling(config.bollinger_period).std(ddof=0)
    result["bollinger_upper"] = result["bollinger_mid"] + config.bollinger_deviation * bollinger_std
    result["bollinger_lower"] = result["bollinger_mid"] - config.bollinger_deviation * bollinger_std
    delta = result["close"].diff()
    average_gain = wilder_average(delta.clip(lower=0.0).fillna(0.0), config.rsi_period)
    average_loss = wilder_average((-delta.clip(upper=0.0)).fillna(0.0), config.rsi_period)
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    result["rsi"] = 100.0 - 100.0 / (1.0 + relative_strength)
    volume_column = next(
        (column for column in ("volume", "tick_volume", "real_volume") if column in result.columns),
        None,
    )
    if volume_column:
        result["reversal_volume_ratio"] = (
            result[volume_column] / result[volume_column].rolling(60).mean()
        )
    else:
        result["reversal_volume_ratio"] = np.nan
    result["reversal_return"] = result["close"].pct_change(config.reversal_lookback_bars)
    result["reversal_lower"] = result["reversal_return"].shift(1).rolling(
        config.reversal_quantile_window
    ).quantile(config.reversal_quantile)
    result["reversal_upper"] = result["reversal_return"].shift(1).rolling(
        config.reversal_quantile_window
    ).quantile(1.0 - config.reversal_quantile)
    result["previous_reversal_return"] = result["reversal_return"].shift(1)
    result["previous_reversal_lower"] = result["reversal_lower"].shift(1)
    result["previous_reversal_upper"] = result["reversal_upper"].shift(1)
    result["regime"] = "unknown"
    ready = result[["fast_ma", "slow_ma", "atr", "atr_slow", "adx"]].notna().all(axis=1)
    high_volatility = ready & (
        result["atr"] / result["atr_slow"] >= config.high_volatility_atr_ratio
    )
    trend = ready & ~high_volatility & (result["adx"] >= config.adx_trend_level)
    result.loc[ready & ~high_volatility & ~trend, "regime"] = "range"
    result.loc[trend, "regime"] = "trend"
    result.loc[high_volatility, "regime"] = "high_volatility"
    if config.higher_timeframe:
        higher_bars = resample_bars(frame, config.higher_timeframe)
        higher_fast = ema(higher_bars["close"], config.higher_fast_ma_period).shift(1)
        higher_slow = ema(higher_bars["close"], config.higher_slow_ma_period).shift(1)
        result["higher_fast_ma"] = higher_fast.reindex(result.index, method="ffill")
        result["higher_slow_ma"] = higher_slow.reindex(result.index, method="ffill")
    return result


def signal_for_bar(row: pd.Series, config: Config) -> int:
    if config.strategy == "trend_breakout":
        if row["regime"] != "trend":
            return 0
        if (
            config.allow_long
            and row["fast_ma"] > row["slow_ma"]
            and row["close"] > row["prior_high"]
            and row["close"] > row["open"]
        ):
            return 1
        if (
            config.allow_short
            and row["fast_ma"] < row["slow_ma"]
            and row["close"] < row["prior_low"]
            and row["close"] < row["open"]
        ):
            return -1
    if config.strategy == "range_mean_reversion":
        if row["regime"] != "range":
            return 0
        if config.allow_long and row["close"] < row["bollinger_lower"] and row["rsi"] <= config.rsi_lower:
            return 1
        if config.allow_short and row["close"] > row["bollinger_upper"] and row["rsi"] >= config.rsi_upper:
            return -1
    if config.strategy == "trend_pullback":
        if pd.isna(row["higher_fast_ma"]) or pd.isna(row["higher_slow_ma"]):
            return 0
        if (
            config.allow_long
            and row["higher_fast_ma"] > row["higher_slow_ma"]
            and row["close"] < row["bollinger_lower"]
            and row["rsi"] <= config.rsi_lower
        ):
            return 1
        if (
            config.allow_short
            and row["higher_fast_ma"] < row["higher_slow_ma"]
            and row["close"] > row["bollinger_upper"]
            and row["rsi"] >= config.rsi_upper
        ):
            return -1
    if config.strategy == "volume_reversal":
        crosses_lower = (
            not config.reversal_require_cross
            or row["previous_reversal_return"] > row["previous_reversal_lower"]
        )
        crosses_upper = (
            not config.reversal_require_cross
            or row["previous_reversal_return"] < row["previous_reversal_upper"]
        )
        if (
            config.allow_long
            and row["reversal_return"] <= row["reversal_lower"]
            and row["reversal_volume_ratio"] >= config.reversal_volume_ratio
            and crosses_lower
        ):
            return 1
        if (
            config.allow_short
            and row["reversal_return"] >= row["reversal_upper"]
            and row["reversal_volume_ratio"] >= config.reversal_volume_ratio
            and crosses_upper
        ):
            return -1
    if config.strategy == "price_reversal":
        if pd.isna(row["higher_fast_ma"]) or pd.isna(row["higher_slow_ma"]):
            return 0
        crosses_lower = (
            not config.reversal_require_cross
            or row["previous_reversal_return"] > row["previous_reversal_lower"]
        )
        crosses_upper = (
            not config.reversal_require_cross
            or row["previous_reversal_return"] < row["previous_reversal_upper"]
        )
        if (
            config.allow_long
            and row["higher_fast_ma"] > row["higher_slow_ma"]
            and row["reversal_return"] <= row["reversal_lower"]
            and crosses_lower
        ):
            return 1
        if (
            config.allow_short
            and row["higher_fast_ma"] < row["higher_slow_ma"]
            and row["reversal_return"] >= row["reversal_upper"]
            and crosses_upper
        ):
            return -1
    if config.strategy == "compression_breakout":
        if (
            pd.isna(row["higher_fast_ma"])
            or pd.isna(row["higher_slow_ma"])
            or pd.isna(row["atr"])
            or pd.isna(row["atr_slow"])
            or row["atr_slow"] <= 0
        ):
            return 0
        compressed = row["atr"] / row["atr_slow"] <= config.compression_max_atr_ratio
        if (
            config.allow_long
            and compressed
            and row["higher_fast_ma"] > row["higher_slow_ma"]
            and row["close"] > row["prior_high"]
        ):
            return 1
        if (
            config.allow_short
            and compressed
            and row["higher_fast_ma"] < row["higher_slow_ma"]
            and row["close"] < row["prior_low"]
        ):
            return -1
    if config.strategy == "ma_crossover":
        if (
            config.allow_long
            and row["fast_ma"] > row["slow_ma"]
            and row["previous_fast_ma"] <= row["previous_slow_ma"]
        ):
            return 1
        if (
            config.allow_short
            and row["fast_ma"] < row["slow_ma"]
            and row["previous_fast_ma"] >= row["previous_slow_ma"]
        ):
            return -1
    return 0


def normalize_volume(raw_volume: float, config: Config) -> float:
    if raw_volume < config.volume_min:
        return 0.0
    steps = math.floor((raw_volume + 1e-12) / config.volume_step)
    volume = min(config.volume_max, steps * config.volume_step)
    return round(max(config.volume_min, volume), 8)


def marked_equity(
    cash: float, position: Position | None, bid_close: float, spread_price: float, config: Config
) -> float:
    if position is None:
        return cash
    mark = bid_close if position.direction == 1 else bid_close + spread_price
    pnl = (
        position.direction
        * (mark - position.entry_price)
        * position.volume
        * config.contract_size
    )
    return cash + pnl


def exit_position(
    position: Position,
    exit_time: pd.Timestamp,
    exit_price: float,
    reason: str,
    cash: float,
    config: Config,
) -> tuple[float, dict]:
    gross_pnl = (
        position.direction
        * (exit_price - position.entry_price)
        * position.volume
        * config.contract_size
    )
    commission = position.volume * config.commission_per_lot_round_turn
    net_pnl = gross_pnl - commission
    trade = {
        "entry_time": position.entry_time.isoformat(),
        "exit_time": exit_time.isoformat(),
        "direction": "long" if position.direction == 1 else "short",
        "volume": position.volume,
        "entry_price": position.entry_price,
        "exit_price": exit_price,
        "initial_stop": (
            position.entry_price
            - position.direction * position.initial_risk / (position.volume * config.contract_size)
        ),
        "take_profit": position.take_profit,
        "gross_pnl": gross_pnl,
        "commission": commission,
        "net_pnl": net_pnl,
        "r_multiple": net_pnl / position.initial_risk if position.initial_risk else 0.0,
        "exit_reason": reason,
    }
    return cash + net_pnl, trade


def run_backtest(frame: pd.DataFrame, config: Config) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    config.validate()
    bars = add_indicators(frame, config)
    cash = config.initial_equity
    peak_equity = cash
    day_start_equity = cash
    current_day = None
    position: Position | None = None
    pending_signal = 0
    pending_atr = 0.0
    trades: list[dict] = []
    equity_rows: list[dict] = []

    for bar_index, (timestamp, row) in enumerate(bars.iterrows()):
        spread_points = float(row["spread"])
        spread_price = spread_points * config.point
        bid_open = float(row["open"])
        ask_open = bid_open + spread_price
        bid_high = float(row["high"])
        bid_low = float(row["low"])
        bid_close = float(row["close"])
        ask_high = bid_high + spread_price
        ask_low = bid_low + spread_price
        ask_close = bid_close + spread_price

        equity_at_open = marked_equity(cash, position, bid_open, spread_price, config)
        bar_day = timestamp.date()
        if current_day != bar_day:
            current_day = bar_day
            day_start_equity = equity_at_open

        daily_lock = equity_at_open <= day_start_equity * (
            1.0 - config.max_daily_loss_percent / 100.0
        )
        drawdown_lock = equity_at_open <= peak_equity * (
            1.0 - config.max_drawdown_percent / 100.0
        )

        if (
            position is None
            and pending_signal
            and not daily_lock
            and not drawdown_lock
            and spread_points <= config.max_spread_points
        ):
            entry = ask_open if pending_signal == 1 else bid_open
            stop_distance = config.stop_atr * pending_atr
            target_distance = config.take_profit_atr * pending_atr
            risk_money = equity_at_open * config.risk_percent / 100.0
            raw_volume = risk_money / (stop_distance * config.contract_size)
            volume = normalize_volume(raw_volume, config)
            if volume > 0:
                stop = entry - pending_signal * stop_distance
                target = entry + pending_signal * target_distance if target_distance > 0 else 0.0
                actual_risk = stop_distance * volume * config.contract_size
                position = Position(
                    direction=pending_signal,
                    entry_time=timestamp,
                    entry_price=entry,
                    stop=stop,
                    take_profit=target,
                    volume=volume,
                    initial_risk=actual_risk,
                    entry_bar=bar_index,
                )

        pending_signal = 0
        pending_atr = 0.0

        if position is not None:
            if position.direction == 1:
                stop_hit = bid_low <= position.stop
                target_hit = position.take_profit > 0 and bid_high >= position.take_profit
                if stop_hit:
                    exit_price = min(bid_open, position.stop)
                    cash, trade = exit_position(
                        position, timestamp, exit_price, "stop", cash, config
                    )
                    trades.append(trade)
                    position = None
                elif target_hit:
                    exit_price = max(bid_open, position.take_profit)
                    cash, trade = exit_position(
                        position, timestamp, exit_price, "take_profit", cash, config
                    )
                    trades.append(trade)
                    position = None
            else:
                stop_hit = ask_high >= position.stop
                target_hit = position.take_profit > 0 and ask_low <= position.take_profit
                if stop_hit:
                    exit_price = max(ask_open, position.stop)
                    cash, trade = exit_position(
                        position, timestamp, exit_price, "stop", cash, config
                    )
                    trades.append(trade)
                    position = None
                elif target_hit:
                    exit_price = min(ask_open, position.take_profit)
                    cash, trade = exit_position(
                        position, timestamp, exit_price, "take_profit", cash, config
                    )
                    trades.append(trade)
                    position = None

        if (
            position is not None
            and config.time_exit_bars > 0
            and bar_index - position.entry_bar >= config.time_exit_bars
        ):
            exit_price = bid_close if position.direction == 1 else ask_close
            cash, trade = exit_position(position, timestamp, exit_price, "time_exit", cash, config)
            trades.append(trade)
            position = None

        if position is not None and pd.notna(row["atr"]):
            trail_distance = config.trailing_atr * float(row["atr"])
            if position.direction == 1:
                position.stop = max(position.stop, bid_close - trail_distance)
            else:
                position.stop = min(position.stop, ask_close + trail_distance)

        equity = marked_equity(cash, position, bid_close, spread_price, config)
        peak_equity = max(peak_equity, equity)
        drawdown = (equity / peak_equity - 1.0) if peak_equity else 0.0
        equity_rows.append(
            {
                "time": timestamp.isoformat(),
                "cash": cash,
                "equity": equity,
                "drawdown": drawdown,
                "regime": row["regime"],
                "position": 0 if position is None else position.direction,
            }
        )

        if position is None and pd.notna(row["atr"]):
            pending_signal = signal_for_bar(row, config)
            pending_atr = float(row["atr"])

    forced_final_close = position is not None
    if forced_final_close:
        timestamp = bars.index[-1]
        row = bars.iloc[-1]
        spread_price = float(row["spread"]) * config.point
        exit_price = float(row["close"]) if position.direction == 1 else float(row["close"]) + spread_price
        cash, trade = exit_position(position, timestamp, exit_price, "end_of_data", cash, config)
        trades.append(trade)

    trades_frame = pd.DataFrame(trades)
    equity_frame = pd.DataFrame(equity_rows)
    if forced_final_close:
        final_peak = max(peak_equity, cash)
        equity_frame.loc[equity_frame.index[-1], ["cash", "equity", "position"]] = [
            cash,
            cash,
            0,
        ]
        equity_frame.loc[equity_frame.index[-1], "drawdown"] = (
            cash / final_peak - 1.0
        )
    final_equity = cash
    net_profit = final_equity - config.initial_equity
    max_drawdown = (
        float(equity_frame["drawdown"].min()) if not equity_frame.empty else 0.0
    )
    wins = int((trades_frame["net_pnl"] > 0).sum()) if not trades_frame.empty else 0
    gross_profit = (
        float(trades_frame.loc[trades_frame["net_pnl"] > 0, "net_pnl"].sum())
        if not trades_frame.empty
        else 0.0
    )
    gross_loss = (
        abs(float(trades_frame.loc[trades_frame["net_pnl"] < 0, "net_pnl"].sum()))
        if not trades_frame.empty
        else 0.0
    )
    summary = {
        "bars": len(bars),
        "start": bars.index[0].isoformat() if len(bars) else None,
        "end": bars.index[-1].isoformat() if len(bars) else None,
        "initial_equity": config.initial_equity,
        "final_equity": final_equity,
        "net_profit": net_profit,
        "total_return_percent": 100.0 * net_profit / config.initial_equity,
        "max_drawdown_percent": -100.0 * max_drawdown,
        "trades": len(trades_frame),
        "win_rate_percent": 100.0 * wins / len(trades_frame) if len(trades_frame) else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "parameters": asdict(config),
    }
    return summary, trades_frame, equity_frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, help="OHLC CSV file")
    parser.add_argument("--output", type=Path, default=Path("outputs/latest"))
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--risk-percent", type=float, default=1.0)
    parser.add_argument("--max-daily-loss-percent", type=float, default=4.0)
    parser.add_argument("--max-drawdown-percent", type=float, default=12.0)
    parser.add_argument("--spread-points", type=float, default=35.0)
    parser.add_argument("--max-spread-points", type=float, default=80.0)
    parser.add_argument("--point", type=float, default=0.01)
    parser.add_argument("--contract-size", type=float, default=100.0)
    parser.add_argument("--volume-min", type=float, default=0.01)
    parser.add_argument("--volume-max", type=float, default=100.0)
    parser.add_argument("--volume-step", type=float, default=0.01)
    parser.add_argument("--commission", type=float, default=0.0)
    parser.add_argument(
        "--resample",
        help="Optional pandas offset alias, such as 15min, 30min, or 1h.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = Config(
        initial_equity=args.initial_equity,
        risk_percent=args.risk_percent,
        max_daily_loss_percent=args.max_daily_loss_percent,
        max_drawdown_percent=args.max_drawdown_percent,
        default_spread_points=args.spread_points,
        max_spread_points=args.max_spread_points,
        point=args.point,
        contract_size=args.contract_size,
        volume_min=args.volume_min,
        volume_max=args.volume_max,
        volume_step=args.volume_step,
        commission_per_lot_round_turn=args.commission,
    )
    bars = load_bars(args.csv, config.default_spread_points)
    bars = resample_bars(bars, args.resample)
    if len(bars) < config.atr_period * 4 + config.breakout_bars:
        raise ValueError("Not enough bars for indicator warm-up")

    summary, trades, equity = run_backtest(bars, config)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    trades.to_csv(args.output / "trades.csv", index=False)
    equity.to_csv(args.output / "equity.csv", index=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
