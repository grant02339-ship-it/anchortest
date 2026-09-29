"""Runnable end-to-end demo.

A toy "strategy": a 5-day moving-average crossover on a synthetic random walk, rebalanced every
`rebalance_days`. It has NO real edge (the walk is pure noise) -- which is exactly the point: this example
shows anchor_average() correctly reporting that, even when the single lucky anchor (shift=0) looks good.

Run: python examples/random_walk_example.py
"""
import numpy as np
import pandas as pd

from anchortest import anchor_average, compare, clears_bar

RNG = np.random.default_rng(42)
N_DAYS = 4000
DAILY_RETURNS = pd.Series(RNG.normal(0.0003, 0.012, N_DAYS), index=pd.bdate_range("2010-01-01", periods=N_DAYS))
PRICES = 100.0 * np.exp(DAILY_RETURNS.cumsum())


def crossover_backtest(params, start_shift=0):
    """A toy strategy: go long only when the fast MA is above the slow MA, checked every rebalance_days.
    Flat (0% return) otherwise. No transaction costs, for simplicity -- add your own before trusting this
    shape on a real strategy."""
    prices = PRICES.iloc[start_shift:]
    fast = prices.rolling(params["fast_days"]).mean()
    slow = prices.rolling(params["slow_days"]).mean()
    signal = (fast > slow).astype(float)

    check_dates = prices.index[:: params["rebalance_days"]]
    equity = [1.0]
    for i in range(len(check_dates) - 1):
        d0, d1 = check_dates[i], check_dates[i + 1]
        period_return = prices.loc[d1] / prices.loc[d0] - 1
        equity.append(equity[-1] * (1 + signal.loc[d0] * period_return))
    return pd.Series(equity, index=check_dates)


if __name__ == "__main__":
    params = {"fast_days": 10, "slow_days": 40, "rebalance_days": 21}

    aggregate, per_anchor = anchor_average(crossover_backtest, params, cycle_days=21, n_anchors=21)

    shift0 = next(a for a in per_anchor if a["shift"] == 0)
    print(f"Single anchor (shift=0):  Sharpe {shift0['sharpe']:.3f}  CAGR {shift0['cagr']*100:.2f}%")
    print(f"Anchor-averaged (n={aggregate['n_anchors']}): mean Sharpe {aggregate['mean_sharpe']:.3f}  "
          f"median {aggregate['median_sharpe']:.3f}  min {aggregate['min_sharpe']:.3f}  "
          f"stdev {aggregate['stdev_sharpe']:.3f}")
    print("-> if these two lines disagree by more than a rounding error, shift=0 was never trustworthy on"
          " its own -- rerun this script with a different RNG seed above and watch the single-anchor number"
          " move around while the average stays roughly where a strategy with no real edge belongs (Sharpe"
          " near 0).")

    baseline_params = {"fast_days": 10, "slow_days": 40, "rebalance_days": 21}
    candidate_params = {"fast_days": 5, "slow_days": 40, "rebalance_days": 21}
    baseline, _ = anchor_average(crossover_backtest, baseline_params, cycle_days=21, n_anchors=21)
    candidate, _ = anchor_average(crossover_backtest, candidate_params, cycle_days=21, n_anchors=21)
    delta = compare(baseline, candidate)
    print(f"\nbaseline (fast=10) vs candidate (fast=5): {delta}")
    print("clears the strict bar (every metric improved)?", clears_bar(delta))
