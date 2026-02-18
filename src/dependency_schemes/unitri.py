from src.dependency_schemes.triangle import TriangleDependencyScheme
from src.instance import Instance


class UniTriDependencyScheme(TriangleDependencyScheme):
    """
    Implements the UniTri Dependency Scheme.
    This scheme extends the Triangle scheme by treating all existential variables
    defined before the variable whose dependency we're computing in a quantifier
    prefix as universals for the purpose of dependency calculation.

    It also implements a transitive reduction mechanism: if y depends on x, and x depends on u,
    then u is removed from y's dependencies (assuming x covers u).
    """

    def __init__(self, instance: Instance):
        # Store full (unreduced) dependencies for transitive closure checks
        self.full_dependencies = {}
        super().__init__(instance)

    def compute(self):
        """
        Compute dependencies using the UniTri scheme with transitive reduction.
        """
        # 1. Map literals to clauses
        lit_to_clauses = {}
        for i, clause in enumerate(self.instance.clauses):
            for lit in clause:
                if lit not in lit_to_clauses:
                    lit_to_clauses[lit] = []
                lit_to_clauses[lit].append(i)

        # Flatten quantifiers to list of variables with their types
        flat_prefix = []
        var_to_qtype = {}
        for q_type, vars in self.instance.quantifiers:
            for v in vars:
                flat_prefix.append((q_type, v))
                var_to_qtype[v] = q_type

        # Iterate through EACH variable in the prefix
        for i, (q_type, target_y) in enumerate(flat_prefix):
            if q_type != "e":
                continue

            # Identify downstream existentials (X_base)
            downstream_existentials = []
            for j in range(i + 1, len(flat_prefix)):
                dq_type, dvar = flat_prefix[j]
                if dq_type == "e":
                    downstream_existentials.append(dvar)

            X_base = set(downstream_existentials)

            # Build adj_core for this X_base
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

            # Check ALL predecessors (Univ + Exist)
            preceding_indices = range(i - 1, -1, -1)
            raw_dependencies = set()

            for p_idx in preceding_indices:
                p_qtype, source_v = flat_prefix[p_idx]

                # Check dependency source_v -> target_y
                c1_candidates = set()
                if source_v in lit_to_clauses:
                    c1_candidates.update(lit_to_clauses[source_v])
                if -source_v in lit_to_clauses:
                    c1_candidates.update(lit_to_clauses[-source_v])

                if not c1_candidates:
                    continue

                # Run BFS
                has_dep = False
                for c1 in c1_candidates:
                    reached = self._bfs(
                        c1,
                        adj_core,
                        ignored_var=target_y,
                        extra_connector_var=source_v,
                        lit_to_clauses=lit_to_clauses,
                    )

                    has_pos_y = False
                    if target_y in lit_to_clauses:
                        for c in lit_to_clauses[target_y]:
                            if c in reached:
                                has_pos_y = True
                                break

                    has_neg_y = False
                    if has_pos_y and -target_y in lit_to_clauses:
                        for c in lit_to_clauses[-target_y]:
                            if c in reached:
                                has_neg_y = True
                                break

                    if has_pos_y and has_neg_y:
                        has_dep = True
                        break

                if has_dep:
                    self._add_dep(source_v, target_y)
                    raw_dependencies.add(source_v)

            # Store full (unreduced) dependencies for transitive closure
            self.full_dependencies[target_y] = raw_dependencies

            # Transitive Reduction Step
            if target_y in self.dependencies:
                deps = list(self.dependencies[target_y])
                to_remove = set()

                for u in deps:
                    # Check if u is covered by any existential dependency v
                    for v in deps:
                        if v == u:
                            continue
                        if var_to_qtype.get(v) == "e":
                            # Check if v depends on u (using FULL dependency set)
                            if (
                                v in self.full_dependencies
                                and u in self.full_dependencies[v]
                            ):
                                to_remove.add(u)
                                break

                for u in to_remove:
                    self.dependencies[target_y].remove(u)
