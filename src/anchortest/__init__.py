"""AnchorTest: stop trusting a single backtest run.

Three checks, each built to catch a specific real mistake:
  - anchor_average / shifts_for  -- average over every phase of your own rebalance cycle, not one lucky start date.
  - compare / clears_bar         -- compare two results with the drawdown sign convention fixed once, here.
  - check_blend_artifact         -- catch a blending/tranching result that only looks good on a phase-invariant control.
  - run_mutation_suite           -- prove your OWN test suite would catch a bug, instead of hoping it would.

See README.md for the real incidents each of these generalizes from.
"""
from .anchors import anchor_average, shifts_for
from .artifacts import ArtifactSuspected, assert_no_blend_artifact, check_blend_artifact, make_control_curve, phase_runs
from .compare import DEFAULT_BAR, METRIC_DIRECTION, clears_bar, compare
from .metrics import cagr, max_drawdown, periods_per_year, sharpe_ratio, split_halves, summarize
from .mutation import Mutation, assert_all_caught, run_mutation_suite

__version__ = "0.1.0"

__all__ = [
    "anchor_average", "shifts_for",
    "compare", "clears_bar", "DEFAULT_BAR", "METRIC_DIRECTION",
    "check_blend_artifact", "assert_no_blend_artifact", "make_control_curve", "phase_runs", "ArtifactSuspected",
    "Mutation", "run_mutation_suite", "assert_all_caught",
    "summarize", "cagr", "sharpe_ratio", "max_drawdown", "split_halves", "periods_per_year",
    "__version__",
]
