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

        # 1. Add Hard Clauses (Matrix instantiated with X values from assignment)
        # We need the clauses from the instance.
        # Assuming self.instance.clauses is List[List[int]]
        # We simplify them based on assignment for X variables.
        # But wait, pysat expects variable IDs.
        # We can just add the clauses as is, but force X variables to their assigned values using unit hard clauses.

        # Add matrix clauses as hard clauses (weight = topw)
        # We don't know topw yet, so we'll use a placeholder or add them later?
        # RC2 handles topw automatically if we use add_hard? No, WCNF needs weights.

        # Let's count soft clauses to estimate weight.
        num_soft = len(candidates)
        top_weight = num_soft + 1

        # Add unit clauses for X variables (features/inputs)
        # Identify variables not in candidates (assumed to be Inputs/X)
        # Or rely on instance.quantifiers to know which are inputs?
        # Manthan assumes X are inputs (Universal? Existential?).
        # In QBF, we have layers.
        # For FL, we assume we have a counter-example for ALL previous layers?
        # The 'assignment' should contain values for everything.

        # Simplest approach: Add unit hard clauses for ALL variables NOT in candidates.
        # (Assuming candidates are the ones we can repair).

        # But wait, what if 'assignment' contains the *failing* values for Y?
        # Yes, it does.
        # We want to find *new* values for Y.
        # So we should validitate X values as hard constraints.

        for var, val in assignment.items():
            if var not in candidates:
                # This is a fixed input (or already correct variable?)
                # Add hard unit clause
                lit = var if val else -var
                wcnf.append([lit], weight=top_weight)

        # Add the original matrix clauses as hard constraints
        for clause in self.instance.clauses:
            wcnf.append(clause, weight=top_weight)

        # 2. Add Soft Clauses for Candidates
        # specific_vars -> candidate_function -> current_val
        # We want y = current_val to be a soft clause.
        for var, func in candidates.items():
            current_val = assignment.get(var)
            if current_val is None:
                continue  # Should not happen if assignment is complete

            # Soft clause: y == current_val
            # If current_val is True, add [var]
            # If current_val is False, add [-var]
            lit = var if current_val else -var
            wcnf.append([lit], weight=1)

        # 3. Solve MaxSAT
        with RC2(wcnf) as rc2:
            model = rc2.compute()

        if model is None:
            # UNSAT even with hard clauses?
            # This means X values + Matrix are UNSAT.
            # This implies the counter-example X is actually a valid X for the matrix?
            # In QBF, if X makes Matrix False, then maybe valid?
            # Wait, if Matrix is UNSAT for this X, then Skolem functions should evaluate to... ?
            # If we are looking for satisfying Y, but none exists, then X is a witness that "Forall X, Exists Y" is False?
            # This depends on the solving phase.
            # Assuming we are in a phase where a solution *should* exist.
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
