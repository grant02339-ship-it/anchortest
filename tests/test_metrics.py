import unittest

import numpy as np
import pandas as pd

from anchortest.metrics import cagr, max_drawdown, periods_per_year, sharpe_ratio, split_halves, summarize


class TestMetrics(unittest.TestCase):
    def test_cagr_of_doubling_over_one_year(self):
        idx = pd.DatetimeIndex(["2020-01-01", "2021-01-01"])
        self.assertAlmostEqual(cagr(pd.Series([1.0, 2.0], index=idx)), 2 ** (365.25 / 366) - 1, places=6)

    def test_max_drawdown_is_negative_and_correct(self):
        eq = pd.Series([1.0, 1.2, 0.9, 1.0, 1.3])
        self.assertAlmostEqual(max_drawdown(eq), 0.9 / 1.2 - 1)
        self.assertLess(max_drawdown(eq), 0)  # every comparison in this library depends on this sign

    def test_sharpe_of_zero_variance_excess_is_zero_not_nan(self):
        rf = 0.02
        flat = pd.Series([rf / 12] * 24)
        self.assertEqual(sharpe_ratio(flat, 12, rf), 0.0)

    def test_periods_per_year_from_median_gap(self):
        idx = pd.date_range("2020-01-01", periods=30, freq="30D")
        self.assertAlmostEqual(periods_per_year(idx), 365.25 / 30)

    def test_split_halves_renormalises_each_half(self):
        eq = pd.Series(np.linspace(1, 3, 21), index=pd.date_range("2020-01-01", periods=21, freq="30D"))
        a, b = split_halves(eq)
        self.assertEqual(a.iloc[0], 1.0)
        self.assertEqual(b.iloc[0], 1.0)

    def test_summarize_keys(self):
        eq = pd.Series(np.linspace(1, 2, 30), index=pd.date_range("2020-01-01", periods=30, freq="30D"))
        self.assertEqual({"cagr", "ann_vol", "sharpe", "max_drawdown", "n_periods", "periods_per_year"}, set(summarize(eq)))


if __name__ == "__main__":
    unittest.main()
