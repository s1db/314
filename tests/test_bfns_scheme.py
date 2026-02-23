from src.candidate_function import FunctionManager
from src.error_schemes.bfns import BFnSErrorFormula


def test_bfns_generation(tmp_path):
    # Setup
    mgr = FunctionManager()
    # F(X,Y): (x1 | y2)
    formula_clauses = [[1, 2]]
    x_vars = [1]
    y_vars = [2]

    # Candidate: y2 = ~x1
    # Node: LIT(-1)
    cand_y2 = mgr.get_lit(-1)
    candidates = {2: cand_y2}

    bfns = BFnSErrorFormula()
    out_file = tmp_path / "error.v"

    bfns.generate_verification_file(
        formula_clauses, candidates, x_vars, y_vars, str(out_file)
    )

    # Check
    with open(out_file, "r") as f:
        content = f.read()

    # 1. Structure
    assert "module FORMULA" in content
    assert "module SKOLEM" in content
    assert "module MAIN" in content

    # 2. Spec wiring in MAIN
    # FORMULA inputs: 1, 2. Output out1
    # FORMULA ports are v1, v2, out. Actuals are v1, v2, out1.
    assert "FORMULA F1 ( v1, v2, out1 );" in content

    # 3. Skolem wiring in MAIN
    # SKOLEM inputs: v1, ip2. Output out2
    # SKOLEM ports are v1, ip2, out. Actuals are v1, ip2, out2.
    assert "SKOLEM S1 ( v1, ip2, out2 );" in content

    # 4. Failure check wiring in MAIN
    # FORMULA F2 inputs: v1, v2 (formal). Actuals: v1, ip2 (since 2 is Y var). Output out3
    assert "FORMULA F2 ( v1, ip2, out3 );" in content

    # 5. Logic
    assert "assign out = out1 & out2 & ~out3;" in content
