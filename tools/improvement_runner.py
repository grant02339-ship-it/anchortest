"""Runs a submitted improvement_submission.py: searches a declared parameter space and reports only the
candidates that survive this project's own two-stage discipline -- a cheap screen, then full validation --
instead of trusting a single pass.

Why two stages, not one: this exact pattern (a thin lead on a cheap search-set screen that does not survive
full validation) is the single most repeated finding in the project this library's checks were extracted
from -- six separate documented instances. A search tool that only screens, and reports a screen-passer as
"found", would reproduce that mistake automatically. So: SEARCH_N_ANCHORS (cheap) screens every candidate in
the declared space; only screen-passers get FULL_N_ANCHORS (expensive) confirmation, and only full-anchor
passers are reported as a genuine result. Screen-passers that fail full validation are still reported --
that disagreement is itself the finding this tool exists to catch.

KNOWN LIMITATION, discovered while testing this exact file: the screen can also produce a false NEGATIVE --
a candidate that genuinely passes full validation can still fail the cheaper screen, because the screen
samples fewer phases and a real effect can land as an exact tie (delta == 0, which fails the strict "> 0"
bar) on one of them purely by which phases happen to be sampled. Confirmed with a constructed example: a
candidate whose 25-anchor full-validation delta improved all six tracked metrics failed the 10-anchor
screen because min_sharpe's delta was exactly 0.0 on that smaller phase subset. The screen is a compute-
saving heuristic, not a strictly more-conservative filter -- it can miss real signal, not just admit noise.
Mitigation below: skip the screen entirely for small search spaces, where there's no compute reason to risk it.

One parameter changes at a time from BASELINE_PARAMS, never several -- so a result can always be attributed.

SAFETY: same as audit_runner.py -- this EXECUTES the submission as Python code, in a subprocess with a
timeout, which is NOT a full sandbox. Read the submission yourself first.

Usage:
    python tools/improvement_runner.py path/to/submission.py --out report.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SEARCH_N_ANCHORS = 10     # cheap screen, matches this project's own search-set convention
FULL_N_ANCHORS = 25       # expensive confirmation before anything is trusted
MAX_CANDIDATES = 40       # bounds total compute -- shrink your SEARCH_SPACE if you hit this
SKIP_SCREEN_BELOW = 15    # below this many candidates, run full validation on everything directly --
                          # see the KNOWN LIMITATION note above for why the screen isn't free to use here
TIMEOUT_SECONDS = 900     # the whole search runs in ONE subprocess call, not one per candidate

_RUNNER_TEMPLATE = """
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("submission", {path!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for name in ("CYCLE_DAYS", "BASELINE_PARAMS", "SEARCH_SPACE", "backtest"):
    if not hasattr(mod, name):
        print("MISSING_NAME:" + name)
        sys.exit(1)

candidates = [(p, v) for p, vals in mod.SEARCH_SPACE.items() for v in vals
              if v != mod.BASELINE_PARAMS.get(p)]
if len(candidates) > {max_candidates}:
    print(f"TOO_MANY_CANDIDATES:{{len(candidates)}}")
    sys.exit(1)

from anchortest import anchor_average, compare, clears_bar

skip_screen = len(candidates) <= {skip_screen_below}

baseline_full, _ = anchor_average(mod.backtest, mod.BASELINE_PARAMS, cycle_days=mod.CYCLE_DAYS, n_anchors={full_anchors})
baseline_screen = baseline_full if skip_screen else \\
    anchor_average(mod.backtest, mod.BASELINE_PARAMS, cycle_days=mod.CYCLE_DAYS, n_anchors={search_anchors})[0]

results = []
for param, value in candidates:
    cand_params = dict(mod.BASELINE_PARAMS)
    cand_params[param] = value

    if skip_screen:
        # Small search space: no compute reason to risk the screen's false-negative failure mode (see the
        # KNOWN LIMITATION note in this file) -- go straight to full validation on every candidate.
        full_agg, _ = anchor_average(mod.backtest, cand_params, cycle_days=mod.CYCLE_DAYS, n_anchors={full_anchors})
        full_delta = compare(baseline_full, full_agg)
        results.append({{"param": param, "value": value, "screen_skipped": True,
                        "screen_delta": full_delta, "screen_pass": clears_bar(full_delta),
                        "full_delta": full_delta, "full_pass": clears_bar(full_delta)}})
        continue

    screen_agg, _ = anchor_average(mod.backtest, cand_params, cycle_days=mod.CYCLE_DAYS, n_anchors={search_anchors})
    screen_delta = compare(baseline_screen, screen_agg)
    row = {{"param": param, "value": value, "screen_skipped": False, "screen_delta": screen_delta,
           "screen_pass": clears_bar(screen_delta), "full_delta": None, "full_pass": None}}
    if row["screen_pass"]:
        full_agg, _ = anchor_average(mod.backtest, cand_params, cycle_days=mod.CYCLE_DAYS, n_anchors={full_anchors})
        full_delta = compare(baseline_full, full_agg)
        row["full_delta"] = full_delta
        row["full_pass"] = clears_bar(full_delta)
    results.append(row)

print("RESULT_JSON:" + json.dumps({{"baseline_screen": baseline_screen, "baseline_full": baseline_full,
                                    "n_candidates": len(candidates), "screen_skipped": skip_screen,
                                    "results": results}}, default=float))
"""


def _run_search(path: Path) -> dict:
    code = _RUNNER_TEMPLATE.format(path=str(path.resolve()), max_candidates=MAX_CANDIDATES,
                                    search_anchors=SEARCH_N_ANCHORS, full_anchors=FULL_N_ANCHORS,
                                    skip_screen_below=SKIP_SCREEN_BELOW)
    try:
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"search did not finish within {TIMEOUT_SECONDS}s -- shrink SEARCH_SPACE, or your backtest is "
            "slow enough that this needs a longer budget (edit TIMEOUT_SECONDS if you're running this yourself)."
        )
    if proc.returncode != 0:
        missing = next((l for l in proc.stdout.splitlines() if l.startswith("MISSING_NAME:")), None)
        too_many = next((l for l in proc.stdout.splitlines() if l.startswith("TOO_MANY_CANDIDATES:")), None)
        if missing:
            raise RuntimeError(f"submission is missing required name: {missing.split(':', 1)[1]}")
        if too_many:
            n = too_many.split(":", 1)[1]
            raise RuntimeError(f"SEARCH_SPACE has {n} candidates, more than the {MAX_CANDIDATES} cap -- shrink it")
        raise RuntimeError(f"submission raised an error:\n{proc.stderr[-3000:]}")
    line = next(l for l in proc.stdout.splitlines() if l.startswith("RESULT_JSON:"))
    return json.loads(line[len("RESULT_JSON:"):])


def build_report(submission: Path) -> str:
    result = _run_search(submission)
    base = result["baseline_full"]
    results = result["results"]
    screen_passed = [r for r in results if r["screen_pass"]]
    confirmed = [r for r in screen_passed if r["full_pass"]]
    screen_only = [r for r in screen_passed if not r["full_pass"]]

    lines = [
        f"# AnchorTest Improvement Search report — {submission.name}",
        "",
        "This searches your declared parameter space and reports what clears this project's strict bar --",
        "it is not investment advice, and a result clearing this bar is a hypothesis worth a closer look,",
        "not a confirmed edge. Real-market transfer is a separate question this tool cannot answer.",
        "",
        f"Baseline ({FULL_N_ANCHORS} anchors): mean Sharpe **{base['mean_sharpe']:.3f}**, "
        f"median {base['median_sharpe']:.3f}, min {base['min_sharpe']:.3f}, "
        f"CAGR {base['mean_cagr']*100:.2f}%, drawdown {base['mean_dd']*100:.2f}%",
        f"Candidates tested: {result['n_candidates']} (1 parameter changed at a time from baseline)",
        (f"Search space small enough ({result['n_candidates']} <= {SKIP_SCREEN_BELOW}) to run full "
         f"{FULL_N_ANCHORS}-anchor validation on every candidate directly -- no cheap-screen step, no risk "
         "of the screen's false-negative failure mode."
         if result.get("screen_skipped") else
         f"Screened at {SEARCH_N_ANCHORS} anchors first; only screen-passers got full "
         f"{FULL_N_ANCHORS}-anchor confirmation."),
        "",
    ]

    if confirmed:
        confirm_note = (f"Cleared the strict bar on full {FULL_N_ANCHORS}-anchor validation:" if result.get("screen_skipped")
                        else "Cleared the strict bar at BOTH the cheap screen and full validation:")
        lines += [f"## Confirmed improvements ({len(confirmed)}/{result['n_candidates']})", confirm_note, ""]
        for r in confirmed:
            d = r["full_delta"]
            lines.append(f"- `{r['param']} = {r['value']}`: Sharpe {d['mean_sharpe']:+.3f}, "
                          f"CAGR {d['mean_cagr']*100:+.2f}pp, drawdown {d['mean_dd']*100:+.2f}pp "
                          f"(positive = shallower/better)")
        lines.append("")
    else:
        lines += ["## Confirmed improvements: none",
                   "No candidate in the declared search space cleared the strict bar at full validation. "
                   "That is a real, informative result, not a failure to search hard enough -- see the "
                   "project's own history of exhausted single-parameter searches for company.", ""]

    if screen_only:
        lines += [f"## Screen-passed but failed full validation ({len(screen_only)})",
                   "These looked like a win on the cheap 10-anchor screen and did NOT hold up at "
                   f"{FULL_N_ANCHORS} anchors -- exactly the pattern this tool exists to catch before you trust it:",
                   ""]
        for r in screen_only:
            lines.append(f"- `{r['param']} = {r['value']}`: screen Sharpe {r['screen_delta']['mean_sharpe']:+.3f}, "
                          f"full Sharpe {r['full_delta']['mean_sharpe']:+.3f}")
        lines.append("")

    lines += [
        "## Reviewer notes",
        "_(fill in before sending -- do the confirmed candidates make structural sense, is this parameter "
        "known to be risky for local-to-real transfer, anything the search space missed)_",
        "",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("submission", type=Path, help="path to the submitter's improvement_submission.py")
    parser.add_argument("--out", type=Path, required=True, help="where to write the markdown report")
    args = parser.parse_args()

    report = build_report(args.submission)
    args.out.write_text(report)
    print(f"wrote {args.out} ({len(report)} chars) -- open it, fill in Reviewer notes, then send it.")
