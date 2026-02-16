from typing import List, Dict, Union

class VerilogGenerator:
    """
    Helper class to generate strict Verilog 1995 code for ABC compatibility.
    Implements batching logic to prevent parser stack overflows.
    """

    @staticmethod
    def clauses_to_verilog(clauses: List[List[int]], module_name: str, x_vars: List[int], y_vars: List[int]) -> str:
        """
        Converts a list of CNF clauses to a Verilog module.
        Implements the 100-clause batching rule.
        """
        all_vars = sorted(list(set(x_vars + y_vars)))
        input_ports = [f"v{v}" for v in all_vars]
        
        verilog = f"module {module_name} ( {', '.join(input_ports)}, out );\n"
        for v in all_vars:
            verilog += f"  input v{v};\n"
        verilog += "  output out;\n\n"

        # Clause wires
        tcount_wires = []
        current_batch = []
        clause_idx = 0
        batch_idx = 0

        for clause in clauses:
            clause_idx += 1
            # Generate clause logic: (~v1 | v2 | v3)
            literals = []
            for lit in clause:
                var = abs(lit)
                if lit > 0:
                    literals.append(f"v{var}")
                else:
                    literals.append(f"~v{var}")
            
            # If empty clause, it's False (0)
            rhs = " | ".join(literals) if literals else "0"
            
            wire_name = f"t_{clause_idx}"
            verilog += f"  wire {wire_name};\n"
            verilog += f"  assign {wire_name} = {rhs};\n"
            current_batch.append(wire_name)

            # Batching rule: 100 clauses
            if len(current_batch) >= 100:
                batch_wire = f"tcount_{batch_idx}"
                verilog += f"  wire {batch_wire};\n"
                # Join with &
                verilog += f"  assign {batch_wire} = {' & '.join(current_batch)};\n"
                tcount_wires.append(batch_wire)
                current_batch = []
                batch_idx += 1

        # Process remaining batch
        if current_batch:
            batch_wire = f"tcount_{batch_idx}"
            verilog += f"  wire {batch_wire};\n"
            verilog += f"  assign {batch_wire} = {' & '.join(current_batch)};\n"
            tcount_wires.append(batch_wire)

        # Final assignment
        if not tcount_wires:
             # No clauses -> True
             verilog += "  assign out = 1;\n"
        else:
            verilog += f"  assign out = {' & '.join(tcount_wires)};\n"

        verilog += "endmodule\n"
        return verilog

    @staticmethod
    def functions_to_verilog(functions: Dict[int, str], module_name: str, x_vars: List[int], y_vars: List[int]) -> str:
        """
        Converts candidate functions to a Verilog checking module.
        Checks: Y' <-> Psi(X)
        Functions dict: { y_var_int: "verilog_expression_string" }
        Implements 10-variable batching rule for the final AND.
        """
        # Inputs: X variables (inputs to functions) AND Y' variables (to check against)
        # Note: Y' variables in the port list should be named differently to avoid clash if we were using same namespace,
        # but here we use positional mapping so we can just name them "ip<var>" inside this module.
        
        # We need a defined order for ports. 
        # For simplicity, we assume the caller handles the external wiring.
        # Here we define inputs as: [X_vars..., Y_vars...] 
        # Internally X vars keep their names (as strings of ints), Y vars are "ip<y>"
        
        input_ports = [f"v{x}" for x in x_vars] + [f"ip{y}" for y in y_vars]
        
        verilog = f"module {module_name} ( {', '.join(input_ports)}, out );\n"
        for x in x_vars:
            verilog += f"  input v{x};\n"
        for y in y_vars:
            verilog += f"  input ip{y};\n"
        verilog += "  output out;\n\n"

        wt_wires = []
        current_batch = []
        batch_idx = 0
        
        # Ensure deterministic order
        for i, y in enumerate(y_vars):
            expr = functions.get(y, "0") # Default to 0 if missing? Or should error.
            
            # Predict wire
            w_wire = f"w{y}"
            verilog += f"  wire {w_wire};\n"
            verilog += f"  assign {w_wire} = {expr};\n"
            
            # Equality check wire: ~(w ^ ip)
            eq_wire = f"eq_{y}"
            verilog += f"  wire {eq_wire};\n"
            verilog += f"  assign {eq_wire} = ~({w_wire} ^ ip{y});\n"
            current_batch.append(eq_wire)
            
            # Batching rule: 10 variables
            if len(current_batch) >= 10:
                batch_wire = f"wt_{batch_idx}"
                verilog += f"  wire {batch_wire};\n"
                verilog += f"  assign {batch_wire} = {' & '.join(current_batch)};\n"
                wt_wires.append(batch_wire)
                current_batch = []
                batch_idx += 1
                
        # Remaining
        if current_batch:
            batch_wire = f"wt_{batch_idx}"
            verilog += f"  wire {batch_wire};\n"
            verilog += f"  assign {batch_wire} = {' & '.join(current_batch)};\n"
            wt_wires.append(batch_wire)
            
        # Final output
        if not wt_wires:
            verilog += "  assign out = 1;\n"
        else:
            verilog += f"  assign out = {' & '.join(wt_wires)};\n"
            
        verilog += "endmodule\n"
        return verilog

    @staticmethod
    def instantiate_module(module_name: str, instance_name: str, ports: Union[List[str], Dict[str, str]]) -> str:
        """
        Generates a module instantiation.
        If ports is a list, generates positional: module inst ( p1, p2 );
        If ports is a dict, generates named: module inst ( .p1(w1), .p2(w2) );
        """
        if isinstance(ports, dict):
             connections = [f".{formal}({actual})" for formal, actual in ports.items()]
             return f"  {module_name} {instance_name} ( {', '.join(connections)} );\n"
        else:
             return f"  {module_name} {instance_name} ( {', '.join(ports)} );\n"
