import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

spec = importlib.util.spec_from_file_location("audit_runner", os.path.join(ROOT, "tools", "audit_runner.py"))
audit_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_runner)

GOOD_SUBMISSION = '''
import numpy as np, pandas as pd
CYCLE_DAYS = 21
_RNG = np.random.default_rng(1)
_PRICES = pd.Series(100.0 * np.exp(np.cumsum(_RNG.normal(0.0004, 0.01, 800))), index=pd.bdate_range("2015-01-01", periods=800))
PARAMS = {}
def backtest(params, start_shift=0):
    prices = _PRICES.iloc[start_shift:]
    marked = prices.iloc[::CYCLE_DAYS]
    return marked / marked.iloc[0]
'''


class TestAuditRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, content):
        p = Path(self.tmp.name) / name
        p.write_text(content)
        return p

    def test_good_submission_produces_a_report_with_headline_numbers(self):
        sub = self.write("submission.py", GOOD_SUBMISSION)
        report = audit_runner.build_report(sub, None)
        self.assertIn("## Anchor-averaged results", report)
        self.assertIn("Sharpe — mean", report)
        self.assertIn("## Reviewer notes", report)
        self.assertNotIn("## Comparison to your baseline", report)

    def test_baseline_comparison_section_appears_when_requested(self):
        sub = self.write("submission.py", GOOD_SUBMISSION)
        base = self.write("baseline.py", GOOD_SUBMISSION)  # identical -- delta should be all zero, not a pass
        report = audit_runner.build_report(sub, base)
        self.assertIn("## Comparison to your baseline", report)
        self.assertIn("**no**", report)  # clears_bar on an IDENTICAL candidate must be False -- ties are not promotions

    def test_missing_required_name_raises_a_clear_error(self):
        sub = self.write("submission.py", "CYCLE_DAYS = 21\nPARAMS = {}\n")  # no backtest()
        with self.assertRaises(RuntimeError) as ctx:
            audit_runner.build_report(sub, None)
        self.assertIn("backtest", str(ctx.exception))

    def test_a_submission_that_raises_surfaces_its_own_traceback(self):
        sub = self.write("submission.py", "CYCLE_DAYS=21\nPARAMS={}\ndef backtest(params, start_shift=0):\n    raise ValueError('boom')\n")
        with self.assertRaises(RuntimeError) as ctx:
            audit_runner.build_report(sub, None)
        self.assertIn("boom", str(ctx.exception))

    def test_a_hanging_submission_times_out_instead_of_blocking_forever(self):
        sub = self.write("submission.py", "import time\nCYCLE_DAYS=21\nPARAMS={}\ndef backtest(params, start_shift=0):\n    time.sleep(30)\n")
        old_timeout = audit_runner.TIMEOUT_SECONDS
        audit_runner.TIMEOUT_SECONDS = 2
        try:
            with self.assertRaises(RuntimeError) as ctx:
                audit_runner.build_report(sub, None)
            self.assertIn("did not finish within", str(ctx.exception))
        finally:
            audit_runner.TIMEOUT_SECONDS = old_timeout

    def test_wide_phase_spread_is_flagged(self):
        # a strategy that's flat except one huge spike on one specific phase -> guaranteed wide min-vs-mean spread
        sub = self.write("submission.py", '''
import numpy as np, pandas as pd
CYCLE_DAYS = 5
_PRICES = pd.Series(np.concatenate([[100.0]*3, [100.0*1.5]] + [[100.0]] * 400), index=pd.bdate_range("2015-01-01", periods=404))
PARAMS = {}
def backtest(params, start_shift=0):
    prices = _PRICES.iloc[start_shift:]
    marked = prices.iloc[::CYCLE_DAYS]
    return marked / marked.iloc[0]
''')
        report = audit_runner.build_report(sub, None)
        self.assertIn("Wide phase spread", report)


if __name__ == "__main__":
    unittest.main()
