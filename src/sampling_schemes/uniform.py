from typing import List
import pycmsgen  # ty:ignore[unresolved-import]
import numpy as np
from src.sampling_schemes.base import SamplingScheme


class UniformSampler(SamplingScheme):
    def __init__(self, variables: List[int], clauses: List[List[int]]):
        super().__init__(variables, clauses)
        self.solver = pycmsgen.Solver(verbose=0)
        self.solver.add_clauses(clauses)
        self.sample_pool = np.empty((0, len(variables)), dtype=bool)

    def sample(self, num_samples: int = 1) -> np.ndarray:
        """
        Generates `num_samples` uniform-like samples of satisfying assignments.
        Returns a 2D boolean numpy array of shape (N, len(self.variables)).
        """
        raw_samples = []
        for _ in range(num_samples):
            status, _ = self.solver.solve()
            if not status:
                break
            raw_samples.append(self.solver.get_model())

        if not raw_samples:
            return np.empty((0, len(self.variables)), dtype=bool)

        # Transformation logic (moved from Solver)
        # We need to map variable IDs to indices in the output matrix
        var_to_idx = {var: i for i, var in enumerate(self.variables)}
        num_rows = len(raw_samples)
        num_cols = len(self.variables)

        # Initialize boolean matrix
        bool_matrix = np.zeros((num_rows, num_cols), dtype=bool)

        for i, model in enumerate(raw_samples):
            # model is a list of literals or a numpy array of literals
            for lit in model:
                var = abs(lit)
                if var in var_to_idx:
                    idx = var_to_idx[var]
                    bool_matrix[i, idx] = lit > 0

        self.sample_pool = np.concatenate((self.sample_pool, bool_matrix), axis=0)
        return bool_matrix
