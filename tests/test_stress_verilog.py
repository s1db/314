import pytest
from src.candidate_function import FunctionManager
from src.error_schemes.bfns import BFnSErrorFormula
from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]


def test_large_skolem_function_generation(tmp_path):
    """
    Test generating Verilog for a very large candidate function to ensure
    Verilog generation handles depth/width correctly (batching, recursion limit, etc).
    """
    mgr = FunctionManager()

    # Create a large candidate: OR of 2000 literals
    # y2 = x1 | x2 | ... | x2000
    # This checks the recursive generator and potential stack limits?
    # Or checking batching of operations?

    # Actually, base.py _candidate_to_verilog joins children with " | ".
    # If we have a flat OR node with 2000 children, it will produce "v1 | v2 | ... | v2000".
    # This might be valid but very long line.
    # ABC might have line length limits (though Verilog 1995 handles newlines).

    num_literals = 2000
    literals = []
    # Just reuse variables 1..100 cyclically if needed, or 1..2000
    x_vars = list(range(1, num_literals + 1))

    for i in x_vars:
        literals.append(mgr.get_lit(i))

    # Flat OR
    cand_large = mgr.get_or(literals)

    # Set up problem
    # y_var = num_literals + 1
    y_var = 9999
    y_vars = [y_var]
    candidates = {y_var: cand_large}

    # Dummy formula: just True (empty clauses? or trivial)
    # Using trivial clause: (1)
    formula_clauses = [[1]]

    bfns = BFnSErrorFormula()
    out_file = tmp_path / "large_skolem.v"

    # Generate
    bfns.generate_verification_file(
        formula_clauses, candidates, x_vars, y_vars, str(out_file)
    )

    assert out_file.exists()

    # Read file size
    size = out_file.stat().st_size
    print(f"Generated Verilog size: {size} bytes")

    # Sanity check content
    with open(out_file, "r") as f:
        content = f.read()

    # Check if we have the long expression
    # Should contain v1 | v2 ...
    assert f"v{num_literals}" in content

    # Try running ABC on it to ensure it parses
    # Even if it's SAT/UNSAT, we just want it not to crash or parse error.
    try:
        from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]

        abc = AbcInterface()
        abc.check_sat(str(out_file))
        # Don't care about result logic, just execution
    except ImportError:
        pytest.skip("ABC extension not built")


def test_deep_skolem_function_generation(tmp_path):
    """
    Test a deep tree (nested ANDs/ORs) to check recursion limits or parser stack.
    """
    mgr = FunctionManager()

    # Create deep tree: AND(1, OR(2, AND(3, ...)))
    depth = 500  # Python recursion limit is usually 1000

    current_node = mgr.get_lit(depth)
    for i in range(depth - 1, 0, -1):
        lit = mgr.get_lit(i)
        if i % 2 == 0:
            current_node = mgr.get_or([lit, current_node])
        else:
            current_node = mgr.get_and([lit, current_node])

    y_var = 9999
    candidates = {y_var: current_node}
    x_vars = list(range(1, depth + 1))
    formula_clauses = [[1]]

    bfns = BFnSErrorFormula()
    out_file = tmp_path / "deep_skolem.v"

    bfns.generate_verification_file(
        formula_clauses, candidates, x_vars, [y_var], str(out_file)
    )

    # Check ABC parsing
    try:
        abc = AbcInterface()
        abc.check_sat(str(out_file))
    except ImportError:
        pytest.skip("ABC extension not built")
