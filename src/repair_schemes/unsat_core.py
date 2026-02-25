from typing import Dict, List, Optional, Set
import logging

from pysat.solvers import Solver

from src.candidate_function import CandidateFunction
from .base import RepairScheme

logger = logging.getLogger(__name__)


class UnsatCoreRepairScheme(RepairScheme):
    """
    Repair scheme that computes the beta patch from the UNSAT core.

    When the hypothesis ``Matrix ∧ assignment ∧ bad-value`` is UNSAT,
    the UNSAT core gives a subset of the assumptions that are jointly
    unsatisfiable.  The beta formula is the conjunction of core literals
    (filtered to the allowed dependency set).
    """

    def _compute_beta(
        self,
        candidate: CandidateFunction,
        variable: int,
        assignment: Dict[int, bool],
        allowed_vars: Set[int],
        sat_oracle: Solver,
    ) -> Optional[CandidateFunction]:
        """Compute beta from the UNSAT core."""
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
            return None  # Represents True
        return self.function_manager.get_and(beta_children)
