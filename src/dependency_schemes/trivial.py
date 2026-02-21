from src.dependency_schemes.base import DependencyScheme


class TrivialDependencyScheme(DependencyScheme):
    """
    Trivial (full-prefix) dependency scheme.

    Every existential variable depends on *all* variables in strictly earlier
    quantifier blocks.  This is the coarsest static scheme and is equivalent
    to standard PCNF quantifier scoping with no refinement.
    """

    def compute(self) -> None:
        seen: set[int] = set()
        for q_type, var_list in self.instance.quantifiers:
            for var in var_list:
                if q_type == "e":
                    self.dependencies[var] = seen.copy()
            seen.update(var_list)
