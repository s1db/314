import unittest
from src.dependency_schemes.triangle import TriangleDependencyScheme
from src.instance import Instance


class TestTriangleSpec(unittest.TestCase):
    def test_markdown_example(self):
        # Formula:
        # P: Au, Ev, Aw, Ex, Ay, Ez
        # Clauses:
        # C1: (u v -v v x) -> [1, -2, 4]
        # C2: (u v -x)     -> [1, -4]
        # C3: (v v z)      -> [2, 6]
        # C4: (v v -z)     -> [2, -6]
        # C5: (w v x v y)  -> [3, 4, 5]
        # C6: (y v -z)     -> [5, -6]

        # Vars: u=1, v=2, w=3, x=4, y=5, z=6
        quantifiers = [
            ("a", [1]),
            ("e", [2]),
            ("a", [3]),
            ("e", [4]),
            ("a", [5]),
            ("e", [6]),
        ]

        clauses = [[1, -2, 4], [1, -4], [2, 6], [2, -6], [3, 4, 5], [5, -6]]

        instance = Instance(6, 6, quantifiers, clauses, TriangleDependencyScheme)
        scheme = instance.dependency_scheme

        print("Computed Dependencies:")
        for v in range(1, 7):
            deps = scheme.get_dependencies(v)
            print(f"D({v}): {deps}")

        # Verify against Markdown Table (Inverse)
        # Table: D(u)={x,z}, D(v)={y}, others empty.
        # This implies:
        # x depends on u
        # z depends on u
        # y depends on v

        # Code stores Dependencies OF the key.

        # D(u=1): {}
        self.assertEqual(scheme.get_dependencies(1), set())

        # D(v=2): {}
        self.assertEqual(scheme.get_dependencies(2), set())

        # D(w=3): {}
        self.assertEqual(scheme.get_dependencies(3), set())

        # D(x=4): {u} -> {1}
        self.assertEqual(scheme.get_dependencies(4), {1})

        # D(y=5): {v} -> {2}
        self.assertEqual(scheme.get_dependencies(5), {2})

        # D(z=6): {u} -> {1}
        # Note: Spec says D(y)={z}, so z depends on y too!
        # D(y)={z} means z depends on y.
        # So D(z) should be {u, y} -> {1, 5}
        self.assertEqual(scheme.get_dependencies(6), {1, 5})


if __name__ == "__main__":
    unittest.main()
