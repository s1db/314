from typing import List, Tuple
from src.dependency_schemes.static import StaticDependencyScheme


class TrivialDependencyScheme(StaticDependencyScheme):
    """
    The trivial dependency scheme: every existential variable depends on
    all variables (universal and existential) that appear before it
    in the quantifier prefix.
    """

    def __init__(
        self,
        quantifiers: List[Tuple[str, List[int]]],
        num_vars: int,
        clauses: List[List[int]] | None = None,
    ):
        super().__init__(quantifiers, num_vars, clauses)

    def compute(self) -> None:
        seen_vars: set[int] = set()
        for q_type, variables in self.quantifiers:
            for var in variables:
                if q_type == "e":
                    if var not in self.dependencies:
                        self.dependencies[var] = set()
                    self.dependencies[var].update(seen_vars)
                seen_vars.add(var)
