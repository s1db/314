import logging
from typing import Dict, List
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2Stratified
from src.candidate_function import CandidateFunction
from .maxsat import MaxSATScheme


class QuantifierLevelMaxSATScheme(MaxSATScheme):
    """
    Fault localization based on MaxSAT with weights determined by quantifier levels.
    Variables in outer quantifier blocks (earlier in the prefix) get higher weights
    to preserve their values, satisfying the "stratified" approach relative to
    quantifier depth.
    """

    def localize(
        self, candidates: Dict[int, CandidateFunction], assignment: Dict[int, bool]
    ) -> List[int]:
        """
        Uses RC2 (MaxSAT) provided by PySAT.

        Strategy:
        1. Universals (X) are fixed to their assignment values (Hard Constraints).
        2. Existentials (Y) are free (no Hard Constraints), constrained only by the formula.
        3. Candidates (subset of Y) have Soft Clauses preferring their assignment values.
        4. Weights are assigned based on Quantifier Block Index.
           Outer blocks (smaller index) get HIGHER weights.
           Weight = (Total Blocks) - Block Index.
        """
        wcnf = WCNF()

        # Add the original matrix clauses as hard constraints
        for clause in self.instance.clauses:
            wcnf.append(clause)  # Hard constraint

        # Add hard constraints for variables NOT in candidates
        # This includes Universals and fixed Existentials (if any)
        for var, val in assignment.items():
            if var not in candidates:
                lit = var if val else -var
                wcnf.append([lit])  # Hard constraint

        # Map variables to their quantifier block level
        # We need to know which block each variable belongs to.
        # instance.quantifiers is List[Tuple[str, List[int]]]
        # e.g. [('a', [1]), ('e', [2,3]), ('a', [4]), ('e', [5])]
        var_to_level = {}
        num_blocks = len(self.instance.quantifiers)

        for idx, (q_type, vars_list) in enumerate(self.instance.quantifiers):
            for var in vars_list:
                var_to_level[var] = idx

        # Calculate weights for candidates
        # Weight = num_blocks - level
        # Level 0 (outmost) -> Weight N
        # Level N (innermost) -> Weight 1
        candidate_weights = {}
        relevant_candidates = []

        for var in candidates:
            # If for some reason var isn't in quantifiers map (unquantified?), default to inner-most (low weight)
            level = var_to_level.get(var, num_blocks)
            weight = num_blocks - level
            if weight < 1:
                weight = 1  # Ensure at least 1

            candidate_weights[var] = weight
            relevant_candidates.append(var)

        # Soft Clauses for Candidates (Y)
        # Prefer current assignment
        for var in candidates:
            current_val = assignment.get(var)

            # If current_val is None, we can't prefer it.
            # In complete assignment, this shouldn't happen.
            if current_val is None:
                continue

            weight = candidate_weights.get(var, 1)
            lit = var if current_val else -var
            wcnf.append([lit], weight=weight)

        # Solve MaxSAT
        logging.info(
            f"Starting RC2Stratified (QuantifierLevel) with {len(candidate_weights)} candidates..."
        )
        with RC2Stratified(wcnf, verbose=True) as rc2:
            model = rc2.compute()

        if model is None:
            return []

        # Identify Faults
        faults = []
        model_map = {abs(lit): (lit > 0) for lit in model}

        for var in candidates:
            original_val = assignment[var]
            new_val = model_map.get(var)

            if new_val is not None and new_val != original_val:
                faults.append(var)

        # Sort faults?
        # Manthan sorts by reverse topological order for dependency-based.
        # Here we should probably sort by reverse level (innermost first)?
        # Innermost = likely sink-ish / dependent.
        # Highest index = innermost.
        faults.sort(key=lambda v: var_to_level.get(v, -1), reverse=True)

        return faults
