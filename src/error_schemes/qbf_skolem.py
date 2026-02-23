import tempfile
import os
from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]
from src.error_schemes.base import ErrorFormula
from src.error_schemes.verilog_utils import VerilogGenerator
from typing import List


class QBFSkolemErrorFormula(ErrorFormula):
    """
    Implements the QBF Skolem Error Formula:
    E(X, Y') = (Y' <-> Psi(X)) /\ ~F(X, Y')

    This checks if there exists an X such that when Y' is computed from X using the candidate functions Psi,
    F(X, Y') is FALSE. If such an X exists (SAT), it is a counter-example.
    If UNSAT, then ForAll X, F(X, Psi(X)) holds, meaning the Skolem functions are valid.
    """

    def _generate_main_module(self, x_vars: List[int], y_vars: List[int]) -> str:
        # Inputs: X (vX), Y' (ipY)
        # Note: In this verification model, the "Y" variables of the original formula
        # are replaced by the outputs of the Skolem functions (Y').
        # The Skolem functions take X as input and produce Y'.

        all_inputs = [f"v{x}" for x in x_vars] + [f"ip{y}" for y in y_vars]

        verilog = f"module MAIN ( {', '.join(all_inputs)}, out );\n"
        for inp in all_inputs:
            verilog += f"  input {inp};\n"

        verilog += "  output out;\n\n"
        verilog += "  wire out_skolem;\n"
        verilog += "  wire out_formula;\n\n"

        # 1. Candidates CHECK (Y' <-> Psi(X)) -> out_skolem
        # SKOLEM ports: vX..., ipY..., out
        skolem_map = {}
        for x in x_vars:
            skolem_map[f"v{x}"] = f"v{x}"
        for y in y_vars:
            skolem_map[f"ip{y}"] = f"ip{y}"
        skolem_map["out"] = "out_skolem"

        verilog += VerilogGenerator.instantiate_module("SKOLEM", "S1", skolem_map)

        # 2. Check F(X, Y') -> out_formula
        # FORMULA ports: vX..., vY..., out
        # Here we map formal vY to actual ipY (Y')
        formula_map = {}
        for x in x_vars:
            formula_map[f"v{x}"] = f"v{x}"
        for y in y_vars:
            # Connect formal port v{y} to actual wire ip{y}
            formula_map[f"v{y}"] = f"ip{y}"
        formula_map["out"] = "out_formula"

        verilog += VerilogGenerator.instantiate_module("FORMULA", "F1", formula_map)

        # Final Logic: out = out_skolem & ~out_formula
        # We look for a case where Psi(X) matches Y' (valid computation) AND F(X, Y') is False.
        verilog += "  assign out = out_skolem & ~out_formula;\n"
        verilog += "endmodule\n"

        return verilog

    def check(
        self,
        formula_clauses: List[List[int]],
        candidates: dict,
        x_vars: List[int],
        y_vars: List[int],
    ) -> tuple:

        # 1. Check for Counter-Example (Exists X. ~F(X, Psi(X)))
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False, mode="w") as tmp:
            tmp_path_check = tmp.name

        try:
            self.generate_verification_file(
                formula_clauses, candidates, x_vars, y_vars, tmp_path_check
            )

            abc = AbcInterface()
            result_bits = abc.check_sat(tmp_path_check)

            if result_bits is None:
                return (False, None, None)

            # Parse X assignment from result_bits
            # Order: vX... then ipY...
            # We only care about X here to find the counter-example content.
            assignment = {}
            bit_idx = 0
            for x in x_vars:
                if bit_idx < len(result_bits):
                    assignment[x] = bool(result_bits[bit_idx])
                    bit_idx += 1

            # Also capture Y' (candidate outputs) for debugging/FL
            for y in y_vars:
                if bit_idx < len(result_bits):
                    assignment[y] = bool(result_bits[bit_idx])
                    bit_idx += 1

            # 2. Compute Oracle Y for this X (Solve F(fixed_X, Y))
            # We need a valid Y assignment for FL to compare against.

            # Create a temporary Verilog file for Oracle Helper
            with tempfile.NamedTemporaryFile(
                suffix=".v", delete=False, mode="w"
            ) as tmp_oracle:
                tmp_path_oracle = tmp_oracle.name

            # Generate Oracle Module: Fix X inputs, solve for Y
            oracle_verilog = self._generate_oracle_module(
                formula_clauses, x_vars, y_vars, assignment
            )
            with open(tmp_path_oracle, "w") as f:
                f.write(oracle_verilog)

            oracle_bits = abc.check_sat(tmp_path_oracle)

            oracle_assignment = {}
            if oracle_bits is None:
                # Should not happen for True QBF (forall X exists Y)
                # But if it does, it means F(X, .) is UNSAT, so no valid Y exists.
                # FL might fail, but we can't provide one.
                pass
            else:
                # Parse Y from oracle_bits
                # Order in _generate_oracle_module is just Y variables
                y_idx = 0
                for y in y_vars:
                    if y_idx < len(oracle_bits):
                        oracle_assignment[y] = bool(oracle_bits[y_idx])
                        y_idx += 1

            if os.path.exists(tmp_path_oracle):
                os.remove(tmp_path_oracle)

            return (True, assignment, oracle_assignment)

        finally:
            if os.path.exists(tmp_path_check):
                os.remove(tmp_path_check)

    def _generate_oracle_module(
        self,
        clauses: List[List[int]],
        x_vars: List[int],
        y_vars: List[int],
        assignment: dict,
    ) -> str:
        # Generate FORMULA module but wrap it to fix X inputs
        # Use existing clauses_to_verilog for the core spec

        core_module = VerilogGenerator.clauses_to_verilog(
            clauses, "FORMULA", x_vars, y_vars
        )

        # Wrapper module
        # Inputs: vY... (we want to find these)
        # Output: out

        y_inputs = [f"v{y}" for y in y_vars]
        verilog = f"{core_module}\n"
        verilog += f"module ORACLE ( {', '.join(y_inputs)}, out );\n"
        for yi in y_inputs:
            verilog += f"  input {yi};\n"
        verilog += "  output out;\n\n"

        # Instantiate FORMULA
        # Fix X ports to constants from assignment

        wires_map = {}
        for x in x_vars:
            # Wire v{x} to 1'b1 or 1'b0
            val = assignment.get(x, False)
            bit = "1'b1" if val else "1'b0"
            wires_map[f"v{x}"] = bit

        for y in y_vars:
            wires_map[f"v{y}"] = f"v{y}"

        wires_map["out"] = "out"

        verilog += VerilogGenerator.instantiate_module("FORMULA", "F_ORACLE", wires_map)
        verilog += "endmodule\n"

        return verilog
