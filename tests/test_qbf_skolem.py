import os
import pytest
from src.candidate_function import FunctionManager, NodeType
from src.error_schemes.qbf_skolem import QBFSkolemErrorFormula


def test_qbf_skolem_generation(tmp_path):
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

    qbf = QBFSkolemErrorFormula()
    out_file = tmp_path / "error_qbf.v"

    qbf.generate_verification_file(
        formula_clauses, candidates, x_vars, y_vars, str(out_file)
    )

    # Check content
    with open(out_file, "r") as f:
        content = f.read()

    # 1. Structure
    assert "module FORMULA" in content
    assert "module SKOLEM" in content
    assert "module MAIN" in content

    # 2. Skolem wiring in MAIN
    # SKOLEM inputs: v1, ip2. Output out_skolem
    assert "SKOLEM S1 ( .v1(v1), .ip2(ip2), .out(out_skolem) );" in content

    # 3. Formula wiring in MAIN
    # FORMULA inputs: vX..., vY...
    # vX mapped to vX, vY mapped to ipY (skolem outputs)
    assert "FORMULA F1 ( .v1(v1), .v2(ip2), .out(out_formula) );" in content

    # 4. Final Logic
    # out = out_skolem & ~out_formula
    assert "assign out = out_skolem & ~out_formula;" in content
