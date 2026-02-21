import sys
from src.instance_parsers.qbf import QBFParser
from src.dependency_schemes.trivial import TrivialDependencyScheme
import os


def test_deep_chain_dependencies():
    # Path to the test instance
    test_file = "test_instances/qbf/deep_chain_5qbf.qdimacs"
    if not os.path.exists(test_file):
        print(f"Test file not found: {test_file}")
        sys.exit(1)

    # Parse the instance
    instance = QBFParser.from_file(test_file)

    # Run the Trivial Dependency Scheme
    scheme = TrivialDependencyScheme.build(instance)

    # Assertions based on "Cumulative" dependencies (all previous variables)

    # Top-level: A x1 (1), E y1 (2)
    # 2 (y1) depends on {1}
    assert scheme.dependencies[2] == {1}

    # Next: A x2 (3), E y2 (4)
    # 4 (y2) depends on {1, 2, 3}
    assert scheme.dependencies[4] == {1, 2, 3}

    # ...
    # Last: A x5 (9), E y5 (10)
    # 10 (y5) depends on {1, 2, ..., 9}
    expected_10 = set(range(1, 10))
    if scheme.dependencies[10] != expected_10:
        print(f"Expected {expected_10}, got {scheme.dependencies[10]}")
    assert scheme.dependencies[10] == expected_10

    # Check intermediate: 8 (y4) depends on {1..7}
    expected_8 = set(range(1, 8))
    assert scheme.dependencies[8] == expected_8

    # Universals should maintain empty dependencies
    assert 1 not in scheme.dependencies
    assert 3 not in scheme.dependencies
    assert 9 not in scheme.dependencies


if __name__ == "__main__":
    try:
        test_deep_chain_dependencies()
        print("Deep chain test passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback

        traceback.print_exc()
