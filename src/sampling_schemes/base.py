from abc import ABC, abstractmethod
from typing import List
import numpy as np


class SamplingScheme(ABC):
    @abstractmethod
    def __init__(self, variables: List[int], clauses: List[List[int]]):
        """
        Initialize the sampler with the variables to be tracked and the formula clauses.
        """
        self.variables = variables
        self.clauses = clauses

    @abstractmethod
    def sample(self, num_samples: int = 1) -> np.ndarray:
        """
        Generates `num_samples` samples of satisfying assignments.
        Returns a 2D boolean numpy array of shape (N, len(self.variables)),
        where N <= num_samples.
        Each column corresponds to the variable in self.variables at the same index.
        """
        pass
