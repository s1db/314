from abc import ABC, abstractmethod
from typing import List, Dict
import os
import logging
from src.candidate_function import CandidateFunction, NodeType
from src.error_schemes.verilog_utils import VerilogGenerator
import tempfile
from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]

logger = logging.getLogger(__name__)


class ErrorFormula(ABC):
    """
    Abstract base class for constructing Error Formulas in Verilog.
    """

    def __init__(self):
        pass

    def generate_verification_file(
        self,
        formula_clauses: List[List[int]],
        candidates: Dict[int, CandidateFunction],
        x_vars: List[int],
        y_vars: List[int],
        file_path: str,
    ) -> None:
        """
        Generates the complete Verilog file to check for counter-examples.
        Steps:
        1. Generate 'FORMULA' module (Specification).
        2. Generate 'SKOLEM' module (Consistency Check).
        3. Generate 'MAIN' module (Wiring).
        4. Write to file.
        """

        # 1. Generate Specification Module (FORMULA)
        # Defines F(X, Y)
        # Inputs: X, Y
        spec_verilog = VerilogGenerator.clauses_to_verilog(
            formula_clauses, "FORMULA", x_vars, y_vars
        )

        # 2. Generate Candidate Module (SKOLEM)
        # Defines Y' <-> Psi(X)
        y_vars_set = set(y_vars)

        # Prepare for splitting to avoid huge lines
        aux_lines = []
        wire_counter = [0]
        conv_candidates = {}

        for y in y_vars:
            if y in candidates:
                conv_candidates[y] = self._candidate_to_verilog(
                    candidates[y], y_vars_set, aux_lines, wire_counter
                )
            else:
                conv_candidates[y] = "0"

        extra_body = "".join(aux_lines)

        skolem_verilog = VerilogGenerator.functions_to_verilog(
            conv_candidates, "SKOLEM", x_vars, y_vars, extra_body=extra_body
        )

        # 3. Generate MAIN Module
        main_verilog = self._generate_main_module(x_vars, y_vars)

        # 4. Write to file
        with open(file_path, "w") as f:
            f.write(spec_verilog)
            f.write("\n")
            f.write(skolem_verilog)
            f.write("\n")
            f.write(main_verilog)

    def check(
        self,
        formula_clauses: List[List[int]],
        candidates: Dict[int, CandidateFunction],
        x_vars: List[int],
        y_vars: List[int],
    ) -> tuple[bool, Dict[int, bool] | None]:
        """
        Checks if the candidates satisfy the specification.
        Returns:
            (True, assignment) if SAT (Error found).
            (False, None) if UNSAT (Verified).
        """

        # Create temporary file for Verilog
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False, mode="w") as tmp:
            tmp_path = tmp.name

        try:
            self.generate_verification_file(
                formula_clauses, candidates, x_vars, y_vars, tmp_path
            )

            abc = AbcInterface()
            # check_sat returns None if UNSAT, bits list if SAT
            # NOW returns Dict[str, bool] if SAT
            result_map = abc.check_sat(tmp_path)

            if result_map is None:
                return (False, None)

            # Map assignments based on names
            # Names in Verilog:
            # X vars: v{x}
            # Y vars (oracle): v{y}
            # Y' vars (candidate): ip{y}

            assignment = {}

            # 1. X vars
            for x in x_vars:
                name = f"v{x}"
                assert name in result_map, f"Missing assignment for X variable {name}"
                assignment[x] = bool(result_map[name])

            # 2. Y vars (Oracles) - Not needed for repair currently
            for y in y_vars:
                name = f"v{y}"
                assert name in result_map, f"Missing assignment for Y variable {name}"

            # 3. Y' vars (Candidate outputs) - These override Y in the main assignment for repair
            for y in y_vars:
                name = f"ip{y}"
                assert name in result_map, f"Missing assignment for Y' variable {name}"
                assignment[y] = bool(result_map[name])

            return (True, assignment)
        except RuntimeError as e:
            logger.error(f"Could not verify formula. Error: {e}")
            raise e

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @abstractmethod
    def _generate_main_module(self, x_vars: List[int], y_vars: List[int]) -> str:
        """
        Abstract method to generate the top-level MAIN wiring.
        Must be implemented by subclasses (BFnS, QBF, etc).
        """
        pass

    def _candidate_to_verilog(
        self,
        func: CandidateFunction,
        y_vars_set: set,
        aux_lines: List[str],
        wire_counter: List[int],
    ) -> str:
        """
        Recursively converts a CandidateFunction to a Verilog expression string.
        Splits complex expressions into auxiliary wires to prevent line length issues.
        """
        if func.node_type == NodeType.LITERAL:
            assert func.value is not None
            val = abs(func.value)
            prefix = "ip" if val in y_vars_set else "v"
            return f"{prefix}{val}" if func.value > 0 else f"~{prefix}{val}"

        elif func.node_type == NodeType.CONSTANT:
            return "1" if func.value == 1 else "0"

        # Complex nodes: AND, OR, ITE
        # 1. Recurse
        children_wires = []
        if func.children:
            for c in func.children:
                children_wires.append(
                    self._candidate_to_verilog(c, y_vars_set, aux_lines, wire_counter)
                )

        # 2. Construct expression
        expr = ""
        if func.node_type == NodeType.AND:
            if not children_wires:
                return "1"
            expr = f"({' & '.join(children_wires)})"
        elif func.node_type == NodeType.OR:
            if not children_wires:
                return "0"
            expr = f"({' | '.join(children_wires)})"
        elif func.node_type == NodeType.ITE:
            c, t, e = children_wires
            expr = f"( ({c} & {t}) | (~{c} & {e}) )"

        # 3. Create auxiliary wire
        wire_name = f"split_{wire_counter[0]}"
        wire_counter[0] += 1

        assign_stmt = f"  wire {wire_name};\n  assign {wire_name} = {expr};\n"
        aux_lines.append(assign_stmt)

        return wire_name
