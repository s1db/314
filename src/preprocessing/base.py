from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import numpy as np

from src.candidate_function import CandidateFunction, FunctionManager


class Preprocessor(ABC):
    """Base class for preprocessing techniques.

    Preprocessors analyse the formula and resolve existential variables
    whose Skolem functions can be determined without sampling or learning.

    All configuration (solver params, budgets, etc.) goes in ``__init__``.
    ``run`` has a uniform signature so the solver can iterate over an
    ordered list of preprocessors.
    """

    @abstractmethod
    def run(
        self,
        clauses: List[List[int]],
        x_vars: List[int],
        y_vars: List[int],
        candidates: Dict[int, CandidateFunction],
        function_manager: FunctionManager,
        samples: Optional[np.ndarray] = None,
    ) -> None:
        """Mutate *candidates* in-place.

        Resolved variables should be assigned a ``CandidateFunction`` with
        ``repairable=False``.

        Parameters
        ----------
        clauses:
            Matrix clauses of the QBF instance.
        x_vars:
            Universal (X) variables.
        y_vars:
            Existential (Y) variables.
        candidates:
            Shared candidate-function map.  Modified in-place.
        function_manager:
            Factory for creating ``CandidateFunction`` nodes.
        samples:
            Optional sample matrix (rows = samples, cols = variables).
            Formula-based preprocessors may ignore this.
        """
