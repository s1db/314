import pytest
import glob
from pathlib import Path
from src.instance_parsers.qbf import QBFParser
from src.error_schemes.bfns import BFnSErrorFormula
from src.candidate_function import FunctionManager
from src.bindings.abc_wrapper import AbcInterface  # ty:ignore[unresolved-import]

# Verify on real valid QBF instances
# We just want to check that the pipeline doesn't crash and ABC returns a result.
# We don't know the ground truth for random functions, so we just run it.


def get_instances():
    # Use glob to find instances
    root = Path(__file__).parent.parent
    instances = glob.glob(str(root / "test_instances" / "*.qdimacs"))
    # If no instances found, maybe return a dummy list to avoid failing collection?
    # Or skip.
    return instances


INSTANCES = get_instances()


@pytest.mark.skipif(not INSTANCES, reason="No instances found in test_instances/")
@pytest.mark.parametrize("instance_path", INSTANCES)
def test_real_instance_pipeline(instance_path, tmp_path):
    # 1. Parse
    instance = QBFParser.from_file(instance_path)

    # 2. Get vars
    # QBFInstance usually separates X (existential) and Y (universal).
    # Wait, 314 Solver usually handles 2QBF: Exists X, Forall Y, Exists Y' (skolem).
    # Let's assume instance has at least 2 scopes.
    # We need to identify X and Y.
    # If instance structure is unknown, we might need to inspect scopes.

    # For now, let's assume simple structure or just take first scope as X, second as Y.
    scopes = instance.quantifiers
    if len(scopes) < 2:
        pytest.skip("Instance doesn't have enough quantifier blocks for 2QBF")

    # Scope 0: X (Existential)
    # Scope 1: Y (Universal)
    # But Manthan solves E X A Y . F
    # So X are existential, Y are universal.

    x_vars = scopes[0][1]
    y_vars = scopes[1][1]

    # 3. Create Dummy Candidates (Constant 0)
    # y = 0
    function_manager = FunctionManager()
    candidates = {}

    # helper for constant 0
    cand_zero = function_manager.get_or([])

    for y in y_vars:
        candidates[y] = cand_zero

    # 4. Generate Verilog
    formula = BFnSErrorFormula()
    verilog_file = tmp_path / f"{Path(instance_path).stem}_check.v"

    formula.generate_verification_file(
        instance.clauses, candidates, x_vars, y_vars, str(verilog_file)
    )

    assert verilog_file.exists()
    assert verilog_file.stat().st_size > 0

    # 5. Run ABC
    abc = AbcInterface()
    res = abc.check_sat(str(verilog_file))

    # Result can be None (UNSAT) or list (SAT)
    # Just asserting it didn't raise exception
    assert res is None or isinstance(res, list)
