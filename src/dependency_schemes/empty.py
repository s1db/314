from typing import List, Tuple
from src.dependency_schemes.base import DependencyScheme


class EmptyDependencyScheme(DependencyScheme):
    """
    A dependency scheme with no dependencies other than the default quantifier-based ones
    (if the base class enforces strict ordering, which it does via verification).
    The compute method creates no additional edges.
    """

    def __init__(
        self,
        num_vars: int,
        clauses: List[List[int]],
        quantifiers: List[Tuple[str, List[int]]],
    ):
        super().__init__(num_vars, clauses, quantifiers)

    def compute(self):
        # No extra dependencies to add
        pass
