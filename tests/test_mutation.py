import os
import tempfile
import unittest

from anchortest.mutation import Mutation, assert_all_caught, run_mutation_suite


class TestRunMutationSuite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lib_path = os.path.join(self.tmp.name, "lib.py")
        self.original = "def add(a, b):\n    return a + b\n"
        with open(self.lib_path, "w") as f:
            f.write(self.original)
        # A real test: fails if add() is broken, passes otherwise.
        self.good_test = os.path.join(self.tmp.name, "check_good.py")
        with open(self.good_test, "w") as f:
            f.write("import sys; sys.path.insert(0, '.'); from lib import add; assert add(2, 3) == 5\n")
        # A useless "test": always exits 0, so it can never catch anything -- proves SURVIVED is real, not a bug in the harness.
        self.blind_test = os.path.join(self.tmp.name, "check_blind.py")
        with open(self.blind_test, "w") as f:
            f.write("pass\n")

    def read_lib(self):
        with open(self.lib_path) as f:
            return f.read()

    def test_a_real_break_is_caught_by_a_real_test(self):
        mut = Mutation("break addition", "lib.py", "return a + b", "return a - b")
        results = run_mutation_suite([mut], ["python3", self.good_test], cwd=self.tmp.name)
        self.assertEqual(results[0]["status"], "CAUGHT")
        self.assertEqual(self.read_lib(), self.original)  # restored

    def test_the_same_break_survives_a_blind_test(self):
        mut = Mutation("break addition", "lib.py", "return a + b", "return a - b")
        results = run_mutation_suite([mut], ["python3", self.blind_test], cwd=self.tmp.name)
        self.assertEqual(results[0]["status"], "SURVIVED")
        self.assertEqual(self.read_lib(), self.original)  # restored even though the mutation "worked"

    def test_ambiguous_anchor_is_skipped_not_misapplied(self):
        mut = Mutation("ambiguous", "lib.py", "a", "z")  # "a" occurs many times
        results = run_mutation_suite([mut], ["python3", self.good_test], cwd=self.tmp.name)
        self.assertEqual(results[0]["status"], "SKIPPED")
        self.assertEqual(self.read_lib(), self.original)

    def test_file_is_restored_even_when_the_mutation_crashes_the_test_process(self):
        results = run_mutation_suite(
            [Mutation("break addition", "lib.py", "return a + b", "return a - b")],
            ["python3", "-c", "import sys; sys.exit(1)"],
            cwd=self.tmp.name,
        )
        self.assertEqual(results[0]["status"], "CAUGHT")
        self.assertEqual(self.read_lib(), self.original)

    def test_assert_all_caught_raises_on_a_survivor_and_is_silent_when_clean(self):
        with self.assertRaises(AssertionError):
            assert_all_caught([dict(name="x", status="SURVIVED")])
        with self.assertRaises(AssertionError):
            assert_all_caught([dict(name="x", status="SKIPPED")])
        assert_all_caught([dict(name="x", status="CAUGHT")])  # must not raise


if __name__ == "__main__":
    unittest.main()
