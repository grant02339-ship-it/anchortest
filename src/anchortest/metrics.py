"""Self-contained performance metrics: no scipy, no exotic deps -- just numpy + pandas.

Every backtest is sampled at whatever cadence the strategy actually rebalances at (often monthly, not daily),
so annualizing with a hardcoded 252 would overstate vol/Sharpe by 4-5x. `periods_per_year` reads the real
sampling frequency from the index instead of assuming one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def periods_per_year(index: pd.DatetimeIndex) -> float:
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2:
        return 252.0
    median_gap_days = np.median(np.diff(idx.values).astype("timedelta64[D]").astype(float))
    return 365.25 / median_gap_days if median_gap_days > 0 else 252.0


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    total_return = equity.iloc[-1] / equity.iloc[0]
    return total_return ** (1 / years) - 1 if total_return > 0 else -1.0


def annualized_vol(returns: pd.Series, ppy: float) -> float:
    return returns.std(ddof=1) * np.sqrt(ppy)


def sharpe_ratio(returns: pd.Series, ppy: float, risk_free_annual: float = 0.02) -> float:
    excess = returns - risk_free_annual / ppy
    vol = excess.std(ddof=1)
    if vol == 0 or np.isnan(vol):
        return 0.0
    return (excess.mean() / vol) * np.sqrt(ppy)


def max_drawdown(equity: pd.Series) -> float:
    """Negative fraction (e.g. -0.20 = a 20% drawdown). Shallower = LARGER (closer to zero). Every comparison
    in this library relies on that sign convention -- see compare.METRIC_DIRECTION."""
    running_max = equity.cummax()
    return (equity / running_max - 1).min()


def split_halves(equity: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Split into two contiguous, independently-renormalized halves -- does a result hold up in the more
    recent period, or was it carried by the first half?"""
    mid = len(equity) // 2
    first = equity.iloc[: mid + 1]
    second = equity.iloc[mid:]
    return first / first.iloc[0], second / second.iloc[0]


def summarize(equity: pd.Series, risk_free_annual: float = 0.02) -> dict:
    returns = equity.pct_change().dropna()
    ppy = periods_per_year(equity.index)
    return dict(
        cagr=cagr(equity),
        ann_vol=annualized_vol(returns, ppy),
        sharpe=sharpe_ratio(returns, ppy, risk_free_annual),
        max_drawdown=max_drawdown(equity),
        n_periods=len(equity),
        periods_per_year=round(ppy, 2),
    )
