import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

spec = importlib.util.spec_from_file_location("improvement_runner", os.path.join(ROOT, "tools", "improvement_runner.py"))
improvement_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(improvement_runner)

GOOD_SUBMISSION = '''
import numpy as np, pandas as pd
CYCLE_DAYS = 21
_RNG = np.random.default_rng(1)
_PRICES = pd.Series(100.0 * np.exp(np.cumsum(_RNG.normal(0.0004, 0.01, 900))), index=pd.bdate_range("2015-01-01", periods=900))
BASELINE_PARAMS = {"n": 10}
SEARCH_SPACE = {"n": [5, 20]}
def backtest(params, start_shift=0):
    prices = _PRICES.iloc[start_shift:]
    marked = prices.iloc[::CYCLE_DAYS]
    return marked / marked.iloc[0]
'''

BASE_AGG = dict(mean_sharpe=0.80, median_sharpe=0.78, min_sharpe=0.60, stdev_sharpe=0.10,
                mean_cagr=0.14, mean_dd=-0.22, worst_dd=-0.30, mean_recent_half_sharpe=0.70)


def make_result(rows):
    return dict(baseline_screen=BASE_AGG, baseline_full=BASE_AGG, n_candidates=len(rows), results=rows)


class TestReportFormatting(unittest.TestCase):
    """Directly test build_report's formatting against fabricated, deterministic _run_search results --
    exercises the confirmed / screen-only / none-found branches without depending on a real search
    happening to land in any particular bucket."""

    def _patched(self, rows):
        return mock.patch.object(improvement_runner, "_run_search", return_value=make_result(rows))

    def test_confirmed_candidate_is_reported_with_its_deltas(self):
        rows = [{"param": "n", "value": 5, "screen_pass": True,
                 "screen_delta": {"mean_sharpe": 0.15}, "full_pass": True,
                 "full_delta": {"mean_sharpe": 0.12, "mean_cagr": 0.02, "mean_dd": 0.01}}]
        with self._patched(rows):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("Confirmed improvements (1/1)", report)
        self.assertIn("n = 5", report)
        self.assertIn("+0.120", report)
        self.assertNotIn("none", report.split("## Confirmed")[1].split("##")[0])

    def test_screen_only_candidate_is_reported_separately_and_not_as_confirmed(self):
        rows = [{"param": "n", "value": 5, "screen_pass": True,
                 "screen_delta": {"mean_sharpe": 0.20}, "full_pass": False,
                 "full_delta": {"mean_sharpe": -0.05, "mean_cagr": -0.01, "mean_dd": -0.02}}]
        with self._patched(rows):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("Confirmed improvements: none", report)
        self.assertIn("Screen-passed but failed full validation (1)", report)
        self.assertIn("screen Sharpe +0.200, full Sharpe -0.050", report)

    def test_a_candidate_that_fails_the_screen_is_not_mentioned_in_either_results_section(self):
        rows = [{"param": "n", "value": 5, "screen_pass": False,
                 "screen_delta": {"mean_sharpe": -0.30}, "full_pass": None, "full_delta": None}]
        with self._patched(rows):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("Confirmed improvements: none", report)
        self.assertNotIn("Screen-passed but failed", report)  # never even ran full validation on it
        self.assertIn("Candidates tested: 1", report)

    def test_no_candidates_at_all_still_produces_a_valid_report(self):
        with self._patched([]):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("Confirmed improvements: none", report)
        self.assertIn("## Reviewer notes", report)

    def test_mixed_batch_sorts_correctly_into_both_sections(self):
        rows = [
            {"param": "a", "value": 1, "screen_pass": True, "screen_delta": {"mean_sharpe": 0.1},
             "full_pass": True, "full_delta": {"mean_sharpe": 0.1, "mean_cagr": 0.01, "mean_dd": 0.005}},
            {"param": "b", "value": 2, "screen_pass": True, "screen_delta": {"mean_sharpe": 0.3},
             "full_pass": False, "full_delta": {"mean_sharpe": -0.1, "mean_cagr": -0.02, "mean_dd": -0.03}},
            {"param": "c", "value": 3, "screen_pass": False, "screen_delta": {"mean_sharpe": -0.2},
             "full_pass": None, "full_delta": None},
        ]
        with self._patched(rows):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("Confirmed improvements (1/3)", report)
        self.assertIn("a = 1", report)
        self.assertIn("Screen-passed but failed full validation (1)", report)
        self.assertIn("b = 2", report)
        self.assertNotIn("c = 3", report)  # failed the screen outright -- shouldn't appear in either list


