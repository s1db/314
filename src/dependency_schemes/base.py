from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Type

if TYPE_CHECKING:
    from src.instance import Instance


class DependencyViolationError(Exception):
    """Raised when an update violates the dependency scheme's constraints."""

    pass


class DependencyScheme(ABC):
    """
    Abstract base class for dependency schemes.

    ## Graph convention
    `dependencies[u] = {v, ...}` means **u depends on v**:
    v must be computed before u (v is a prerequisite of u).
    Arrows point from dependent → dependency.

    ## Construction
    Do NOT instantiate directly. Use the factory classmethod::

        scheme = MyScheme.build(instance)

    This ensures `compute()` is always called after the subclass is fully
    initialised, avoiding the "virtual call in __init__" anti-pattern.

    ## Extending
    - **Static schemes** (Standard, Triangle, Trivial): override `compute()` to
      populate `self.dependencies` once; do not expose mutation methods.
    - **Dynamic schemes** (Mutable): extend `MutableDependencyScheme` which adds
      `update_dependencies` and `_add_edge`.
    """

    # ------------------------------------------------------------------ #
    # Construction                                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def build(
        cls: Type["DependencyScheme"], instance: "Instance"
    ) -> "DependencyScheme":
        """
        Factory method — the correct way to create any DependencyScheme.

        Order of operations:
        1. Allocate the object (bypass __init__ so subclasses control their own).
        2. Run shared base initialisation (_base_init).
        3. Run subclass-specific computation (compute).
        4. Validate the resulting graph (verify).
        """
        obj = cls.__new__(cls)
        obj._base_init(instance)
        obj.compute()
        obj.verify()
        return obj

    def _base_init(self, instance: "Instance") -> None:
        """
        Shared initialisation logic. Call this via super()._base_init(instance)
        at the top of any subclass __init__ if you need custom attributes set
        before compute() is called.
        """
        self.instance = instance

        # Graph: u -> {v, ...}  means u depends on v.
        self.dependencies: Dict[int, Set[int]] = {}

        # _prefix_scope[var] = all variables that appear in *strictly earlier*
        # quantifier blocks — i.e. the maximum set quantifier prefix order permits
        # var to depend on.  Subclasses may further restrict this in
        # get_allowed_variables().
        self._prefix_scope: Dict[int, Set[int]] = {}
        self._compute_prefix_scope()

    def _compute_prefix_scope(self) -> None:
        """Populate _prefix_scope from the quantifier prefix of the instance."""
        previous: Set[int] = set()
        for _q_type, var_list in self.instance.quantifiers:
            for var in var_list:
                self._prefix_scope[var] = previous.copy()
            previous.update(var_list)

    # ------------------------------------------------------------------ #
    # Abstract interface                                                 #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def compute(self) -> None:
        """
        Populate self.dependencies.

        Called once by build() after _base_init(). All variables that the scheme
        cares about should be inserted as keys (even with empty sets) so that
        graph algorithms can iterate over them.
        """

    # ------------------------------------------------------------------ #
    # Policy hook — override in subclasses to restrict/expand scope      #
    # ------------------------------------------------------------------ #

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Returns the set of variables that *target_variable* is permitted to depend on.

        Default: the quantifier-prefix scope (_prefix_scope), i.e. everything in
        strictly earlier blocks.  Static schemes (Standard, Triangle) typically
        restrict this further.  MutableDependencyScheme expands it to include
        same-block peers (subject to cycle avoidance).
        """
        return self._prefix_scope.get(target_variable, set())

    # ------------------------------------------------------------------ #
    # Read API                                                           #
    # ------------------------------------------------------------------ #

    def get_dependencies(self, var: int) -> Set[int]:
        """Direct dependencies of var (one hop)."""
        return self.dependencies.get(var, set())

    def get_transitive_dependencies(self, var: int) -> Set[int]:
        """All variables that var depends on transitively (full reachability)."""
        visited: Set[int] = set()
        stack = [var]
        while stack:
            curr = stack.pop()
            for dep in self.get_dependencies(curr):
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited

    def get_total_order(self) -> List[int]:
        """
        Topological sort of all variables in the dependency graph.

        Returns variables in *computation order*: prerequisites come before
        the variables that depend on them.
        """
        return self.topological_sort()

    def topological_sort(self, nodes: Optional[Set[int]] = None) -> List[int]:
        """
        Kahn's algorithm on the dependency graph.

        Parameters
        ----------
        nodes:
            Subset of nodes to sort.  Defaults to all nodes in self.dependencies.

        Returns
        -------
        List[int]
            Variables in computation order (prerequisites first).

        Raises
        ------
        DependencyViolationError
            If a cycle is detected.
        """
        if nodes is None:
            nodes = set(self.dependencies.keys())
            for deps in self.dependencies.values():
                nodes.update(deps)

        # in_degree counts how many nodes in `nodes` depend on each node v.
        # (i.e., how many u have v in dependencies[u])
        in_degree: Dict[int, int] = {n: 0 for n in nodes}
        for u in nodes:
            for v in self.get_dependencies(u):
                if v in nodes:
                    in_degree[v] += 1

        # Start with nodes nothing depends on (they are deepest dependencies).
        queue = [n for n, deg in in_degree.items() if deg == 0]
        result: List[int] = []
        while queue:
            u = queue.pop(0)
            result.append(u)
            for v in self.get_dependencies(u):
                if v in nodes:
                    in_degree[v] -= 1
                    if in_degree[v] == 0:
                        queue.append(v)

        if len(result) != len(nodes):
            raise DependencyViolationError("Cycle detected during topological sort")

        # result is currently [deepest-dependency ... dependent].
        # Reverse so prerequisites come first.
        return list(reversed(result))

    def sort_by_dependency_order(self, variables: List[int]) -> List[int]:
        """
        Sort *variables* so prerequisites appear before their dependents.

        Raises DependencyViolationError if a cycle is detected or a variable is
        not present in the dependency graph.
        """
        total_order = self.get_total_order()
        order_map = {node: i for i, node in enumerate(total_order)}

        def get_order(variable: int) -> int:
            if variable not in order_map:
                raise DependencyViolationError(
                    f"Variable {variable} not found in dependency graph order."
                )
            return order_map[variable]

        return sorted(variables, key=get_order)

    def get_partial_order(self, variable: int) -> List[int]:
        """
        Topological order of *variable* and all its transitive dependencies.

        Returns [deepest-prerequisite, ..., variable] (computation order).
        """
        descendants = self.get_transitive_dependencies(variable)
        nodes = descendants | {variable}
        return self.topological_sort(nodes)

    def _is_reachable(self, start: int, target: int) -> bool:
        """Return True if *target* is reachable from *start* via dependency edges."""
        if start == target:
            return True
        stack = [start]
        visited = {start}
        while stack:
            node = stack.pop()
            if node == target:
                return True
            for neighbour in self.get_dependencies(node):
                if neighbour not in visited:
                    visited.add(neighbour)
                    stack.append(neighbour)
        return False

    # ------------------------------------------------------------------ #
    # Validation                                                         #
    # ------------------------------------------------------------------ #

    def verify(self) -> None:
        """
        Validate the dependency graph after compute().

        Checks:
        1. All variables in the graph are quantified in the instance.
        2. Variables are within valid range [1, num_vars].
        3. Universal variables have no outgoing dependencies.
        4. No self-dependencies.
        5. Quantifier-order: a variable may only depend on variables from
           the same or earlier quantifier blocks.
        6. No cycles.
        """
        var_to_info: Dict[int, tuple[int, str]] = {}
        for idx, (q_type, var_list) in enumerate(self.instance.quantifiers):
            for v in var_list:
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
                        f"Self-dependency: variable {u} depends on itself."
                    )

                if v not in var_to_info:
                    raise ValueError(f"Dependency target {v} is not quantified.")

                v_block_idx, _ = var_to_info[v]
                if v_block_idx > u_block_idx:
                    raise ValueError(
                        f"Quantifier-order violation: {u} (block {u_block_idx}) "
                        f"depends on {v} (block {v_block_idx})."
                    )

        for v in var_to_info:
            if not (1 <= v <= self.instance.num_vars):
                raise ValueError(
                    f"Variable {v} is out of valid range [1, {self.instance.num_vars}]."
                )

        # Cycle check via topological sort
        self.topological_sort()
