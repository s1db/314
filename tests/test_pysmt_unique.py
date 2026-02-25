"""Tests for PySMTUniquePreprocessor (uniquely defined function detection via Craig interpolation)."""

import pytest

try:
    import mathsat  # noqa: F401

    HAS_MATHSAT = True
except ImportError:
    HAS_MATHSAT = False

from src.preprocessing.pysmt_unique import PySMTUniquePreprocessor
from src.candidate_function import CandidateFunction, FunctionManager

pytestmark = pytest.mark.skipif(not HAS_MATHSAT, reason="MathSAT5 not installed")


@pytest.fixture
def fm() -> FunctionManager:
    return FunctionManager()


@pytest.fixture
def preprocessor() -> PySMTUniquePreprocessor:
    return PySMTUniquePreprocessor()


class TestUniquelyDefined:
    """Variable whose value is uniquely determined by X."""

    def test_y_equals_x(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x ∨ ¬y) ∧ (¬x ∨ y) — y = x, uniquely defined."""
        clauses = [[1, -2], [-1, 2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].repairable is False

    def test_y_equals_not_x(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x ∨ y) ∧ (¬x ∨ ¬y) — y = ¬x, uniquely defined."""
        clauses = [[1, 2], [-1, -2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].repairable is False


class TestNotUnique:
    """Variable is NOT uniquely defined — multiple valid values exist."""

    def test_free_y(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x ∨ y) — y can be 0 or 1 when x=1."""
        clauses = [[1, 2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 not in candidates


class TestForcedConstant:
    """Variable forced to a constant — should still be detected as unique."""

    def test_unit_clause_forces_true(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (y) — y must be 1."""
        clauses = [[2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].repairable is False

    def test_unit_clause_forces_false(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (¬y) — y must be 0."""
        clauses = [[-2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].repairable is False


class TestEdgeCases:
    """Edge cases."""

    def test_no_y_vars(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """No existential variables — no-op."""
        clauses = [[1]]
        x_vars = [1]
        y_vars: list[int] = []
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert not candidates

    def test_existing_candidates_preserved(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """Non-unique vars should not overwrite existing candidates."""
        clauses = [[1, 2]]  # y is free (not unique)
        x_vars = [1]
        y_vars = [2]
        existing = fm.get_lit(3)  # dummy function
        candidates: dict[int, CandidateFunction] = {2: existing}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        # Variable 2 is NOT unique, so existing candidate stays
        assert candidates[2] is existing


class TestRepairable:
    """Resolved vars must have repairable=False."""

    def test_unique_not_repairable(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """Uniquely defined vars should not be repairable."""
        clauses = [[1, -2], [-1, 2]]  # y = x
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert not candidates[2].repairable


class TestFunctionCorrectness:
    """Verify that extracted functions are semantically correct."""

    def test_y_equals_x_evaluates_correctly(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """y = x: function should evaluate to True when x=True, False when x=False."""
        clauses = [[1, -2], [-1, 2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        func = candidates[2]
        # When x=1, y should be 1
        assert func.evaluate({1: True}) is True
        # When x=0, y should be 0
        assert func.evaluate({1: False}) is False

    def test_y_equals_not_x_evaluates_correctly(
        self, preprocessor: PySMTUniquePreprocessor, fm: FunctionManager
    ) -> None:
        """y = ¬x: function should evaluate to False when x=True, True when x=False."""
        clauses = [[1, 2], [-1, -2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict[int, CandidateFunction] = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        func = candidates[2]
        # When x=1, y should be 0
        assert func.evaluate({1: True}) is False
        # When x=0, y should be 1
        assert func.evaluate({1: False}) is True
