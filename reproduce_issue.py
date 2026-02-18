import sys
import os
import logging
from pathlib import Path
from src.solver import Solver
from src.guessing_schemes.dependency_guided import DependencyGuidedGuesser
from src.dependency_schemes.triangle import TriangleDependencyScheme
from src.error_schemes.qbf_skolem import QBFSkolemErrorFormula
from src.fault_localization_schemes import LexMaxSATScheme
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.utils.logging_config import setup_logging


def create_xor_instance(filename):
    with open(filename, "w") as f:
        f.write("c XOR instance: Forall x1, x2. Exists y. y <-> x1 ^ x2\n")
        f.write("p cnf 3 4\n")
        f.write("a 1 2 0\n")
        f.write("e 3 0\n")

        # CNF for y <-> (x1 != x2)
        # (x1 v x2 v -y) -> if x1=0, x2=0, then -y must be true -> y=0. Correct.
        f.write("1 2 -3 0\n")

        # (-x1 v -x2 v -y) -> if x1=1, x2=1, then -y must be true -> y=0. Correct.
        f.write("-1 -2 -3 0\n")

        # (-x1 v x2 v y) -> if x1=1, x2=0, then y must be true -> y=1. Correct.
        f.write("-1 2 3 0\n")

        # (x1 v -x2 v y) -> if x1=0, x2=1, then y must be true -> y=1. Correct.
        f.write("1 -2 3 0\n")


def create_chain_xor_instance(filename):
    with open(filename, "w") as f:
        # Forall x1, x2, x3. Exists y1, y2.
        # y1 = x1 ^ x2
        # y2 = y1 ^ x3
        # Vars: x1=1, x2=2, x3=3, y1=4, y2=5
        f.write("c Chained XOR: y1=x1^x2, y2=y1^x3\n")
        f.write("p cnf 5 8\n")
        f.write("a 1 2 3 0\n")
        f.write("e 4 5 0\n")

        # y1 = x1 ^ x2
        f.write("1 2 -4 0\n")
        f.write("-1 -2 -4 0\n")
        f.write("-1 2 4 0\n")
        f.write("1 -2 4 0\n")

        # y2 = y1 ^ x3
        f.write("4 3 -5 0\n")
        f.write("-4 -3 -5 0\n")
        f.write("-4 3 5 0\n")
        f.write("4 -3 5 0\n")


def main():
    instance_path = Path("markdown_example.qdimacs")
    if not instance_path.exists():
        print("Please create markdown_example.qdimacs first.")
        return

    setup_logging("DEBUG", Path("reproduce.log"))

    # Configure solver components
    solver = Solver(
        instance_path=instance_path,
        fl_scheme_cls=LexMaxSATScheme,
        repair_scheme_cls=UnsatCoreRepairScheme,
        num_samples=20,
        max_iterations=100,
        cert_formats=["verilog"],
        error_formula_cls=QBFSkolemErrorFormula,
        dependency_scheme_cls=TriangleDependencyScheme,
        guesser_cls=DependencyGuidedGuesser,
    )

    print("Starting solver on Markdown Example...")
    solver.solve()
    print(f"Solver finished.")


if __name__ == "__main__":
    main()
