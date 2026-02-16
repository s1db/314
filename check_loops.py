import re
import sys
import os
from pathlib import Path
from typing import Dict, Set, List, Tuple


def parse_verilog_dependencies(
    file_path: str,
) -> Tuple[Dict[str, Set[str]], Set[str], Set[str]]:
    """
    Parses a structural Verilog file to build a dependency graph.
    Returns:
        adj: Dict[wire_name, Set[dependency_wire_names]]
        inputs: Set[wire_names]
        outputs: Set[wire_names]
    """
    adj = {}
    inputs = set()
    outputs = set()

    # Regex for module declaration (ports) - roughly
    # regex for input/output declarations
    # regex for assignments: assign <target> = <expr>;

    # We assume standard format produced by verilog_skolem.py:
    # input i1, i2...;
    # output o1, o2...;
    # wire w_0;
    # assign w_0 = ...;
    # assign o1 = w_0;

    with open(file_path, "r") as f:
        content = f.read()

    # 1. Inputs/Outputs
    # Simple parsing: look for "input" and "output" keywords and split by comma
    # Remove comments if any? (Not expected in our generated file)

    # Clean up newlines and semi-colons for easier regex
    # But be careful not to merge unrelated lines.
    # Let's iterate line by line.

    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("//") or not line:
            continue

        if line.startswith("input "):
            # input i87, i88;
            parts = line[6:].replace(";", "").split(",")
            for p in parts:
                inputs.add(p.strip())

        elif line.startswith("output "):
            parts = line[7:].replace(";", "").split(",")
            for p in parts:
                outputs.add(p.strip())

        elif line.startswith("assign "):
            # assign target = expr;
            # remove 'assign ' and ';'
            statement = line[7:].replace(";", "").strip()
            if "=" not in statement:
                continue

            target, expr = statement.split("=", 1)
            target = target.strip()
            expr = expr.strip()

            # Parse dependencies from expr
            # Extract all alphanumeric identifiers strings that are not keywords?
            # Our identifiers: i<num>, o<num>, w_<num>, 1'b0, 1'b1
            # Keywords to ignore: &, |, ~, ?, :

            # Simple tokenization: match [a-zA-Z0-9_]+
            tokens = re.findall(r"[a-zA-Z0-9_]+", expr)

            deps = set()
            for token in tokens:
                if token.startswith("1'b"):
                    continue  # constant
                deps.add(token)

            if target not in adj:
                adj[target] = set()
            adj[target].update(deps)

    return adj, inputs, outputs


def find_cycles(adj: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Finds cycles in the graph.
    """
    visited = set()
    recursion_stack = set()
    cycles = []

    def dfs(u, path):
        visited.add(u)
        recursion_stack.add(u)
        path.append(u)

        if u in adj:
            for v in adj[u]:
                if v not in visited:
                    dfs(v, path)
                elif v in recursion_stack:
                    # Cycle
                    try:
                        idx = path.index(v)
                        cycles.append(list(path[idx:]))
                    except ValueError:
                        pass

        recursion_stack.remove(u)
        path.pop()

    # Iterate over all nodes, but prioritize outputs as roots?
    # Actually, wire definitions might be roots of sub-islands?
    # Just iterate all known keys in adj.
    nodes = list(adj.keys())
    for n in nodes:
        if n not in visited:
            dfs(n, [])

    return cycles


def generate_dot(
    adj: Dict[str, Set[str]],
    inputs: Set[str],
    outputs: Set[str],
    cycles: List[List[str]],
    output_path: str,
):
    """
    Generates DOT file.
    """
    lines = []
    lines.append("digraph Verilog {")
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=circle];")

    # Identify loop nodes
    loop_nodes = set()
    for c in cycles:
        loop_nodes.update(c)

    # Nodes
    all_nodes = set(adj.keys())
    for deps in adj.values():
        all_nodes.update(deps)

    for n in all_nodes:
        attrs = []
        if n in inputs:
            attrs.append("shape=box")
            attrs.append('label="' + n + '"')
        elif n in outputs:
            attrs.append("shape=doublecircle")
            attrs.append('label="' + n + '"')
        else:
            # intermediate wires
            attrs.append('label="' + n + '"')
            attrs.append("style=filled")
            attrs.append("color=lightgrey")

        if n in loop_nodes:
            attrs.append("color=red")
            attrs.append("fontcolor=red")

        lines.append(f'  "{n}" [{", ".join(attrs)}];')

    # Edges
    # In adj: target -> deps means target USES deps.
    # Flow: deps -> target.
    for target, deps in adj.items():
        for source in deps:
            color = "black"
            if target in loop_nodes and source in loop_nodes:
                color = "red"
            lines.append(f'  "{source}" -> "{target}" [color={color}];')

    lines.append("}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 check_loops.py <verilog_file> [output_dot_file]")
        sys.exit(1)

    verilog_file = sys.argv[1]
    dot_file = sys.argv[2] if len(sys.argv) > 2 else verilog_file + ".dot"

    print(f"Parsing {verilog_file}...")
    adj, inputs, outputs = parse_verilog_dependencies(verilog_file)

    print(
        f"Found {len(inputs)} inputs, {len(outputs)} outputs, {len(adj)} declarations."
    )

    print("Checking for cycles...")
    cycles = find_cycles(adj)

    if cycles:
        print(f"❌ Found {len(cycles)} cycles!")
        for i, c in enumerate(cycles[:5]):
            print(f"  Cycle {i + 1}: {' -> '.join(c)}")
        if len(cycles) > 5:
            print(f"  ... and {len(cycles) - 5} more.")
    else:
        print("✅ No execution loops found (assuming combinatorial logic).")

    print(f"Generating visualization to {dot_file}...")
    generate_dot(adj, inputs, outputs, cycles, dot_file)
    print("Done.")


if __name__ == "__main__":
    main()
