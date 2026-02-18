from pathlib import Path
from src.instance_parsers.qbf import QBFParser
from src.dependency_schemes.triangle import TriangleDependencyScheme
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)

instance_path = Path("test_instances/qbf/existential_chain.qdimacs")

# Parse instance using QBFParser
try:
    instance = QBFParser.from_file(
        instance_path, dependency_scheme_class=TriangleDependencyScheme
    )
except Exception as e:
    print(f"Error parsing instance: {e}")
    sys.exit(1)

# Compute dependencies
instance.dependency_scheme.compute()
deps = instance.dependency_scheme.dependencies

print("Computed Dependencies:")
for var, dependent_on in deps.items():
    print(f"Var {var} depends on: {dependent_on}")

# Expected:
# 2 depends on 1 (because -1 2 0)
# 3 depends on 2 (because -2 3 0)
# 1 depends on nothing (or maybe nothing because it's first)

# Check if 2 depends on 1
if 2 in deps and 1 in deps[2]:
    print("SUCCESS: 2 depends on 1")
else:
    print("FAILURE: 2 DOES NOT depend on 1")

# Check if 3 depends on 2
if 3 in deps and 2 in deps[3]:
    print("SUCCESS: 3 depends on 2")
else:
    print("FAILURE: 3 DOES NOT depend on 2")
