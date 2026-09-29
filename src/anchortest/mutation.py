"""Prove your test suite would actually catch a bug, instead of hoping it would.

Deliberately breaks your code in specific, named ways, one at a time, reruns your test command, and confirms
each break makes something fail. A file that never gets restored, or a mutation that "survives" (tests still
pass with the bug in place), is exactly the kind of blind spot a green test suite can hide.
"""
from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Mutation:
    """One deliberate break. `old` must appear in `path` exactly once (a mutation with an ambiguous or
    missing anchor is skipped, not silently applied to the wrong spot)."""
    name: str
    path: str
    old: str
    new: str


def run_mutation_suite(mutations: list[Mutation], test_command: list[str], cwd: str = ".") -> list[dict]:
    """Apply each mutation, run `test_command`, record the outcome, and ALWAYS restore the original file --
    in a `finally`, and verified by checksum, so a crash mid-run can't leave a mutated file behind.

    Returns one `{"name", "status", ...}` dict per mutation. `status` is one of:
      "CAUGHT"   -- test_command exited non-zero with the mutation in place (good: your tests found it)
      "SURVIVED" -- test_command exited zero anyway (a blind spot -- nothing tests this code path)
      "SKIPPED"  -- `old` wasn't found exactly once in `path` (fix the mutation, not the library)
    """
    results = []
    for mut in mutations:
        full_path = f"{cwd.rstrip('/')}/{mut.path}"
        with open(full_path) as f:
            original = f.read()
        occurrences = original.count(mut.old)
        if occurrences != 1:
            results.append(dict(name=mut.name, status="SKIPPED", detail=f"'old' found {occurrences} times, need exactly 1"))
            continue

        before_hash = hashlib.md5(original.encode()).hexdigest()
        try:
            with open(full_path, "w") as f:
                f.write(original.replace(mut.old, mut.new))
            proc = subprocess.run(test_command, cwd=cwd, capture_output=True, text=True)
            results.append(dict(
                name=mut.name,
                status="CAUGHT" if proc.returncode != 0 else "SURVIVED",
                returncode=proc.returncode,
                stdout_tail=proc.stdout[-2000:],
                stderr_tail=proc.stderr[-2000:],
            ))
        finally:
            with open(full_path, "w") as f:
                f.write(original)
            with open(full_path) as f:
                restored = f.read()
            if hashlib.md5(restored.encode()).hexdigest() != before_hash:
                raise RuntimeError(f"failed to restore {mut.path} after mutation {mut.name!r} -- fix this before trusting anything else")
    return results


def assert_all_caught(results: list[dict]) -> None:
    """Raise with the full list of offending mutation names if anything SURVIVED or was SKIPPED."""
    bad = [r for r in results if r["status"] != "CAUGHT"]
    if bad:
        detail = ", ".join(f"{r['name']} ({r['status']})" for r in bad)
        raise AssertionError(f"mutation check failed -- not every mutation was caught: {detail}")
