import argparse
import sys
from typing import Dict, Set

from src.instance_parsers.qbf import QBFParser
from src.dependency_schemes.trivial_inter_block import TrivialInterBlockDependencyScheme
from src.dependency_schemes.trivial import TrivialDependencyScheme
from src.dependency_schemes.standard import StandardDependencyScheme
from src.dependency_schemes.triangle import TriangleDependencyScheme
from src.dependency_schemes.unitri import UniTriDependencyScheme
from src.dependency_schemes.base import DependencyViolationError


def generate_dot(name: str, dependencies: Dict[int, Set[int]], output_path: str):
    """Generates a Graphviz DOT file for the dependency graph."""
    with open(output_path, "w") as f:
        # cleanup name for DOT ID
        clean_name = name.replace(" ", "_").replace("(", "").replace(")", "")
        f.write(f"digraph {clean_name} {{\n")
        f.write("    rankdir=BT;\n")
        f.write("    node [shape=circle];\n")

        # Sort for deterministic output
        all_vars = sorted(dependencies.keys())
        for u in all_vars:
            deps = sorted(list(dependencies[u]))
            for v in deps:
                f.write(f"    {u} -> {v};\n")

        f.write("}\n")


def print_dependencies(name: str, dependencies: Dict[int, Set[int]]):
    print(f"\n--- {name} ---")
    sorted_vars = sorted(dependencies.keys())
    for var in sorted_vars:
        deps = sorted(list(dependencies[var]))
        if deps:
            print(f"D({var}) = {{{', '.join(map(str, deps))}}}")
        else:
            print(f"D({var}) = {{}}")


def main():
    parser = argparse.ArgumentParser(
        description="Compute dependencies for a QBF instance using various schemes."
    )
    parser.add_argument("input_file", help="Path to the QDIMACS file")
    args = parser.parse_args()

    try:
        instance = QBFParser.from_file(args.input_file)

        schemes_classes = [
            # ("Trivial (Legacy)", TrivialInterBlockDependencyScheme),
            # ("Trivial", TrivialDependencyScheme),
            ("Standard", StandardDependencyScheme),
            ("Triangle", TriangleDependencyScheme),
            ("UniTri", UniTriDependencyScheme),
        ]

        print(f"Instance: {args.input_file}")

        num_universal = 0
        num_existential = 0
        for q_type, vars in instance.quantifiers:
            if q_type == "a":
                num_universal += len(vars)
            elif q_type == "e":
                num_existential += len(vars)

        print(
            f"Variables: {instance.num_vars} (Universal: {num_universal}, Existential: {num_existential}), Clauses: {instance.num_clauses}"
        )

        # Compute and validate all dependencies
        results = {}
        for name, scheme_cls in schemes_classes:
            print(f"Computing dependencies for {name}...")
            try:
                scheme = scheme_cls(instance)
                # Verification happens in __init__ -> compute -> verify_dependencies
                # If we get here, no exception was raised, so no cycles.
                print(
                    f"  [OK] {name} scheme instantiated and validated (no cycles detected)."
                )
                results[name] = scheme.dependencies

                # Generate DOT file
                safe_name = (
                    name.lower().replace(" ", "_").replace("(", "").replace(")", "")
                )
                dot_filename = f"dependencies_{safe_name}.dot"
                generate_dot(name, scheme.dependencies, dot_filename)
                print(f"  [DOT] Generated {dot_filename}")

            except DependencyViolationError as dve:
                print(
                    f"  [FAIL] {name} scheme validation failed: {dve}", file=sys.stderr
                )
                results[name] = {}  # Empty deps on failure
            except Exception as e:
                print(f"  [FAIL] {name} scheme error: {e}", file=sys.stderr)
                results[name] = {}

        # Map variable to quantifier type
        var_to_qtype = {}
        for q_type, vars in instance.quantifiers:
            for v in vars:
                var_to_qtype[v] = q_type

        # Print grouped by variable
        all_vars = sorted(range(1, instance.num_vars + 1))

        for var in all_vars:
            q_type = var_to_qtype.get(var, "?")
            # Only print for existential variables as requested/implied
            if q_type != "e":
                continue

            print(f"\nVariable {var} (Existential):")
            for name, _ in schemes_classes:
                deps = results.get(name, {}).get(var, set())
                deps_str = "{" + ", ".join(map(str, sorted(deps))) + "}"
                print(f"  {name:<20}: {deps_str}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
