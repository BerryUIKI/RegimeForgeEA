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


def math_is_finite(value: float) -> bool:
    return bool(np.isfinite(value))


if __name__ == "__main__":
    unittest.main()
