import pytest
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.candidate_function import FunctionManager
from src.instance_parsers.qbf import Instance
from unittest.mock import Mock


class TestRepair:
    @pytest.fixture
    def manager(self):
        return FunctionManager()

    @pytest.fixture
    def simple_instance(self):
        # QBF: Exists y1. (x1 or y1)
        # We model this manually.
        quantifiers = [("a", [1]), ("e", [2])]
        clauses = [[1, 2]]
        # Use a mock or trivial dependency scheme class
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        instance = Instance(2, 1, quantifiers, clauses, TrivialDependencyScheme)
        return instance

    def test_repair_basic(self, manager, simple_instance):
        dep_scheme = Mock()
        dep_scheme.get_total_order.return_value = [2, 1]
        # Mock sort_by_dependency_order to return suspects sorted by [2, 1]
        # logic: 2 comes first (index 0), 1 comes second (index 1).
        # if suspects is [2], return [2].
        dep_scheme.sort_by_dependency_order.side_effect = lambda s: sorted(
            s, key=lambda x: {2: 0, 1: 1}.get(x, 999)
        )
        dep_scheme.get_allowed_variables.return_value = {
            1
        }  # y1 (2) allowed to depend on x1 (1)

        scheme = UnsatCoreRepairScheme(simple_instance, dep_scheme, manager)

        # Candidate y1 = 0 (False)
        # Assignment x1 = 0, y1 = 0 (False)
        # Matrix (0 or 0) -> False.
        # Candidate check: y1 == 0 (True).
        # Expected repair:
        # Original was 0.
        # Bad Value is 0 (y1=0). Should be 1.
        # New = Old OR Beta.

        # Candidate: Constant False
        x1 = manager.get_lit(1)
        not_x1 = manager.get_lit(-1)
        y1_func = manager.get_and([x1, not_x1])  # Always False

        assignment = {1: False, 2: False}
        variable = 2

        candidates = {variable: y1_func}
        suspects = [variable]
        new_candidates = scheme.repair(candidates, assignment, suspects)
        repaired = new_candidates[variable]

        # Check if repaired function evaluates to True when x1=0
        # Beta should contain NOT x1 (because x1=False causes conflict).
        val = repaired.evaluate({1: False})
        assert val is True

        # Check if repaired function evaluates to False when x1=1
        # Original 0. Beta (-1) is False.
        # 0 OR 0 = 0.
        val = repaired.evaluate({1: True})
        assert val is False

    def test_repair_no_conflict(self, manager, simple_instance):
        dep_scheme = Mock()
        dep_scheme.get_total_order.return_value = [2, 1]
        dep_scheme.sort_by_dependency_order.side_effect = lambda s: sorted(
            s, key=lambda x: {2: 0, 1: 1}.get(x, 999)
        )
        dep_scheme.get_allowed_variables.return_value = {1}

        scheme = UnsatCoreRepairScheme(simple_instance, dep_scheme, manager)

        # x1=1. y1=0. Consistent.
        x1 = manager.get_lit(1)
        not_x1 = manager.get_lit(-1)
        y1_func = manager.get_and([x1, not_x1])  # False

        assignment = {1: True, 2: False}
        variable = 2

        candidates = {variable: y1_func}
        suspects = [variable]
        new_candidates = scheme.repair(candidates, assignment, suspects)
        repaired = new_candidates[variable]

        # Should be same as original or structurally equivalent
        # If no core found, it returns candidate.
        assert repaired == y1_func


class TestInterpolantRepair:
    @pytest.fixture
    def manager(self):
        return FunctionManager()

    @pytest.fixture
    def simple_instance(self):
        # QBF: Exists y1. (x1 or y1)
        quantifiers = [("a", [1]), ("e", [2])]
        clauses = [[1, 2]]
        from src.dependency_schemes.trivial import TrivialDependencyScheme

        instance = Instance(2, 1, quantifiers, clauses, TrivialDependencyScheme)
        return instance

    def test_repair_basic(self, manager, simple_instance):
        from src.repair_schemes.interpolant import InterpolantRepairScheme

        dep_scheme = Mock()
        dep_scheme.get_total_order.return_value = [2, 1]
        dep_scheme.sort_by_dependency_order.side_effect = lambda s: sorted(
            s, key=lambda x: {2: 0, 1: 1}.get(x, 999)
        )
        dep_scheme.get_allowed_variables.return_value = {1}

        scheme = InterpolantRepairScheme(simple_instance, dep_scheme, manager)

        # Candidate y1 = 0 (False)
        # Assignment x1 = 0, y1 = 0 → Matrix (0 or 0) = False.
        # Expected: repair via interpolation or core fallback.
        x1 = manager.get_lit(1)
        not_x1 = manager.get_lit(-1)
        y1_func = manager.get_and([x1, not_x1])  # Always False

        assignment = {1: False, 2: False}
        variable = 2

        candidates = {variable: y1_func}
        suspects = [variable]
        new_candidates = scheme.repair(candidates, assignment, suspects)
        repaired = new_candidates[variable]

        # Repaired function must evaluate to True when x1=0
        val = repaired.evaluate({1: False})
        assert val is True

        # Repaired function should evaluate to False when x1=1
        val = repaired.evaluate({1: True})
        assert val is False

    def test_repair_no_conflict(self, manager, simple_instance):
        from src.repair_schemes.interpolant import InterpolantRepairScheme

        dep_scheme = Mock()
        dep_scheme.get_total_order.return_value = [2, 1]
        dep_scheme.sort_by_dependency_order.side_effect = lambda s: sorted(
            s, key=lambda x: {2: 0, 1: 1}.get(x, 999)
        )
        dep_scheme.get_allowed_variables.return_value = {1}

        scheme = InterpolantRepairScheme(simple_instance, dep_scheme, manager)

        # x1=1. y1=0. Consistent (1 or 0 = True).
        x1 = manager.get_lit(1)
        not_x1 = manager.get_lit(-1)
        y1_func = manager.get_and([x1, not_x1])  # False

        assignment = {1: True, 2: False}
        variable = 2

        candidates = {variable: y1_func}
        suspects = [variable]
        new_candidates = scheme.repair(candidates, assignment, suspects)
        repaired = new_candidates[variable]

        # Should be same as original (SAT hypothesis → no repair)
        assert repaired == y1_func
