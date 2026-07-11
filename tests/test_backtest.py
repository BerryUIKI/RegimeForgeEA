"""Regression tests for the Python backtester."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backtest import regime_forge_backtest as BACKTEST


class BacktestTests(unittest.TestCase):
    def make_trending_bars(self, count: int = 500) -> pd.DataFrame:
        rng = np.random.default_rng(7)
        changes = rng.normal(0.025, 0.22, count)
        close = 2300.0 + np.cumsum(changes)
        open_price = np.r_[close[0], close[:-1]]
        high = np.maximum(open_price, close) + rng.uniform(0.05, 0.35, count)
        low = np.minimum(open_price, close) - rng.uniform(0.05, 0.35, count)
        return pd.DataFrame(
            {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "spread": 25.0,
            },
            index=pd.date_range("2025-01-01", periods=count, freq="5min", tz="UTC"),
        )

    def test_indicators_and_regimes_are_produced(self) -> None:
        config = BACKTEST.Config()
        result = BACKTEST.add_indicators(self.make_trending_bars(), config)
        self.assertGreater(result["atr"].notna().sum(), 400)
        self.assertIn("trend", set(result["regime"]))

    def test_backtest_is_deterministic_and_finite(self) -> None:
        config = BACKTEST.Config()
        bars = self.make_trending_bars()
        first, trades, equity = BACKTEST.run_backtest(bars, config)
        second, _, _ = BACKTEST.run_backtest(bars, config)
        self.assertEqual(first, second)
        self.assertTrue(math_is_finite(first["final_equity"]))
        self.assertEqual(len(equity), len(bars))
        self.assertAlmostEqual(first["final_equity"], float(equity["equity"].iloc[-1]))
        self.assertGreater(len(trades), 0)
        self.assertTrue(np.isfinite(trades["net_pnl"]).all())

    def test_volume_is_rounded_down(self) -> None:
        config = BACKTEST.Config(volume_step=0.01, volume_min=0.01)
        self.assertEqual(BACKTEST.normalize_volume(0.019, config), 0.01)
        self.assertEqual(BACKTEST.normalize_volume(0.009, config), 0.0)

    def test_invalid_risk_limits_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BACKTEST.Config(max_drawdown_percent=0).validate()
        with self.assertRaises(ValueError):
            BACKTEST.Config(volume_max=0.001, volume_min=0.01).validate()

    def test_resampling_preserves_ohlc_extremes(self) -> None:
        bars = self.make_trending_bars(count=6)
        resampled = BACKTEST.resample_bars(bars, "15min")
        self.assertEqual(len(resampled), 2)
        self.assertEqual(resampled["open"].iloc[0], bars["open"].iloc[0])
        self.assertEqual(resampled["close"].iloc[0], bars["close"].iloc[2])
        self.assertEqual(resampled["high"].iloc[0], bars["high"].iloc[:3].max())
        self.assertEqual(resampled["low"].iloc[0], bars["low"].iloc[:3].min())

    def test_range_signal_requires_a_range_regime(self) -> None:
        config = BACKTEST.Config(strategy="range_mean_reversion")
        row = pd.Series(
            {
                "regime": "range",
                "close": 99.0,
                "bollinger_lower": 100.0,
                "bollinger_upper": 110.0,
                "rsi": 25.0,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)
        row["regime"] = "trend"
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 0)

    def test_pullback_signal_requires_completed_higher_timeframe_trend(self) -> None:
        config = BACKTEST.Config(strategy="trend_pullback", higher_timeframe="1h")
        row = pd.Series(
            {
                "higher_fast_ma": 110.0,
                "higher_slow_ma": 100.0,
                "close": 99.0,
                "bollinger_lower": 100.0,
                "bollinger_upper": 110.0,
                "rsi": 25.0,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)
        row["higher_fast_ma"] = 90.0
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 0)

    def test_volume_reversal_signal_uses_trailing_extremes(self) -> None:
        config = BACKTEST.Config(strategy="volume_reversal", take_profit_atr=0.0)
        row = pd.Series(
            {
                "reversal_return": -0.01,
                "reversal_lower": -0.005,
                "reversal_upper": 0.005,
                "reversal_volume_ratio": 2.0,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)
        row["reversal_return"] = 0.01
        self.assertEqual(BACKTEST.signal_for_bar(row, config), -1)

    def test_volume_reversal_cross_blocks_repeated_extreme(self) -> None:
        config = BACKTEST.Config(
            strategy="volume_reversal",
            take_profit_atr=0.0,
            reversal_require_cross=True,
        )
        row = pd.Series(
            {
                "reversal_return": -0.01,
                "reversal_lower": -0.005,
                "reversal_upper": 0.005,
                "reversal_volume_ratio": 2.0,
                "previous_reversal_return": -0.008,
                "previous_reversal_lower": -0.006,
                "previous_reversal_upper": 0.006,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 0)
        row["previous_reversal_return"] = -0.004
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)

    def test_price_reversal_uses_completed_higher_timeframe_direction(self) -> None:
        config = BACKTEST.Config(
            strategy="price_reversal",
            higher_timeframe="1h",
            take_profit_atr=2.0,
        )
        row = pd.Series(
            {
                "higher_fast_ma": 110.0,
                "higher_slow_ma": 100.0,
                "reversal_return": -0.01,
                "reversal_lower": -0.005,
                "reversal_upper": 0.005,
                "previous_reversal_return": -0.003,
                "previous_reversal_lower": -0.006,
                "previous_reversal_upper": 0.006,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)
        row["higher_fast_ma"] = 90.0
        row["higher_slow_ma"] = 100.0
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 0)
        row["reversal_return"] = 0.01
        self.assertEqual(BACKTEST.signal_for_bar(row, config), -1)

    def test_compression_breakout_supports_both_directions(self) -> None:
        config = BACKTEST.Config(
            strategy="compression_breakout",
            higher_timeframe="1h",
            take_profit_atr=2.0,
            compression_max_atr_ratio=0.8,
        )
        row = pd.Series(
            {
                "higher_fast_ma": 110.0,
                "higher_slow_ma": 100.0,
                "atr": 0.6,
                "atr_slow": 1.0,
                "close": 101.0,
                "prior_high": 100.0,
                "prior_low": 90.0,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)
        row["higher_fast_ma"] = 90.0
        row["higher_slow_ma"] = 100.0
        row["close"] = 89.0
        self.assertEqual(BACKTEST.signal_for_bar(row, config), -1)

    def test_ma_crossover_requires_an_actual_cross(self) -> None:
        config = BACKTEST.Config(strategy="ma_crossover", take_profit_atr=2.0)
        row = pd.Series(
            {
                "fast_ma": 101.0,
                "slow_ma": 100.0,
                "previous_fast_ma": 99.0,
                "previous_slow_ma": 100.0,
            }
        )
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 1)
        row["previous_fast_ma"] = 101.0
        self.assertEqual(BACKTEST.signal_for_bar(row, config), 0)
        row["fast_ma"] = 99.0
        row["previous_fast_ma"] = 101.0
        self.assertEqual(BACKTEST.signal_for_bar(row, config), -1)


def math_is_finite(value: float) -> bool:
    return bool(np.isfinite(value))


if __name__ == "__main__":
    unittest.main()
