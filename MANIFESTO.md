# Your backtest is lying to you, and it's not the bug you're looking for

Every backtester knows to check for lookahead bias. Fewer check for the three things below — because each
one produces a result that looks completely honest. The code runs. The number is real. The chart is
plausible. And it's still wrong, in a way that a normal test suite and a normal code review will not catch.

These are three real incidents from one live quant-research project. All three shipped — became "confirmed"
results the project acted on — before something caught them.

## 1. The single-anchor illusion

A covered-call strategy rebalanced every 30 trading days. Its backtest picked rebalance dates the obvious
way: every 30th day, starting from the first day of data. Nobody thought twice about that "first day of
data" choice — it's just where the data starts.

Except it isn't a neutral choice. It's a phase. Shift the starting point by a single trading day and you get
a genuinely different, non-overlapping sequence of ~120 entry and exit dates across a decade of data — not
noise around a stable number, a different simulation.

Someone eventually swept all 30 possible phases of that 30-day cycle. Sharpe ranged from 0.35 to 1.46. And
the one phase every prior test had used — the "obvious" one, day zero — was the single best of all 30.

Every parameter decision the project had made up to that point had been validated against the luckiest
number available, not a representative one. Nobody had cherry-picked it on purpose. The backtest had
cherry-picked it for them, silently, the moment someone wrote `data[::30]` instead of thinking about what
that slice actually meant.

**The fix is almost insultingly simple: run every phase, not one.** The hard part is remembering to, every
single time, on every candidate, forever — which is the actual reason to put it in a library instead of a
habit.

## 2. The bug that only breaks in one direction

Drawdown is naturally a negative number. A 20% drawdown is `-0.20`; a worse, 30% drawdown is `-0.30`. That's
correct and everyone knows it. It's also exactly the setup for a comparison bug that only breaks in the
direction that makes you happy.

Write the comparison the way it reads in English — "is the candidate's drawdown at least as good as the
baseline's?" — and you get `candidate_dd <= baseline_dd`. Plug in the numbers: `-0.30 <= -0.20` is `True`.
The candidate with the DEEPER, WORSE drawdown just passed the check.

This shipped. Three separate candidates were reported as "confirmed improvements — every metric passed" on
this exact line of code, before someone doing an unrelated manual double-check noticed the numbers didn't
smell right and traced it back.

The bug is one character's worth of intent, encoded in a symbol (`<=`) that means something different than
it looks like it means once you remember which way the number is stored. Nobody writing that line was
careless. The line just doesn't say what it looks like it says.

**The fix, again, is simple — get the direction right once, in one function everyone calls, and never let
anyone write the comparison inline again.** The value isn't the fix. It's that the fix has to exist
somewhere other than "be careful," because "be careful" already failed three times.

## 3. The result that was better on a strategy with no strategy in it

This is the one that should worry you most, because it doesn't look like a bug. It looks like a genuine,
exciting result.

The idea: split one strategy into several "tranches," each running the same logic but offset by a few days,
then blend them — average tranche 1's cycle-7 return with tranche 2's cycle-7 return, and so on — the way
you'd diversify a portfolio across managers who trade slightly out of phase with each other.

It looked fantastic. Sharpe up 27%. Drawdown several points shallower. A real, structural improvement, the
kind you build a new version of your strategy around.

Someone ran the control before believing it: apply the *exact same blending code* to plain buy-and-hold. Buy
plain SPY, do nothing else, blend it the same way. Buy-and-hold cannot possibly have any real "phase skill"
to capture — there's no strategy in it, just a price series. It "improved" by almost the same ratio. Sharpe
0.89 to 1.20, on doing literally nothing, blended.

What was actually happening: averaging several time-shifted windows smooths out variance across those
windows. It's a low-pass filter on noise, dressed up in returns notation. It has nothing to do with skill,
diversification, or risk reduction — it would have "worked" on a coin flip. If that one control run hadn't
happened, that result would have shipped as the project's best-ever finding.

**The generalizable lesson: if a technique can only be validated by looking at the strategy, it hasn't been
validated.** Construct the version where you know the honest answer in advance — a control, a null model, a
strategy-free baseline — and run your technique against *that* first. If it "wins" there too, you've found
an artifact, not an edge.

---

## Why these three, and not a list of forty

They're not exotic. None involves a subtle statistics error or a rare edge case in floating-point math.
They're the kind of mistake that survives a working code review, survives `git blame`, survives a green test
suite — because in each case, the code did exactly what it was written to do. The bug was in what it was
written to *mean*.

That's the actual argument for packaging these as automated checks instead of a mental checklist: a mental
checklist degrades every time you're tired, in a hurry, or excited about a number that finally looks good.
A function that runs anyway doesn't.

## What we built

**[AnchorTest](https://github.com/grant02339-ship-it/anchortest)** is the smallest library that runs these three
checks by default: anchor-average instead of trusting one phase, compare with the sign convention fixed in
one place, and check any blending logic against a phase-invariant control before trusting it. Plus a small
mutation-testing helper, because "we have tests" is a claim that deserves its own falsification check.

It's free, it's MIT-licensed, and it's about 400 lines of code — on purpose. The value isn't the amount of
code. It's that these three specific mistakes, having already cost one project real time and nearly cost it
a shipped false result, don't get to cost you the same thing.

```bash
pip install -e .   # from the repo, until it's on PyPI
```

If you've got your own war story — a result that looked right until you ran the control that wasn't obvious
to run — that's the kind of issue or PR this project wants most.
