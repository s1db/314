from typing import Set, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from src.candidate_function import CandidateFunction
from src.instance import Instance
from .base import DependencyScheme, DependencyViolationError


class LearnedDependencyScheme(DependencyScheme):
    """
    A dependency scheme where:
    1. Dependencies strictly respect QBF quantifier blocks.
    2. Intra-block dependencies are allowed and learned, providing they don't form cycles.
    """

    def __init__(self, instance: Instance):
        super().__init__(instance)

        # Precompute the "hard" constraints based on QBF prefix
        self.hard_predecessors: Dict[int, Set[int]] = {}
        self.same_block_peers: Dict[int, Set[int]] = {}
        self._initialize_structure()

    def _initialize_structure(self):
        """Analyzes the QBF prefix to populate hard constraints."""
        all_previous_vars = set()

        for q_type, var_list in self.instance.quantifiers:
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

    def compute(self):
        pass

    def register_candidates(
        self, candidates: Dict[int, "CandidateFunction"], logger=None
    ):
        """
        Registers candidates and updates dependencies.
        """
        if logger is None:
            import logging

            logger = logging.getLogger(__name__)

        for y, func in candidates.items():
            # IMPORTANT: Register the learned dependencies!
            try:
                logger.info(f"Registering dependencies for {y}: {func}")
                self.update_dependencies(y, func.support)
            except Exception as e:
                logger.warning(
                    f"Initial candidate for {y} violates dependencies: {e}. Clearing support."
                )
                pass

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
