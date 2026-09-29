import unittest

import numpy as np
import pandas as pd

from anchortest.anchors import anchor_average, shifts_for


def make_backtest_fn(seed=0):
    """A deterministic toy 'strategy': a noisy geometric walk, marked every `rebalance_days`, with the
    walk's own start row shifted by `start_shift` -- exactly the mechanic anchor_average expects."""
    rng = np.random.default_rng(seed)
    daily = pd.Series(rng.normal(0.0006, 0.01, 5000), index=pd.bdate_range("2005-01-01", periods=5000))
    prices = 100.0 * np.exp(daily.cumsum())

    def backtest_fn(params, start_shift=0):
        shifted = prices.iloc[start_shift:]
        marked = shifted.iloc[:: params["rebalance_days"]]
        return marked / marked.iloc[0]

    return backtest_fn


class TestShiftsFor(unittest.TestCase):
    def test_thirty_anchors_at_25_day_cycle_is_only_25_unique_shifts(self):
        self.assertEqual(shifts_for(25, 30), list(range(25)))

    def test_ten_anchor_search_set(self):
        self.assertEqual(shifts_for(25, 10), [0, 2, 5, 7, 10, 12, 15, 17, 20, 22])

    def test_rejects_nonpositive_cycle(self):
        with self.assertRaises(ValueError):
            shifts_for(0, 10)


class TestAnchorAverage(unittest.TestCase):
    def test_runs_every_requested_phase_and_matches_shifts_for(self):
        agg, per_anchor = anchor_average(make_backtest_fn(), {"rebalance_days": 21}, cycle_days=21, n_anchors=21)
        self.assertEqual([a["shift"] for a in per_anchor], shifts_for(21, 21))
        self.assertEqual(agg["n_anchors"], 21)

    def test_a_single_phase_can_disagree_with_the_average(self):
        # The whole point of this library: don't trust shift=0 alone. Confirm the fixture actually has
        # phase dependence, so this test is not vacuous.
        agg, per_anchor = anchor_average(make_backtest_fn(seed=3), {"rebalance_days": 21}, cycle_days=21, n_anchors=21)
        shift0 = next(a for a in per_anchor if a["shift"] == 0)
        self.assertGreater(agg["stdev_sharpe"], 0.01)
        self.assertNotAlmostEqual(shift0["sharpe"], agg["mean_sharpe"], places=2)

    def test_aggregate_keys(self):
        agg, _ = anchor_average(make_backtest_fn(), {"rebalance_days": 21}, cycle_days=21, n_anchors=10)
        expected = {"n_anchors", "mean_sharpe", "median_sharpe", "min_sharpe", "stdev_sharpe",
                    "mean_cagr", "mean_dd", "worst_dd", "mean_recent_half_sharpe"}
        self.assertEqual(expected, set(agg))

    def test_min_sharpe_is_never_above_mean(self):
        agg, _ = anchor_average(make_backtest_fn(seed=7), {"rebalance_days": 21}, cycle_days=21, n_anchors=21)
        self.assertLessEqual(agg["min_sharpe"], agg["mean_sharpe"] + 1e-12)


if __name__ == "__main__":
    unittest.main()
