from src.repair_schemes.unsat_core import UnsatCoreRepairScheme
from src.instance import Instance
from src.candidate_function import FunctionManager


# Mock objects
class MockInstance:
    def __init__(self):
        self.clauses = []
        self.num_vars = 0


instance = MockInstance()
function_manager = FunctionManager()
dep_scheme = None

print("Attempting instantiation with 3 args (instance, fm, dep_scheme)...")
try:
    obj = UnsatCoreRepairScheme(instance, function_manager, dep_scheme)
    print("Success with 3 args!")
except Exception as e:
    print(f"Failed with 3 args: {e}")

print("\nAttempting instantiation with 2 args (instance, dep_scheme)...")
try:
    obj = UnsatCoreRepairScheme(instance, dep_scheme)
    print("Success with 2 args!")
except Exception as e:
    print(f"Failed with 2 args: {e}")
