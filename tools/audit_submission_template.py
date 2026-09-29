"""AnchorTest free-audit submission template.

Fill in CYCLE_DAYS, PARAMS, and backtest() below. Do not rename these three names -- tools/audit_runner.py
finds them by name. Do not import anything beyond numpy/pandas/anchortest/your own price-data access unless
you flag that clearly in your submission -- the reviewer runs this file as-is.

See examples/random_walk_example.py in this repo for a complete, runnable reference.
"""
import pandas as pd  # noqa: F401  (available to your backtest() below)

CYCLE_DAYS = 25   # your strategy's rebalance/cycle length, in trading days

PARAMS = {
    # whatever your own backtest() needs -- passed through to it unchanged.
    # "rebalance_days": 25,
    # "universe": ["SPY", ...],
}


def backtest(params, start_shift=0):
    """Return a pandas Series equity curve: DatetimeIndex, starting value 1.0.

    MUST drop the first `start_shift` rows of your underlying price data before computing anything --
    that's what lets anchor_average() test every phase of your cycle instead of just one. If your data
    loading doesn't support that, say so explicitly in your issue instead of faking it.
    """
    raise NotImplementedError("fill this in with your own backtest")
