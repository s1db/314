from src.error_schemes.base import ErrorFormula
from src.error_schemes.verilog_utils import VerilogGenerator
from typing import List

class BFnSErrorFormula(ErrorFormula):
    """
    Implements the BFnS Error Formula:
    E(X, Y, Y') = F(X, Y) /\ (Y' <-> Psi(X)) /\ ~F(X, Y')
    """

    def _generate_main_module(self, x_vars: List[int], y_vars: List[int]) -> str:
        # Inputs: X, Y, Y' (named ipY in VerilogGenerator)
        # But MAIN module inputs need to be explicitly declared.
        # We need 3 sets of input ports:
        # 1. X variables (shared)
        # 2. Y variables (for F(X,Y))
        # 3. Y' variables (for F(X,Y') and SKOLEM check)
        
        # NOTE: VerilogGenerator.clauses_to_verilog uses input names "v" for v in x_vars+y_vars.
        # VerilogGenerator.functions_to_verilog uses "v" for x and "ipv" for y.
        
        # We need to map the ports correctly.
        # Main module inputs:
        # X: [x1, x2...]
        # Y: [y1, y2...] (Oracles/Original)
        # Y': [ip1, ip2...] (Candidate outputs)
        
        all_inputs = [f"v{x}" for x in x_vars] + [f"v{y}" for y in y_vars] + [f"ip{y}" for y in y_vars]
        
        verilog = f"module MAIN ( {', '.join(all_inputs)}, out );\n"
        for inp in all_inputs:
            verilog += f"  input {inp};\n"
        
        verilog += "  output out;\n\n"
        verilog += "  wire out1;\n"
        verilog += "  wire out2;\n"
        verilog += "  wire out3;\n\n"

        # 1. Spec F(X, Y) -> out1
        # FORMULA ports: vX..., vY..., out
        spec1_map = {}
        for x in x_vars:
            spec1_map[f"v{x}"] = f"v{x}"
        for y in y_vars:
            spec1_map[f"v{y}"] = f"v{y}"
        spec1_map["out"] = "out1"
        
        verilog += VerilogGenerator.instantiate_module("FORMULA", "F1", spec1_map)

        # 2. Candidates CHECK (Y' <-> Psi(X)) -> out2
        # SKOLEM ports: vX..., ipY..., out
        skolem_map = {}
        for x in x_vars:
            skolem_map[f"v{x}"] = f"v{x}"
        for y in y_vars:
            skolem_map[f"ip{y}"] = f"ip{y}"
        skolem_map["out"] = "out2"
        
        verilog += VerilogGenerator.instantiate_module("SKOLEM", "S1", skolem_map)

        # 3. Check Failure F(X, Y') -> out3
        # FORMULA ports: vX..., vY..., out
        # Here we map formal vY to actual ipY (Y')
        spec2_map = {}
        for x in x_vars:
            spec2_map[f"v{x}"] = f"v{x}"
        for y in y_vars:
            # Connect formal port v{y} to actual wire ip{y}
            spec2_map[f"v{y}"] = f"ip{y}"
        spec2_map["out"] = "out3"
        
        verilog += VerilogGenerator.instantiate_module("FORMULA", "F2", spec2_map)

        # Final Logic: out1 & out2 & ~out3
        verilog += "  assign out = out1 & out2 & ~out3;\n"
        verilog += "endmodule\n"
        
        return verilog
