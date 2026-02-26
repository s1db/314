"""Manthan-style uniquely-defined function preprocessor.

Detects existential variables whose value is **uniquely determined**
by a subset of defining variables (X ∪ earlier-Y).  Uses the
interpolating MiniSAT solver from Manthan's ``unique`` dependency
(``itp`` C++ module) to both check definability *and* extract a
concrete Skolem function as a list of AND-of-literal clauses.

Algorithm (per Manthan's ``DefinabilityChecker``):

For each existential *y* with defining variables *D*:

    F(X, Y)  ∧  F(X, Y')  ∧  (∀d ∈ D: d = d')  ∧  (y ≠ y')

If UNSAT, *y* is uniquely defined by *D* and the interpolant gives
a concrete Skolem function.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.dependency_schemes.base import DependencyScheme

import numpy as np
from pysat.solvers import Solver as SATSolver

from src.candidate_function import CandidateFunction, FunctionManager
from src.preprocessing.base import Preprocessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Low-level helpers (mirrors Manthan's Utils.py)
# ---------------------------------------------------------------------------

ITP_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "dependencies", "itp"
)


def _ensure_itp_importable() -> None:
    """Add the itp shared-library directory to *sys.path* once."""
    resolved = os.path.realpath(ITP_DIR)
    if resolved not in sys.path:
        sys.path.insert(0, resolved)


def _minisat_literals(literals: List[int]) -> List[int]:
    """Convert signed DIMACS literals to MiniSAT internal encoding."""
    return [2 * abs(lit) + (lit < 0) for lit in literals]


def _minisat_clauses(clauses: List[List[int]]) -> List[List[int]]:
    return [_minisat_literals(c) for c in clauses]


def _max_var_index(clause_list: List[List[int]]) -> int:
    return max((abs(lit) for c in clause_list for lit in c), default=0)


def _rename_literal(lit: int, renaming: Dict[int, int]) -> int:
    return renaming.get(lit, lit) if lit > 0 else -renaming.get(abs(lit), abs(lit))


def _rename_clause(clause: List[int], renaming: Dict[int, int]) -> List[int]:
    return [_rename_literal(lit, renaming) for lit in clause]


def _rename_formula(
    clauses: List[List[int]], renaming: Dict[int, int]
) -> List[List[int]]:
    return [_rename_clause(c, renaming) for c in clauses]


def _equality(lit1: int, lit2: int, switch: int) -> List[List[int]]:
    """Conditional equality:  switch → (lit1 ↔ lit2)."""
    return [[-switch, lit1, -lit2], [-switch, -lit1, lit2]]


def _candidate_to_clauses(
    output_var: int,
    func: "CandidateFunction",
    aux_start: int,
) -> Tuple[List[List[int]], int]:
    """Tseitin-encode ``output_var ↔ func`` into CNF clauses.

    Returns ``(clauses, next_aux)`` where *next_aux* is the first
    unused auxiliary variable index.
    """
    from src.candidate_function import NodeType

    clauses: List[List[int]] = []
    memo: Dict[int, int] = {}  # CandidateFunction id → variable representing it
    counter = aux_start

    def _encode(node: "CandidateFunction") -> int:
        """Return the DIMACS variable whose truth matches *node*."""
        nonlocal counter
        node_id = id(node)
        if node_id in memo:
            return memo[node_id]

        if node.node_type == NodeType.CONSTANT:
            g = counter
            counter += 1
            # Force g to the constant value
            clauses.append([g] if node.value == 1 else [-g])
            memo[node_id] = g
            return g

        if node.node_type == NodeType.LITERAL:
            assert node.value is not None
            # No auxiliary needed — the literal itself is the variable.
            # Return the *signed* variable but memo stores the unsigned key.
            memo[node_id] = node.value
            return node.value

        # Allocate a gate variable for composite nodes
        g = counter
        counter += 1
        memo[node_id] = g

        if node.node_type == NodeType.AND:
            child_lits = [_encode(c) for c in node.children]
            # g ↔ AND(c1, c2, ...)
            # Forward:  g → ci   ⟺  ¬g ∨ ci
            for ci in child_lits:
                clauses.append([-g, ci])
            # Backward: c1 ∧ c2 ∧ ... → g  ⟺  ¬c1 ∨ ¬c2 ... ∨ g
            clauses.append([-ci for ci in child_lits] + [g])

        elif node.node_type == NodeType.OR:
            child_lits = [_encode(c) for c in node.children]
            # g ↔ OR(c1, c2, ...)
            # Forward:  g → (c1 ∨ c2 ∨ ...)  ⟺  ¬g ∨ c1 ∨ c2 ...
            clauses.append([-g] + child_lits)
            # Backward: ci → g  ⟺  ¬ci ∨ g
            for ci in child_lits:
                clauses.append([-ci, g])

        elif node.node_type == NodeType.ITE:
            s = _encode(node.children[0])
            t = _encode(node.children[1])
            e = _encode(node.children[2])
            # g ↔ ITE(s, t, e) = (s ∧ t) ∨ (¬s ∧ e)
            # Clauses: (¬g ∨ ¬s ∨ t), (¬g ∨ s ∨ e),
            #          (g ∨ ¬s ∨ ¬t), (g ∨ s ∨ ¬e)
            clauses.append([-g, -s, t])
            clauses.append([-g, s, e])
            clauses.append([g, -s, -t])
            clauses.append([g, s, -e])

        return g

    root = _encode(func)
    # Assert output_var ↔ root
    if isinstance(root, int) and abs(root) == output_var:
        # Already the same variable — nothing to encode
        pass
    else:
        clauses.append([-output_var, root])
        clauses.append([output_var, -root])

    return clauses, counter


# ---------------------------------------------------------------------------
#  InterpolatingSolver wrapper (mirrors Manthan's InterpolatingSolver.py)
# ---------------------------------------------------------------------------

TRIBOOL_FALSE = 0
TRIBOOL_TRUE = 1
TRIBOOL_INDETERMINATE = 2


class _InterpolatingSolver:
    """Thin Python wrapper around the ``itp`` C++ module."""

    def __init__(self, first_part: List[List[int]], second_part: List[List[int]]):
        _ensure_itp_importable()
        import itp as _itp  # type: ignore[import-untyped]

        self._itp = _itp
        self.max_var_index = _max_var_index(first_part + second_part)
        self.solver: Any = _itp.InterpolatingMiniSAT(self.max_var_index)
        self.solver.addFormula(
            _minisat_clauses(first_part), _minisat_clauses(second_part)
        )

    def add_clause(self, literals: List[int], first_part: bool = True) -> None:
        max_var = max(abs(v) for v in literals)
        if max_var > self.max_var_index:
            self.max_var_index = max_var
            self.solver.reserve(self.max_var_index)
        part = 1 if first_part else 2
        self.solver.addClause(_minisat_literals(literals), part)

    def solve(self, assumptions: Optional[List[int]] = None, limit: int = 1000) -> int:
        if assumptions is None:
            assumptions = []
        return self.solver.solve(_minisat_literals(assumptions), limit)

    def get_definition(
        self,
        input_variable_ids: List[int],
        output_variable_id: int,
        offset: int,
        compress: bool = False,
    ) -> Any:
        return self.solver.getDefinition(
            input_variable_ids,
            output_variable_id,
            compress,
            max(self.max_var_index, offset),
        )

    def get_var_val(self, variable: int) -> int:
        return self.solver.getVarVal(variable)

    def get_assignment(self, variables: List[int]) -> Dict[int, int]:
        return {v: self.solver.getVarVal(v) for v in variables}


# ---------------------------------------------------------------------------
#  DefinabilityChecker (mirrors Manthan's DefinabilityChecker.py)
# ---------------------------------------------------------------------------


class _DefinabilityChecker:
    """Checks whether an existential variable is uniquely defined.

    Builds the formula:
        Part 1: F(X, Y) + on-selectors
        Part 2: F(X, Y') + off-selectors + equality selectors
    """

    def __init__(self, formula: List[List[int]], existentials: List[int]):
        self.max_variable = _max_var_index(formula)
        variables: Set[int] = {abs(lit) for clause in formula for lit in clause}
        self.renaming: Dict[int, int] = {v: v + self.max_variable for v in variables}
        formula_copy = _rename_formula(formula, self.renaming)

        # On/off selectors for existential variables
        self.on_selector_dict: Dict[int, int] = {
            v: v + (2 * self.max_variable) for v in existentials
        }
        on: List[List[int]] = [[v, -self.on_selector_dict[v]] for v in existentials]

        self.off_selector_dict: Dict[int, int] = {
            v: v + (3 * self.max_variable) for v in existentials
        }
        off: List[List[int]] = []
        for v in existentials:
            if v in self.renaming:
                off.append([-self.renaming[v], -self.off_selector_dict[v]])

        # Equality selectors for all variables
        self.eq_selector_dict: Dict[int, int] = {
            v: v + (4 * self.max_variable) for v in variables
        }
        eq: List[List[int]] = [
            eq_clause
            for v in variables
            for eq_clause in _equality(v, self.renaming[v], self.eq_selector_dict[v])
        ]

        self.max_variable = 5 * self.max_variable

        self.solver = _InterpolatingSolver(formula + on, formula_copy + off + eq)
        self.backbone_solver = SATSolver(name="cadical195", bootstrap_with=formula)

    def add_clause(self, clause: List[int]) -> None:
        self.solver.add_clause(clause, True)
        renamed = _rename_clause(clause, self.renaming)
        self.solver.add_clause(renamed, False)
        self.backbone_solver.add_clause(clause)

    def check_definability(
        self,
        defining_variables: List[int],
        defined_variable: int,
        offset: Optional[int] = None,
        assumptions: Optional[List[int]] = None,
    ) -> Tuple[bool, Any]:
        if offset is None:
            offset = self.max_variable + 1
        if assumptions is None:
            assumptions = []

        # First check backbone (is the variable forced to a constant?)
        is_forced, forced_def = self._check_forced(defined_variable)
        if is_forced:
            return True, forced_def

        # Equality assumptions for defining variables
        eq_enabled = [
            self.eq_selector_dict[v]
            for v in defining_variables
            if v in self.eq_selector_dict
        ]
        defining_set = set(defining_variables)
        eq_disabled = [
            -self.eq_selector_dict[v]
            for v in self.eq_selector_dict
            if v not in defining_set
        ]

        on = self.on_selector_dict[defined_variable]
        off = self.off_selector_dict[defined_variable]

        all_assumptions = eq_disabled + eq_enabled + assumptions + [on, off]
        satisfiable = self.solver.solve(all_assumptions)

        if satisfiable == TRIBOOL_FALSE:
            definition = self.solver.get_definition(
                defining_variables, defined_variable, offset
            )
            return True, definition
        else:
            return False, None

    def _check_forced(self, variable: int) -> Tuple[bool, Any]:
        if not self.backbone_solver.solve(assumptions=[variable]):
            return True, [[-variable]]
        elif not self.backbone_solver.solve(assumptions=[-variable]):
            return True, [[variable]]
        else:
            return False, None

    def delete(self) -> None:
        self.backbone_solver.delete()


# ---------------------------------------------------------------------------
#  Public preprocessor
# ---------------------------------------------------------------------------


class ManthanUniquePreprocessor(Preprocessor):
    """Detects uniquely defined existential variables using an
    interpolating SAT solver, following Manthan's approach.

    For each existential variable *y*, checks whether *y* is uniquely
    determined by ``x_vars + y_vars[:i]`` (variables that come before *y*
    in the quantifier prefix).  When uniquely defined, the interpolant
    provides a concrete Skolem function which is stored as a
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

        # Augment the formula with clauses encoding  y ↔ f(support)  for
        # every already-resolved variable.  This lets the
        # DefinabilityChecker see that those variables are determined,
        # enabling it to detect more uniquely-defined functions downstream.
        augmented_clauses = list(clauses)
        num_vars = _max_var_index(clauses)
        aux_start = num_vars + 1
        for y in resolved:
            if y in candidates:
                new_clauses, aux_start = candidates[y].to_cnf(y, aux_start)
                augmented_clauses.extend(new_clauses)

        checker = _DefinabilityChecker(augmented_clauses, y_vars)
        try:
            self._run_detection(
                checker,
                clauses,
                x_vars,
                y_vars,
                y_set,
                resolved,
                candidates,
                function_manager,
                dep_scheme,
            )
        finally:
            checker.delete()

    def _run_detection(
        self,
        checker: _DefinabilityChecker,
        clauses: List[List[int]],
        x_vars: List[int],
        y_vars: List[int],
        y_set: Set[int],
        resolved: Set[int],
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
        dep_scheme: Optional["DependencyScheme"] = None,
    ) -> None:
        num_vars = _max_var_index(clauses)
        offset = 5 * num_vars + 100
        unique_vars: List[int] = []

        for itr, y in enumerate(y_vars):
            if y in resolved:
                continue

            if dep_scheme:
                defining_vars = list(dep_scheme.prefix_scope.get(y, set()))
            else:
                defining_y = y_vars[:itr]
                defining_vars = x_vars + defining_y

            result = checker.check_definability(defining_vars, y, offset)

            if result[0]:
                unique_vars.append(y)
                definition = result[1]
                func = self._definition_to_candidate(
                    definition,
                    y,
                    x_vars,
                    y_vars,
                    y_set,
                    function_manager,
                )
                func.repairable = False
                candidates[y] = func
                logger.debug(
                    "Unique: variable %d uniquely defined (definition=%s)",
                    y,
                    definition,
                )
            offset += 100

        logger.info(
            "Unique detection: %d uniquely defined out of %d existential vars",
            len(unique_vars),
            len(y_vars),
        )
        if unique_vars:
            logger.debug("Uniquely defined vars: %s", unique_vars)

    @staticmethod
    def _definition_to_candidate(
        definition: Any,
        y: int,
        x_vars: List[int],
        y_vars: List[int],
        y_set: Set[int],
        fm: FunctionManager,
    ) -> CandidateFunction:
        """Convert the ITP solver's definition to a ``CandidateFunction``.

        The definition can be:
        - A list of (clause, gate_var) pairs forming an CNF circuit
        - A single literal (forced constant/copy)
        - A tuple wrapping one of the above
        """
        if definition is None:
            return fm.get_true()

        # Unwrap tuple if needed
        if isinstance(definition, tuple):
            definition = definition[0]

        # Single literal (constant or unit)
        if isinstance(definition, int):
            if definition > 0:
                return fm.get_true()
            else:
                return fm.get_false()

        # List of clauses — build AND of ORs
        or_children: List[CandidateFunction] = []
        temp_map: Dict[int, CandidateFunction] = {}

        for item in definition:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                clause, gate_var = item[0], item[1]
            elif isinstance(item, (list, tuple)) and len(item) == 1:
                # Single-element list — just a literal
                lit = item[0]
                if isinstance(lit, int):
                    return _lit_to_func(lit, x_vars, y_vars, y_set, fm, temp_map)
                clause = item
                gate_var = None
            else:
                # Fallback — treat as a single literal
                if isinstance(item, int):
                    return _lit_to_func(item, x_vars, y_vars, y_set, fm, temp_map)
                continue

            if isinstance(clause, (list, tuple)):
                lits: List[CandidateFunction] = []
                for lit in clause:
                    if isinstance(lit, int):
                        lits.append(
                            _lit_to_func(lit, x_vars, y_vars, y_set, fm, temp_map)
                        )
                func = (
                    fm.get_and(lits)
                    if len(lits) > 1
                    else (lits[0] if lits else fm.get_true())
                )

                if gate_var is not None:
                    var_key = abs(gate_var) if isinstance(gate_var, int) else gate_var
                    if isinstance(var_key, int) and var_key not in y_set:
                        temp_map[var_key] = func
                    else:
                        # This is the final assignment to y
                        return func
                else:
                    or_children.append(func)
            elif isinstance(clause, int):
                # Single literal defining the variable
                return _lit_to_func(clause, x_vars, y_vars, y_set, fm, temp_map)

        if or_children:
            return fm.get_and(or_children)

        return fm.get_true()


def _lit_to_func(
    lit: int,
    x_vars: List[int],
    y_vars: List[int],
    y_set: Set[int],
    fm: FunctionManager,
    temp_map: Dict[int, CandidateFunction],
) -> CandidateFunction:
    """Convert a DIMACS literal to a ``CandidateFunction``."""
    var = abs(lit)

    # Check if it's a temporary gate variable
    if var in temp_map:
        func = temp_map[var]
        return func if lit > 0 else func.Not(fm)

    # Regular variable — create a literal node
    return fm.get_lit(lit)
