import argparse
import sys
import logging
from pathlib import Path
from src.solver import Solver
from src.fault_localization_schemes import MaxSATScheme, LexMaxSATScheme
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.error_schemes.bfns import BFnSErrorFormula
from src.error_schemes.qbf_skolem import QBFSkolemErrorFormula
from src.guessing_schemes.manthan import ManthanGuesser
from src.guessing_schemes.dependency_guided import DependencyGuidedGuesser
from src.dependency_schemes import (
    LearnedDependencyScheme,
    TriangleDependencyScheme,
    UniTriDependencyScheme,
    StandardDependencyScheme,
)
from src.utils.logging_config import setup_logging


def parse_args():
    parser = argparse.ArgumentParser(description="314 QBF Solver CLI")

    parser.add_argument("instance", type=Path, help="Path to the QDIMACS instance file")

    parser.add_argument(
        "-f",
        "--fl-scheme",
        choices=["maxsat", "lexmaxsat"],
        default="lexmaxsat",
        help="Fault Localization Scheme to use",
    )

    parser.add_argument(
        "-r",
        "--repair-scheme",
        choices=["unsat-core"],
        default="unsat-core",
        help="Repair Scheme to use",
    )

    parser.add_argument(
        "-s", "--samples", type=int, default=100, help="Number of samples to use"
    )

    parser.add_argument(
        "-i",
        "--max-iterations",
        type=int,
        default=100,
        help="Maximum number of repair iterations",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to the log file. If not set, defaults to instance_name.log",
    )

    parser.add_argument(
        "--cert-format",
        nargs="+",
        choices=["verilog", "aiger", "aiger_caqe"],
        default=["verilog"],
        help="Format(s) for the Skolem function output (Verilog, AIGER)",
    )

    parser.add_argument(
        "-e",
        "--error-scheme",
        choices=["bfns", "qbf-skolem"],
        default="bfns",
        help="Error Scheme to verify candidates (BFnS, QBF-Skolem)",
    )

    parser.add_argument(
        "-g",
        "--guesser",
        choices=["manthan", "dependency-guided"],
        default="dependency-guided",
        help="Candidate Function Guesser to use",
    )

    parser.add_argument(
        "-d",
        "--dep-scheme",
        choices=["learned", "triangle", "unitri", "standard"],
        default=None,
        help="Dependency Scheme to use. Defaults: 'learned' for Manthan, 'triangle' for Dependency-Guided.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Determine log file path
    log_file = args.log_file
    if not log_file:
        # Default to instance_name.log in current directory
        log_file = Path(f"{args.instance.stem}.log")

    try:
        setup_logging(args.log_level, log_file)
    except ValueError as e:
        print(f"Error setting up logging: {e}", file=sys.stderr)
        sys.exit(1)

    logger = logging.getLogger(__name__)

    if not args.instance.exists():
        logger.error(f"Error: Instance file {args.instance} does not exist.")
        sys.exit(1)

    # Map choices to classes
    fl_schemes = {"maxsat": MaxSATScheme, "lexmaxsat": LexMaxSATScheme}
    repair_schemes = {"unsat-core": UnsatCoreRepairScheme}
    error_schemes = {
        "bfns": BFnSErrorFormula,
        "qbf-skolem": QBFSkolemErrorFormula,
    }
    dep_schemes = {
        "learned": LearnedDependencyScheme,
        "triangle": TriangleDependencyScheme,
        "unitri": UniTriDependencyScheme,
        "standard": StandardDependencyScheme,
    }

    fl_cls = fl_schemes[args.fl_scheme]
    repair_cls = repair_schemes[args.repair_scheme]
    error_cls = error_schemes[args.error_scheme]

    # Resolve Guesser and Dependency Scheme
    guesser_cls = None
    dep_scheme_name = args.dep_scheme

    if args.guesser == "manthan":
        if dep_scheme_name is None:
            dep_scheme_name = "learned"
        elif dep_scheme_name != "learned":
            raise ValueError(
                "Manthan guesser only supports 'learned' dependency scheme."
            )
        guesser_cls = ManthanGuesser

    elif args.guesser == "dependency-guided":
        if dep_scheme_name is None:
            dep_scheme_name = "triangle"
        elif dep_scheme_name == "learned":
            raise ValueError(
                "Dependency-guided guesser cannot use 'learned' dependency scheme."
            )
        guesser_cls = DependencyGuidedGuesser
    else:
        # Should be covered by argparse choices, but for safety
        raise ValueError(f"Unknown guesser type: {args.guesser}")

    dep_cls = dep_schemes[dep_scheme_name]

    logger.info(f"Initializing Solver for {args.instance}...")
    logger.info(f"Guesser: {args.guesser}, Dependency Scheme: {dep_scheme_name}")

    solver = Solver(
        instance_path=args.instance,
        fl_scheme_cls=fl_cls,
        repair_scheme_cls=repair_cls,
        num_samples=args.samples,
        max_iterations=args.max_iterations,
        cert_formats=args.cert_format,
        error_formula_cls=error_cls,
        dependency_scheme_cls=dep_cls,
        guesser_cls=guesser_cls,
    )

    solver.solve()


if __name__ == "__main__":
    main()
