from typing import Set, Dict, List, Tuple
from src.dependency_schemes.base import DependencyScheme, DependencyViolationError


class MutableDependencyScheme(DependencyScheme):
    """
    A dependency scheme that starts empty and is updated at runtime
    as learning schemes discover dependencies.

    Replaces both EmptyDependencyScheme and LearnedDependencyScheme.

    Key properties:
    - Dependencies strictly respect QBF quantifier blocks.
    - Intra-block dependencies are allowed and learned, providing they don't form cycles.
    - get_allowed_variables dynamically excludes peers that would create cycles.
    """

    def __init__(
        self,
        quantifiers: List[Tuple[str, List[int]]],
        num_vars: int,
    ):
        # Initialize before super().__init__ calls compute()
        self.hard_predecessors: Dict[int, Set[int]] = {}
        self.same_block_peers: Dict[int, Set[int]] = {}

        super().__init__(quantifiers, num_vars)

        # Precompute structural constraints from the QBF prefix
        self._initialize_structure()

    def _initialize_structure(self) -> None:
        """Analyzes the QBF prefix to populate hard constraints."""
        all_previous_vars: Set[int] = set()

        for q_type, var_list in self.quantifiers:
            current_block_vars = set(var_list)

            if q_type == "e":
                for var in var_list:
                    # Every existential variable can depend on EVERYTHING before
                    self.hard_predecessors[var] = all_previous_vars.copy()

                    # Peers are other variables in the same block
                    peers = current_block_vars.copy()
                    peers.discard(var)
                    self.same_block_peers[var] = peers

                    # Ensure node exists in dependencies
                    if var not in self.dependencies:
                        self.dependencies[var] = set()

            all_previous_vars.update(current_block_vars)

    def compute(self) -> None:
        """Starts with an empty dependency graph (dependencies are learned at runtime)."""
        pass

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Returns the set of variables that target_variable is allowed to depend on.

        Allowed = (Hard Predecessors) ∪ (Allowed Same-Block Peers)
        Allowed Same-Block Peers = (All Peers) minus (Descendants of Target)

        This dynamically excludes peers that would create cycles.
        """
        allowed = self.hard_predecessors.get(target_variable, set()).copy()

        peers = self.same_block_peers.get(target_variable, set())
        if not peers:
            return allowed

        for p in peers:
            # Exclude peer if it already transitively depends on target
            if not self._is_reachable(p, target_variable):
                allowed.add(p)

        return allowed

    def update_dependencies(
        self, target_variable: int, used_variables: Set[int]
    ) -> None:
        """
        Updates the dependency graph with new edges.
        Validates against scheme policy and checks for cycles.
        """
        allowed = self.get_allowed_variables(target_variable)
        invalid = used_variables - allowed
        if invalid:
            raise DependencyViolationError(
                f"Variable {target_variable} depends on forbidden variables: {invalid}. "
                f"Valid scope: {allowed}"
            )

        for dep in used_variables:
            self._add_edge(target_variable, dep)

    def _add_edge(self, u: int, v: int) -> None:
        """
        Adds dependency u -> v (u depends on v).
        Checks for cycles immediately.
        """
        if u not in self.dependencies:
            self.dependencies[u] = set()

        if v in self.dependencies[u]:
            return

        # Check if adding u -> v would create a cycle
        # (i.e., is u already reachable from v?)
        if self._is_reachable(v, u):
            raise DependencyViolationError(f"Dependency {u} -> {v} creates a cycle.")

        self.dependencies[u].add(v)
        if v not in self.dependencies:
            self.dependencies[v] = set()
