"""Runs a submitted audit_submission.py through the standard checks and writes a report skeleton.

SAFETY -- read before running this on a stranger's submission:
  This EXECUTES the submitted file as Python code. It runs in a separate subprocess with a timeout, which
  contains a crash or a hang, but that is NOT a security sandbox: the code can still read/write files,
  make network calls, or do anything else your own user account can do while it runs. Read the submission
  yourself first, especially any import beyond numpy/pandas/anchortest. For anything you don't fully trust,
  run this inside a disposable virtualenv (or a container) instead of your normal environment.

What this automates: loading the submission, running anchor_average() (and compare()/clears_bar() if a
baseline is given), and formatting the numbers into a report with the mechanical findings pre-written.
What it does NOT automate, on purpose: reading the submitter's code for anything suspicious before you run
it, and the personal-judgment parts of the report (does this candidate actually make sense for their
strategy, anything unusual worth a comment). Those stay yours -- see the "Reviewer notes" section the
report leaves blank for you.

Usage:
    python tools/audit_runner.py path/to/submission.py --out report.md
    python tools/audit_runner.py path/to/submission.py --out report.md --baseline path/to/baseline_submission.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TIMEOUT_SECONDS = 300

_RUNNER_TEMPLATE = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("submission", {path!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for name in ("CYCLE_DAYS", "PARAMS", "backtest"):
    if not hasattr(mod, name):
        print("MISSING_NAME:" + name)
        sys.exit(1)

from anchortest import anchor_average
n_anchors = min(mod.CYCLE_DAYS, 25)
agg, per_anchor = anchor_average(mod.backtest, mod.PARAMS, cycle_days=mod.CYCLE_DAYS, n_anchors=n_anchors)
print("RESULT_JSON:" + json.dumps({{"aggregate": agg, "per_anchor": per_anchor}}, default=float))
"""


def _run_submission(path: Path) -> dict:
    """Loads and runs `path` in its own subprocess. Raises with the submission's own traceback on failure,
    rather than swallowing it -- a broken submission is information for the report, not something to hide."""
    code = _RUNNER_TEMPLATE.format(path=str(path.resolve()))
    try:
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"submission did not finish within {TIMEOUT_SECONDS}s -- either it's genuinely slow (a lot of "
            "anchors x a slow backtest) or something's hanging. Investigate before raising the timeout."
        )
    if proc.returncode != 0:
        missing = next((l for l in proc.stdout.splitlines() if l.startswith("MISSING_NAME:")), None)
        if missing:
            raise RuntimeError(f"submission is missing required name: {missing.split(':', 1)[1]}")
        raise RuntimeError(f"submission raised an error:\n{proc.stderr[-3000:]}")
    line = next(l for l in proc.stdout.splitlines() if l.startswith("RESULT_JSON:"))
    return json.loads(line[len("RESULT_JSON:"):])


def _findings(agg: dict) -> list[str]:
    """Mechanical, always-true-if-triggered observations -- NOT a substitute for reading the numbers
    yourself, but it catches the things this project's own history says are worth flagging every time."""
    notes = []
    spread = agg["mean_sharpe"] - agg["min_sharpe"]
    if agg["mean_sharpe"] and spread > 0.3 * abs(agg["mean_sharpe"]):
        notes.append(
            f"- **Wide phase spread**: mean Sharpe {agg['mean_sharpe']:.3f} vs worst-phase {agg['min_sharpe']:.3f}. "
            "A single-anchor backtest run on this strategy could plausibly have reported either number -- "
            "treat any ONE-run result you've seen for this strategy with real skepticism."
        )
    if agg["stdev_sharpe"] and agg["mean_sharpe"] and agg["stdev_sharpe"] > 0.5 * abs(agg["mean_sharpe"]):
        notes.append(
            f"- **High dispersion across phases** (stdev {agg['stdev_sharpe']:.3f} vs mean {agg['mean_sharpe']:.3f}): "
            "this strategy's result is unusually phase-dependent even by the standard this library assumes "
            "is already the norm."
        )
    if agg["mean_recent_half_sharpe"] < 0.5 * agg["mean_sharpe"] and agg["mean_sharpe"] > 0:
        notes.append(
            f"- **Recent-half Sharpe ({agg['mean_recent_half_sharpe']:.3f}) is well below the full-sample "
            f"mean ({agg['mean_sharpe']:.3f})**: whatever edge this shows, it looks weaker in the more "
            "recent data. Worth asking whether the edge is decaying."
        )
    if not notes:
        notes.append("- No mechanical red flags from this pass (that is not the same as a clean bill of health -- see the reviewer notes below).")
    return notes


def build_report(submission: Path, baseline: Path | None) -> str:
    result = _run_submission(submission)
    agg = result["aggregate"]

    lines = [
        f"# AnchorTest report — {submission.name}",
        "",
        "This is a review of your validation PROCESS, not investment advice, not a recommendation to trade "
        "anything, and not a claim that this strategy is profitable.",
        "",
        "## Anchor-averaged results",
        f"- Anchors: {agg['n_anchors']}",
        f"- Sharpe — mean **{agg['mean_sharpe']:.3f}**, median {agg['median_sharpe']:.3f}, min {agg['min_sharpe']:.3f}, stdev {agg['stdev_sharpe']:.3f}",
        f"- CAGR (mean): {agg['mean_cagr']*100:.2f}%",
        f"- Drawdown — mean {agg['mean_dd']*100:.2f}%, worst {agg['worst_dd']*100:.2f}%",
        f"- Recent-half Sharpe (mean): {agg['mean_recent_half_sharpe']:.3f}",
        "",
        "## Automated findings",
        *_findings(agg),
        "",
    ]

    if baseline is not None:
        from anchortest import clears_bar, compare  # local import: keep the no-baseline path dependency-light

        base_result = _run_submission(baseline)
        delta = compare(base_result["aggregate"], agg)
        passed = clears_bar(delta)
        lines += [
            "## Comparison to your baseline",
            f"- Clears the strict promotion bar (every tracked metric improved)? **{'YES' if passed else 'no'}**",
            "- Per-metric delta (positive = candidate improved on baseline, direction already corrected for drawdown's sign):",
            "```",
            json.dumps({k: round(v, 4) for k, v in delta.items()}, indent=2),
            "```",
            "",
        ]

    lines += [
        "## Reviewer notes",
        "_(fill in before sending -- does this candidate make sense for what they're actually trying to do,"
        " anything unusual in the submission worth a comment, any caveats about their data/universe)_",
        "",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("submission", type=Path, help="path to the submitter's audit_submission.py")
    parser.add_argument("--baseline", type=Path, default=None, help="optional baseline submission, for a compare()/clears_bar() section")
    parser.add_argument("--out", type=Path, required=True, help="where to write the markdown report")
    args = parser.parse_args()

    report = build_report(args.submission, args.baseline)
    args.out.write_text(report)
    print(f"wrote {args.out} ({len(report)} chars) -- open it, fill in Reviewer notes, then send it.")
