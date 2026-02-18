import pytest
from src.fault_localization_schemes.maxsat import MaxSATScheme
from src.fault_localization_schemes.lexmaxsat import LexMaxSATScheme
from src.candidate_function import FunctionManager
from src.instance_parsers.qbf import Instance


class TestFaultLocalization:
    @pytest.fixture
    def manager(self):
        return FunctionManager()

    @pytest.fixture
    def simple_instance(self):
        # QBF: Exists y1. (x1 or y1)
        # We model this manually.
        from src.dependency_schemes.trivial_inter_block import (
            TrivialInterBlockDependencyScheme,
        )

        quantifiers = [("a", [1]), ("e", [2])]
        clauses = [[1, 2]]  # x1=1, y1=2

        instance = Instance(
            2, 1, quantifiers, clauses, TrivialInterBlockDependencyScheme
        )
        return instance

    def test_maxsat_simple_unsat(self, manager, simple_instance):
        scheme = MaxSATScheme(simple_instance)

        # Candidate y1 = 0 (False)
        # Assignment x1 = 0, y1 = 0
        # Matrix (0 or 0) -> False.
        # Candidate check: y1 == 0 (True).
        # MaxSAT should flip y1 to satisfy matrix.

        y1_func = manager.get_lit(
            -1
        )  # Function NOT x1? No, let's just use constant false?
        # Logic: y1 = 0.
        # We can implement y1 = x1 AND NOT x1
        x1 = manager.get_lit(1)
        not_x1 = manager.get_lit(-1)
        y1_func = manager.get_and([x1, not_x1])  # Always False

        candidates = {2: y1_func}
        assignment = {1: False, 2: False}  # x1=0, y1=0

        # Run localize
        faults = scheme.localize(candidates, assignment)

        # y1 should be identified as fault because matrix requires y1=1 when x1=0
        assert 2 in faults

    def test_maxsat_no_conflict(self, manager, simple_instance):
        scheme = MaxSATScheme(simple_instance)

        # X1=1. Matrix (1 or y1) is True regardless of y1.
        # Candidate y1=0.
        # Assignment x1=1, y1=0.
        # Consistent.

        x1 = manager.get_lit(1)
        not_x1 = manager.get_lit(-1)
        y1_func = manager.get_and([x1, not_x1])  # Always False

        candidates = {2: y1_func}
        assignment = {1: True, 2: False}

        faults = scheme.localize(candidates, assignment)
        assert faults == []

    def test_lexmaxsat_priority(self, manager):
        # QBF: Exists y1, y2. Clauses: (y1 or y2) and (not y1 or not y2) -> y1 != y2
        # Candidates: y1=0, y2=0.
        # Assignment: y1=0, y2=0. Matrix fails.
        # We need to flip one.
        # LexMaxSAT should prefer flipping y2 (later) if weights are set correctly.
        # Check LexMaxSAT implementation: Earlier vars have HIGHER weight.
        # So we prefer satisfying y1=0 (weight High) over y2=0 (weight Low).
        # So MaxSAT should break y2=0 constraint.
        # Thus y2 should be the fault.

        from src.dependency_schemes.trivial_inter_block import (
            TrivialInterBlockDependencyScheme,
        )

        clauses = [[1, 2], [-1, -2]]  # y1=1, y2=2
        quantifiers = [("e", [1, 2])]
        # num_vars=2, quantifiers count=2?
        # Variable 1 and 2 are both existential?
        # clauses use 1 and 2.
        # quantifiers has ("e", [1, 2]).
        # So quantified_vars = 2.
        # Instance(2, 2, ...) -> num_vars=2. Matches.

        instance = Instance(
            2, 2, quantifiers, clauses, TrivialInterBlockDependencyScheme
        )

        scheme = LexMaxSATScheme(instance)

        y1_func = manager.get_and([manager.get_lit(3), manager.get_lit(-3)])  # 0
        y2_func = manager.get_and([manager.get_lit(3), manager.get_lit(-3)])  # 0

        candidates = {1: y1_func, 2: y2_func}
        assignment = {1: False, 2: False}

        faults = scheme.localize(candidates, assignment)

        # Depending on "TopW", we might get multiple faults if hard clauses requires it?
        # Here changing y2 to 1 (keeping y1=0) satisfies both clauses.
        # y1=0, y2=1 -> (0 or 1) & (1 or 0) -> True.
        # Cost: Flip y2 (Low weight).
        # Changing y1 to 1 (keeping y2=0).
        # y1=1, y2=0 -> True.
        # Cost: Flip y1 (High weight).
        # So solver should choose to flip y2.

        assert 2 in faults
        assert 1 not in faults
