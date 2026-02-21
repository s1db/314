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
    ) -> tuple[bool, dict | None]:

        # 1. Check for Counter-Example (Exists X. ~F(X, Psi(X)))
        with tempfile.NamedTemporaryFile(suffix=".v", delete=False, mode="w") as tmp:
            tmp_path_check = tmp.name

        try:
            self.generate_verification_file(
                formula_clauses, candidates, x_vars, y_vars, tmp_path_check
            )

            abc = AbcInterface()
            # check_sat returns None if UNSAT, dict if SAT
            result_map = abc.check_sat(tmp_path_check)

            if result_map is None:
                return (False, None)

            # Parse X assignment from result_map
            # We want v{x} and ip{y} (candidate outputs used as Y)
            assignment = {}

            # 1. X vars
            for x in x_vars:
                name = f"v{x}"
                assert name in result_map, f"Missing assignment for X variable {name}"
                assignment[x] = bool(result_map[name])

            # 2. Y' vars (Candidate outputs)
            for y in y_vars:
                name = f"ip{y}"
                assert name in result_map, f"Missing assignment for Y' variable {name}"
                assignment[y] = bool(result_map[name])

            # Note: Oracle Y generation is removed as per user request.

            return (True, assignment)

        except RuntimeError as e:
            # Re-raise to be handled by solver or for debugging
            raise e

        finally:
            if os.path.exists(tmp_path_check):
                os.remove(tmp_path_check)

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
