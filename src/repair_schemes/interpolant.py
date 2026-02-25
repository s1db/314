"""Interpolant-based repair scheme using Craig interpolation.

Computes the beta correction formula via pySMT / MathSAT5 binary
interpolation.  When the hypothesis for a suspect variable is UNSAT,
the formula is split into two parts that share only the *allowed*
variables, and an interpolant over those shared variables serves as a
precise beta patch.

Falls back to the UNSAT-core method if interpolation fails.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from pysat.solvers import Solver as SATSolver

from pysmt.shortcuts import And, Interpolator, Not, Or, Symbol
from pysmt.fnode import FNode

from src.candidate_function import CandidateFunction, FunctionManager
from src.instance import Instance
from src.preprocessing.pysmt_unique import _fnode_to_candidate
from .base import RepairScheme

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Helpers (DIMACS ↔ pySMT, local to this module)
# ---------------------------------------------------------------------------


def _var_sym(var: int) -> FNode:
    """Return the pySMT Boolean Symbol for DIMACS variable ``var``."""
    return Symbol(f"v{var}")


def _lit_to_pysmt(lit: int) -> FNode:
    """Convert a signed DIMACS literal to a pySMT formula."""
    sym = _var_sym(abs(lit))
    return sym if lit > 0 else Not(sym)


def _clauses_to_pysmt_formula(clauses: List[List[int]]) -> FNode:
    """Convert a CNF clause list to a pySMT conjunction-of-disjunctions."""
    pysmt_clauses: List[FNode] = []
    for clause in clauses:
        if len(clause) == 1:
            pysmt_clauses.append(_lit_to_pysmt(clause[0]))
        else:
            pysmt_clauses.append(Or(*[_lit_to_pysmt(lit) for lit in clause]))
    if not pysmt_clauses:
        return Symbol("__true__")
    return And(*pysmt_clauses) if len(pysmt_clauses) > 1 else pysmt_clauses[0]


# ---------------------------------------------------------------------------
#  InterpolantRepairScheme
# ---------------------------------------------------------------------------


class InterpolantRepairScheme(RepairScheme):
    """Repair scheme that computes the beta patch via Craig interpolation.

    When the hypothesis ``Matrix ∧ assignment ∧ bad_value`` is UNSAT:

    * **Part A**: ``Matrix ∧ X-fixed ∧ allowed-Y-fixed ∧ (y = bad)``
    * **Part B**: ``Matrix ∧ X-fixed ∧ allowed-Y-fixed ∧ (y = ¬bad)``
    * Shared variables: allowed vars of *y* (X ∪ upstream Y)

    The binary interpolant ``I(shared)`` is the beta formula.

    If interpolation fails for any reason, falls back to extracting
    beta from the SAT solver's UNSAT core.
    """

    def __init__(
        self,
        instance: Instance,
        dependency_scheme: Any,
        function_manager: FunctionManager,
    ):
        super().__init__(instance, dependency_scheme, function_manager)
        # Build the symbol-name → DIMACS-var map used by _fnode_to_candidate
        all_vars: Set[int] = {abs(lit) for clause in instance.clauses for lit in clause}
        self._symbol_name_to_var: Dict[str, int] = {f"v{v}": v for v in all_vars}
        self._y_set: Set[int] = set(instance.get_existential_vars())

    # ------------------------------------------------------------------
    #  Beta via interpolation
    # ------------------------------------------------------------------

    def _compute_beta(
        self,
        candidate: CandidateFunction,
        variable: int,
        assignment: Dict[int, bool],
        allowed_vars: Set[int],
        sat_oracle: SATSolver,
    ) -> Optional[CandidateFunction]:
        """Compute beta via Craig interpolation; fall back to core."""
        beta = self._interpolation_beta(variable, assignment, allowed_vars)
        if beta is not None:
            return beta

        # Fallback: UNSAT-core method
        logger.debug(
            "Interpolation failed for variable %d, falling back to core.",
            variable,
        )
        return self._core_beta(variable, assignment, allowed_vars, sat_oracle)

    # ------------------------------------------------------------------

    def _interpolation_beta(
        self,
        variable: int,
        assignment: Dict[int, bool],
        allowed_vars: Set[int],
    ) -> Optional[CandidateFunction]:
        """Build Part-A / Part-B and run binary interpolation.

        The partition is chosen so that:
          - **Part A**: ``Matrix(X, Y) ∧ (y = bad)`` — the formula with
            the suspect forced to its bad value.  This is satisfiable on
            its own (the bad value is only wrong under *this* assignment).
          - **Part B**: the concrete counter-example — fixed X and
            allowed-Y assignments.

        Shared variables between A and B are exactly the *allowed*
        variables of ``y``.  The interpolant ``I(allowed)`` captures
        the condition under which the bad value leads to a conflict.
        """
        x_vars = self.instance.get_universal_vars()
        y_vars = self.instance.get_existential_vars()
        clauses = self.instance.clauses

        matrix = _clauses_to_pysmt_formula(clauses)
        bad_val = assignment[variable]

        # Part A: Matrix ∧ (y = bad)
        selector_a = _var_sym(variable) if bad_val else Not(_var_sym(variable))
        part_a = And(matrix, selector_a)

        # Part B: fixed X + fixed allowed-Y assignments
        fixed: List[FNode] = []
        for x in x_vars:
            if x in assignment:
                fixed.append(_var_sym(x) if assignment[x] else Not(_var_sym(x)))
        for y in y_vars:
            if y == variable:
                continue
            if y in allowed_vars and y in assignment:
                fixed.append(_var_sym(y) if assignment[y] else Not(_var_sym(y)))

        if not fixed:
            # No shared context — interpolation can't help
            return None

        part_b = And(*fixed) if len(fixed) > 1 else fixed[0]

        try:
            with Interpolator(name="msat") as itp:
                interpolant: Optional[FNode] = itp.binary_interpolant(part_a, part_b)
        except Exception as e:
            logger.debug("Interpolator exception for variable %d: %s", variable, e)
            return None

        if interpolant is None:
            # SAT → shouldn't normally happen (hypothesis was UNSAT)
            logger.debug(
                "Interpolant was None for variable %d (unexpected SAT?).",
                variable,
            )
            return None

        # Convert pySMT FNode → CandidateFunction.
        # The interpolant I is implied by Part A (the bad scenario) and
        # I ∧ B is UNSAT.  So I captures when the bad value is
        # *consistent*.  We want ¬I: the condition where the bad value
        # is *impossible* — that's the correction we need to apply.
        raw = _fnode_to_candidate(
            interpolant,
            self.function_manager,
            self._y_set,
            self._symbol_name_to_var,
        )
        beta = raw.Not(self.function_manager)
        logger.debug("Interpolation beta for variable %d: ¬(%s)", variable, interpolant)
        return beta

    # ------------------------------------------------------------------

    def _core_beta(
        self,
        variable: int,
        assignment: Dict[int, bool],
        allowed_vars: Set[int],
        sat_oracle: SATSolver,
    ) -> Optional[CandidateFunction]:
        """Fallback: compute beta from the UNSAT core."""
        core: Optional[List[int]] = sat_oracle.get_core()
        if core is None:
            return None

        beta_children: List[CandidateFunction] = []
        for lit in core:
            var = abs(lit)
            if var == variable:
                continue
            if var not in allowed_vars:
                continue
            node = self.function_manager.get_lit(lit)
            beta_children.append(node)

        if not beta_children:
            return None
        return self.function_manager.get_and(beta_children)
