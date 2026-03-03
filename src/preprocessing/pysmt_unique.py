"""Uniquely-defined function preprocessor using pySMT Craig interpolation.

Detects existential variables whose value is **uniquely determined**
by a subset of defining variables (X ∪ earlier-Y) and extracts
concrete Skolem functions via Craig interpolation (MathSAT5 backend).

Algorithm:

For each existential *y* with defining variables *D*:

    Part A:  F(X, Y)  ∧  (y = val)        [on-selector]
    Part B:  F(X, Y') ∧  (y' = ¬val)      [off-selector]
             ∧  (∀d ∈ D: d = d')           [equalities]

If A ∧ B is UNSAT, *y* is uniquely defined by *D* and the
binary interpolant gives a concrete Skolem function over the
shared (defining) variables.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.dependency_schemes.base import DependencyScheme

import numpy as np

from pysmt.shortcuts import (
    And,
    Iff,
    Interpolator,
    Not,
    Or,
    Symbol,
)
from pysmt.fnode import FNode
import pysmt.operators as op

from src.candidate_function import CandidateFunction, FunctionManager
from src.preprocessing.base import Preprocessor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  DIMACS ↔ pySMT conversion helpers
# ---------------------------------------------------------------------------


def _dimacs_var_symbol(var: int) -> FNode:
    """Return the pySMT Boolean Symbol for DIMACS variable ``var``."""
    return Symbol(f"v{var}")


def _dimacs_lit_to_pysmt(lit: int) -> FNode:
    """Convert a signed DIMACS literal to a pySMT formula."""
    sym = _dimacs_var_symbol(abs(lit))
    return sym if lit > 0 else Not(sym)


def _clauses_to_pysmt(clauses: List[List[int]]) -> FNode:
    """Convert a CNF clause list to a pySMT formula (conjunction of disjunctions)."""
    pysmt_clauses: List[FNode] = []
    for clause in clauses:
        if len(clause) == 1:
            pysmt_clauses.append(_dimacs_lit_to_pysmt(clause[0]))
        else:
            pysmt_clauses.append(Or(*[_dimacs_lit_to_pysmt(lit) for lit in clause]))
    if not pysmt_clauses:
        return Symbol("__true__")  # empty formula is vacuously true
    return And(*pysmt_clauses) if len(pysmt_clauses) > 1 else pysmt_clauses[0]


def _rename_clauses(
    clauses: List[List[int]], renaming: Dict[int, int]
) -> List[List[int]]:
    """Apply variable renaming to a clause list."""
    result: List[List[int]] = []
    for clause in clauses:
        new_clause: List[int] = []
        for lit in clause:
            var = abs(lit)
            new_var = renaming.get(var, var)
            new_clause.append(new_var if lit > 0 else -new_var)
        result.append(new_clause)
    return result


# ---------------------------------------------------------------------------
#  FNode → CandidateFunction conversion
# ---------------------------------------------------------------------------


def _fnode_to_candidate(
    node: FNode,
    fm: FunctionManager,
    y_set: Set[int],
    renaming_inv: Dict[str, int],
) -> CandidateFunction:
    """Recursively convert a pySMT FNode to a CandidateFunction.

    Parameters
    ----------
    node:
        pySMT formula node.
    fm:
        Function manager for structural hashing.
    y_set:
        Set of existential variable IDs (for reference).
    renaming_inv:
        Map from pySMT symbol name (e.g. "v3") to DIMACS variable ID.
    """
    node_type = node.node_type()

    if node.is_true():
        return fm.get_true()
    if node.is_false():
        return fm.get_false()

    if node_type == op.SYMBOL:
        name = node.symbol_name()
        if name in renaming_inv:
            return fm.get_lit(renaming_inv[name])
        # Fallback: parse "v<N>" format
        if name.startswith("v"):
            var_id = int(name[1:])
            return fm.get_lit(var_id)
        return fm.get_true()  # unknown symbol — safe fallback

    if node_type == op.NOT:
        child = _fnode_to_candidate(node.arg(0), fm, y_set, renaming_inv)
        return child.Not(fm)

    if node_type == op.AND:
        children = [
            _fnode_to_candidate(arg, fm, y_set, renaming_inv) for arg in node.args()
        ]
        return fm.get_and(children)

    if node_type == op.OR:
        children = [
            _fnode_to_candidate(arg, fm, y_set, renaming_inv) for arg in node.args()
        ]
        return fm.get_or(children)

    if node_type == op.IMPLIES:
        # a → b  ≡  ¬a ∨ b
        a = _fnode_to_candidate(node.arg(0), fm, y_set, renaming_inv)
        b = _fnode_to_candidate(node.arg(1), fm, y_set, renaming_inv)
        return fm.get_or([a.Not(fm), b])

    if node_type == op.IFF:
        # a ↔ b  ≡  (a ∧ b) ∨ (¬a ∧ ¬b)
        a = _fnode_to_candidate(node.arg(0), fm, y_set, renaming_inv)
        b = _fnode_to_candidate(node.arg(1), fm, y_set, renaming_inv)
        return fm.get_or([fm.get_and([a, b]), fm.get_and([a.Not(fm), b.Not(fm)])])

    if node_type == op.ITE:
        cond = _fnode_to_candidate(node.arg(0), fm, y_set, renaming_inv)
        then_br = _fnode_to_candidate(node.arg(1), fm, y_set, renaming_inv)
        else_br = _fnode_to_candidate(node.arg(2), fm, y_set, renaming_inv)
        return fm.get_ite(cond, then_br, else_br)

    # Fallback for any other node type
    logger.warning("Unknown pySMT node type %s, returning True", node_type)
    return fm.get_true()


# ---------------------------------------------------------------------------
#  DefinabilityChecker using pySMT interpolation
# ---------------------------------------------------------------------------


class _PySMTDefinabilityChecker:
    """Checks whether an existential variable is uniquely defined
    using pySMT's Craig interpolation (MathSAT5 backend).

    For a variable y with defining variables D:
        Part A:  F(X, Y)  ∧  on_selector(y)
        Part B:  F(X, Y') ∧  off_selector(y') ∧  equalities(D, D')

    If UNSAT, the interpolant I(D) is the Skolem function for y.
    """

    def __init__(
        self,
        clauses: List[List[int]],
        existentials: List[int],
        num_vars: Optional[int] = None,
    ):
        self.clauses = clauses
        self.existentials = existentials
        if num_vars is None:
            self.max_variable = max((abs(lit) for c in clauses for lit in c), default=0)
        else:
            self.max_variable = num_vars

        # Build variable sets
        all_vars: Set[int] = {abs(lit) for clause in clauses for lit in clause}
        if num_vars is not None:
            all_vars.update(existentials)
        self.all_vars = all_vars

        # Create renaming for primed copies: v → v + max_var
        self.renaming: Dict[int, int] = {v: v + self.max_variable for v in all_vars}
        self.renaming_inv: Dict[int, int] = {v + self.max_variable: v for v in all_vars}

        # Primed copy of formula
        self.primed_clauses = _rename_clauses(clauses, self.renaming)

        # Build inverse symbol name map for interpolant conversion
        self.symbol_name_to_var: Dict[str, int] = {f"v{v}": v for v in all_vars}

    def check_definability(
        self,
        defining_variables: List[int],
        defined_variable: int,
    ) -> Tuple[bool, Optional[FNode]]:
        """Check if defined_variable is uniquely defined by defining_variables.

        Returns (is_unique, interpolant_or_None).
        """
        # Part A: F(X, Y) ∧ (y = True)   [on-selector]
        part_a_formula = _clauses_to_pysmt(self.clauses)
        on_selector = _dimacs_var_symbol(defined_variable)
        part_a = And(part_a_formula, on_selector)

        # Part B: F(X, Y') ∧ (y' = False) ∧ equalities for defining vars
        part_b_formula = _clauses_to_pysmt(self.primed_clauses)
        off_selector = Not(_dimacs_var_symbol(self.renaming[defined_variable]))

        # Equalities: for each defining variable d, assert d = d'
        equalities: List[FNode] = []
        for d in defining_variables:
            if d in self.renaming:
                equalities.append(
                    Iff(_dimacs_var_symbol(d), _dimacs_var_symbol(self.renaming[d]))
                )

        part_b_parts = [part_b_formula, off_selector] + equalities
        part_b = And(*part_b_parts) if len(part_b_parts) > 1 else part_b_parts[0]

        # Run interpolation
        try:
            with Interpolator(name="msat") as itp:
                interpolant = itp.binary_interpolant(part_a, part_b)
        except Exception as e:
            logger.debug(
                "Interpolation failed for variable %d: %s", defined_variable, e
            )
            return False, None

        if interpolant is None:
            # SAT — variable is not uniquely defined
            return False, None

        # UNSAT — interpolant is the Skolem function for y
        return True, interpolant

    def add_clauses(self, new_clauses: List[List[int]]) -> None:
        """Augment the formula with additional clauses (e.g., Tseitin
        encodings of resolved candidates)."""
        self.clauses = self.clauses + new_clauses
        self.primed_clauses = self.primed_clauses + _rename_clauses(
            new_clauses, self.renaming
        )
        # Update max variable
        new_max = max((abs(lit) for c in new_clauses for lit in c), default=0)
        if new_max > self.max_variable:
            # Extend renaming for new variables
            for v in range(self.max_variable + 1, new_max + 1):
                if v not in self.renaming:
                    self.renaming[v] = v + self.max_variable
                    self.renaming_inv[v + self.max_variable] = v
                    self.symbol_name_to_var[f"v{v}"] = v


# ---------------------------------------------------------------------------
#  Public preprocessor
# ---------------------------------------------------------------------------


class PySMTUniquePreprocessor(Preprocessor):
    """Detects uniquely defined existential variables using Craig
    interpolation via pySMT (MathSAT5 backend).

    For each existential variable *y*, checks whether *y* is uniquely
    determined by ``x_vars + y_vars[:i]``.  When uniquely defined, the
    interpolant provides a concrete Skolem function which is stored as a
    ``CandidateFunction`` with ``repairable=False``.
    """

    def run(
        self,
        clauses: List[List[int]],
        x_vars: List[int],
        y_vars: List[int],
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
        samples: Optional[np.ndarray] = None,
        dep_scheme: Optional["DependencyScheme"] = None,
    ) -> None:
        if not y_vars:
            return

        y_set = set(y_vars)
        resolved: Set[int] = {y for y, c in candidates.items() if not c.repairable}

        # Augment the formula with Tseitin encodings of already-resolved
        # candidates so the checker can leverage them for cascading detection.
        augmented_clauses = list(clauses)
        num_vars = max(
            max((abs(lit) for c in clauses for lit in c), default=0),
            max(x_vars, default=0),
            max(y_vars, default=0),
        )
        aux_start = num_vars + 1
        for y in resolved:
            if y in candidates:
                new_clauses, aux_start = candidates[y].to_cnf(y, aux_start)
                augmented_clauses.extend(new_clauses)

        checker = _PySMTDefinabilityChecker(
            augmented_clauses, y_vars, num_vars=num_vars
        )

        unique_vars: List[int] = []

        for itr, y in enumerate(y_vars):
            if y in resolved:
                continue

            if dep_scheme:
                defining_vars = list(dep_scheme.prefix_scope.get(y, set()))
            else:
                defining_y = y_vars[:itr]
                defining_vars = x_vars + defining_y

            is_unique, interpolant = checker.check_definability(defining_vars, y)

            if is_unique and interpolant is not None:
                unique_vars.append(y)
                func = _fnode_to_candidate(
                    interpolant,
                    function_manager,
                    y_set,
                    checker.symbol_name_to_var,
                )
                func.repairable = False
                candidates[y] = func
                logger.debug(
                    "Unique: variable %d uniquely defined (interpolant=%s)",
                    y,
                    interpolant,
                )

        logger.info(
            "Unique detection: %d uniquely defined out of %d existential vars",
            len(unique_vars),
            len(y_vars),
        )
        if unique_vars:
            logger.debug("Uniquely defined vars: %s", unique_vars)
