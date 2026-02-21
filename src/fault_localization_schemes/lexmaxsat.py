import logging
from typing import Dict, List
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2Stratified
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
        Uses RC2 (MaxSAT) provided by PySAT.

        Strategy:
        1. Universals (X) are fixed to their assignment values (Hard Constraints).
        2. Existentials (Y) are free (no Hard Constraints), constrained only by the formula.
        3. Candidates (subset of Y) have Soft Clauses preferring their assignment values.
        4. Weights are assigned based on Topological Order (Source -> Sink).
           Upstream variables get higher weights to preserve them.
        """
        wcnf = WCNF()

        # Add the original matrix clauses as hard constraints
        for clause in self.instance.clauses:
            wcnf.append(clause)  # Hard constraint

        for var, val in assignment.items():
            if var not in candidates:
                lit = var if val else -var
                wcnf.append([lit])  # Hard constraint
        if self.instance.dependency_scheme is None:
            raise ValueError("Dependency scheme not set for instance.")

        topo_order = self.instance.dependency_scheme.get_total_order()

        # Filter candidates based on topological order (Source -> Sink)
        # This is O(N) and ensures the correct order for weight assignment
        relevant_vars = [v for v in topo_order if v in candidates]

        # Calculate Unique Weights (No Chunking)
        # Weight = N - index
        num_vars = len(relevant_vars)
        candidate_weights = {}
        for idx, var in enumerate(relevant_vars):
            weight = num_vars - idx
            candidate_weights[var] = weight

        # 4. Soft Clauses for Candidates (Y)
        # Prefer current assignment
        for var in candidates:
            current_val = assignment.get(var)
            weight = candidate_weights.get(var, 1)
            lit = var if current_val else -var
            wcnf.append([lit], weight=weight)

        # 5. Solve MaxSAT
        logging.info(
            f"Starting RC2Stratified with {len(candidate_weights)} distinct weights..."
        )
        with RC2Stratified(wcnf, verbose=True) as rc2:
            model = rc2.compute()

        if model is None:
            return []

        # 6. Identify Faults
        faults = []
        model_map = {abs(lit): (lit > 0) for lit in model}

        for var in candidates:
            original_val = assignment[var]
            new_val = model_map.get(var)

            if new_val is not None and new_val != original_val:
                faults.append(var)

        # Sort faults by reverse topological order (Sink -> Source)
        # Higher index in relevant_vars means "more dependent" / "sink"
        # We want to return the sinks first, as they are "lighter" in weight
        # and more likely to be the immediate cause of satisfaction.
        var_rank = {v: i for i, v in enumerate(relevant_vars)}
        faults.sort(key=lambda v: var_rank.get(v, -1), reverse=True)
        return faults
