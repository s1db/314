from typing import Dict, List
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from src.candidate_function import CandidateFunction
from .maxsat import MaxSATScheme


class LexMaxSATScheme(MaxSATScheme):
    """
    Fault localization based on Lexicographical MaxSAT using variable weights.
    Prioritizes keeping values of variables that appear earlier in the prefix.
    """

    def localize(
        self, candidates: Dict[int, CandidateFunction], assignment: Dict[int, bool]
    ) -> List[int]:
        """
        Uses RC2 (MaxSAT) with weights prioritized by variable order.
        Earlier variables in the prefix get higher weights, discouraging them from being identified as faults.
        """
        wcnf = WCNF()

        # 1. Determine variable order and weights
        # Extract all existential variables in order
        existential_vars = []
        for q_type, vars_list in self.instance.quantifiers:
            if q_type == "e":
                existential_vars.extend(vars_list)

        # Create a map from var -> weight
        # Only for variables in candidates
        # Weight = len(existential_vars) - index + bound
        # The variables not in 'existential_vars' (if any, e.g. free vars?) should be handled.
        # Assuming candidates are all existential.

        num_vars = len(existential_vars)
        candidate_weights = {}

        for idx, var in enumerate(existential_vars):
            if var in candidates:
                # Earlier (smaller idx) -> Higher weight
                weight = num_vars - idx
                candidate_weights[var] = weight

        # Fallback for candidates not found in quantifiers (should not happen in valid QBF)
        min_weight_fallback = 1
        for var in candidates:
            if var not in candidate_weights:
                candidate_weights[var] = min_weight_fallback

        # Top soft weight sum (upper bound) to set hard clause weight
        sum_soft_weights = sum(candidate_weights.values())
        top_weight = sum_soft_weights + 1

        # 2. Add Hard Clauses (Matrix)
        # Simplify matrix based on assignment for X variables.
        # Same logic as MaxSATScheme.

        for var, val in assignment.items():
            if var not in candidates:
                # Fixed input / non-candidate
                lit = var if val else -var
                wcnf.append([lit], weight=top_weight)

        for clause in self.instance.clauses:
            wcnf.append(clause, weight=top_weight)

        # 3. Add Soft Clauses for Candidates with Weights
        for var, func in candidates.items():
            current_val = assignment.get(var)
            if current_val is None:
                continue

            weight = candidate_weights.get(var, 1)  # Default 1 if not ordered

            lit = var if current_val else -var
            wcnf.append([lit], weight=weight)

        # 4. Solve MaxSAT
        with RC2(wcnf) as rc2:
            model = rc2.compute()

        if model is None:
            # See MaxSATScheme comments
            return []

        # 5. Identify Faults
        faults = []
        model_map = {abs(lit): (lit > 0) for lit in model}

        for var in candidates:
            original_val = assignment[var]
            new_val = model_map.get(var)

            if new_val is not None and new_val != original_val:
                faults.append(var)
        return faults
