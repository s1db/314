from src.dependency_schemes.base import DependencyScheme
from src.instance import Instance


class TrivialInterBlockDependencyScheme(DependencyScheme):
    def __init__(self, instance: Instance):
        super().__init__(instance)

    def compute(self):
        # computes the dependency scheme for the instance by the following rules:
        # 1. All variables are allowed to depend on variables that appear before them.
        # 2. Within the same quantifier scope, variables are allowed to depend on variables that appear before them.
        # 3. Variables are not allowed to depend on variables that appear after them.
        # 4. Variables are not allowed to depend on variables that are in a different quantifier scope.

        seen_vars = set()
        for q_type, variables in self.instance.quantifiers:
            for var in variables:
                if q_type == "e":
                    if var not in self.dependencies:
                        self.dependencies[var] = set()
                    self.dependencies[var].update(seen_vars)

                seen_vars.add(var)
