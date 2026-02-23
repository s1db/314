from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import os
from src.candidate_function import CandidateFunction, NodeType
from src.error_schemes.verilog_utils import VerilogGenerator


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
        self._verilog_memo: Dict[CandidateFunction, str] = {}
        self._verilog_defs: List[str] = []
        self._wire_counter: int = 0

        # Optimization: Pass 1 - Count node occurrences to identify shared sub-expressions
        self._node_counts: Dict[CandidateFunction, int] = {}

        def count_nodes(func: CandidateFunction):
            if func in self._node_counts:
                self._node_counts[func] += 1
                return
            self._node_counts[func] = 1
            for child in func.children:
                count_nodes(child)

        for cand in candidates.values():
            count_nodes(cand)

        y_vars_set = set(y_vars)
        conv_candidates = {
            y: self._candidate_to_verilog(candidates[y], y_vars_set)
            for y in y_vars
            if y in candidates
        }
        # Ensure all y_vars are present, default to 0 if not
        skolem_verilog = VerilogGenerator.functions_to_verilog(
            conv_candidates, "SKOLEM", x_vars, y_vars, extra_defs=self._verilog_defs
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
    ) -> tuple[bool, Optional[Dict[int, bool]], Optional[Dict[int, bool]]]:
        """
        Checks if the candidates satisfy the specification.
        Returns:
            (True, assignment, oracle_assignment) if SAT (Error found).
            (False, None, None) if UNSAT (Verified).
        """
        import tempfile
        from src.bindings.abc_wrapper import AbcInterface  # type: ignore

        # Create temporary file for Verilog
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False, mode="w") as tmp:
            tmp_path = tmp.name

        try:
            self.generate_verification_file(
                formula_clauses, candidates, x_vars, y_vars, tmp_path
            )

            abc = AbcInterface()
            # check_sat returns None if UNSAT, bits list if SAT
            result_bits = abc.check_sat(tmp_path)

            if result_bits is None:
                return (False, None, None)

            # Map bits to variables
            # Order in verilog_utils.py: X variables then Y variables (then Y' but CEX usually covers PIs)
            # The PIs of MAIN module are: vX..., vY..., ipY...
            # vX are inputs (size len(x_vars))
            # vY are inputs (size len(y_vars))
            # ipY are inputs (size len(y_vars))

            # Current ABC wrapper returns raw bits from CEX.
            # We need to map them.
            # Assuming the order matches the port definition sequence.

            assignment = {}
            bit_idx = 0

            # 1. X vars
            for x in x_vars:
                if bit_idx < len(result_bits):
                    assignment[x] = bool(result_bits[bit_idx])
                    bit_idx += 1

            # 2. Y vars (Oracles) - Capture these for repair context
            oracle_assignment = {}
            for y in y_vars:
                if bit_idx < len(result_bits):
                    oracle_assignment[y] = bool(result_bits[bit_idx])
                    bit_idx += 1

            # 3. Y' vars (Candidate outputs) - These are the actual values produced by candidates
            for y in y_vars:
                if bit_idx < len(result_bits):
                    assignment[y] = bool(result_bits[bit_idx])
                    bit_idx += 1

            return (True, assignment, oracle_assignment)

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

    def _candidate_to_verilog(self, func: CandidateFunction, y_vars_set: set) -> str:
        """
        Pass 2: Converts a CandidateFunction to a Verilog expression string.
        Shared nodes (occurrence > 1) are assigned to wires.
        """
        # Initialization check for direct calls (not through generate_verification_file)
        if not hasattr(self, "_verilog_memo"):
            self._verilog_memo = {}
        if not hasattr(self, "_verilog_defs"):
            self._verilog_defs = []
        if not hasattr(self, "_wire_counter"):
            self._wire_counter = 0
        if not hasattr(self, "_node_counts"):
            self._node_counts = {}

        # Check memoization
        if func in self._verilog_memo:
            return self._verilog_memo[func]

        if func.node_type == NodeType.LITERAL:
            assert func.value is not None
            val = abs(func.value)
            prefix = "ip" if val in y_vars_set else "v"
            res = f"{prefix}{val}" if func.value > 0 else f"~{prefix}{val}"
            # Literals don't need their own wires, return directly
            return res

        if func.node_type == NodeType.CONSTANT:
            return "1'b1" if func.value == 1 else "1'b0"

        # Structural generation
        if func.node_type == NodeType.AND:
            if not func.children:
                expr = "1'b1"
            else:
                children_str = [
                    self._candidate_to_verilog(c, y_vars_set) for c in func.children
                ]
                expr = f"({' & '.join(children_str)})"

        elif func.node_type == NodeType.OR:
            if not func.children:
                expr = "1'b0"
            else:
                children_str = [
                    self._candidate_to_verilog(c, y_vars_set) for c in func.children
                ]
                expr = f"({' | '.join(children_str)})"

        elif func.node_type == NodeType.ITE:
            c = self._candidate_to_verilog(func.children[0], y_vars_set)
            t = self._candidate_to_verilog(func.children[1], y_vars_set)
            e = self._candidate_to_verilog(func.children[2], y_vars_set)
            expr = f"({c} ? {t} : {e})"
        else:
            expr = "1'b0"

        # Emit wire ONLY if shared (occurrence > 1)
        if self._node_counts.get(func, 0) > 1:
            self._wire_counter += 1
            wire_name = f"ga_{self._wire_counter}"
            self._verilog_defs.append(f"wire {wire_name};")
            self._verilog_defs.append(f"assign {wire_name} = {expr};")
            self._verilog_memo[func] = wire_name
            return wire_name

        return expr
