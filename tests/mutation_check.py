"""Mutation check for anchortest's own source, using anchortest's own mutation helper (dogfooding).

Deliberately breaks the library in ways that mirror the real incidents in README.md, and confirms the test
suite catches every one. Run: .venv/bin/python tests/mutation_check.py
Exit code 1 if anything SURVIVED or was SKIPPED.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from anchortest.mutation import Mutation, run_mutation_suite  # noqa: E402

MUTATIONS = [
    Mutation(
        "compare: reintroduce the drawdown sign bug",
        "src/anchortest/compare.py",
        '"mean_dd": 1,          # stored negative; candidate - baseline > 0 already means "shallower, better"',
        '"mean_dd": -1,          # stored negative; candidate - baseline > 0 already means "shallower, better"',
    ),
    Mutation(
        "clears_bar: allow a tie to pass",
        "src/anchortest/compare.py",
        "return all(delta.get(k, -1.0) > 0 for k in keys)",
        "return all(delta.get(k, -1.0) >= 0 for k in keys)",
    ),
    Mutation(
        "shifts_for: off-by-one in the phase arithmetic",
        "src/anchortest/anchors.py",
        "return sorted({int(i * cycle_days / n_anchors) for i in range(n_anchors)})",
        "return sorted({int(i * cycle_days / n_anchors) for i in range(n_anchors + 1)})",
    ),
    Mutation(
        "check_blend_artifact: threshold direction flipped",
        "src/anchortest/artifacts.py",
        "suspect=ratio > threshold,",
        "suspect=ratio < threshold,",
    ),
    Mutation(
        "run_mutation_suite: stop restoring the mutated file",
        "src/anchortest/mutation.py",
        "        finally:\n            with open(full_path, \"w\") as f:\n                f.write(original)",
        "        finally:\n            pass  # oops: restore removed\n            _unused = original",
    ),
]

if __name__ == "__main__":
    results = run_mutation_suite(MUTATIONS, [sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT)
    for r in results:
        print(f"{r['name']:52s} {r['status']}")
    bad = [r["name"] for r in results if r["status"] != "CAUGHT"]
    sys.exit(1 if bad else 0)
