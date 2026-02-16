from typing import Set, Dict
from src.instance import Instance
from .base import DependencyScheme


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
