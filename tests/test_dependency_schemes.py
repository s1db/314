from typing import List, Tuple
from src.instance import Instance
from src.dependency_schemes.mutable import MutableDependencyScheme
from src.dependency_schemes.base import DependencyViolationError


def make_instance(quantifiers: List[Tuple[str, List[int]]]) -> Instance:
    """Build a minimal Instance with MutableDependencyScheme for testing."""
    num_vars = sum(len(var_list) for _, var_list in quantifiers)
    return Instance(num_vars, 0, quantifiers, [], MutableDependencyScheme)


def make_scheme(quantifiers: List[Tuple[str, List[int]]]) -> MutableDependencyScheme:
    instance = make_instance(quantifiers)
    assert isinstance(instance.dependency_scheme, MutableDependencyScheme)
    return instance.dependency_scheme


def test_2qbf_simple():
    # Forall x1 (1), Exists y1 (2)
    scheme = make_scheme([("a", [1]), ("e", [2])])

    allowed = scheme.get_allowed_variables(2)
    assert 1 in allowed
    assert 2 not in allowed
    print("test_2qbf_simple passed")


def test_strict_qbf():
    # Forall x1 (1), Exists y1 (2), Forall x2 (3), Exists y2 (4)
    scheme = make_scheme([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])

    # y1 (2) can only depend on x1 (1)
    allowed_y1 = scheme.get_allowed_variables(2)
    assert allowed_y1 == {1}

    # y2 (4) can depend on x1, y1, x2
    allowed_y2 = scheme.get_allowed_variables(4)
    assert allowed_y2 == {1, 2, 3}
    print("test_strict_qbf passed")


def test_mixed_blocks():
    # Exists y0 (1), Forall x1 (2), Exists y1 (3)
    scheme = make_scheme([("e", [1]), ("a", [2]), ("e", [3])])

    # y0 (1) has no predecessors
    allowed_y0 = scheme.get_allowed_variables(1)
    assert allowed_y0 == set()

    # y1 (3) depends on y0, x1
    allowed_y1 = scheme.get_allowed_variables(3)
    assert allowed_y1 == {1, 2}
    print("test_mixed_blocks passed")


def test_order_violation():
    # Forall x1 (1), Exists y1 (2), Forall x2 (3), Exists y2 (4)
    scheme = make_scheme([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])

    # Try to make y1 depend on x2 (future scope)
    try:
        scheme.update_dependencies(2, {3})
        raise AssertionError("Should have raised DependencyViolationError")
    except DependencyViolationError:
        pass
    print("test_order_violation passed")


def test_intra_block_dependencies_and_cycles():
    # Exists y1, y2, y3 (1, 2, 3)
    scheme = make_scheme([("e", [1, 2, 3])])

    # Initially, all can depend on each other (peers)
    assert 2 in scheme.get_allowed_variables(1)
    assert 1 in scheme.get_allowed_variables(2)

    # 1 depends on 2
    scheme.update_dependencies(1, {2})

    # 2 cannot depend on 1 (would form a cycle)
    try:
        scheme.update_dependencies(2, {1})
        raise AssertionError("Should have raised DependencyViolationError for cycle")
    except DependencyViolationError:
        pass
    print("test_intra_block_dependencies_and_cycles passed")


def test_transitive_cycle_prevention():
    # Exists y1, y2, y3
    scheme = make_scheme([("e", [1, 2, 3])])

    # 1 -> 2 -> 3
    scheme.update_dependencies(1, {2})
    scheme.update_dependencies(2, {3})

    # 3 -> 1 would close the cycle
    try:
        scheme.update_dependencies(3, {1})
        raise AssertionError(
            "Should have raised DependencyViolationError for transitive cycle"
        )
    except DependencyViolationError:
        pass
    print("test_transitive_cycle_prevention passed")


def test_total_order():
    # Exists y1, y2. y1 depends on y2.
    # Computation order: y2 before y1.
    scheme = make_scheme([("e", [1, 2])])
    # Manually inject dependency edge for testing
    scheme.dependencies = {1: {2}, 2: set()}

    order = scheme.get_total_order()
    assert order == [2, 1]
    print("test_total_order passed")


def test_partial_order_transitive():
    # 1 -> 2 -> 3
    scheme = make_scheme([("e", [1, 2, 3])])
    scheme.dependencies = {1: {2}, 2: {3}, 3: set()}

    # Partial order for 1: compute 3, then 2, then 1
    order = scheme.get_partial_order(1)
    assert order == [3, 2, 1]
    print("test_partial_order_transitive passed")


if __name__ == "__main__":
    test_2qbf_simple()
    test_strict_qbf()
    test_mixed_blocks()
    test_order_violation()
    test_intra_block_dependencies_and_cycles()
    test_transitive_cycle_prevention()
    test_total_order()
    test_partial_order_transitive()
    print("All tests passed in test_dependency_schemes.py")
