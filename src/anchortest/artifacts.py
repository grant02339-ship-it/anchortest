"""Guard against a specific, real measurement artifact: blending phase-shifted backtest runs can inflate
Sharpe and shrink drawdown with NO real skill involved, and it looks exactly like a genuine diversification
win when you only look at the strategy.

What happened on a real project: averaging K "tranches" of one strategy, offset by cycle_days/K trading
days, by taking the mean of cycle-i's return across all K tranches, looked like a +27% Sharpe improvement and
several points of shallower drawdown. The catch: the SAME transform, applied to plain buy-and-hold (which
cannot have any real phase-dependent skill by construction), "improved" it by almost the same ratio -- 0.89 to
1.20 Sharpe. The blend was smoothing variance across offset windows, not reducing real risk; the engine only
marks equity at cycle boundaries, so the within-cycle noise that was actually being averaged away is invisible
unless you go looking for it. `check_blend_artifact` is that "go looking for it" step, made automatic: run
your blending function against a synthetic control where the true answer is "no real improvement is possible",
and see whether it reports one anyway.
"""
from __future__ import annotations

import statistics
from typing import Callable

import numpy as np
import pandas as pd

from .anchors import shifts_for
from .metrics import summarize


def make_control_curve(n: int = 3000, mu: float = 0.0006, sigma: float = 0.010, seed: int = 0) -> pd.Series:
    """A synthetic geometric-random-walk price series with no real phase-dependent structure at all -- by
    construction, no blend of its own phase-shifted copies can contain genuine, extractable skill."""
    rng = np.random.default_rng(seed)
    prices = 100.0 * np.exp(np.cumsum(rng.normal(mu, sigma, n)))
    return pd.Series(prices, index=pd.bdate_range("2000-01-01", periods=n))


def phase_runs(curve: pd.Series, cycle_days: int, n_anchors: int) -> dict[int, pd.Series]:
    """The control curve, marked (and independently renormalized to 1.0) at every phase of `cycle_days`,
    exactly like `anchortest.anchors.anchor_average` would sample a real strategy's own equity curve."""
    out = {}
    for shift in shifts_for(cycle_days, n_anchors):
        marked = curve.iloc[shift::cycle_days]
        out[shift] = marked / marked.iloc[0]
    return out


def check_blend_artifact(
    blend_fn: Callable[[list[pd.Series]], pd.Series],
    cycle_days: int = 25,
    n_anchors: int = 25,
    threshold: float = 1.15,
    seed: int = 0,
) -> dict:
    """Run `blend_fn` (your tranching / ensembling / phase-blending logic: takes a list of equity curves,
    returns one blended equity curve) against the phase-invariant control above. Returns a report dict;
    `result["suspect"]` is True if the blended Sharpe beat the mean single-phase Sharpe by more than
    `threshold`x -- a gain the control cannot possibly have earned honestly. Call this BEFORE trusting any
    real result `blend_fn` produces on an actual strategy, not after."""
    curve = make_control_curve(seed=seed)
    runs = phase_runs(curve, cycle_days, n_anchors)
    single_sharpes = [summarize(r)["sharpe"] for r in runs.values()]
    single_mean_sharpe = statistics.mean(single_sharpes)

    blended = blend_fn(list(runs.values()))
    blended_sharpe = summarize(blended)["sharpe"]

    ratio = blended_sharpe / single_mean_sharpe if single_mean_sharpe not in (0, None) else float("inf")
    return dict(
        single_mean_sharpe=single_mean_sharpe,
        blended_sharpe=blended_sharpe,
        ratio=ratio,
        threshold=threshold,
        suspect=ratio > threshold,
    )


def assert_no_blend_artifact(result: dict) -> None:
    """Raise if `check_blend_artifact`'s report is suspect. Kept as a separate call (rather than a
    `raise_on_suspect=True` flag) so you can inspect the report either way."""
    if result["suspect"]:
        raise ArtifactSuspected(
            f"blend_fn inflated the CONTROL's Sharpe {result['ratio']:.2f}x "
            f"({result['single_mean_sharpe']:.3f} -> {result['blended_sharpe']:.3f}) with NO real skill "
            "possible -- this is very likely a measurement artifact, not a genuine result."
        )


class ArtifactSuspected(AssertionError):
    pass
