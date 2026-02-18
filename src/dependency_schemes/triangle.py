from typing import List, Set, Dict, Tuple
from src.dependency_schemes.base import DependencyScheme
from src.instance import Instance


class TriangleDependencyScheme(DependencyScheme):
    """
    Implements the Triangle Dependency Scheme.
    """

    def __init__(self, instance: Instance):
        super().__init__(instance)

    def compute(self):
        # Optimized Triangle Scheme using block structure and alternating quantifiers.

        # 1. Map literals to clauses
        lit_to_clauses = {}
        for i, clause in enumerate(self.instance.clauses):
            for lit in clause:
                if lit not in lit_to_clauses:
                    lit_to_clauses[lit] = []
                lit_to_clauses[lit].append(i)

        quantifiers = self.instance.quantifiers
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

            # Identify X_base: Set of existential variables in downstream blocks
            X_base = set()
            for j in range(i + 1, n_blocks):
                jq_type, jvars = quantifiers[j]
                if jq_type == "e":
                    X_base.update(jvars)

            # Build core adjacency from X_base
            # We need labeled edges to support filtering (for Case 1 ignored_var)

            x_var_to_clauses = {}
            for v in X_base:
                clauses = []
                if v in lit_to_clauses:
                    clauses.extend(lit_to_clauses[v])
                if -v in lit_to_clauses:
                    clauses.extend(lit_to_clauses[-v])
                x_var_to_clauses[v] = list(set(clauses))

            adj_core = {idx: {} for idx in range(len(self.instance.clauses))}
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

            downstream_vars = get_vars_from_blocks(i + 1)

            # Process variables in current block
            # Case 1: Block is Universal
            if q_type == "a":
                # For each x (Universal), check y (Existential downstream)
                # X = X_base U {x} \ {y}
                # adj = adj_core + edges(x) - edges(y)
                # We simulate adding x by passing extra_connector_var=x
                # We simulate removing y by passing ignored_var=y

                for x in vars:
                    c1_candidates = set()
                    if x in lit_to_clauses:
                        c1_candidates.update(lit_to_clauses[x])
                    if -x in lit_to_clauses:
                        c1_candidates.update(lit_to_clauses[-x])

                    if not c1_candidates:
                        continue  # No clauses contain x, so no dependencies?

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
                # X = X_base U {y}
                # adj = adj_core + edges(y)
                # extra_connector_var = y
                # x is NOT in X, so no extra connector for x.

                for x in vars:
                    c1_candidates = set()
                    if x in lit_to_clauses:
                        c1_candidates.update(lit_to_clauses[x])
                    if -x in lit_to_clauses:
                        c1_candidates.update(lit_to_clauses[-x])

                    # Usually x starts the chain?
                    # Spec: "Triangle: C1(y), C2(x), C3(-x)"
                    # Connections: C1-C2 and C1-C3 via X.
                    # We check if Exists C1(y) such that C1 reaches C2(x) and C3(-x).
                    # This is symmetric to starting from C2/C3 and reaching C1?
                    # BFS is undirected.
                    # So if we start from C1(y), we check if we reach C2(x) and C3(-x).

                    for y in downstream_vars:
                        if var_to_qtype[y] == "e":
                            continue

                        # C1 candidates are clauses containing y
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

    def verify_dependencies(self) -> None:
        """
        Custom verification for Triangle Scheme.
        """
        self.topological_sort()
        for u, deps in self.dependencies.items():
            for v in deps:
                if u == v:
                    raise ValueError(
                        f"Self-dependency detected: variable {u} depends on itself."
                    )
                if not (1 <= v <= self.instance.num_vars):
                    raise ValueError(f"Variable {v} is out of valid range.")
            if not (1 <= u <= self.instance.num_vars):
                raise ValueError(f"Variable {u} is out of valid range.")
