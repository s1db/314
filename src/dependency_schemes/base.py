from abc import ABC, abstractmethod
from typing import Set, Dict, Optional, List
from src.instance import Instance


class DependencyViolationError(Exception):
    """Raised when an update violates the dependency scheme's constraints."""

    pass


class DependencyScheme(ABC):
    """
    Abstract base class for dependency schemes.
    Manages the dependency graph and provides common algorithms (cycle detection, sorting).
    """

    def __init__(self, instance: Instance):
        self.instance = instance
        self.dependencies: Dict[int, Set[int]] = {}
        self.potential_dependencies: Dict[int, Set[int]] = {}
        self.allowed_dependencies: Dict[int, Set[int]] = {}

        dependencies = set()
        for quantifier_block in self.instance.quantifiers:
            dependencies.update(quantifier_block[1])
            for var in quantifier_block[1]:
                self.allowed_dependencies[var] = dependencies.copy()

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
        for quantifier in self.instance.quantifiers:
            for var in quantifier[1]:
                self.potential_dependencies[var] = previous_quantifier_vars.copy()
            previous_quantifier_vars.update(quantifier[1])

    def get_dependencies(self, var: int) -> Set[int]:
        return self.dependencies.get(var, set())

    def get_transitive_dependencies(self, var: int) -> Set[int]:
        """Returns all variables that `var` depends on transitively (descendants in dependency graph)."""
        visited = set()
        stack = [var]
        while stack:
            curr = stack.pop()
            for dep in self.get_dependencies(curr):
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited

    def get_total_order(self) -> List[int]:
        """Returns a topological sort of all variables in the dependency graph."""
        return self.topological_sort()

    def topological_sort(self, nodes: Optional[Set[int]] = None) -> List[int]:
        if nodes is None:
            nodes = set(self.dependencies.keys())
            for deps in self.dependencies.values():
                nodes.update(deps)

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

        # In our dependency graph [Dependent -> Dependency], result is [Independent, ..., Dependent]
        # Wait, if U -> V, U depends on V. In-degree 0 means nothing depends on it.
        # Result [NothingDependsOnIt, ..., DependencyChain]
        # So it's [Dependent, ..., Dependency].
        # Computation order should be reversed.
        return list(reversed(result))

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
        for idx, (q_type, vars) in enumerate(self.instance.quantifiers):
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
            if not (1 <= v <= self.instance.num_vars):
                raise ValueError(
                    f"Variable {v} is out of valid range [1, {self.instance.num_vars}]."
                )

        # Cycle detection
        self.topological_sort()

    def get_partial_order(self, variable: int) -> List[int]:
        """
        Returns transitive closure of dependencies for `variable`.
        Computation order: [Dependency, ..., Variable]
        """
        descendants = self.get_transitive_dependencies(variable)
        nodes = descendants | {variable}
        return self.topological_sort(nodes)

    def _is_reachable(self, start: int, target: int) -> bool:
        """Returns True if target is reachable from start (DFS)."""
        if start == target:
            return True

        stack = [start]
        visited = {start}
        while stack:
            node = stack.pop()
            if node == target:
                return True
            for neighbor in self.get_dependencies(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        return False

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Returns the set of variables that `target_variable` is allowed to depend on.
        """
        return self.allowed_dependencies[target_variable]

    def update_dependencies(self, target_variable: int, used_variables: Set[int]):
        """
        Updates the dependency scheme
        """
        # 1. Validation against scheme policy
        allowed = self.get_allowed_variables(target_variable)
        invalid = used_variables - allowed
        if invalid:
            raise DependencyViolationError(
                f"Variable {target_variable} depends on forbidden variables: {invalid}. "
                f"Valid scope: {allowed}"
            )

        # 2. Update Graph structure
        for dep in used_variables:
            self._add_edge(target_variable, dep)

    def _add_edge(self, u: int, v: int):
        """
        Adds dependency u -> v (u depends on v).
        Checks for cycles immediately.
        """
        if u not in self.dependencies:
            self.dependencies[u] = set()

        # If edge already exists, skip
        if v in self.dependencies[u]:
            return

        # Check if v depends on u (which would make u -> v a cycle)
        # i.e., is u reachable from v?
        if self._is_reachable(v, u):
            raise DependencyViolationError(f"Dependency {u} -> {v} creates a cycle.")

        self.dependencies[u].add(v)
        # Ensure v exists in graph keys
        if v not in self.dependencies:
            self.dependencies[v] = set()
