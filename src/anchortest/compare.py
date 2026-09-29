"""Compare two anchor_average() results without the sign-convention trap that has burned real projects.

`max_drawdown` and `worst_dd` are stored NEGATIVE (a shallower, better drawdown is a LARGER number, closer to
zero). A comparison written the obvious way -- `candidate_dd <= baseline_dd` -- silently treats a DEEPER,
WORSE drawdown as a pass, because -0.30 <= -0.20 is true. On one real project this exact bug shipped three
false "confirmed" candidates before it was caught. `compare()` gets the direction right once, here, so no
caller has to remember it.
"""
from __future__ import annotations

METRIC_DIRECTION: dict[str, int] = {
    "mean_sharpe": 1,
    "median_sharpe": 1,
    "min_sharpe": 1,
    "mean_cagr": 1,
    "mean_dd": 1,          # stored negative; candidate - baseline > 0 already means "shallower, better"
    "worst_dd": 1,         # same
    "mean_recent_half_sharpe": 1,
    "stdev_sharpe": -1,    # lower dispersion is better, so this one has to flip
}

# The strict promotion bar: a candidate counts only if EVERY one of these improves. Central-tendency Sharpe
# alone is not enough -- a candidate that improves mean/median Sharpe while its minimum-case Sharpe or its
# recent-half Sharpe gets worse has, in real testing, been about a coin flip, not a real improvement.
DEFAULT_BAR: tuple[str, ...] = (
    "mean_sharpe", "median_sharpe", "min_sharpe", "mean_cagr", "mean_dd", "mean_recent_half_sharpe",
)


def compare(baseline: dict, candidate: dict, keys: tuple[str, ...] = DEFAULT_BAR) -> dict:
    """`{metric: delta}` where a POSITIVE delta always means "candidate improved on baseline", for every
    metric, regardless of that metric's own storage sign convention (see METRIC_DIRECTION)."""
    out = {}
    for k in keys:
        if k in baseline and k in candidate:
            direction = METRIC_DIRECTION.get(k, 1)
            out[k] = direction * (candidate[k] - baseline[k])
    return out


def clears_bar(delta: dict, keys: tuple[str, ...] = DEFAULT_BAR) -> bool:
    """True only if EVERY tracked metric strictly improved. An identical candidate (delta == 0 everywhere)
    does NOT pass -- ties are not promotions -- and improving 5 of 6 metrics does not pass either."""
    return all(delta.get(k, -1.0) > 0 for k in keys)
