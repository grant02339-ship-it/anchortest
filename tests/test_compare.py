import unittest

from anchortest.compare import DEFAULT_BAR, clears_bar, compare


def agg(**over):
    base = dict(mean_sharpe=1.0, median_sharpe=1.0, min_sharpe=0.7, stdev_sharpe=0.14, mean_cagr=0.17,
                mean_dd=-0.22, worst_dd=-0.31, mean_recent_half_sharpe=0.8)
    base.update(over)
    return base


class TestDrawdownSignConvention(unittest.TestCase):
    """The regression for the exact bug described in artifacts.py's module docstring."""

    def test_shallower_drawdown_counts_as_improvement(self):
        self.assertGreater(compare(agg(), agg(mean_dd=-0.20))["mean_dd"], 0)

    def test_deeper_drawdown_is_not_an_improvement(self):
        self.assertLess(compare(agg(), agg(mean_dd=-0.24))["mean_dd"], 0)

    def test_worst_dd_uses_the_same_convention(self):
        # worst_dd isn't in DEFAULT_BAR (it's informational, not part of the strict bar) -- request it explicitly.
        self.assertGreater(compare(agg(), agg(worst_dd=-0.25), keys=("worst_dd",))["worst_dd"], 0)


class TestClearsBar(unittest.TestCase):
    def test_all_six_improving_clears_the_bar(self):
        better = agg(mean_sharpe=1.05, median_sharpe=1.05, min_sharpe=0.75, mean_cagr=0.18,
                     mean_dd=-0.21, mean_recent_half_sharpe=0.85)
        self.assertTrue(clears_bar(compare(agg(), better)))

    def test_any_single_regression_fails_the_bar(self):
        better = dict(mean_sharpe=1.05, median_sharpe=1.05, min_sharpe=0.75, mean_cagr=0.18,
                      mean_dd=-0.21, mean_recent_half_sharpe=0.85)
        for key, worse_value in [("mean_sharpe", 0.99), ("median_sharpe", 0.99), ("min_sharpe", 0.69),
                                 ("mean_cagr", 0.16), ("mean_dd", -0.23), ("mean_recent_half_sharpe", 0.79)]:
            candidate = agg(**{**better, key: worse_value})
            self.assertFalse(clears_bar(compare(agg(), candidate)), f"{key} regression must fail the bar")

    def test_identical_candidate_does_not_pass(self):
        self.assertFalse(clears_bar(compare(agg(), agg())))  # ties are not promotions

    def test_bar_covers_exactly_the_documented_metrics(self):
        self.assertEqual(set(DEFAULT_BAR),
                         {"mean_sharpe", "median_sharpe", "min_sharpe", "mean_cagr", "mean_dd", "mean_recent_half_sharpe"})


if __name__ == "__main__":
    unittest.main()
