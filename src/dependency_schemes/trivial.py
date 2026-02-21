from src.dependency_schemes.base import DependencyScheme
from typing import List, Tuple


class TrivialDependencyScheme(DependencyScheme):
    """
    Implements the Trivial Dependency Scheme.
    Dependencies are calculated based on the quantifier prefix:
    A variable x depends on all variables y to its right in the quantifier prefix,
    but only starting from the first variable (from left to right) that has a different quantification type.
    """

    def __init__(
        self,
        num_vars: int,
        clauses: List[List[int]],
        quantifiers: List[Tuple[str, List[int]]],
    ):
        super().__init__(num_vars, clauses, quantifiers)

    def compute(self):
        # Inverted Trivial Scheme: Store variables that 'var' depends on.
        # Text says: x maps to all y to its right (starting from diff type).
        # With strict alternation, block i has different type from block i+1.
        # So x in block i is a dependency for all y in blocks > i.
        # Therefore, y in block j depends on all x in blocks < j.

        quantifiers = self.quantifiers

        cumulative_upstream = set()

        for i, (q_type, vars) in enumerate(quantifiers):
            # Assign current cumulative upstream to all vars in this block
            # (Because they depend on everything previous)
            upstream_copy = cumulative_upstream.copy()
            for var in vars:
                if var not in self.dependencies:
                    self.dependencies[var] = set()
                self.dependencies[var] = upstream_copy.copy()

            # Add current block to upstream for next blocks
            cumulative_upstream.update(vars)

    def verify_dependencies(self) -> None:
        """
        Custom verification for Trivial Scheme.
        Allows strict forward dependencies and universal variable dependencies.
        """
        # Cycle detection
        self.topological_sort()

        # Range check and self-dependency check
        for u, deps in self.dependencies.items():
            for v in deps:
                if u == v:
                    raise ValueError(
                        f"Self-dependency detected: variable {u} depends on itself."
                    )
                if not (1 <= v <= self.num_vars):
                    raise ValueError(f"Variable {v} is out of valid range.")
            if not (1 <= u <= self.num_vars):
                raise ValueError(f"Variable {u} is out of valid range.")
