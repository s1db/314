from typing import List, Tuple
from src.instance import Instance
from src.dependency_schemes.learned import LearnedDependencyScheme
from src.dependency_schemes.base import DependencyViolationError


class MockQBFInstance(Instance):
    def __init__(self, quantifiers: List[Tuple[str, List[int]]]):
        num_vars = sum(len(vars) for _, vars in quantifiers)
        # Mock instance with empty clauses and LearnedDependencyScheme
        super().__init__(num_vars, 0, quantifiers, [], LearnedDependencyScheme)

        # Dependency logic is now in DependencyScheme, so Instance doesn't need self.dependencies
        # But for Mocks that might be used by old code or inspection? No, Instance cleaned up.
        # So we don't need self.dependencies here.

    # Override verify_dependencies to avoid strict checks for mock
    def verify_dependencies(self):
        pass


def test_2qbf_simple():
    # Forall x1 (1), Exists y1 (2)
    instance = MockQBFInstance([("a", [1]), ("e", [2])])
    scheme = LearnedDependencyScheme(instance)

    allowed = scheme.get_allowed_variables(2)
    assert 1 in allowed
    assert 2 not in allowed
    print("test_2qbf_simple passed")


def test_strict_qbf():
    # Forall x1 (1), Exists y1 (2), Forall x2 (3), Exists y2 (4)
    instance = MockQBFInstance([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])
    scheme = LearnedDependencyScheme(instance)

    # y1 (2) can only depend on x1 (1)
    allowed_y1 = scheme.get_allowed_variables(2)
    assert allowed_y1 == {1}

    # y2 (4) can depend on x1, y1, x2
    allowed_y2 = scheme.get_allowed_variables(4)
    assert allowed_y2 == {1, 2, 3}
    print("test_strict_qbf passed")


def test_mixed_blocks():
    # Exists y0 (1), Forall x1 (2), Exists y1 (3)
    instance = MockQBFInstance([("e", [1]), ("a", [2]), ("e", [3])])
    scheme = LearnedDependencyScheme(instance)

    # y0 (1) has no predecessors
    allowed_y0 = scheme.get_allowed_variables(1)
    assert allowed_y0 == set()

    # y1 (3) depends on y0, x1
    allowed_y1 = scheme.get_allowed_variables(3)
    assert allowed_y1 == {1, 2}
    print("test_mixed_blocks passed")


def test_order_violation():
    # Forall x1 (1), Exists y1 (2), Forall x2 (3), Exists y2 (4)
    instance = MockQBFInstance([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])
    scheme = LearnedDependencyScheme(instance)

    # Try to make y1 depend on x2 (future scope)
    try:
        scheme.update_dependencies(2, {3})
        raise AssertionError("Should have raised DependencyViolationError")
    except DependencyViolationError:
        pass
    print("test_order_violation passed")


def test_intra_block_dependencies_and_cycles():
    # Exists y1, y2, y3 (1, 2, 3)
    instance = MockQBFInstance([("e", [1, 2, 3])])
    scheme = LearnedDependencyScheme(instance)

    # Initially, all can depend on each other (peers)
    assert 2 in scheme.get_allowed_variables(1)
    assert 1 in scheme.get_allowed_variables(2)

    # 1 depends on 2
    scheme.update_dependencies(1, {2})

    # Now 2 cannot depend on 1 (cycle)
    # The learned scheme should dynamically remove 1 from allowed for 2
    # if it implements dynamic cycle checking in get_allowed_variables OR checks in update_dependencies.
    # Looking at LearnedDependencyScheme implementation, get_allowed_variables logic was a bit complex.
    # Let's rely on update_dependencies raining error for cycle.

    try:
        scheme.update_dependencies(2, {1})
        raise AssertionError("Should have raised DependencyViolationError for cycle")
    except DependencyViolationError:
        pass
    print("test_intra_block_dependencies_and_cycles passed")


def test_transitive_cycle_prevention():
    # Exists y1, y2, y3
    instance = MockQBFInstance([("e", [1, 2, 3])])
    scheme = LearnedDependencyScheme(instance)

    # 1 -> 2
    scheme.update_dependencies(1, {2})
    # 2 -> 3
    scheme.update_dependencies(2, {3})

    # 3 -> 1 should be blocked (1 -> 2 -> 3 -> 1 cycle)
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
    # U -> V means U depends on V.
    # Computation order: [2, 1] (Compute 2, then 1)
    instance = MockQBFInstance([("e", [1, 2])])
    scheme = LearnedDependencyScheme(instance)
    # Manually inject dependency for testing
    scheme.dependencies = {1: {2}, 2: set()}

    order = scheme.get_total_order()
    # Expect 2 comes before 1 in computation
    assert order == [2, 1]
    print("test_total_order passed")


def test_partial_order_transitive():
    # 1 -> 2 -> 3
    instance = MockQBFInstance([("e", [1, 2, 3])])
    scheme = LearnedDependencyScheme(instance)
    scheme.dependencies = {1: {2}, 2: {3}, 3: set()}

    # Partial order for 1 should include 2 and 3
    # Computation order: 3, 2, 1
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
