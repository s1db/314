import unittest
from src.dependency_schemes.triangle import TriangleDependencyScheme
from src.instance import Instance


class TestTriangleEEDeps(unittest.TestCase):
    def test_existential_dependency(self):
        # A(x) E(y1) E(y2)
        # y1 <-> x
        # y2 <-> y1
        # Clauses:
        # y1 <-> x: (-x v y1), (x v -y1) -> [-1, 2], [1, -2]
        # y2 <-> y1: (-y1 v y2), (y1 v -y2) -> [-2, 3], [2, -3]

        # Triangle should find y2 -> y1?
        # y1 is 2, y2 is 3.
        # y1 is in Block 1? Or separate block?
        # Let's put them in separate blocks to be safe for Triangle iteration.
        # A(x) E(y1) E(y2) -> 3 blocks.

        quantifiers = [("a", [1]), ("e", [2]), ("e", [3])]
        clauses = [[-1, 2], [1, -2], [-2, 3], [2, -3]]

        instance = Instance(3, 4, quantifiers, clauses, TriangleDependencyScheme)
        scheme = instance.dependency_scheme
        # scheme.compute() is called in __init__

        print(f"Dependencies for 3 (y2): {scheme.get_dependencies(3)}")

        # We expect 3 to depend on 2
        self.assertIn(2, scheme.get_dependencies(3))


if __name__ == "__main__":
    unittest.main()
