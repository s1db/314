from abc import ABC, abstractmethod
from collections import deque
from typing import Set, Dict, Optional, List, Tuple


class DependencyViolationError(Exception):
    """Raised when an update violates the dependency scheme's constraints."""

    pass


class DependencyScheme(ABC):
    """
    Abstract base class for dependency schemes.
    Provides graph algorithms over an immutable dependency DAG.
    Subclasses populate `self.dependencies` in `compute()`.

    The constructor takes quantifier prefix data directly (not the full Instance)
    to avoid circular references.
    """

    def __init__(
        self,
        quantifiers: List[Tuple[str, List[int]]],
        num_vars: int,
        clauses: Optional[List[List[int]]] = None,
    ):
        self.quantifiers = quantifiers
        self.num_vars = num_vars
        self.clauses = clauses if clauses is not None else []
        self.dependencies: Dict[int, Set[int]] = {}
        self.prefix_scope: Dict[int, Set[int]] = {}

        self._compute_prefix_scope()
        self.compute()
        self.verify_dependencies()

    @abstractmethod
    def compute(self) -> None:
        """Populate self.dependencies. Called once during __init__."""
        pass

    @abstractmethod
    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """Returns the set of variables that target_variable is allowed to depend on."""
        pass

    def _compute_prefix_scope(self) -> None:
        """
        For each variable, prefix_scope[var] is the set of all variables
        (both universal and existential) in strictly earlier quantifier blocks.
        Used by learning schemes to determine valid feature sets.
        """
        previous_vars: Set[int] = set()
        for _q_type, var_list in self.quantifiers:
            for var in var_list:
                self.prefix_scope[var] = previous_vars.copy()
            previous_vars.update(var_list)

    def get_dependencies(self, var: int) -> Set[int]:
        """Returns the direct dependencies of `var`."""
        return self.dependencies.get(var, set())

    def get_transitive_dependencies(self, var: int) -> Set[int]:
        """Returns all variables that `var` transitively depends on."""
        return self._reachable_from(var)

    def _reachable_from(self, start: int) -> Set[int]:
        """BFS/DFS to find all nodes reachable from `start` via dependency edges."""
        visited: Set[int] = set()
        stack = list(self.get_dependencies(start))
        while stack:
            curr = stack.pop()
            if curr not in visited:
                visited.add(curr)
                stack.extend(self.get_dependencies(curr))
        return visited

    def _is_reachable(self, start: int, target: int) -> bool:
        """Returns True if `target` is reachable from `start` via dependency edges."""
        if start == target:
            return True
        return target in self._reachable_from(start)

    def get_topological_order(self, nodes: Optional[Set[int]] = None) -> List[int]:
        """Returns a topological sort of the variables in the dependency graph."""
        if nodes is None:
            # Include all variables that appear in any quantifier block
            nodes = set()
            for _, vars in self.quantifiers:
                nodes.update(vars)

        in_degree: Dict[int, int] = {n: 0 for n in nodes}
        for u in nodes:
            for v in self.get_dependencies(u):
                if v in nodes:
                    in_degree[v] += 1

        queue: deque[int] = deque(n for n, deg in in_degree.items() if deg == 0)
        result: List[int] = []
        while queue:
            u = queue.popleft()
            result.append(u)
            for v in self.get_dependencies(u):
                if v in nodes:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)

        if len(result) != len(nodes):
            raise DependencyViolationError("Cycle detected during topological sort")

        # In our graph U -> V means "U depends on V".
        # Kahn's produces [no-incoming-edges-first] = [dependents first].
        # Computation order is reversed: [independent ... dependent].
        return list(reversed(result))

    def sort_by_dependency_order(self, variables: List[int]) -> List[int]:
        """
        Sorts the given variables by their position in the topological order.
        Variables earlier in computation order come first.
        Raises DependencyViolationError if a variable is not in the graph.
        """
        total_order = self.get_topological_order()
        order_map = {node: i for i, node in enumerate(total_order)}

        def get_order(variable: int) -> int:
            if variable not in order_map:
                raise DependencyViolationError(
                    f"Variable {variable} not found in dependency graph order."
                )
            return order_map[variable]

        return sorted(variables, key=get_order)

    def verify_dependencies(self) -> None:
        """
        Validates the dependency graph:
        1. All variables must be quantified.
        2. No self-dependencies.
        3. Universal variables must not have outgoing dependencies.
        4. Variables may only depend on variables in current or earlier blocks.
        5. No cycles.
        6. All variables in valid range [1, num_vars].
        """
        var_to_info: Dict[int, Tuple[int, str]] = {}
        for idx, (q_type, var_list) in enumerate(self.quantifiers):
            for v in var_list:
                var_to_info[v] = (idx, q_type)

        for u, deps in self.dependencies.items():
            if u not in var_to_info:
                raise DependencyViolationError(
                    f"Variable {u} in dependency graph is not quantified."
                )

            u_block_idx, u_type = var_to_info[u]

            if u_type == "a" and deps:
                raise DependencyViolationError(
                    f"Universal variable {u} cannot have dependencies."
                )

            for v in deps:
                if v == u:
                    raise DependencyViolationError(
                        f"Self-dependency detected: variable {u} depends on itself."
                    )

                if v not in var_to_info:
                    raise DependencyViolationError(
                        f"Dependency variable {v} is not quantified."
                    )

                v_block_idx, _ = var_to_info[v]
                if v_block_idx > u_block_idx:
                    raise DependencyViolationError(
                        f"Quantifier order violation: {u} (block {u_block_idx}) "
                        f"depends on {v} (block {v_block_idx})."
                    )

        for v in var_to_info:
            if not (1 <= v <= self.num_vars):
                raise DependencyViolationError(
                    f"Variable {v} is out of valid range [1, {self.num_vars}]."
                )

        # Cycle detection via topological sort
        self.get_topological_order()

    def __repr__(self) -> str:
        edge_count = sum(len(deps) for deps in self.dependencies.values())
        return (
            f"{type(self).__name__}("
            f"vars={self.num_vars}, "
            f"nodes={len(self.dependencies)}, "
            f"edges={edge_count})"
        )
