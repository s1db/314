from typing import Dict, List, Optional, TYPE_CHECKING
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2Stratified
from src.candidate_function import CandidateFunction
from .maxsat import Manthan1MaxSATScheme
import logging

if TYPE_CHECKING:
    from src.dependency_schemes.base import DependencyScheme

logger = logging.getLogger(__name__)


class LexMaxSATScheme(Manthan1MaxSATScheme):
    """
    Fault localization based on Lexicographical MaxSAT using variable weights.
    Prioritizes keeping values of variables that appear earlier in the computation order.
    """

    def localize(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        dependency_scheme: Optional["DependencyScheme"] = None,
    ) -> List[int]:
        """
        Uses RC2 (MaxSAT) with weights prioritized by variable order.
        Earlier variables in the topological order get higher weights.
        """
        wcnf = WCNF()

        # 1. Determine variable weights based on topological order
        candidate_weights = {}
        if dependency_scheme:
            total_order = dependency_scheme.get_topological_order()
            order_map = {node: i for i, node in enumerate(total_order)}
            num_order = len(total_order)

            for var in candidates:
                if var in order_map:
                    candidate_weights[var] = num_order - order_map[var]
                else:
                    candidate_weights[var] = 1
        else:
            candidate_weights = {var: 1 for var in candidates}

        # 2. Add Hard Clauses (Matrix)
        for clause in self.instance.clauses:
            wcnf.append(clause)

        # 3. Add Hard Clauses (Inputs - Universal variables only)
        x_vars = set(self.instance.get_universal_vars())
        for x in x_vars:
            if x in assignment:
                val = assignment[x]
                wcnf.append([x if val else -x])

        # 4. Add Soft/Hard Clauses for Candidates
        for var, func in candidates.items():
            current_val = assignment.get(var)
            if current_val is None:
                continue

            lit = var if current_val else -var
            if not func.repairable:
                wcnf.append([lit])
                continue
            weight = candidate_weights.get(var, 1)
            wcnf.append([lit], weight=weight)

        # 5. Solve MaxSAT
        with RC2Stratified(wcnf) as rc2:
            model = rc2.compute()

        if model is None:
            logger.warning(
                "LexMaxSAT found no model. Matrix might be UNSAT for this counter-example."
            )
            return []

        # 6. Identify Faults
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
