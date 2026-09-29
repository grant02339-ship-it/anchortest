# Ready-to-post launch copy

Drafts for the three venues, in each community's own register. Nothing here has been posted — read them,
edit anything that doesn't sound like you, and post them yourself (or tell me to, and I'll walk you through
it in the browser). Suggested order: **Show HN first** (title matters most and only gets one shot), then
r/algotrading a few hours later, then the QuantConnect forum once there's an HN/Reddit thread to link back to.

---

## Show HN

**Title** (80 char limit — this one is 74):
```
Show HN: AnchorTest – catch backtest overfitting before you ship a strategy
```

**Text:**
```
I spent a while on a quant-research side project and kept re-discovering the same three mistakes, each of
which looked like a completely valid result until something caught it:

1. A backtest that struck rebalance dates as a fixed stride from wherever the data happened to start. The
   "wherever it starts" turned out to be a phase, not a neutral choice — sweeping all 30 possible phases of
   one strategy's 30-day cycle found Sharpe ranging 0.35 to 1.46, and the one phase every earlier test had
   used was the best of all 30.

2. A drawdown comparison written the obvious way, `candidate_dd <= baseline_dd`. Drawdown is stored
   negative, so this silently treats a DEEPER, worse drawdown as a pass. Three candidates shipped as
   "confirmed improvements" on this exact line before a manual re-check caught it.

3. Blending several phase-shifted copies of a strategy looked like a genuine diversification win — Sharpe
   up 27%. Running the identical blend on plain buy-and-hold, which cannot have any real phase-dependent
   skill, "improved" it by almost the same ratio. It was smoothing variance across offset windows, not
   reducing risk.

AnchorTest is a small (~400 line), dependency-light (numpy+pandas only) library that runs these three checks
by default: anchor-average across every phase instead of trusting one, compare with the sign convention
fixed once, and check any blending logic against a synthetic phase-invariant control before you trust it.
Plus a small mutation-testing helper, because a green test suite is a claim, not a fact.

MIT licensed. 30 tests, a self-hosted mutation check that breaks 5 of the library's own invariants and
confirms all 5 are caught, and a runnable example. Not a backtesting engine — bring your own, this only
tells you how much to trust its output.

https://github.com/grant02339-ship-it/anchortest

Happy to go into more detail on any of the three incidents in the comments, or on why I built this instead
of just being more careful next time (spoiler: "be careful" already failed three times).
```

*HN norms: no emoji, no hype adjectives, be ready to defend the technical claims in comments, and expect
someone to ask "why not walk-forward analysis / CPCV / X existing tool" — have an honest answer ready (this
targets a narrower, more specific set of failure modes than a full walk-forward framework, and is meant to
be usable in an afternoon, not a replacement for one).*

---

## r/algotrading

**Title:**
```
I kept shipping backtest bugs that all looked like valid results — built a small library to catch them
```

**Body:**
```
Long-time lurker, finally have something concrete to share. Working on a systematic strategy, I kept hitting
the same category of mistake: bugs that don't look like bugs, because the code runs fine and the number is
real.

The one that should worry everyone here: a backtest picks rebalance dates as `data[::N]` — every Nth day,
starting from wherever your price history happens to begin. That start date is a phase, and it's not
neutral. I swept all 30 possible phases of one strategy's 30-day cycle and got Sharpe ranging from 0.35 to
1.46. The "obvious" choice — day zero — happened to be the best of all 30. Every backtest before that sweep
had been validated against the luckiest number available.

Two other real ones (both in the README with numbers): a drawdown comparison bug that silently treated a
WORSE drawdown as a pass (drawdown is stored negative, `-0.30 <= -0.20` is True), and a "diversification"
result from blending phase-shifted backtests that turned out to be pure variance-smoothing — confirmed by
running the same blend on plain buy-and-hold, which "improved" by almost the same amount with literally
zero strategy in it.

Wrote a small MIT-licensed library that runs these checks by default instead of hoping I remember to:
anchor-averaging, a comparison function with the drawdown sign fixed in one place, and a control-based check
for blending artifacts. numpy+pandas only, works on any equity-curve-producing backtest, not tied to any
specific engine.

https://github.com/grant02339-ship-it/anchortest

Genuinely curious if others here have their own version of incident #1 — the single-anchor problem feels
like it should be way more talked about than it is.
```

*Reddit norms: this community is skeptical of anything that smells like a sales pitch — the current draft
leans on the bugs, not the product, which is right for this sub. No pricing/audit mention here; that reads
as spammy in r/algotrading specifically even though it's fine in your own README.*

---

## QuantConnect forum

Post in the general/community forum, or wherever tooling/library shares go.

**Title:**
```
AnchorTest: a small library for anchor-averaging backtests (open source)
```

**Body:**
```
Sharing a small open-source tool that might be useful to others here: AnchorTest (MIT licensed,
numpy+pandas only).

The core idea is anchor-averaging — instead of running your backtest once from a fixed start date, run it
across every phase of your own rebalance cycle and look at the mean, median, minimum, and standard
deviation of Sharpe, not a single number. On one project this found Sharpe ranging 0.35 to 1.46 across 30
phases of a 30-day cycle, which is a wider spread than most of us probably assume when reporting a single
backtest result.

It also includes a comparison function with the drawdown sign convention fixed in one place (an easy trap:
drawdown stored negative means the "obvious" `<=` comparison silently prefers a WORSE drawdown), and a
check for a specific blending/tranching artifact where averaging phase-shifted runs can inflate Sharpe with
no real skill involved — validated against a synthetic control before you trust a real result.

It's engine-agnostic — works fine against a QC backtest's equity curve, or a local backtest, or anything
else that produces a pandas Series. Not trying to replace anything QC already does, just a validation layer
on top.

https://github.com/grant02339-ship-it/anchortest

Feedback welcome, especially from anyone who's hit the single-anchor problem on a real QC strategy.
```

*QC forum norms: more technical/neutral tone than Reddit is fine here, and QC users specifically will
recognize the "single backtest run" problem, so lead with the anchor-averaging concept rather than the
incident-log framing.*
