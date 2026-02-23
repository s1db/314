"""Manthan-style unate preprocessing.

Reproduces the definability-based unate detection algorithm from
`manthan-preprocess <https://github.com/meelgroup/manthan-preprocess>`_.

For each existential variable *y* the algorithm checks whether *y* is
forced to a constant value (positive-unate = always 1, negative-unate =
always 0).  Detected unates are assigned constant Skolem functions and
marked ``repairable=False``.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
from pysat.solvers import Solver as SATSolver

from src.candidate_function import CandidateFunction, FunctionManager
from src.preprocessing.base import Preprocessor

logger = logging.getLogger(__name__)


class ManthanUnatePreprocessor(Preprocessor):
    """Definability-based unate detector using PySAT.

    Parameters
    ----------
    solver_name:
        PySAT solver backend (default ``"g4"`` = Glucose4).
    conf_budget:
        Conflict budget per SAT call. ``0`` means unlimited (complete check).
        Manthan's default is ``50`` (incomplete but fast).
    """

    def __init__(self, solver_name: str = "g4", conf_budget: int = 50):
        self.solver_name = solver_name
        self.conf_budget = conf_budget

    # ------------------------------------------------------------------ #
    #  Public API                                                        #
    # ------------------------------------------------------------------ #

    def run(
        self,
        clauses: List[List[int]],
        x_vars: List[int],
        y_vars: List[int],
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
        samples: Optional[np.ndarray] = None,
    ) -> None:
        if not y_vars:
            return

        num_vars = max(
            max((abs(lit) for clause in clauses for lit in clause), default=0),
            max((abs(v) for v in x_vars + y_vars), default=0),
        )
        y_set = set(y_vars)

        solver = SATSolver(name=self.solver_name)
        try:
            self._run_detection(
                solver,
                clauses,
                y_vars,
                y_set,
                num_vars,
                candidates,
                function_manager,
            )
        finally:
            solver.delete()

    # ------------------------------------------------------------------ #
    #  Construction                                                      #
    # ------------------------------------------------------------------ #

    def _run_detection(
        self,
        solver: SATSolver,
        clauses: List[List[int]],
        y_vars: List[int],
        y_set: set[int],
        num_vars: int,
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
    ) -> None:
        """Build the definability formula and run unate detection."""

        # Variable allocation:
        #   1..num_vars          — original variables
        #   y'_i = y_i + num_vars — primed copies of Y
        #   c_i  = y_i + 2*num_vars — control variables
        #   z_j  = num_vars*3 + 1 + j — Tseitin aux for ¬F(X, Y')

        prime_offset = num_vars
        control_offset = 2 * num_vars
        z_base = 3 * num_vars + 1  # first z variable

        # 1. Add F(X, Y)
        for clause in clauses:
            solver.add_clause(clause)

        # 2. For each y, add Equality encoding: c_i → (y_i ↔ y'_i)
        #    Encoded as: (¬c_i ∨ ¬y_i ∨ y'_i) ∧ (¬c_i ∨ y_i ∨ ¬y'_i)
        for y in y_vars:
            yp = y + prime_offset
            c = y + control_offset
            # ¬c ∨ ¬y ∨ yp
            solver.add_clause([-c, -y, yp])
            # ¬c ∨ y ∨ ¬yp
            solver.add_clause([-c, y, -yp])

        # 3. Add ¬F(X, Y') via Tseitin
        #    For each clause C_j of F, create z_j such that
        #    z_j = 1 iff all literals of C_j[Y→Y'] are false.
        #    Then assert (z_1 ∨ z_2 ∨ ... ∨ z_m) — at least one clause falsified.
        z_lits: List[int] = []
        for j, clause in enumerate(clauses):
            z_j = z_base + j
            z_lits.append(z_j)

            # For each literal l' in the primed clause:
            #   z_j → ¬l'  ⟺  ¬z_j ∨ ¬l'
            for lit in clause:
                var = abs(lit)
                if var in y_set:
                    # Replace y with y'
                    lit_prime = (
                        (var + prime_offset) if lit > 0 else -(var + prime_offset)
                    )
                else:
                    # X vars (and any others) stay the same
                    lit_prime = lit
                solver.add_clause([-z_j, -lit_prime])

        # At least one original clause must be falsified in the primed copy
        solver.add_clause(z_lits)

        # 4. Run detection
        #    Start with all c_i assumed true (all y forced to differ from y')
        #    Process in reverse order as manthan-preprocess does.
        active_controls: List[int] = [y + control_offset for y in reversed(y_vars)]

        pos_unates: List[int] = []
        neg_unates: List[int] = []

        for y in y_vars:
            c = y + control_offset
            yp = y + prime_offset

            # Release this variable's control
            active_controls = [a for a in active_controls if a != c]

            # -- Positive unate test: y=0, y'=1 --
            assumptions = list(active_controls) + [-y, yp]
            is_pos_unate = self._solve_limited(solver, assumptions)

            if is_pos_unate:
                pos_unates.append(y)
                # Fix y=1 and y'=1
                solver.add_clause([y])
                solver.add_clause([yp])
                # Set candidate
                func = function_manager.get_true()
                func.repairable = False
                candidates[y] = func
                continue

            # -- Negative unate test: y=1, y'=0 --
            assumptions = list(active_controls) + [y, -yp]
            is_neg_unate = self._solve_limited(solver, assumptions)

            if is_neg_unate:
                neg_unates.append(y)
                # Fix y=0 and y'=0
                solver.add_clause([-y])
                solver.add_clause([-yp])
                # Set candidate
                func = function_manager.get_false()
                func.repairable = False
                candidates[y] = func
            else:
                # Not unate — assert control (y must differ from y')
                solver.add_clause([c])

        logger.info(
            "Unate detection: %d positive, %d negative out of %d existential vars",
            len(pos_unates),
            len(neg_unates),
            len(y_vars),
        )
        if pos_unates:
            logger.debug("Positive unates: %s", pos_unates)
        if neg_unates:
            logger.debug("Negative unates: %s", neg_unates)

    # ------------------------------------------------------------------ #
    #  Helpers                                                           #
    # ------------------------------------------------------------------ #

    def _solve_limited(self, solver: SATSolver, assumptions: List[int]) -> bool:
        """Solve with optional conflict budget. Returns True if UNSAT."""
        if self.conf_budget > 0:
            solver.conf_budget(self.conf_budget)
            result = solver.solve_limited(assumptions=assumptions)
            # solve_limited returns None on budget exhaustion
            return result is False
        else:
            result = solver.solve(assumptions=assumptions)
            return not result
