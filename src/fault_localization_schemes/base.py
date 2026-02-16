from abc import ABC, abstractmethod
from typing import List, Dict
from src.candidate_function import CandidateFunction
from src.instance import Instance


class FaultLocalizationScheme(ABC):
    """
    Abstract base class for fault localization schemes.
    Values returned are variable IDs that are deemed "suspicious".
    """

    def __init__(self, instance: Instance):
        self.instance = instance

    @abstractmethod
    def localize(
        self, candidates: Dict[int, CandidateFunction], assignment: Dict[int, bool]
    ) -> List[int]:
        """
        Identifies suspicious candidates that might be causing the assignment to be unsatisfied.

        Args:
            candidates: Dictionary mapping variable ID to its current candidate function.
            assignment: The assignment (sample) that caused a conflict/failure.
                        Maps variable ID -> boolean value.
                        Should include values for all variables (X and Y).

        Returns:
            List of variable IDs (keys in `candidates`) that are identified as potential faults.
        """
        pass
