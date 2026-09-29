# Ready-to-post launch copy

Drafts for the three venues, written to sound like a person typing this in one sitting, not a press
release. Read them, change anything that doesn't sound like you, and post them yourself. Suggested order:
**Show HN first** (title matters most and only gets one shot), then r/algotrading a few hours later, then
the QuantConnect forum once there's a thread to link back to.

**Note on posting automation:** I checked whether I could post these for you directly through the browser.
Hacker News and the QuantConnect forum both showed no logged-in session, and Reddit is blocked entirely by
the browser tool's own safety policy — I can't even load reddit.com, logged in or not. So all three need
you to paste these in yourself, or log into HN/QC in the Chrome session and tell me, and I can drive it from
there for those two.

---

## Show HN

**Title:**
```
Show HN: AnchorTest – stop trusting a single backtest run
```

**Text:**
```
I've spent a while working on a systematic options strategy (options-strategy-research, backtest-only,
nothing live) and kept running into the same three problems over and over. Each one looked completely fine
until I happened to check it a different way.

The big one: my backtest picked rebalance dates as basically data[::30] — every 30th day, starting from
wherever the price history happened to begin. Turns out that start date is a phase, not a neutral choice. I
swept all 30 possible phases of one strategy's cycle and got Sharpe ranging from 0.35 to 1.46. The "default"
phase I'd been using the whole time turned out to be the best of all 30. Every number I'd trusted up to that
point was the luckiest one available, not a representative one.

Two more, smaller but just as dumb in hindsight: a drawdown comparison (`candidate_dd <= baseline_dd`) that
silently treats a WORSE drawdown as a pass, because drawdown is stored negative and -0.30 <= -0.20 is true.
Shipped three false "wins" before I caught it. And a blending trick — averaging several phase-shifted
backtests together — that looked like a real diversification win, Sharpe up 27%, until I ran the identical
blend on plain buy-and-hold, which "improved" by almost the same ratio despite having zero strategy in it.

So I pulled the checks that would've caught all three into a small library: anchor-averaging instead of one
run, a comparison function without the sign bug, and a way to test a blending function against a synthetic
control before trusting it. Plus a small mutation-testing helper, because I don't fully trust my own tests
either.

https://github.com/grant02339-ship-it/anchortest

MIT, numpy/pandas only. Also doing free audits (running these checks against someone else's backtest) for
the first 10 people who want one — details in the README if that's useful.
```

*HN norms: no emoji, be ready to defend the technical claims in the comments, and expect someone to ask "why
not walk-forward analysis / CPCV / an existing tool" — honest answer: this targets a narrower set of
failure modes and is meant to be usable in an afternoon, not a replacement for a full framework.*

---

## r/algotrading

**Title:**
```
Kept shipping backtest bugs that all looked fine — built something to catch them
```

**Body:**
```
Long-time lurker. Finally have something worth posting.

I've been building a systematic options strategy (options-strategy-research, backtest-only, no live money)
and kept hitting the same kind of mistake — not bugs that crash, bugs where the code runs, the number looks
real, and it's just... wrong.

The one I think more people here should worry about: picking rebalance dates as data[::N] — every Nth day
starting from wherever your price history happens to start. That start date is a phase. It's not neutral. I
swept all 30 phases of one strategy's 30-day cycle and got Sharpe from 0.35 all the way to 1.46. The phase
I'd been using without thinking about it was the best one of the 30. Every backtest before that sweep had
been validated against the luckiest number available, not a real one.

Two other ones, both dumber in hindsight: a drawdown check written as `candidate_dd <= baseline_dd` that
silently treats a WORSE drawdown as a win (drawdown's stored negative, so -0.30 <= -0.20 reads True). That
one shipped three fake "confirmed improvements" before someone — me, later, annoyed — caught it. And a
"diversification" result from blending a few phase-shifted backtests together — looked amazing, Sharpe up
27% — until I ran the exact same blend on plain buy-and-hold, which improved by almost the same amount with
literally no strategy involved. It was just smoothing noise across offset windows.

Wrote a small library that does these checks automatically instead of relying on me remembering to:
anchor-averaging, a comparison function with the drawdown sign fixed for good, and a control-based check for
the blending thing. numpy + pandas only, works on whatever backtest engine you're already using.

https://github.com/grant02339-ship-it/anchortest

Also offering free audits (I'll run your backtest through these checks, no charge) for the first 10 people —
details in the repo.

Curious if anyone else here has their own version of the single-anchor thing. Feels like it should come up
more than it does.
```

*Reddit norms: skeptical of anything that smells like a sales pitch, but a genuinely free offer with a hard
cap of 10 reads as generous here, not spammy.*

---

## QuantConnect forum

Post in the general/community forum, or wherever tooling/library shares go.

**Title:**
```
AnchorTest — small open source library for anchor-averaging backtests
```

**Body:**
```
Sharing something I built that might be useful to people here — AnchorTest, MIT licensed, just numpy and
pandas.

The core idea: instead of running your backtest once from a fixed start date, run it across every phase of
your own rebalance cycle and look at the mean, median, min, and stdev of Sharpe instead of trusting one
number. I did this on options-strategy-research (my own backtest project) and got Sharpe ranging from 0.35
to 1.46 across 30 phases of a 30-day cycle — a much wider spread than I expected the first time I ran it.

There's also a comparison function with the drawdown sign convention fixed (easy trap: drawdown's stored
negative, so the "obvious" `<=` comparison quietly prefers a worse drawdown), and a check for a specific
blending artifact where averaging phase-shifted backtest runs can inflate Sharpe with zero real skill behind
it — validated against a synthetic control before you trust anything it tells you.

It's engine-agnostic, so it works fine against a QC backtest's equity curve or anything else that spits out
a pandas Series. Not trying to replace anything QC does, just sits on top as a sanity check.

https://github.com/grant02339-ship-it/anchortest

Would genuinely like to know if anyone here has hit the single-anchor problem on a real QC strategy — feels
like something this community in particular would run into a lot. Also doing free audits for the first 10
people who want their own backtest run through this, details in the repo.
```

*QC forum norms: more technical/neutral tone than Reddit is fine here, and QC users specifically will
recognize the "single backtest run" problem immediately.*
