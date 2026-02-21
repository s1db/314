from abc import ABC, abstractmethod
from typing import Set, Dict, Optional, List, Tuple


class DependencyViolationError(Exception):
    """Raised when an update violates the dependency scheme's constraints."""

    pass


class DependencyScheme(ABC):
    """
    Abstract base class for dependency schemes.
    Manages the dependency graph and provides common algorithms (cycle detection, sorting).
    """

    def __init__(
        self,
        num_vars: int,
        clauses: List[List[int]],
        quantifiers: List[Tuple[str, List[int]]],
    ):
        self.num_vars = num_vars
        self.clauses = clauses
        self.quantifiers = quantifiers
        self.dependencies: Dict[int, Set[int]] = {}
        self.potential_dependencies: Dict[int, Set[int]] = {}
        self.allowed_dependencies: Dict[int, Set[int]] = {}
        self.var_to_block_idx: Dict[int, int] = {}

        dependencies = set()
        for idx, (q_type, vars_list) in enumerate(self.quantifiers):
            dependencies.update(vars_list)
            for var in vars_list:
                self.allowed_dependencies[var] = dependencies.copy()
                self.var_to_block_idx[var] = idx

        self._topological_order: Optional[List[int]] = None

        self.compute_potential_dependencies()
        self.compute()
        self.verify_dependencies()

    @abstractmethod
    def compute(self):
        pass

    def compute_potential_dependencies(self):
        """
        Computes potential dependencies based on the quantifier prefix.
        For each variable, potential dependencies are all variables (X and Y)
        that appear in previous quantifier blocks.
        """
        previous_quantifier_vars = set()
        for quantifier in self.quantifiers:
            for var in quantifier[1]:
                self.potential_dependencies[var] = previous_quantifier_vars.copy()
            previous_quantifier_vars.update(quantifier[1])

    def get_dependencies(self, var: int) -> Set[int]:
        return self.dependencies.get(var, set())

    def get_total_order(self) -> List[int]:
        """Returns a topological sort of all variables in the dependency graph."""
        return self.topological_sort()

    def topological_sort(self, nodes: Optional[Set[int]] = None) -> List[int]:
        # If specific nodes requested, compute sort only for them (no caching)
        if nodes is not None:
            return self._compute_topological_sort(nodes)

        # Use cached global sort if available
        if self._topological_order is not None:
            return self._topological_order

        # Compute global sort and cache it
        nodes = set(self.dependencies.keys())
        for deps in self.dependencies.values():
            nodes.update(deps)

        self._topological_order = self._compute_topological_sort(nodes)
        return self._topological_order

    def _compute_topological_sort(self, nodes: Set[int]) -> List[int]:
        in_degree = {n: 0 for n in nodes}
        for u in nodes:
            for v in self.get_dependencies(u):
                if v in nodes:
                    in_degree[v] += 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            u = queue.pop(0)
            result.append(u)
            for v in self.get_dependencies(u):
                if v in nodes:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)

        if len(result) != len(nodes):
            # This implies a cycle
            raise DependencyViolationError("Cycle detected during topological sort")

        return list(reversed(result))

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Returns the set of variables that `target_variable` is allowed to depend on.
        Default implementation returns static allowed dependencies.
        Override in dynamic schemes for smarter logic.
        """
        return self.allowed_dependencies.get(target_variable, set())

    def update_dependencies(self, target_variable: int, used_variables: Set[int]):
        """
        Updates the dependency scheme.
        Default implementation is a no-op for static schemes.
        Override in dynamic schemes (e.g. LearnedDependencyScheme) to perform updates.
        """
        pass

    def sort_by_dependency_order(self, variables: List[int]) -> List[int]:
        """
        Sorts the given variables based on their topological order in the dependency graph.
        Variables that appear earlier in the dependency order come first.
        Raises DependencyViolationError if a cycle is detected or if a variable is not in the dependency graph.
        """
        total_order = self.get_total_order()
        order_map = {node: i for i, node in enumerate(total_order)}

        def get_order(variable):
            if variable not in order_map:
                raise DependencyViolationError(
                    f"Variable {variable} not found in dependency graph order."
                )
            return order_map[variable]

        return sorted(variables, key=get_order)

    def verify_dependencies(self) -> None:
        """
        Comprehensive verification of the dependency graph:
        1. Quantifier order: variables should only depend on variables in current or previous blocks.
        2. No circular dependencies.
        3. All variables in dependencies must be quantified in the instance and within valid range.
        4. Universal variables should not have outgoing dependencies.
        5. No self-dependencies.
        """
        # Build map of variable to its quantifier block index and type
        var_to_info = {}
        for idx, (q_type, vars) in enumerate(self.quantifiers):
            for v in vars:
                var_to_info[v] = (idx, q_type)

        for u, deps in self.dependencies.items():
            if u not in var_to_info:
                raise ValueError(f"Variable {u} in dependency graph is not quantified.")

            u_block_idx, u_type = var_to_info[u]

            if u_type == "a" and deps:
                raise ValueError(f"Universal variable {u} cannot have dependencies.")

            for v in deps:
                if v == u:
                    raise ValueError(
                        f"Self-dependency detected: variable {u} depends on itself."
                    )

                if v not in var_to_info:
                    raise ValueError(f"Dependency variable {v} is not quantified.")

                v_block_idx, _ = var_to_info[v]
                if v_block_idx > u_block_idx:
                    raise ValueError(
                        f"Quantifier order violation: {u} (block {u_block_idx}) "
                        f"depends on {v} (block {v_block_idx})."
                    )

        # Range check
        for v in var_to_info:
            if not (1 <= v <= self.num_vars):
                raise ValueError(
                    f"Variable {v} is out of valid range [1, {self.num_vars}]."
                )

        # Cycle detection
        self.topological_sort()
