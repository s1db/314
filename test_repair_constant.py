import unittest
from unittest.mock import MagicMock
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.candidate_function import FunctionManager, NodeType
from src.instance import Instance
from src.dependency_schemes.base import DependencyScheme


class TestRepairConstant(unittest.TestCase):
    def test_repair_constant_function(self):
        # Scenario:
        # Var 3 (Existential) should be x1 (Var 1).
        # Currently Candidate(3) = False (Constant).
        # We simulate a repair request.

        manager = FunctionManager()

        # Mock Instance
        instance = MagicMock(spec=Instance)
        instance.get_existential_vars.return_value = [3]
        instance.get_universal_vars.return_value = [1]
        instance.clauses = [[1, -3], [-1, 3]]  # 1 <-> 3

        # Mock Dependency Scheme
        dep_scheme = MagicMock(spec=DependencyScheme)
        # Allowed to depend on 1
        dep_scheme.get_allowed_variables.return_value = {1}
        dep_scheme.sort_by_dependency_order.side_effect = lambda x: x  # Identity sort

        repair_scheme = UnsatCoreRepairScheme(instance, dep_scheme, manager)

        # Initial candidates: 3 is False
        candidates = {3: manager.get_false()}

        # Assignment where check failed: 1=True, 3=False.
        # 3 should be True when 1 is True.
        assignment = {1: True, 3: False}
        suspects = [3]

        # Perform Repair
        # This will use a SAT solver on clauses [[1, -3], [-1, 3]].
        # And assumptions: 1=True, 3=False (Bad value).
        # The solver should find UNSAT and returns a core.
        # Core should contain 1 (or -1).
        # If repair works, validation passes.

        try:
            new_candidates = repair_scheme.repair(candidates, assignment, suspects)

            # Check if 3 is no longer constant False
            func_3 = new_candidates[3]
            print(f"Repaired Function for 3: {func_3}")

            self.assertFalse(func_3.is_false, "Function should not be False anymore")
            self.assertTrue(1 in func_3.support, "Function should depend on 1")

        except Exception as e:
            self.fail(f"Repair failed with exception: {e}")


if __name__ == "__main__":
    unittest.main()
