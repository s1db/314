from typing import List, Tuple, Set
from src.dependency_schemes.base import DependencyScheme


class StandardDependencyScheme(DependencyScheme):
    """
    Implements the Standard Dependency Scheme.
    A variable y depends on x if:
    1. y is to the right of x (y > x).
    2. x and y have different quantifier types.
    3. There is an X-path between a clause containing x and a clause containing y,
       where X = {existential variables to the right of x}.
    """

    def __init__(
        self,
        num_vars: int,
        clauses: List[List[int]],
        quantifiers: List[Tuple[str, List[int]]],
    ):
        super().__init__(num_vars, clauses, quantifiers)

    def compute(self):
        # Optimized Standard Scheme using block structure and alternating quantifiers.

        # 1. Map variables to clauses they appear in
        lit_to_clauses = {}
        for i, clause in enumerate(self.clauses):
            for lit in clause:
                if lit not in lit_to_clauses:
                    lit_to_clauses[lit] = []
                lit_to_clauses[lit].append(i)

        quantifiers = self.quantifiers
        n_blocks = len(quantifiers)

        # Helper: Get all variables from a list of blocks
        def get_vars_from_blocks(start_block_idx):
            vars_list = []
            for i in range(start_block_idx, n_blocks):
                vars_list.extend(quantifiers[i][1])
            return vars_list

        # Helper map: var -> qtype
        var_to_qtype = {}
        for q_type, vars in quantifiers:
            for v in vars:
                var_to_qtype[v] = q_type

        # Iterate over blocks
        for i, (q_type, vars) in enumerate(quantifiers):
            if not vars:
                continue

            # Identify X: Set of existential variables in downstream blocks
            # For Standard Scheme: X = {v in R(x) | type(v) == 'e'}
            # We treat blocks as units. X is constant for all x in the current block,
            # assuming independence within the block.

            X = set()
            for j in range(i + 1, n_blocks):
                jq_type, jvars = quantifiers[j]
                if jq_type == "e":
                    X.update(jvars)

            # Map variable in X -> list of clauses it connects
            x_var_to_clauses = {}
            for v in X:
                clauses = []
                if v in lit_to_clauses:
                    clauses.extend(lit_to_clauses[v])
                if -v in lit_to_clauses:
                    clauses.extend(lit_to_clauses[-v])
                x_var_to_clauses[v] = list(set(clauses))

            # Build adjacency list for clauses based on X
            clause_adj = {c_idx: set() for c_idx in range(len(self.clauses))}
            for v, c_idxs in x_var_to_clauses.items():
                for k in range(len(c_idxs)):
                    c1 = c_idxs[k]
                    for m in range(k + 1, len(c_idxs)):
                        c2 = c_idxs[m]
                        clause_adj[c1].add(c2)
                        clause_adj[c2].add(c1)

            # Determine reachable clauses for each x in the block
            downstream_vars = get_vars_from_blocks(i + 1)

            for x in vars:
                start_clauses = set()
                if x in lit_to_clauses:
                    start_clauses.update(lit_to_clauses[x])
                if -x in lit_to_clauses:
                    start_clauses.update(lit_to_clauses[-x])

                if not start_clauses:
                    continue

                # BFS
                reachable_clauses = set()
                queue = list(start_clauses)
                visited = set(start_clauses)

                idx = 0
                while idx < len(queue):
                    curr = queue[idx]
                    idx += 1
                    reachable_clauses.add(curr)
                    for neighbor in clause_adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                # Check connections to y
                if x not in self.dependencies:
                    self.dependencies[x] = set()

                for y in downstream_vars:
                    if var_to_qtype[y] == q_type:
                        continue

                    is_connected = False
                    if y in lit_to_clauses:
                        for c in lit_to_clauses[y]:
                            if c in reachable_clauses:
                                is_connected = True
                                break
                    if not is_connected and -y in lit_to_clauses:
                        for c in lit_to_clauses[-y]:
                            if c in reachable_clauses:
                                is_connected = True
                                break

                    if is_connected:
                        if y not in self.dependencies:
                            self.dependencies[y] = set()
                        self.dependencies[y].add(x)

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        Standard is a static scheme.
        Allowed variables are strictly those computed during initialization/compute().
        """
        return self.dependencies.get(target_variable, set()).copy()

    def update_dependencies(self, target_variable: int, used_variables: Set[int]):
        """
        Validates that used_variables are within the statically computed allowed set.
        """
        allowed = self.get_allowed_variables(target_variable)
        if not used_variables.issubset(allowed):
            # Identify which variables are violations
            violations = used_variables - allowed
            raise ValueError(
                f"Dependency violation: Variable {target_variable} tried to depend on {violations}, "
                f"which is not allowed by the static Standard scheme."
            )
        # No graph update needed as it's static and we just verified compliance.

    def verify_dependencies(self) -> None:
        """
        Custom verification for Standard Scheme.
        Allows strict forward dependencies and universal variable dependencies.
        """
        # Cycle detection
        self.topological_sort()

        # Range check and self-dependency check
        for u, deps in self.dependencies.items():
            for v in deps:
                if u == v:
                    raise ValueError(
                        f"Self-dependency detected: variable {u} depends on itself."
                    )
                if not (1 <= v <= self.num_vars):
                    raise ValueError(f"Variable {v} is out of valid range.")
            if not (1 <= u <= self.num_vars):
                raise ValueError(f"Variable {u} is out of valid range.")
