from typing import List, Tuple, Set, Dict
from src.dependency_schemes.static import StaticDependencyScheme


class TriangleDependencyScheme(StaticDependencyScheme):
    """
    Implements the Triangle Dependency Scheme.
    A variable y depends on x if:
    1. y is to the right of x (y > x).
    2. x and y have different quantifier types.
    3. Exists an X-path between two clauses C1, C2 such that
       {x, y} subset C1 and {-x, y} subset C2, where X = {existential variables to the right of y}.
    """

    def __init__(
        self,
        quantifiers: List[Tuple[str, List[int]]],
        num_vars: int,
        clauses: List[List[int]],
    ):
        self.clauses = clauses
        super().__init__(quantifiers, num_vars)

    def compute(self):
        # 1. Map literals to clauses
        lit_to_clauses: Dict[int, List[int]] = {}
        for i, clause in enumerate(self.clauses):
            for lit in clause:
                if lit not in lit_to_clauses:
                    lit_to_clauses[lit] = []
                lit_to_clauses[lit].append(i)

        quantifiers = self.quantifiers
        n_blocks = len(quantifiers)

        var_to_qtype = {}
        for q_type, vars in quantifiers:
            for v in vars:
                var_to_qtype[v] = q_type

        # Iterate over blocks
        for i, (q_type, vars) in enumerate(quantifiers):
            if not vars:
                continue

            # Downstream variables are those in blocks > i
            downstream_vars = []
            for j in range(i + 1, n_blocks):
                downstream_vars.extend(quantifiers[j][1])

            # Precompute X_base: set of all existential variables to the right of EVERYTHING in this block.
            # Triangle Spec: X(y) = {v in R(y) | type(v) == 'e'}
            # Here, we refine X because we only care about existentials to the right of y.
            # We'll compute X_base as the union of all existential variables in blocks > i.
            X_base = set()
            for j in range(i + 1, n_blocks):
                jq_type, jvars = quantifiers[j]
                if jq_type == "e":
                    X_base.update(jvars)

            # Build adj_core for X_base (subset of X(y) for any y in downstream_vars)
            x_var_to_clauses = {}
            for v in X_base:
                clauses = []
                if v in lit_to_clauses:
                    clauses.extend(lit_to_clauses[v])
                if -v in lit_to_clauses:
                    clauses.extend(lit_to_clauses[-v])
                x_var_to_clauses[v] = list(set(clauses))

            adj_core: Dict[int, Dict[int, Set[int]]] = {
                idx: {} for idx in range(len(self.clauses))
            }
            for v, c_idxs in x_var_to_clauses.items():
                for k in range(len(c_idxs)):
                    c1 = c_idxs[k]
                    for m in range(k + 1, len(c_idxs)):
                        c2 = c_idxs[m]
                        if c2 not in adj_core[c1]:
                            adj_core[c1][c2] = set()
                        adj_core[c1][c2].add(v)
                        if c1 not in adj_core[c2]:
                            adj_core[c2][c1] = set()
                        adj_core[c2][c1].add(v)

            # Case 1: Block is Universal
            if q_type == "a":
                # For each x (Universal), check y (Existential downstream)
                for x in vars:
                    # Identify clauses containing x and -x (candidates for C1)
                    c1_candidates = set()
                    if x in lit_to_clauses:
                        c1_candidates.update(lit_to_clauses[x])
                    if -x in lit_to_clauses:
                        c1_candidates.update(lit_to_clauses[-x])

                    if not c1_candidates:
                        continue

                    # We need to iterate y.
                    # Optimization: Iterate only existential y
                    for y in downstream_vars:
                        if var_to_qtype[y] == "a":
                            continue

                        # Check reachability
                        # We can start BFS from any c1 in c1_candidates.
                        # But we need ONE c1 to connect to BOTH y and -y (via X).

                        for c1 in c1_candidates:
                            reached = self._bfs(
                                c1,
                                adj_core,
                                ignored_var=y,
                                extra_connector_var=x,
                                lit_to_clauses=lit_to_clauses,
                            )

                            has_pos_y = False
                            if y in lit_to_clauses:
                                for c in lit_to_clauses[y]:
                                    if c in reached:
                                        has_pos_y = True
                                        break

                            has_neg_y = False
                            if has_pos_y and -y in lit_to_clauses:
                                for c in lit_to_clauses[-y]:
                                    if c in reached:
                                        has_neg_y = True
                                        break

                            if has_pos_y and has_neg_y:
                                self._add_dep(x, y)
                                break

            # Case 2: Block is Existential
            else:  # q_type == 'e'
                # For each x (Existential), check y (Universal downstream)
                for x in vars:
                    # C1 candidates are clauses containing y
                    for y in downstream_vars:
                        if var_to_qtype[y] == "e":
                            continue

                        y_candidates = set()
                        if y in lit_to_clauses:
                            y_candidates.update(lit_to_clauses[y])
                        if -y in lit_to_clauses:
                            y_candidates.update(lit_to_clauses[-y])

                        if not y_candidates:
                            continue

                        for c1 in y_candidates:
                            reached = self._bfs(
                                c1,
                                adj_core,
                                extra_connector_var=y,
                                lit_to_clauses=lit_to_clauses,
                            )

                            has_pos_x = False
                            if x in lit_to_clauses:
                                for c in lit_to_clauses[x]:
                                    if c in reached:
                                        has_pos_x = True
                                        break

                            has_neg_x = False
                            if has_pos_x and -x in lit_to_clauses:
                                for c in lit_to_clauses[-x]:
                                    if c in reached:
                                        has_neg_x = True
                                        break

                            if has_pos_x and has_neg_x:
                                self._add_dep(x, y)
                                break

    def _bfs(
        self,
        start_node,
        adj,
        ignored_var=None,
        extra_connector_var=None,
        lit_to_clauses=None,
    ):
        queue = [start_node]
        visited = {start_node}

        extra_clauses = []
        if extra_connector_var is not None and lit_to_clauses:
            if extra_connector_var in lit_to_clauses:
                extra_clauses.extend(lit_to_clauses[extra_connector_var])
            if -extra_connector_var in lit_to_clauses:
                extra_clauses.extend(lit_to_clauses[-extra_connector_var])

        extra_clauses_set = set(extra_clauses)
        visited_extra_clique = False

        if start_node in extra_clauses_set:
            visited_extra_clique = True
            for c in extra_clauses:
                if c not in visited:
                    visited.add(c)
                    queue.append(c)

        idx = 0
        while idx < len(queue):
            curr = queue[idx]
            idx += 1

            # Normal neighbors (with filtering)
            if curr in adj:
                for neighbor, reasons in adj[curr].items():
                    is_valid = False
                    if ignored_var is None:
                        is_valid = True
                    else:
                        for r in reasons:
                            if r != ignored_var:
                                is_valid = True
                                break

                    if is_valid and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            # Extra connector neighbors
            if extra_connector_var is not None and not visited_extra_clique:
                if curr in extra_clauses_set:
                    visited_extra_clique = True
                    for c in extra_clauses:
                        if c not in visited:
                            visited.add(c)
                            queue.append(c)

        return visited

    def _add_dep(self, x, y):
        # x is predecessor, y is successor.
        # We want to store dependencies of y (i.e. x).
        if y not in self.dependencies:
            self.dependencies[y] = set()
        self.dependencies[y].add(x)
