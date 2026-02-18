import unittest
from pathlib import Path
from src.dependency_schemes.triangle import TriangleDependencyScheme
from src.instance_parsers.qbf import QBFParser


class TestTriangleChain(unittest.TestCase):
    def test_chain_dependencies(self):
        instance_path = Path("reproduce_chain.qdimacs")
        if not instance_path.exists():
            print("Please run reproduce_issue.py first to generate the qdimacs file.")
            return

        instance = QBFParser.from_file(instance_path, TriangleDependencyScheme)
        scheme = instance.dependency_scheme

        # Vars: x1=1, x2=2, x3=3, y1=4, y2=5
        # y1 depends on x1, x2.
        # y2 depends on y1, x3 -> transitively x1, x2, x3.

        d4 = scheme.get_dependencies(4)
        print(f"D(y1=4): {d4}")
        self.assertIn(1, d4)
        self.assertIn(2, d4)

        d5 = scheme.get_dependencies(5)
        print(f"D(y2=5): {d5}")

        # Check if x1, x2 are in D(y2)
        # If they are missing, Triangle is failing to connect via y1.
        self.assertIn(1, d5, "y2 should depend on x1")
        self.assertIn(2, d5, "y2 should depend on x2")
        self.assertIn(3, d5, "y2 should depend on x3")


if __name__ == "__main__":
    unittest.main()
