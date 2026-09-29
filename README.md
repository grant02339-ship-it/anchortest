# AnchorTest

**Stop trusting a single backtest run.**

Most backtests report one run's Sharpe ratio, on one start date, over one universe. That number is a sample
of one. AnchorTest is a small, dependency-light Python library (`numpy` + `pandas`, nothing else) that runs
three specific checks that have each caught a real, shipped bug in real trading-strategy research:

1. **Anchor-average**, instead of trusting one lucky start date.
2. **Compare candidates correctly**, with the drawdown sign-convention trap fixed once, in one place.
3. **Catch a blending/tranching artifact** before it becomes your headline result.

Plus a small, general-purpose **mutation-testing helper**, because a green test suite doesn't tell you it
would have caught the bug you didn't think to write a test for.

## Why this exists

Three real incidents from **options-strategy-research**, my ongoing systematic options-strategy backtest
research project (backtest-only, no live trading — not published), each of which shipped before it was
caught:

> **1. A single-anchor backtest is a sample of one.** A strategy's backtest struck rebalance dates as a
> fixed stride starting from wherever the data happened to begin. Sweeping every possible phase of a 30-day
> cycle found Sharpe ranging from 0.35 to 1.46 -- and the ONE phase every earlier test had used happened to
> land on literally the best of all 30. Every parameter decision made before this was caught had been
> validated against the luckiest possible number, not a representative one.

> **2. A sign-convention bug that shipped three false wins.** Drawdown is naturally stored as a negative
> number (a shallower, better drawdown is closer to zero). A comparison written the obvious way --
> `candidate_dd <= baseline_dd` -- silently treats a DEEPER, WORSE drawdown as a pass, because `-0.30 <=
> -0.20` is true. Three candidates were reported as "confirmed improvements" on this exact bug before a
> manual re-check caught it.

> **3. A blending result that was pure measurement artifact.** Averaging several phase-shifted copies of a
> strategy (offset "tranches") by taking the mean of cycle-i's return across all of them looked like a
> genuine diversification win: Sharpe up 27%, drawdown several points shallower. The check that caught it:
> running the IDENTICAL blend on plain buy-and-hold, which cannot have any real phase-dependent skill by
> construction. Buy-and-hold "improved" by almost the same ratio (Sharpe 0.89 -> 1.20). The blend was
> smoothing variance across offset windows, not reducing real risk -- and it would have shipped as the
> project's best result if that one control hadn't been run.

None of these are exotic mistakes. They're the kind of thing that survives code review, survives a
reasonable test suite, and looks exactly like a genuine result until someone runs the specific control that
exposes it. AnchorTest packages those controls so you run them by default, not by luck.

## Install

```bash
pip install anchortest    # once published -- see below
# or, for now:
pip install -e .
```

Requires Python 3.9+, `numpy`, `pandas`. No `scipy`, no broker SDK, no options-pricing library -- this works
on any equity-curve-producing backtest, in any asset class, options or not.

## Get your strategy audited

I'll run these checks against YOUR backtest and send back a written report: what passed, what didn't, and
why. **Free for the first 10 people** (best-effort, no guaranteed turnaround) — your submission must already
be shaped like `tools/audit_submission_template.py` (see `examples/random_walk_example.py` for a full
reference), then [open an audit-request issue](https://github.com/grant02339-ship-it/anchortest/issues/new?template=audit-request.yml).
Once your submission's in that shape, `python tools/audit_runner.py your_submission.py --out report.md` runs
it and drafts most of the report automatically. **Full Audit ($249, 7 business days):** a
held-out/out-of-sample test designed for your specific strategy, plus a 30-minute call — for more depth, or
if you're not among the first 10.
This is a review of your validation process, not investment advice and not a claim that any strategy is
profitable.

## Quickstart

```python
from anchortest import anchor_average, compare, clears_bar

def backtest(params, start_shift=0):
    """Your own backtest. MUST accept start_shift and drop that many rows of your underlying
    price data before computing anything -- see examples/random_walk_example.py for a full one."""
    ...  # returns a pandas Series equity curve, indexed by date, starting at 1.0

baseline, _ = anchor_average(backtest, baseline_params, cycle_days=25, n_anchors=25)
candidate, _ = anchor_average(backtest, candidate_params, cycle_days=25, n_anchors=25)

delta = compare(baseline, candidate)
if clears_bar(delta):
    print("candidate improves EVERY tracked metric -- worth a closer look")
else:
    print("not a promotion:", delta)
```

Run `python examples/random_walk_example.py` for a runnable end-to-end demo, including a case where the
single-anchor (`shift=0`) result actively disagrees with the honest average.

## What's in the box

| function | catches |
|---|---|
| `anchor_average(backtest_fn, params, cycle_days, n_anchors=25)` | trusting one lucky start date |
| `shifts_for(cycle_days, n_anchors)` | the phase-shift arithmetic itself (deduplicates correctly when `n_anchors > cycle_days`) |
| `compare(baseline, candidate)` / `clears_bar(delta)` | the drawdown sign-convention trap; "5 of 6 metrics improved" being reported as a win |
| `check_blend_artifact(blend_fn)` / `assert_no_blend_artifact(result)` | a tranching/blending function that inflates Sharpe with no real skill |
| `run_mutation_suite(mutations, test_command)` / `assert_all_caught(results)` | a test suite that would not actually have caught the bug you just fixed |

Each function's docstring explains the real failure mode it generalizes from -- read them; the "why" is not
padding.

## Philosophy

- **Compare against a control before you trust a transform.** If you can construct a version of your data
  where the "true" answer is known (a phase-invariant control, a random baseline, a null model), run your
  method against it before running it on the real thing. `check_blend_artifact` is one instance of this
  principle; it generalizes further than this library currently automates.
- **The strict bar exists because partial improvement has been about a coin flip.** A candidate that
  improves mean Sharpe while its minimum-case Sharpe or recent-half Sharpe gets worse is not free money --
  in real testing, that exact pattern has predicted a real-world regression as often as an improvement.
  `clears_bar`'s default requires every tracked metric to improve, deliberately.
- **A green test suite is a claim, not a fact, until you've tried to falsify it.** `run_mutation_suite` is
  the smallest possible version of "did this test actually assert anything, or did it just not crash."

## What this is not

- Not a backtesting engine. Bring your own `backtest_fn`; AnchorTest only tells you how much to trust its
  output.
- Not investment advice, and not a signal that any particular strategy works. It's a set of falsification
  checks -- what survives them still needs real out-of-sample and (if it trades real markets) real
  historical-data testing before anyone should trust it with money.
- Not a substitute for testing out-of-sample, on assets or time periods you didn't tune on. That discipline
  matters at least as much as anything in this library automates; there's no shortcut for it here yet.

## Contributing

Issues and PRs welcome, especially: additional artifact-detection controls, a walk-forward /
purged-cross-validation helper, and real-world "this caught a bug" case studies to add to the list above.

## License

MIT. See `LICENSE`.
