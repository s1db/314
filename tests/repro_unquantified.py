import unittest
import logging
from src.instance import Instance
from src.dependency_schemes.trivial_inter_block import TrivialInterBlockDependencyScheme

# Configure logging to see the warning
logging.basicConfig(level=logging.WARNING)


class TestUnquantifiedVariables(unittest.TestCase):
    def test_unquantified_vars_added_to_existential(self):
        # Setup: 3 variables, only 2 quantified
        num_vars = 3
        num_clauses = 1
        # Quantifiers: existentially quantify variable 1. Variable 3 is explicitly universal? No, let's say only 1 is quantified.
        quantifiers = [("e", [1])]
        clauses = [[1, 2, 3]]

        # Expectation: 2 and 3 are unquantified. They should be added to the outermost existential block.
        # Since block 0 is existential, they should be merged into it.
        # Resulting quantifiers should be [("e", [1, 2, 3])] (sorted)

        instance = Instance(
            num_vars,
            num_clauses,
            quantifiers,
            clauses,
            TrivialInterBlockDependencyScheme,
        )

        self.assertEqual(len(instance.quantifiers), 1)
        self.assertEqual(instance.quantifiers[0][0], "e")
        self.assertEqual(instance.quantifiers[0][1], [1, 2, 3])

    def test_unquantified_vars_prepended_to_universal(self):
        # Setup: 2 variables, var 2 is universal. Var 1 is unquantified.
        num_vars = 2
        num_clauses = 1
        quantifiers = [("a", [2])]
        clauses = [[1, 2]]

        # Expectation: 1 is unquantified. Should be added to NEW outermost existential block.
        # Resulting quantifiers: [("e", [1]), ("a", [2])]

        instance = Instance(
            num_vars,
            num_clauses,
            quantifiers,
            clauses,
            TrivialInterBlockDependencyScheme,
        )

        self.assertEqual(len(instance.quantifiers), 2)
        self.assertEqual(instance.quantifiers[0], ("e", [1]))
        self.assertEqual(instance.quantifiers[1], ("a", [2]))

    def test_all_unquantified(self):
        # Setup: 2 vars, none quantified
        num_vars = 2
        num_clauses = 1
        quantifiers = []
        clauses = [[1, 2]]

        # Expectation: [("e", [1, 2])]

        instance = Instance(
            num_vars,
            num_clauses,
            quantifiers,
            clauses,
            TrivialInterBlockDependencyScheme,
        )

        self.assertEqual(len(instance.quantifiers), 1)
        self.assertEqual(instance.quantifiers[0], ("e", [1, 2]))


if __name__ == "__main__":
    unittest.main()
