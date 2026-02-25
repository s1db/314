import argparse
import sys
import logging
from pathlib import Path
from typing import Type, Dict
from src.solver import Solver
from src.fault_localization_schemes import (
    FaultLocalizationScheme,
    MaxSATScheme,
    LexMaxSATScheme,
)
from src.repair_schemes.base import RepairScheme
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.repair_schemes.interpolant import InterpolantRepairScheme
from src.error_schemes.base import ErrorFormula
from src.error_schemes.bfns import BFnSErrorFormula
from src.error_schemes.qbf_skolem import QBFSkolemErrorFormula
from src.utils.logging_config import setup_logging
from src.preprocessing import (
    ManthanUnatePreprocessor,
    ManthanUniquePreprocessor,
    GuessUnatePreprocessor,
    PySMTUniquePreprocessor,
)


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
        choices=["unsat-core", "interpolant"],
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
        "-l",
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )

    parser.add_argument(
        "-lf",
        "--log-file",
        type=Path,
        help="Path to the log file. If not set, defaults to instance_name.log",
    )

    parser.add_argument(
        "-c",
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
        "-p",
        "--preprocess",
        nargs="*",
        choices=["manthan-unate", "manthan-unique", "guess-unate", "pysmt-unique"],
        default=[],
        help="Preprocessing techniques to enable (e.g., manthan-unate, manthan-unique, guess-unate, pysmt-unique)",
    )

    parser.add_argument(
        "--no-verify-unate",
        action="store_true",
        help="Disable formal verification in guess-unate preprocessor",
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
    fl_schemes: Dict[str, Type[FaultLocalizationScheme]] = {
        "maxsat": MaxSATScheme,
        "lexmaxsat": LexMaxSATScheme,
    }
    repair_schemes: Dict[str, Type[RepairScheme]] = {
        "unsat-core": UnsatCoreRepairScheme,
        "interpolant": InterpolantRepairScheme,
    }
    error_schemes: Dict[str, Type[ErrorFormula]] = {
        "bfns": BFnSErrorFormula,
        "qbf-skolem": QBFSkolemErrorFormula,
    }

    fl_cls = fl_schemes[args.fl_scheme]
    repair_cls = repair_schemes[args.repair_scheme]
    error_cls = error_schemes[args.error_scheme]

    # Setup Preprocessors
    preprocessor_map = {
        "manthan-unate": lambda: ManthanUnatePreprocessor(),
        "manthan-unique": lambda: ManthanUniquePreprocessor(),
        "guess-unate": lambda: GuessUnatePreprocessor(verify=not args.no_verify_unate),
        "pysmt-unique": lambda: PySMTUniquePreprocessor(),
    }
    preprocessors = []
    for p_name in args.preprocess:
        preprocessors.append(preprocessor_map[p_name]())

    logger.info(f"Initializing Solver for {args.instance}...")
    solver = Solver(
        instance_path=args.instance,
        fl_scheme_cls=fl_cls,
        repair_scheme_cls=repair_cls,
        num_samples=args.samples,
        max_iterations=args.max_iterations,
        cert_formats=args.cert_format,
        error_formula_cls=error_cls,
        preprocessors=preprocessors,
    )

    solver.solve()


if __name__ == "__main__":
    main()
