import logging
from typing import Dict, List
from pathlib import Path
from src.instance import Instance
from src.candidate_function import CandidateFunction, NodeType

logger = logging.getLogger(__name__)


def write_verilog_skolem(
    path: Path, instance: Instance, candidates: Dict[int, CandidateFunction]
):
    """
    Writes the Skolem functions to a Structural Verilog file.

    Adheres to the format expected by checkers/manthan/checkSkolem.py:
    1. Ports are named using raw variable IDs (e.g., "1", "2").
    2. Input ports (Universals) appear first, in the order they appear in the QDIMACS file.
    3. Output ports (Existentials) appear next, in the order they appear in the QDIMACS file.
    """

    inputs: List[int] = instance.get_universal_vars()
    outputs: List[int] = instance.get_existential_vars()

    lines = []

    module_name = "SkolemFormula"
    ports = [str(i) for i in inputs] + [str(o) for o in outputs]

    lines.append(f"module {module_name} (")
    lines.append("  " + ", ".join(ports))
    lines.append(");")
    lines.append("")

    # Declarations
    # input 1; output 2;
    if inputs:
        lines.append("  input " + ", ".join(str(i) for i in inputs) + ";")
    if outputs:
        lines.append("  output " + ", ".join(str(o) for o in outputs) + ";")
    lines.append("")

    # Wires for intermediate nodes
    node_to_wire: Dict[int, str] = {}  # id(node) -> wire_name
    wire_definitions: list[str] = []
    assignments: list[str] = []
    wire_counter = 0

    # We need to map variable IDs to their string representation for use in expressions.
    # simple str(var)

    def get_expr(node: CandidateFunction) -> str:
        nonlocal wire_counter
        node_id = id(node)
        if node_id in node_to_wire:
            return node_to_wire[node_id]

        if node.node_type == NodeType.CONSTANT:
            # 1'b1 or 1'b0
            return "1'b1" if node.value == 1 else "1'b0"

        if node.node_type == NodeType.LITERAL:
            assert node.value is not None
            var = abs(node.value)
            var_str = str(var)

            # If negated
            if node.value < 0:
                return f"~{var_str}"
            return var_str

        # For operations, create a wire
        wire_name = f"w_{wire_counter}"
        wire_counter += 1
        node_to_wire[node_id] = wire_name
        wire_definitions.append(f"  wire {wire_name};")

        if node.node_type == NodeType.AND:
            children_exprs = [get_expr(child) for child in node.children]
            expr = " & ".join(children_exprs)
            assignments.append(f"  assign {wire_name} = {expr};")

        elif node.node_type == NodeType.OR:
            children_exprs = [get_expr(child) for child in node.children]
            expr = " | ".join(children_exprs)
            assignments.append(f"  assign {wire_name} = {expr};")

        elif node.node_type == NodeType.ITE:
            cond = get_expr(node.children[0])
            true_br = get_expr(node.children[1])
            false_br = get_expr(node.children[2])
            expr = f"{cond} ? {true_br} : {false_br}"
            assignments.append(f"  assign {wire_name} = {expr};")

        return wire_name

    # Generate logic for each output
    output_assignments = []

    # We assume 'candidates' contains functions for the output variables.
    # Note: 'candidates' might not contain ALL outputs if some weren't learned/needed?
    # But for a valid Skolem certificate, they usually should be.
    # If a variable is not in candidates, we do nothing? Or assign 0?
    # Let's process those present in candidates.

    for var, func in candidates.items():
        if var not in outputs:
            # This is weird if we have a candidate for a variable not classified as existential in instance.
            # But let's trust the candidate key.
            continue

        root_expr = get_expr(func)
        output_assignments.append(f"  assign {var} = {root_expr};")

    # Write to file
    lines.extend(wire_definitions)
    lines.append("")
    lines.extend(assignments)
    lines.append("")
    lines.append("")
    lines.extend(output_assignments)
    lines.append("endmodule")

    with open(path, "w") as f:
        f.write("\n".join(lines))

    logger.info(f"Wrote VerilogSkolem functions to {path}")
