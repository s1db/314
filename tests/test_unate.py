"""Tests for ManthanUnatePreprocessor."""

import pytest
from src.preprocessing.manthan_unate import ManthanUnatePreprocessor
from src.candidate_function import FunctionManager


@pytest.fixture
def fm() -> FunctionManager:
    return FunctionManager()


@pytest.fixture
def preprocessor() -> ManthanUnatePreprocessor:
    # Use conf_budget=0 (unlimited) for deterministic tests
    return ManthanUnatePreprocessor(conf_budget=0)


class TestPositiveUnate:
    """Variable forced to 1."""

    def test_unit_clause_forces_true(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (y) — y must be 1."""
        # a 1 0  e 2 0  (2) 0
        clauses = [[2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_true
        assert candidates[2].repairable is False

    def test_implied_positive(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x ∨ y) ∧ (¬x ∨ y) — y must be 1 regardless of x."""
        clauses = [[1, 2], [-1, 2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_true
        assert candidates[2].repairable is False


class TestNegativeUnate:
    """Variable forced to 0."""

    def test_unit_clause_forces_false(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (¬y) — y must be 0."""
        clauses = [[-2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_false
        assert candidates[2].repairable is False

    def test_implied_negative(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x ∨ ¬y) ∧ (¬x ∨ ¬y) — y must be 0 regardless of x."""
        clauses = [[1, -2], [-1, -2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_false
        assert candidates[2].repairable is False


class TestNonUnate:
    """Variable is free — neither pos nor neg unate."""

    def test_free_variable(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x == y). y is not unate because it must follow x."""
        clauses = [[1, -2], [-1, 2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        # Should NOT resolve y
        assert 2 not in candidates

    def test_true_formula_is_unate(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = True. Any value works, so it is unate (Manthan picks True)."""
        clauses: list[list[int]] = []
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        # In a vacuously SAT formula, F(y=0) & !F(y'=1) is False & !False = False?
        # No, F(y=0) is True. F(y'=1) is True. !F(y'=1) is False.
        # True & False is False (UNSAT).
        # So it is marked positive unate.
        assert 2 in candidates
        assert candidates[2].is_true


class TestMixed:
    """Mix of unate and non-unate variables."""

    def test_one_unate_one_not(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """y1 forced True, y2 follows x.
        F = (y1) ∧ (x == y2)
        """
        clauses = [[2], [1, -3], [-1, 3]]
        x_vars = [1]
        y_vars = [2, 3]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_true
        assert 3 not in candidates


class TestCascading:
    """Fixing one unate reveals another."""

    def test_cascade(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (y1) ∧ (¬y1 ∨ y2).
        Initially y2 is free (it is POS unate but Manthan finds it after y1 is fixed).
        Actually, in my implementation, y1 is fixed, then y2 becomes unate.
        """
        clauses = [[2], [-2, 3]]
        x_vars = [1]
        y_vars = [2, 3]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_true
        assert 3 in candidates
        assert candidates[3].is_true


class TestRepairable:
    """Verify the repairable flag is set correctly."""

    def test_unate_not_repairable(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        clauses = [[2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert not candidates[2].repairable

    def test_existing_candidates_preserved(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """Preprocessing should not overwrite pre-existing candidates for non-unate vars."""
        clauses = [[1, -2], [-1, 2]]  # non-unate (y == x)
        x_vars = [1]
        y_vars = [2]
        existing = fm.get_lit(3)  # dummy function
        candidates = {2: existing}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        # Variable 2 is NOT unate, so the existing candidate should remain
        assert candidates[2] is existing


class TestEdgeCases:
    """Edge cases."""

    def test_no_existential_vars(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """No Y vars — should return immediately."""
        clauses = [[1]]
        x_vars = [1]
        y_vars: list[int] = []
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert not candidates

    def test_mostly_free(
        self, preprocessor: ManthanUnatePreprocessor, fm: FunctionManager
    ) -> None:
        """F = (x | y) & (!x | y) - y is unate.
        F = (x | !y) & (!x | !y) - y is negative unate.
        Use something truly not unate.
        """
        clauses = [[1, 2], [-1, -2]]  # y = !x
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)
        assert 2 not in candidates

    def test_conf_budget_default(self, fm: FunctionManager) -> None:
        """Default preprocessor uses conf_budget=50."""
        preprocessor = ManthanUnatePreprocessor()
        assert preprocessor.conf_budget == 50

        # Even with limited budget, obvious unates should be found
        clauses = [[2]]
        x_vars = [1]
        y_vars = [2]
        candidates: dict = {}

        preprocessor.run(clauses, x_vars, y_vars, candidates, fm)

        assert 2 in candidates
        assert candidates[2].is_true
