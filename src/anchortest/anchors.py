"""Anchor-averaging: never trust a single backtest run.

A backtest that strikes rebalance dates as a fixed stride (every N-th trading day, starting from wherever
your data happens to start) depends on exactly where that stride lands. Shift the start by even one day and
you get a genuinely different, non-overlapping simulation -- not measurement noise around a stable number.
On one real strategy, sweeping every phase of a 30-day cycle found Sharpe ranging 0.35-1.46, with the single
phase every earlier test had used landing at literally the best of all 30. This module makes averaging across
every phase the default, so that mistake can't repeat silently.
"""
from __future__ import annotations

import statistics
from typing import Callable

import pandas as pd

from .metrics import split_halves, summarize


def shifts_for(cycle_days: int, n_anchors: int) -> list[int]:
    """`n_anchors` evenly-spaced phase shifts of the strategy's own cycle length. Requesting more anchors
    than `cycle_days` just returns every integer shift once (deduplicated) -- there is no such thing as a
    26th distinct phase of a 25-day cycle."""
    if cycle_days <= 0:
        raise ValueError("cycle_days must be positive")
    return sorted({int(i * cycle_days / n_anchors) for i in range(n_anchors)})


def anchor_average(
    backtest_fn: Callable[..., pd.Series],
    params: dict,
    cycle_days: int,
    n_anchors: int = 25,
    risk_free_annual: float = 0.02,
) -> tuple[dict, list[dict]]:
    """Run `backtest_fn(params, start_shift=<int>)` at every phase shift of the strategy's own cycle and
    aggregate. `backtest_fn` must return a `pd.Series` equity curve (DatetimeIndex, starting at 1.0), and
    must itself apply `start_shift` by dropping the first `start_shift` rows of its underlying price data
    before computing anything -- shifting where the WHOLE cycle grid falls, not just the first trade.

    Returns `(aggregate, per_anchor)`. `aggregate` has `mean_sharpe`, `median_sharpe`, `min_sharpe`,
    `stdev_sharpe`, `mean_cagr`, `mean_dd`, `worst_dd`, `mean_recent_half_sharpe`, `n_anchors`. Compare two
    aggregates with `compare()`, not by hand -- drawdown's sign convention has a documented trap.
    """
    per_anchor = []
    for shift in shifts_for(cycle_days, n_anchors):
        equity = backtest_fn(params, start_shift=shift)
        m = summarize(equity, risk_free_annual)
        _, recent_half = split_halves(equity)
        m_rh = summarize(recent_half, risk_free_annual)
        per_anchor.append({"shift": shift, **m, "recent_half_sharpe": m_rh["sharpe"]})

    sharpes = [a["sharpe"] for a in per_anchor]
    cagrs = [a["cagr"] for a in per_anchor]
    dds = [a["max_drawdown"] for a in per_anchor]
    rh_sharpes = [a["recent_half_sharpe"] for a in per_anchor]

    aggregate = dict(
        n_anchors=len(per_anchor),
        mean_sharpe=statistics.mean(sharpes),
        median_sharpe=statistics.median(sharpes),
        min_sharpe=min(sharpes),
        stdev_sharpe=statistics.stdev(sharpes) if len(sharpes) > 1 else 0.0,
        mean_cagr=statistics.mean(cagrs),
        mean_dd=statistics.mean(dds),
        worst_dd=min(dds),
        mean_recent_half_sharpe=statistics.mean(rh_sharpes),
    )
    return aggregate, per_anchor