class TestSkipScreenReporting(unittest.TestCase):
    """The regression tests for the false-negative bug found while building this tool: a small search
    space must skip the cheap screen and go straight to full validation, and the report must say so."""

    def test_confirmed_note_reflects_screen_skipped(self):
        rows = [{"param": "n", "value": 5, "screen_skipped": True, "screen_pass": True,
                 "screen_delta": {"mean_sharpe": 0.1, "mean_cagr": 0.01, "mean_dd": 0.01},
                 "full_pass": True, "full_delta": {"mean_sharpe": 0.1, "mean_cagr": 0.01, "mean_dd": 0.01}}]
        result = make_result(rows)
        result["screen_skipped"] = True
        with mock.patch.object(improvement_runner, "_run_search", return_value=result):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("no cheap-screen step", report)
        self.assertIn("Cleared the strict bar on full 25-anchor validation", report)
        self.assertNotIn("BOTH the cheap screen", report)

    def test_not_skipped_note_mentions_the_screen(self):
        with mock.patch.object(improvement_runner, "_run_search", return_value=make_result([])):
            report = improvement_runner.build_report(Path("dummy.py"))
        self.assertIn("Screened at 10 anchors first", report)


class TestRunSearch(unittest.TestCase):
    """End-to-end against a real (small, fast) submission -- proves the subprocess plumbing, not just the
    report formatting."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, content):
        p = Path(self.tmp.name) / name
        p.write_text(content)
        return p

    def test_real_search_runs_and_produces_a_well_formed_report(self):
        sub = self.write("submission.py", GOOD_SUBMISSION)
        report = improvement_runner.build_report(sub)
        self.assertIn("# AnchorTest Improvement Search report", report)
        self.assertIn("Candidates tested: 2", report)  # n=5 and n=20 both differ from baseline n=10
        self.assertIn("## Reviewer notes", report)

    def test_missing_required_name_raises_a_clear_error(self):
        sub = self.write("submission.py", "CYCLE_DAYS = 21\nBASELINE_PARAMS = {}\nSEARCH_SPACE = {}\n")
        with self.assertRaises(RuntimeError) as ctx:
            improvement_runner.build_report(sub)
        self.assertIn("backtest", str(ctx.exception))

    def test_too_many_candidates_is_rejected_with_a_clear_error(self):
        big_space = ", ".join(f'"p{i}": [1, 2, 3]' for i in range(20))  # 60 candidates, over the 40 cap
        sub = self.write("submission.py", f'''
import pandas as pd
CYCLE_DAYS = 21
BASELINE_PARAMS = {{}}
SEARCH_SPACE = {{{big_space}}}
def backtest(params, start_shift=0):
    return pd.Series([1.0, 1.01], index=pd.bdate_range("2020-01-01", periods=2))
''')
        with self.assertRaises(RuntimeError) as ctx:
            improvement_runner.build_report(sub)
        self.assertIn("cap", str(ctx.exception))

    def test_real_small_search_finds_a_genuine_constructed_improvement(self):
        # A deterministic, rigged-but-real scenario: three sharp crash windows a vol filter can avoid.
        # This is the exact scenario that first exposed the screen's false-negative bug (see
        # improvement_runner.py's KNOWN LIMITATION note) -- kept here as the regression test for it,
        # against the real anchor_average/compare/clears_bar pipeline, not mocks.
        sub = self.write("submission.py", '''
import numpy as np, pandas as pd
CYCLE_DAYS = 21
n = 3000
idx = pd.bdate_range("2012-01-01", periods=n)
rng = np.random.default_rng(42)
rets = rng.normal(0.0004, 0.008, n)
for start in (500, 1400, 2300):
    rets[start:start + 15] = -0.03
prices = pd.Series(100.0 * np.exp(np.cumsum(rets)), index=idx)
vol = prices.pct_change().rolling(10).std()
BASELINE_PARAMS = {"vol_cap": 999.0}
SEARCH_SPACE = {"vol_cap": [0.10, 0.02, 0.015]}
def backtest(params, start_shift=0):
    px = prices.iloc[start_shift:]
    v = vol.iloc[start_shift:]
    dates = px.index[::CYCLE_DAYS]
    equity = [1.0]
    for i in range(len(dates) - 1):
        d0, d1 = dates[i], dates[i + 1]
        entry_vol = v.asof(d0)
        exposure = 0.0 if (pd.notna(entry_vol) and entry_vol > params["vol_cap"]) else 1.0
        r = px.loc[d1] / px.loc[d0] - 1
        equity.append(equity[-1] * (1 + exposure * r))
    return pd.Series(equity, index=dates)
''')
        report = improvement_runner.build_report(sub)
        self.assertIn("no cheap-screen step", report)  # 3 candidates, well under SKIP_SCREEN_BELOW
        self.assertIn("Confirmed improvements (1/3)", report)
        self.assertIn("vol_cap = 0.015", report)

    def test_a_value_equal_to_baseline_is_not_counted_as_a_candidate(self):
        # SEARCH_SPACE includes the baseline's own value for "n" -- that's not a real candidate, must be skipped
        sub = self.write("submission.py", GOOD_SUBMISSION.replace('"n": [5, 20]', '"n": [10, 20]'))
        report = improvement_runner.build_report(sub)
        self.assertIn("Candidates tested: 1", report)  # only n=20 is a real candidate; n=10 == baseline, skipped


if __name__ == "__main__":
    unittest.main()
