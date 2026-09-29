import unittest

import numpy as np
import pandas as pd

from anchortest.artifacts import ArtifactSuspected, assert_no_blend_artifact, check_blend_artifact


def naive_cycle_index_blend(runs: list[pd.Series]) -> pd.Series:
    """The exact flawed pattern this module exists to catch: average cycle-i's return across every run,
    then cumulative-product the averaged returns back into one equity curve."""
    n = min(len(r) for r in runs)
    eqs = np.array([r.values[:n] for r in runs])
    rets = eqs[:, 1:] / eqs[:, :-1] - 1.0
    blended = np.concatenate([[1.0], np.cumprod(1.0 + rets.mean(axis=0))])
    return pd.Series(blended, index=runs[0].index[:n])


def identity_blend(runs: list[pd.Series]) -> pd.Series:
    """A 'blend' that just returns the first run untouched -- cannot inflate anything, must NOT be suspect."""
    return runs[0]


class TestCheckBlendArtifact(unittest.TestCase):
    def test_naive_cycle_index_blend_is_flagged_suspect(self):
        result = check_blend_artifact(naive_cycle_index_blend, cycle_days=25, n_anchors=25)
        self.assertTrue(result["suspect"])
        self.assertGreater(result["ratio"], 1.15)

    def test_identity_blend_is_not_suspect(self):
        # identity_blend returns exactly ONE phase (shift=0), not the mean of all phases -- since real phase
        # dependence exists (that's what this whole library is about), its ratio need not be exactly 1.0.
        # The property that must hold is "not flagged", not "ratio == 1".
        result = check_blend_artifact(identity_blend, cycle_days=25, n_anchors=25)
        self.assertFalse(result["suspect"])
        self.assertLess(result["ratio"], result["threshold"])

    def test_assert_no_blend_artifact_raises_for_the_flawed_blend(self):
        result = check_blend_artifact(naive_cycle_index_blend, cycle_days=25, n_anchors=25)
        with self.assertRaises(ArtifactSuspected):
            assert_no_blend_artifact(result)

    def test_assert_no_blend_artifact_is_silent_for_the_honest_blend(self):
        result = check_blend_artifact(identity_blend, cycle_days=25, n_anchors=25)
        assert_no_blend_artifact(result)  # must not raise

    def test_deterministic_given_a_fixed_seed(self):
        a = check_blend_artifact(naive_cycle_index_blend, seed=1)
        b = check_blend_artifact(naive_cycle_index_blend, seed=1)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
