from pathlib import Path
from typing import Dict, List, Type

import logging
from src.instance import Instance
from src.instance_parsers.qbf import QBFParser
from src.sampling_schemes.uniform import UniformSampler
from src.dependency_schemes.mutable import MutableDependencyScheme
from src.guessing_schemes.manthan import ManthanGuesser
from src.candidate_function import FunctionManager, CandidateFunction
from src.error_schemes.base import ErrorFormula
from src.error_schemes.bfns import BFnSErrorFormula
from src.fault_localization_schemes import FaultLocalizationScheme
from src.preprocessing.base import Preprocessor
from src.repair_schemes.base import RepairScheme
from src.outputs.verilog_skolem import write_verilog_skolem
from src.outputs.aiger_skolem import write_aiger_skolem


class Solver:
    def __init__(
        self,
        instance_path: Path,
        fl_scheme_cls: Type[FaultLocalizationScheme],
        repair_scheme_cls: Type[RepairScheme],
        num_samples: int = 5000,
        max_iterations: int = 1000,
        cert_formats: List[str] | None = None,
        error_formula_cls: Type[ErrorFormula] = BFnSErrorFormula,
        preprocessors: List[Preprocessor] | None = None,
    ):

        self.logger = logging.getLogger(__name__)
        self.instance_path = instance_path
        self.num_samples = num_samples
        self.max_iterations = max_iterations
        self.cert_formats = cert_formats if cert_formats else ["verilog"]
        self.preprocessors = preprocessors if preprocessors else []

        # 1. Parse Instance
        self.logger.info(f"Parsing instance: {instance_path}")
        # Pass the desired dependency scheme class to the parser
        self.instance: Instance = QBFParser.from_file(
            instance_path, dependency_scheme_class=MutableDependencyScheme
        )

        self.logger.info(
            f"Parsed {self.instance.num_vars} variables and {self.instance.num_clauses} clauses."
        )

        # Identify variable types
        self.x_vars: List[int] = sorted(self.instance.get_universal_vars())
        self.y_vars: List[int] = sorted(self.instance.get_existential_vars())
        all_vars = sorted(self.x_vars + self.y_vars)

        # 2. Initialize Components
        # The dependency scheme is now initialized within the Instance
        self.dep_scheme = self.instance.dependency_scheme

        self.sampler = UniformSampler(all_vars, self.instance.clauses)
        self.function_manager = FunctionManager()
        self.learner = ManthanGuesser()

        self.error_formula = error_formula_cls()

        self.fl_scheme = fl_scheme_cls(self.instance)
        self.repair_scheme = repair_scheme_cls(
            self.instance, self.dep_scheme, self.function_manager
        )

        self.candidates: Dict[int, CandidateFunction] = {}

    def solve(self):
        # Phase 1: Sampling
        self.logger.info(f"Generating {self.num_samples} samples...")
        samples = self.sampler.sample(self.num_samples)
        if len(samples) == 0:
            self.logger.warning("No samples generated (Matrix UNSAT).")
            print("s False")
            exit(0)

        # Phase 0: Preprocessing
        if self.preprocessors:
            self.logger.info("Running %d preprocessor(s)...", len(self.preprocessors))
            for preprocessor in self.preprocessors:
                preprocessor.run(
                    self.instance.clauses,
                    self.x_vars,
                    self.y_vars,
                    self.candidates,
                    self.function_manager,
                    samples=samples,
                )
            resolved = [v for v, f in self.candidates.items() if not f.repairable]
            if resolved:
                self.logger.info(
                    "Preprocessing resolved %d variables: %s", len(resolved), resolved
                )
                # Register dependencies of resolved candidates in the
                # dependency scheme so the repair loop knows about them.
                y_set = set(self.y_vars)
                if isinstance(self.dep_scheme, MutableDependencyScheme):
                    for v in resolved:
                        func = self.candidates[v]
                        used_vars = func.support & (set(self.x_vars) | y_set)
                        self.dep_scheme.update_dependencies(v, used_vars)

        self.logger.info("Learning initial candidates...")

        # Phase 2: Candidate Learning
        self.candidates = self.learner.guess_candidates(
            self.instance,
            samples,
            self.function_manager,
            self.dep_scheme,
            self.candidates,
        )

        # Phase 3: Verification Loop
        self.logger.info("Entering verification loop...")

        iteration = 0
        while iteration <= self.max_iterations:
            iteration += 1
            self.logger.info(f"--- Iteration {iteration} ---")

            # 1. Check
            is_sat, assignment, oracle_assignment = self.error_formula.check(
                self.instance.clauses, self.candidates, self.x_vars, self.y_vars
            )

            if not is_sat:
                self.logger.info("UNSAT! Skolem functions verified.")
                self.print_solution()
                return

            assert assignment is not None
            self.logger.info("SAT! Counter-example found.")

            # 2. Fault Localization
            self.logger.info("Localizing faults...")
            suspects = self.fl_scheme.localize(
                self.candidates, assignment, self.dep_scheme
            )
            if len(suspects) == 0:
                self.logger.warning("Valid Skolem functions but verification failed.")
                print("s False")
                return
            # Filter out non-repairable candidates (resolved by preprocessing)
            suspects = [
                s
                for s in suspects
                if s not in self.candidates or self.candidates[s].repairable
            ]

            # 3. Repair
            self.candidates = self.repair_scheme.repair(
                self.candidates, assignment, suspects
            )

        self.logger.warning("Max iterations reached. Stopping.")
        print("s UNKNOWN")
        return

    def print_solution(self):
        print("s TRUE")

        # Write Verilog
        # Write Certificates
        instance_name = self.instance_path.stem
        output_dir = self.instance_path.parent.parent / "outputs"
        # Assuming standard structure: root/instances/file.qdimacs -> root/outputs/
        if not output_dir.exists():
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)

        if "verilog" in self.cert_formats:
            output_path = output_dir / f"{instance_name}.v"
            write_verilog_skolem(output_path, self.instance, self.candidates)

        if "aiger" in self.cert_formats:
            output_path = output_dir / f"{instance_name}.aag"
            write_aiger_skolem(
                output_path, self.instance, self.candidates, include_result_output=False
            )

        if "aiger_caqe" in self.cert_formats:
            # Use specific suffix for CAQE compatibility version
            output_path = output_dir / f"{instance_name}.caqe.aag"
            write_aiger_skolem(
                output_path, self.instance, self.candidates, include_result_output=True
            )
