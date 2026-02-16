from abc import ABC, abstractmethod
from typing import Dict, List
from src.candidate_function import CandidateFunction
from src.instance import Instance


class RepairScheme(ABC):
    """
    Abstract base class for repair schemes.
    """

    def __init__(self, instance: Instance, dependency_scheme, function_manager):
        self.instance = instance
        self.dep_scheme = dependency_scheme
        self.function_manager = function_manager

    @abstractmethod
    def repair(
        self,
        candidates: Dict[int, CandidateFunction],
        assignment: Dict[int, bool],
        suspects: List[int],
    ) -> Dict[int, CandidateFunction]:
        """
        Repairs the candidate functions based on a checking failure.

        Args:
            candidates: The current candidate functions.
            assignment: The counter-example assignment (variables -> bool) from the verification check.
            suspects: List of suspect variable IDs identified by fault localization.

        Returns:
            The updated candidate functions.
        """
        pass
