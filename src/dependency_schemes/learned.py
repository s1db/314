from typing import Set, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

from .base import DependencyScheme, DependencyViolationError


class LearnedDependencyScheme(DependencyScheme):
    """
    A dependency scheme where:
    1. Dependencies strictly respect QBF quantifier blocks.
    2. Intra-block dependencies are allowed and learned, providing they don't form cycles.
    """

    def __init__(
        self,
        num_vars: int,
        clauses: List[List[int]],
        quantifiers: List[Tuple[str, List[int]]],
    ):
        super().__init__(num_vars, clauses, quantifiers)

        # Precompute the "hard" constraints based on QBF prefix
        self.hard_predecessors: Dict[int, Set[int]] = {}
        self.same_block_peers: Dict[int, Set[int]] = {}
        self._initialize_structure()

    def _initialize_structure(self):
        """Analyzes the QBF prefix to populate hard constraints."""
        all_previous_vars = set()

        for q_type, var_list in self.quantifiers:
            current_block_vars = set(var_list)

            if q_type == "e":
                for var in var_list:
                    # Every existential variable can depend on EVERYTHING that came before
                    self.hard_predecessors[var] = all_previous_vars.copy()

                    # Peers are other variables in the same block
                    peers = current_block_vars.copy()
                    peers.remove(var)
                    self.same_block_peers[var] = peers

                    # Ensure node exists in instance dependencies
                    if var not in self.dependencies:
                        self.dependencies[var] = set()

            # Add current block to "previous" for the next blocks
            all_previous_vars.update(current_block_vars)

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

    def compute(self):
        """
        Learned scheme is dynamic; initial computation is handled in __init__ via _initialize_structure.
        """
        logger.info(
            "Learning based dependency scheme, dependencies will be computed during learning."
        )
        pass

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Allowed = (Hard Predecessors) U (Allowed Same-Block Peers)
        Allowed Same-Block Peers = (All Peers) \ (Descendants of Target)
        """
        allowed = self.hard_predecessors.get(target_variable, set()).copy()

        peers = self.same_block_peers.get(target_variable, set())
        if not peers:
            return allowed

        valid_peers = set()
        for p in peers:
            # Check if p depends on target (p -> ... -> target)
            if not self._is_reachable(p, target_variable):
                valid_peers.add(p)

        allowed.update(valid_peers)
        return allowed

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
        Invalidates topological sort cache.
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

        # Invalidate cache
        self._topological_order = None
