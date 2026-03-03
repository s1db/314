from src.dependency_schemes.static import StaticDependencyScheme
from typing import List, Tuple, Optional, Set


class TrivialInterBlockDependencyScheme(StaticDependencyScheme):
    """
    The Trivial Inter-Block Dependency Scheme:
    1. All variables are allowed to depend on variables that appear before them in different quantifier blocks.
    2. Variables are not allowed to depend on variables within the same block or downstream.
    """

    def __init__(
        self,
        quantifiers: List[Tuple[str, List[int]]],
        num_vars: int,
        clauses: Optional[List[List[int]]] = None,
    ):
        super().__init__(quantifiers, num_vars, clauses)

    def compute(self):
        # computes the dependency scheme for the instance by the following rules:
        # 1. All variables are allowed to depend on variables that appear before them.
        # 2. Within the same quantifier scope, variables are NOT allowed to depend on variables.
        # 3. Variables are not allowed to depend on variables that appear after them.

        seen_vars: Set[int] = set()
        for q_type, variables in self.quantifiers:
            for var in variables:
                if q_type == "e":
                    if var not in self.dependencies:
                        self.dependencies[var] = set()
                    self.dependencies[var].update(seen_vars)

                # Add variables from earlier blocks only
            for var in variables:
                seen_vars.add(var)
