import pytest
import os
import sys

# Try to import built extension
try:
    from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]
except ImportError:
    pytest.skip("ABC extension not built", allow_module_level=True)

def test_abc_unsat(tmp_path):
    # (a & ~a) -> UNSAT
    # Module that always outputs 0
    # Wait, check_sat checks satisfiability. (a & ~a) is UNSAT.
    # So output is 0?
    # No, check_sat usually runs on a circuit output.
    # If the circuit output is constant 0, it is UNSAT.
    # If it can be 1, it is SAT.
    
    verilog = """
    module top(a, out);
      input a;
      output out;
      assign out = a & ~a;
    endmodule
    """
    f = tmp_path / "unsat.v"
    f.write_text(verilog)
    
    abc = AbcInterface()
    res = abc.check_sat(str(f))
    assert res is None # None means verified (UNSAT)

def test_abc_sat(tmp_path):
    # (a) -> SAT when a=1
    verilog = """
    module top(a, out);
      input a;
      output out;
      assign out = a;
    endmodule
    """
    f = tmp_path / "sat.v"
    f.write_text(verilog)
    
    abc = AbcInterface()
    res = abc.check_sat(str(f))
    assert isinstance(res, list)
    # Counter example should be a=1? 
    # Or just a list of bits.
    # 'a' is the only input.
    assert len(res) >= 1

def test_memory_stress(tmp_path):
    # Loop to ensure no leaks in start/stop or internal frame usage
    verilog = """
    module top(a, out);
      input a;
      output out;
      assign out = a & ~a;
    endmodule
    """
    f = tmp_path / "stress.v"
    f.write_text(verilog)
    
    abc = AbcInterface()
    # Run 100 times
    for _ in range(100):
        abc.check_sat(str(f))
