from typing import Dict, List
from pysat.formula import WCNF
from pysat.examples.rc2 import RC2
from src.candidate_function import CandidateFunction
from .base import FaultLocalizationScheme


class MaxSATScheme(FaultLocalizationScheme):
    """
    Fault localization based on MaxSAT.
    Minimizes the number of candidates that need to be flipped to satisfy the matrix.
    """

    def localize(
        self, candidates: Dict[int, CandidateFunction], assignment: Dict[int, bool]
    ) -> List[int]:
        """
        Uses RC2 (MaxSAT) to find a satisfying assignment for the Y variables that maximizes
        agreement with the current candidate evaluations.
        """
        wcnf = WCNF()

        # Add the original matrix clauses as hard constraints
        for clause in self.instance.clauses:
            wcnf.append(clause)  # Hard constraint

        for var, val in assignment.items():
            if var not in candidates:
                # This is a fixed input (or already correct variable?)
                # Add hard unit clause
                lit = var if val else -var
                wcnf.append([lit])  # Hard constraint

        # 2. Add Soft Clauses for Candidates
        # specific_vars -> candidate_function -> current_val
        # We want y = current_val to be a soft clause.
        for var, func in candidates.items():
            current_val = assignment.get(var)

            lit = var if current_val else -var
            wcnf.append([lit], weight=1)

        # 3. Solve MaxSAT
        with RC2(wcnf) as rc2:
            model = rc2.compute()

        if model is None:
            print("Warning: MaxSAT found no model. Matrix might be UNSAT for this X.")
            return []

        # 4. Identify Faults
        # Variables where model value != assigned value
        faults = []
        model_map = {abs(lit): (lit > 0) for lit in model}

        for var in candidates:
            # Original value in assignment
            original_val = assignment[var]
            # New value in MaxSAT model
            new_val = model_map.get(var)

            if new_val is not None and new_val != original_val:
                faults.append(var)

        return faults
