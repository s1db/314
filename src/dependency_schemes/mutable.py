from typing import Set

from src.dependency_schemes.base import DependencyScheme, DependencyViolationError


class MutableDependencyScheme(DependencyScheme):
    """
    A dependency scheme whose graph is built dynamically at solve time.

    The graph starts empty and grows via `update_dependencies` as the solver
    learns which variables each Skolem function actually uses.

    Allowed dependencies
    --------------------
    For a target variable *y*:
    - All variables in strictly earlier quantifier blocks (_prefix_scope[y]).
    - Same-block existential peers that do not (transitively) depend on *y*
      — i.e. adding the edge would not create a cycle.
    """

    def compute(self) -> None:
        """Graph starts empty; populated incrementally via update_dependencies."""
        for _q_type, var_list in self.instance.quantifiers:
            for var in var_list:
                if var not in self.dependencies:
                    self.dependencies[var] = set()

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Returns variables that *target_variable* is currently permitted to depend on.

        Includes same-block existential peers that would not create a cycle.
        """
        # Start with strict quantifier-prefix scope
        allowed = self._prefix_scope.get(target_variable, set()).copy()

        # Add same-block peers that are existential and would not form a cycle
        for q_type, var_list in self.instance.quantifiers:
            if target_variable in var_list:
                if q_type == "e":
                    for peer in var_list:
                        if peer != target_variable:
                            # Only add peer if it doesn't (transitively) depend on target
                            if not self._is_reachable(peer, target_variable):
                                allowed.add(peer)
                break

        return allowed

    def update_dependencies(
        self, target_variable: int, used_variables: Set[int]
    ) -> None:
        """
        Record that *target_variable*'s Skolem function uses *used_variables*.

        Raises DependencyViolationError if any of the used variables fall outside
        the currently allowed scope (quantifier order violation or cycle).
        """
        allowed = self.get_allowed_variables(target_variable)
        invalid = used_variables - allowed
        if invalid:
            raise DependencyViolationError(
                f"Variable {target_variable} depends on forbidden variables: {invalid}. "
                f"Allowed scope: {allowed}"
            )

        for dep in used_variables:
            self._add_edge(target_variable, dep)

    def _add_edge(self, u: int, v: int) -> None:
        """
        Add the dependency edge u → v (u depends on v).

        Raises DependencyViolationError if the edge would create a cycle.
        """
        if u not in self.dependencies:
            self.dependencies[u] = set()

        if v in self.dependencies[u]:
            return  # Edge already exists

        # Would adding u → v create a cycle?  That happens iff u is reachable from v.
        if self._is_reachable(v, u):
            raise DependencyViolationError(
                f"Dependency {u} → {v} would create a cycle."
            )

        self.dependencies[u].add(v)

        if v not in self.dependencies:
            self.dependencies[v] = set()
