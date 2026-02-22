from src.error_schemes.verilog_utils import VerilogGenerator

def test_clauses_to_verilog_simple():
    clauses = [[1, -2], [2, 3]]
    verilog = VerilogGenerator.clauses_to_verilog(clauses, "TEST", [1, 2, 3], [])
    
    assert "module TEST" in verilog
    assert "input v1;" in verilog
    assert "assign t_1 = v1 | ~v2;" in verilog
    assert "assign t_2 = v2 | v3;" in verilog
    assert "assign out = tcount_0;" in verilog # small enough for 1 batch
    assert "endmodule" in verilog

def test_clauses_batching_exact_100():
    # 100 clauses
    clauses = [[1, 2] for _ in range(100)]
    verilog = VerilogGenerator.clauses_to_verilog(clauses, "TEST_100", [1, 2], [])
    
    # wiring: t_1 to t_100
    assert "assign t_1 =" in verilog
    assert "assign t_100 =" in verilog
    
    # 100 clauses -> 1 batch (indices 0 to 99? logic: >= 100 flushes)
    # 100 items -> loop finishes, then flushes remainder or checks inside?
    # Logic: if len(current) >= 100: flush.
    # iter 100 (idx 100): adds to current (len 100). Flushes tcount_0.
    # So tcount_0 should contain t_1 to t_100.
    assert "assign tcount_0 =" in verilog
    assert "t_1 &" in verilog
    assert "t_100" in verilog
    assert "assign out = tcount_0;" in verilog

def test_clauses_batching_101():
    clauses = [[1, 2] for _ in range(101)]
    verilog = VerilogGenerator.clauses_to_verilog(clauses, "TEST_101", [1, 2], [])
    
    # tcount_0 (1-100)
    # tcount_1 (101)
    assert "assign tcount_0 =" in verilog
    assert "assign tcount_1 =" in verilog
    assert "assign out = tcount_0 & tcount_1;" in verilog

def test_functions_to_verilog_batching():
    # 15 functions
    funcs = {i: "w" for i in range(15)}
    verilog = VerilogGenerator.functions_to_verilog(funcs, "FUNCS", [], list(range(15)))
    
    # 0-9 -> wt_0
    # 10-14 -> wt_1
    assert "assign wt_0 =" in verilog
    assert "eq_0" in verilog
    assert "eq_9" in verilog
    assert "assign wt_1 =" in verilog
    assert "eq_10" in verilog
    assert "eq_14" in verilog
    assert "assign out = wt_0 & wt_1;" in verilog
