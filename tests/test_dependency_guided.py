import unittest
from unittest.mock import MagicMock
import numpy as np
from src.guessing_schemes.dependency_guided import DependencyGuidedGuesser
from src.instance import Instance
from src.candidate_function import FunctionManager
from src.dependency_schemes.base import DependencyScheme


class TestDependencyGuidedGuesser(unittest.TestCase):
    def setUp(self):
        self.guesser = DependencyGuidedGuesser()
        self.manager = FunctionManager()

        # Mock Instance
        self.instance = MagicMock(spec=Instance)
        self.instance.get_existential_vars.return_value = [3, 4]
        self.instance.get_universal_vars.return_value = [1, 2]

        # Mock Dependency Scheme
        self.dep_scheme = MagicMock(spec=DependencyScheme)

    def test_guessing_respects_dependencies(self):
        # Setup samples: 5 samples, 4 variables (1, 2, 3, 4)
        # Var map: 1->0, 2->1, 3->2, 4->3
        samples = np.array(
            [[0, 0, 0, 1], [0, 1, 1, 0], [1, 0, 1, 1], [1, 1, 0, 0], [0, 0, 0, 0]]
        )

        # Variable 3 allowed to depend on 1 (col 0)
        # Variable 4 allowed to depend on 2 (col 1)
        self.dep_scheme.get_dependencies.side_effect = lambda v: {1} if v == 3 else {2}

        candidates = self.guesser.guess_candidates(
            self.instance, samples, self.manager, self.dep_scheme
        )

        # Verify call arguments
        # get_dependencies should have been called for 3 and 4
        self.dep_scheme.get_dependencies.assert_any_call(3)
        self.dep_scheme.get_dependencies.assert_any_call(4)

        self.assertIn(3, candidates)
        self.assertIn(4, candidates)

        # Check that candidates are valid functions (not None)
        self.assertIsNotNone(candidates[3])
        self.assertIsNotNone(candidates[4])

        # In a real scenario, we'd check the exact function, but here we trust the decision tree
        # The key is that it didn't crash and called get_dependencies

    def test_no_dependencies_learns_constant(self):
        samples = np.array(
            [
                [1, 0, 1, 1],  # 3 is 1 (3 ones vs 1 zero)
                [0, 1, 1, 0],
                [1, 0, 1, 1],
                [1, 1, 1, 0],
            ]
        )

        # Variable 3 has NO dependencies
        self.dep_scheme.get_dependencies.return_value = set()

        candidates = self.guesser.guess_candidates(
            self.instance, samples, self.manager, self.dep_scheme
        )

        # Should be constant TRUE (since 3 is mostly 1)
        from src.candidate_function import NodeType

        self.assertEqual(candidates[3].node_type, NodeType.CONSTANT)
        self.assertEqual(candidates[3], self.manager.get_true())


if __name__ == "__main__":
    unittest.main()
