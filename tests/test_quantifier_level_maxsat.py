import pytest
from src.fault_localization_schemes.quantifier_level_maxsat import (
    QuantifierLevelMaxSATScheme,
)
from src.candidate_function import FunctionManager
from src.instance_parsers.qbf import Instance


class TestQuantifierLevelMaxSAT:
    @pytest.fixture
    def manager(self):
        return FunctionManager()

    def test_quantifier_level_weighting(self, manager):
        # QBF: Exists y1 (Block 0). Exists y2 (Block 1).
        # Clauses: y1 != y2
        # (y1 or y2) and (-y1 or -y2)
        # Candidates: y1=0, y2=0.
        # Assignment: y1=0, y2=0. Matrix Fails.
        # We need to flip one.

        # Block 0 (y1) should have HIGHER weight than Block 1 (y2).
        # So we prefer to KEEP y1 (High Weight) and flip y2 (Low Weight).
        # Fault should be y2.

        quantifiers = [("e", [1]), ("e", [2])]
        clauses = [[1, 2], [-1, -2]]

        instance = Instance(2, 2, quantifiers, clauses)
        # No dependency scheme needed for this scheme logic, but instance might validly have one.

        scheme = QuantifierLevelMaxSATScheme(instance)

        # Candidates: both false
        y1_func = manager.get_and([manager.get_lit(3), manager.get_lit(-3)])  # 0
        y2_func = manager.get_and([manager.get_lit(3), manager.get_lit(-3)])  # 0

        candidates = {1: y1_func, 2: y2_func}
        assignment = {1: False, 2: False}

        faults = scheme.localize(candidates, assignment)

        # Expect y2 to be the fault because it has lower weight (inner block)
        assert 2 in faults
        assert 1 not in faults

    def test_quantifier_level_mixed(self, manager):
        # QBF: Forall x (Block 0). Exists y1 (Block 1). Exists y2 (Block 2).
        # Clauses: ...
        # Testing if Block Index mapping handles Universals correctly.

        # y1 is Block 1. y2 is Block 2.
        # w(y1) > w(y2).

        quantifiers = [("a", [1]), ("e", [2]), ("e", [3])]
        clauses = [[2, 3], [-2, -3]]  # y1 != y2 (ignoring x for now)

        instance = Instance(3, 2, quantifiers, clauses)
        scheme = QuantifierLevelMaxSATScheme(instance)

        # y1=0, y2=0.
        candidates = {2: manager.get_and([]), 3: manager.get_and([])}  # Dummy funcs
        assignment = {1: False, 2: False, 3: False}

        # We force conflict on y1, y2.
        # MaxSAT should flip y2 (lower weight).

        faults = scheme.localize(candidates, assignment)

        assert 3 in faults
        assert 2 not in faults
