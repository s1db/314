"""Sampling-based unate preprocessing (GuessUnate).

Identifies existential variables that can be replaced by constant values
by evaluating their behavior across generated samples.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

import numpy as np
from pysat.solvers import Solver as SATSolver

from src.candidate_function import CandidateFunction, FunctionManager
from src.preprocessing.base import Preprocessor

logger = logging.getLogger(__name__)


class GuessUnatePreprocessor(Preprocessor):
    """Sampling-based unate detector.

    Parameters
    ----------
    solver_name:
        PySAT solver backend (default ``"g4"``).
    verify:
        If True, verify guesses using a global SAT query.
    """

    def __init__(self, solver_name: str = "cadical195", verify: bool = True):
        self.solver_name = solver_name
        self.verify = verify

    def run(
        self,
        clauses: List[List[int]],
        x_vars: List[int],
        y_vars: List[int],
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
        samples: Optional[np.ndarray] = None,
    ) -> None:
        if not y_vars or samples is None or len(samples) == 0:
            return

        all_vars = sorted(x_vars + y_vars)
        var_to_idx = {var: i for i, var in enumerate(all_vars)}
        y_vars_set = set(y_vars)

        # 1. Bit-flip analysis via "Critical Literals"
        # profile[y] = { 'A', 'B', 'C' }
        profiles: Dict[int, Set[str]] = {y: set() for y in y_vars}

        # Pre-process clauses for faster access
        indexed_clauses = []
        for clause in clauses:
            indexed_clauses.append([(lit, var_to_idx[abs(lit)]) for lit in clause])

        for i in range(len(samples)):
            sample = samples[i]

            # For each sample, identify critical variables
            # A variable is critical if it's the ONLY literal satisfying a clause.
            critical_vars: Set[int] = set()

            for c_lits in indexed_clauses:
                true_var = -1
                count = 0
                for lit, idx in c_lits:
                    if (lit > 0) == sample[idx]:
                        if count == 0:
                            true_var = abs(lit)
                            count = 1
                        else:
                            count = 2
                            break

                if count == 1:
                    critical_vars.add(true_var)

            for y in y_vars:
                if y in critical_vars:
                    # Forced to its current value
                    val = sample[var_to_idx[y]]
                    profiles[y].add("A" if val else "C")
                else:
                    # Both y=1 and y=0 satisfy the formula in this context
                    profiles[y].add("B")

        # 2. Deduction and Optional Verification
        num_vars = max(
            max((abs(lit) for clause in clauses for lit in clause), default=0),
            max((abs(v) for v in all_vars), default=0),
        )

        # Reuse single solver for all verification queries
        verify_solver: Optional[SATSolver] = None
        if self.verify:
            verify_solver = SATSolver(name=self.solver_name)
            for clause in clauses:
                verify_solver.add_clause(clause)

        try:
            for y in y_vars:
                profile = profiles[y]
                guess: Optional[int] = None

                if "A" in profile and "C" in profile:
                    continue  # Not a constant
                elif "A" in profile:
                    guess = 1
                elif "C" in profile:
                    guess = 0
                elif "B" in profile:
                    guess = 1  # Default to 1 for Don't Care
                else:
                    continue

                if self.verify:
                    assert verify_solver is not None
                    if self._verify_guess(
                        verify_solver, clauses, y_vars_set, num_vars, y, guess
                    ):
                        self._apply_guess(y, guess, candidates, function_manager)
                else:
                    self._apply_guess(y, guess, candidates, function_manager)
        finally:
            if verify_solver:
                verify_solver.delete()

    def _apply_guess(
        self,
        y: int,
        guess: int,
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
    ) -> None:
        if guess == 1:
            func = function_manager.get_true()
        else:
            func = function_manager.get_false()
        func.repairable = False
        candidates[y] = func
        logger.debug("GuessUnate: Variable %d resolved to %d", y, guess)

    def _verify_guess(
        self,
        solver: SATSolver,
        clauses: List[List[int]],
        y_set: Set[int],
        num_vars: int,
        y_target: int,
        guess: int,
    ) -> bool:
        """Soundness check: F(X, Y) & !F(X, Y_{-y}, y_target=guess) is UNSAT."""

        # We reuse the solver. But adding clauses for !F is tricky if we want to reuse.
        # We can use assumptions if we encode !F once with control variables?
        # Manthan's unate detection does this.

        # For simplicity and robust global check as requested, let's stick to the
        # "F(X, Y) & !F(X, Y_{-y}, y_target=guess)" check for now,
        # but maybe we should use a fresh solver per variable if we don't use control variables?
        # Actually, adding clauses to a solver is permanent.
        # So we NEED a fresh solver or control variables.

        # Let's use a fresh solver for verification of EACH variable to keep it simple and correct.
        # Reusing the solver for bit-flip was already optimized away.
        # Reusing the solver for verification would require Tseitin with control variables.

        verify_solver = SATSolver(name=self.solver_name)
        try:
            for clause in clauses:
                verify_solver.add_clause(clause)

            z_base = 2 * num_vars + 1
            z_lits = []
            for j, clause in enumerate(clauses):
                z_j = z_base + j
                z_lits.append(z_j)
                for lit in clause:
                    var = abs(lit)
                    if var == y_target:
                        val = (guess == 1) if lit > 0 else (guess == 0)
                        if val:
                            verify_solver.add_clause([-z_j])
                    else:
                        verify_solver.add_clause([-z_j, -lit])

            verify_solver.add_clause(z_lits)
            return verify_solver.solve() is False
        finally:
            verify_solver.delete()
