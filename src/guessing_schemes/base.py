from src.instance import Instance
from abc import ABC, abstractmethod
from typing import Dict
from src.candidate_function import CandidateFunction
from src.candidate_function import FunctionManager
import numpy as np


from src.dependency_schemes.base import DependencyScheme


class BaseCandidateFunctionGuesser(ABC):
    def __init__(self):
        self.updates_dependencies = False

    @abstractmethod
    def guess_candidates(
        self,
        instance: Instance,
        samples: np.ndarray,
        function_manager: FunctionManager,
        dependency_scheme: DependencyScheme,
    ) -> Dict[int, CandidateFunction]:
        """
        Learns candidate functions for all existential variables.

        Args:
            instance: The QBF instance.
            samples: The samples to use for learning.
            function_manager: The function manager to use.

        Returns:
            A dictionary of candidate functions for each existential variable.
        """
        pass
