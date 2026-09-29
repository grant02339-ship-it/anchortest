"""AnchorTest Improvement Search submission template.

Fill in CYCLE_DAYS, BASELINE_PARAMS, SEARCH_SPACE, and backtest() below -- do not rename these four names,
tools/improvement_runner.py finds them by name. See examples/random_walk_example.py for a runnable
backtest() reference, and README.md's "Improvement Search" section for how the search itself works.
"""
import pandas as pd  # noqa: F401  (available to your backtest() below)

CYCLE_DAYS = 25   # your strategy's rebalance/cycle length, in trading days

BASELINE_PARAMS = {
    # your current accepted parameters -- the thing every candidate is compared against.
    # "fast_days": 10, "slow_days": 40,
}

SEARCH_SPACE = {
    # one entry per parameter you want searched, each a list of alternative values to try.
    # ONE parameter changes at a time from BASELINE_PARAMS -- never several at once, so a result can
    # always be attributed to the specific change that produced it.
    # "fast_days": [5, 8, 15, 20],
    # "slow_days": [30, 50, 60],
}


def backtest(params, start_shift=0):
    """Return a pandas Series equity curve: DatetimeIndex, starting value 1.0.

    MUST drop the first `start_shift` rows of your underlying price data before computing anything.
    """
    raise NotImplementedError("fill this in with your own backtest")
