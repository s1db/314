import unittest
from src.dependency_schemes.unitri import UniTriDependencyScheme
from src.instance import Instance


class TestUniTriDependencyScheme(unittest.TestCase):
    def test_basic_dependencies(self):
        # 1 (Univ) -> 2 (Exist)
        # Clauses: [1, 2], [-1, -2] (XOR)
        # If 1=T, 2=F. If 1=F, 2=T. Dependency exists.

        quantifiers = [("a", [1]), ("e", [2])]
        clauses = [[1, 2], [-1, -2]]
        instance = Instance(2, len(clauses), quantifiers, clauses)
        scheme = UniTriDependencyScheme(2, clauses, quantifiers)
        instance.set_dependency_scheme(scheme)

        scheme = UniTriDependencyScheme(
            instance.num_vars, instance.clauses, instance.quantifiers
        )

        # 2 depends on 1
        self.assertIn(1, scheme.dependencies.get(2, set()))

    def test_transitive_reduction(self):
        # 1(A) -> 2(E) -> 3(E)
        # 1->2: [1, 2], [-1, -2]
        # 2->3: [2, 3], [-2, -3]
        # 1->3: [1, 3], [-1, -3] (Direct connection)

        quantifiers = [("a", [1]), ("e", [2]), ("e", [3])]
        # All XOR-like clauses to ensure strong dependencies
        clauses = [
            [1, 2],
            [-1, -2],  # 2 depends on 1
            [2, 3],
            [-2, -3],  # 3 depends on 2
            [1, 3],
            [-1, -3],  # 3 depends on 1
        ]
        instance = Instance(3, len(clauses), quantifiers, clauses)
        scheme = UniTriDependencyScheme(3, clauses, quantifiers)
        instance.set_dependency_scheme(scheme)

        scheme = UniTriDependencyScheme(
            instance.num_vars, instance.clauses, instance.quantifiers
        )

        deps_2 = scheme.full_dependencies.get(2, set())  # Check full deps for coverage
        self.assertIn(1, deps_2)

        # 3 should depend on 2
        deps_3 = scheme.dependencies.get(3, set())
        self.assertIn(2, deps_3)

        # 3 should NOT depend on 1 because 2 depends on 1 and checks cover it (transitive reduction)
        # Wait, does 2 COVER 1?
        # UniTri reduction: if y deps x, and x full_deps u.
        # Here y=3, x=2, u=1.
        # 2 deps 1. 2 full_deps 1.
        # So 1 should be removed from 3.
        self.assertNotIn(
            1,
            deps_3,
            f"Dependency 1 should be reduced because 2 covers it. Deps: {deps_3}",
        )


if __name__ == "__main__":
    unittest.main()
