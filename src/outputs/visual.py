from typing import Dict, List, Set
from pathlib import Path
from src.candidate_function import CandidateFunction, NodeType
import sys

# Increase recursion depth just in case for deep trees
sys.setrecursionlimit(20000)


def detect_loops_in_candidates(
    candidates: Dict[int, CandidateFunction],
) -> List[List[int]]:
    """
    Detects loops in the dependency graph of candidate functions.
    Returns a list of loops, where each loop is a list of variable IDs (integers).
    """
    # Build adjacency list: var_id -> set of dependency var_ids (only outputs)
    adj: Dict[int, Set[int]] = {}
    output_vars = set(candidates.keys())

    # Build the dependency graph
    for var, func in candidates.items():
        deps = set()
        stack = [func]
        visited_nodes = set()

        while stack:
            node = stack.pop()
            if id(node) in visited_nodes:
                continue
            visited_nodes.add(id(node))

            if node.node_type == NodeType.LITERAL:
                if node.value is not None:
                    lit = abs(node.value)
                    if lit in output_vars:
                        deps.add(lit)

            # Recurse on children
            for child in node.children:
                stack.append(child)

        adj[var] = deps

    # DFS for Cycle Detection
    visited = set()
    recursion_stack = set()
    # To store found cycles as lists of nodes
    cycles = []

    # Pre-check: if a node is fully processed (black), don't revisit.
    # Gray nodes are in recursion_stack.

    def dfs(u, path):
        visited.add(u)
        recursion_stack.add(u)
        path.append(u)

        if u in adj:
            for v in adj[u]:
                if v not in visited:
                    dfs(v, path)
                elif v in recursion_stack:
                    # Cycle detected!
                    # Extract cycle from path based on v's index
                    try:
                        idx = path.index(v)
                        cycle = path[idx:]
                        cycles.append(list(cycle))
                    except ValueError:
                        pass

        recursion_stack.remove(u)
        path.pop()

    for v in output_vars:
        if v not in visited:
            dfs(v, [])

    return cycles


def generate_dot(candidates: Dict[int, CandidateFunction], output_path: Path) -> None:
    """
    Generates a Graphviz DOT file for the candidate functions showing dependencies between output variables.
    Highlights loops in red.
    """
    loops = detect_loops_in_candidates(candidates)
    loop_nodes = set()
    for cycle in loops:
        loop_nodes.update(cycle)

    lines = []
    lines.append("digraph Skolem {")
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=circle];")

    output_vars = set(candidates.keys())

    # 1. Define Nodes
    # Inputs don't have explicit candidate functions but appear as dependencies.
    # We'll identify all inputs encountered during traversal.
    all_inputs = set()

    # Pre-calculate dependencies for edges and find inputs
    adj: Dict[int, Set[str]] = {}  # var -> set of dependency strings (iX or oY)

    for var, func in candidates.items():
        # Node attributes
        color = "red" if var in loop_nodes else "black"
        label = f"o{var}"
        lines.append(f'  "{label}" [label="{label}", color={color}];')

        deps = set()
        stack = [func]
        visited_nodes = set()

        while stack:
            node = stack.pop()
            if id(node) in visited_nodes:
                continue
            visited_nodes.add(id(node))

            if node.node_type == NodeType.LITERAL:
                if node.value is not None:
                    lit = abs(node.value)
                    if lit in output_vars:
                        deps.add(f"o{lit}")
                    else:
                        deps.add(f"i{lit}")
                        all_inputs.add(lit)
            for child in node.children:
                stack.append(child)

        adj[var] = deps

    # Define Input Nodes (box shape for distinction)
    lines.append("  node [shape=box];")
    for inp in sorted(list(all_inputs)):
        lines.append(f'  "i{inp}" [label="i{inp}"];')

    # 2. Define Edges
    # Edge semantic: if A depends on B, draw B -> A (Data Flow)
    for var, deps in adj.items():
        target = f"o{var}"
        for source in deps:
            # Check if edge is part of a loop
            is_loop_edge = False
            # Source must be an output variable to be part of a loop
            if source.startswith("o"):
                src_id = int(source[1:])
                if var in loop_nodes and src_id in loop_nodes:
                    # Rough heuristic: if both in loops, highlight edge.
                    # Ideally check if edge is part of a specific SCC, but this is fine for viz.
                    is_loop_edge = True

            color = "red" if is_loop_edge else "black"
            lines.append(f'  "{source}" -> "{target}" [color={color}];')

    lines.append("}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
