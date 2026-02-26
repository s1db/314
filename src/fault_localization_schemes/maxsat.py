from typing import Dict, List, Optional, TYPE_CHECKING
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from src.candidate_function import CandidateFunction
from .base import FaultLocalizationScheme
import logging

if TYPE_CHECKING:
    from src.dependency_schemes.base import DependencyScheme

logger = logging.getLogger(__name__)


class Manthan1MaxSATScheme(FaultLocalizationScheme):
    """
    Fault localization based on Manthan's MaxSAT.
    Minimizes the number of candidates that need to be flipped to satisfy the matrix.
    """

    def localize(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        dependency_scheme: Optional["DependencyScheme"] = None,
    ) -> List[int]:
        """
        Uses RC2 (MaxSAT) to find a satisfying assignment for the Y variables that maximizes
        agreement with the current candidate evaluations, respecting non-repairable constraints.
        """
        wcnf = WCNF()

        # 1. Add Hard Clauses (Matrix)
        for clause in self.instance.clauses:
            wcnf.append(clause)

        # 2. Add Hard Clauses (Inputs - Universal variables only)
        x_vars = set(self.instance.get_universal_vars())
        for x in x_vars:
            if x in assignment:
                val = assignment[x]
                wcnf.append([x if val else -x])

        # 3. Add Soft/Hard Clauses for Candidates
        for var, func in candidates.items():
            current_val = assignment.get(var)
            if current_val is None:
                continue

            lit = var if current_val else -var
            if not func.repairable:
                continue
            # Repairable variables are soft constraints (minimize flips)
            wcnf.append([lit], weight=1)

        # 4. Solve MaxSAT
        with RC2(wcnf) as rc2:
            model = rc2.compute()

        if model is None:
            logger.warning(
                "MaxSAT found no model. Assignment over universal variables makes the matrix UNSAT."
            )
            return []

        # 5. Identify Faults
        faults = []
        model_map = {abs(lit): (lit > 0) for lit in model}

        for var in candidates:
            # Original value in assignment (from verifier)
            original_val = assignment.get(var)
            if original_val is None:
                continue

            # New value in MaxSAT model
            new_val = model_map.get(var)

            if new_val is not None and new_val != original_val:
                faults.append(var)

        return faults


class QuantifiedMaxSATScheme(FaultLocalizationScheme):
    """
    Fault localization based on MaxSAT, modified to respect the QBF quantifier hierarchy.
    Assigns exponential weights to soft constraints (candidate outputs), penalizing
    flips of outermost variables more heavily than innermost variables.
    """

    def localize(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        dependency_scheme: Optional["DependencyScheme"] = None,
    ) -> List[int]:
        """
        Uses RC2 (MaxSAT) to find a satisfying assignment for the Y variables.
        Soft constraints enforce candidate agreements, weighted by variable depth.
        """
        wcnf = WCNF()

        # 1. Add Hard Clauses (Matrix)
        for clause in self.instance.clauses:
            wcnf.append(clause)

        # 2. Add Hard Clauses (Inputs - Universal variables only)
        x_vars = set(self.instance.get_universal_vars())
        for x in x_vars:
            if x in assignment:
                val = assignment[x]
                wcnf.append([x if val else -x])

        # 3. Compute depths for weight assignment
        var_depths: Dict[int, int] = {}
        max_depth = 0
        current_depth = 0

        # Traverse quantifiers to determine block depth
        # We only increment depth for existential blocks to give them distinct weights
        for q_type, vars_in_block in self.instance.quantifiers:
            if q_type == "e":
                for v in vars_in_block:
                    var_depths[v] = current_depth
                max_depth = max(max_depth, current_depth)
                current_depth += 1

        # 4. Add Soft/Hard Clauses for Candidates
        for var, func in candidates.items():
            current_val = assignment.get(var)
            if current_val is None:
                continue

            lit = var if current_val else -var
            if not func.repairable:
                continue

            # Weight definition: w = 2^(max_depth - depth)
            # Outermost block (depth=0) gets max weight, innermost block gets weight=1
            depth = var_depths.get(var, max_depth)  # default to max depth if unknown
            weight = 2 ** (max_depth - depth)

            wcnf.append([lit], weight=weight)

        # 5. Solve MaxSAT
        with RC2(wcnf) as rc2:
            model = rc2.compute()

        if model is None:
            logger.warning(
                "QuantifiedMaxSAT found no model. Assignment over universal variables makes the matrix UNSAT."
            )
            return []

        # 6. Identify Faults
        faults = []
        model_map = {abs(lit): (lit > 0) for lit in model}

        for var in candidates:
            original_val = assignment.get(var)
            if original_val is None:
                continue

            new_val = model_map.get(var)

            if new_val is not None and new_val != original_val:
                faults.append(var)

        return faults
