from pathlib import Path
from src.solver import Solver
from src.fault_localization_schemes import LexMaxSATScheme
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.error_schemes.bfns import BFnSErrorFormula
from src.guessing_schemes.dependency_guided import DependencyGuidedGuesser
from src.dependency_schemes import TriangleDependencyScheme
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)

instance_path = Path("test_instances/qbf/simple_existential.qdimacs")

solver = Solver(
    instance_path=instance_path,
    fl_scheme_cls=LexMaxSATScheme,
    repair_scheme_cls=UnsatCoreRepairScheme,
    num_samples=100,
    max_iterations=10,
    cert_formats=["verilog"],
    error_formula_cls=BFnSErrorFormula,
    dependency_scheme_cls=TriangleDependencyScheme,
    guesser_cls=DependencyGuidedGuesser,
)

solver.solve()
