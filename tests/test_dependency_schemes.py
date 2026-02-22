"""
Comprehensive tests for the refactored dependency scheme hierarchy.

Covers:
- DependencyScheme base class graph algorithms
- MutableDependencyScheme (runtime-learned dependencies)
- StaticDependencyScheme / TrivialDependencyScheme (pre-computed, immutable)
"""

import pytest
from typing import List, Tuple
from src.dependency_schemes.base import DependencyViolationError
from src.dependency_schemes.mutable import MutableDependencyScheme
from src.dependency_schemes.trivial import TrivialDependencyScheme


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mutable(quantifiers: List[Tuple[str, List[int]]]) -> MutableDependencyScheme:
    """Create a MutableDependencyScheme from quantifier blocks."""
    num_vars = sum(len(vs) for _, vs in quantifiers)
    return MutableDependencyScheme(quantifiers, num_vars)


def make_trivial(quantifiers: List[Tuple[str, List[int]]]) -> TrivialDependencyScheme:
    """Create a TrivialDependencyScheme from quantifier blocks."""
    num_vars = sum(len(vs) for _, vs in quantifiers)
    return TrivialDependencyScheme(quantifiers, num_vars)


# ===========================================================================
# Base class graph algorithms
# ===========================================================================


class TestBaseGraphAlgorithms:
    """Tests for DependencyScheme graph algorithms using MutableDependencyScheme
    as a concrete subclass with manually injected dependencies."""

    def test_get_topological_order_linear_chain(self):
        """A -> B -> C yields computation order [C, B, A]."""
        scheme = make_mutable([("e", [1, 2, 3])])
        scheme.dependencies = {1: {2}, 2: {3}, 3: set()}
        order = scheme.get_topological_order()
        assert order == [3, 2, 1]

    def test_get_topological_order_diamond(self):
        """Diamond DAG: 1->{2,3}, 2->{4}, 3->{4}."""
        scheme = make_mutable([("e", [1, 2, 3, 4])])
        scheme.dependencies = {1: {2, 3}, 2: {4}, 3: {4}, 4: set()}
        order = scheme.get_topological_order()
        # 4 must come before 2 and 3; 2 and 3 must come before 1
        assert order.index(4) < order.index(2)
        assert order.index(4) < order.index(3)
        assert order.index(2) < order.index(1)
        assert order.index(3) < order.index(1)

    def test_get_topological_order_disjoint(self):
        """Disconnected components sort correctly."""
        scheme = make_mutable([("e", [1, 2, 3, 4])])
        scheme.dependencies = {1: {2}, 2: set(), 3: {4}, 4: set()}
        order = scheme.get_topological_order()
        assert order.index(2) < order.index(1)
        assert order.index(4) < order.index(3)

    def test_get_topological_order_cycle_raises(self):
        """Cyclic graph raises DependencyViolationError."""
        scheme = make_mutable([("e", [1, 2])])
        scheme.dependencies = {1: {2}, 2: {1}}
        with pytest.raises(DependencyViolationError, match="Cycle detected"):
            scheme.get_topological_order()

    def test_get_transitive_dependencies(self):
        """Transitive closure 1->{2,3} via chain 1->2->3."""
        scheme = make_mutable([("e", [1, 2, 3])])
        scheme.dependencies = {1: {2}, 2: {3}, 3: set()}
        assert scheme.get_transitive_dependencies(1) == {2, 3}
        assert scheme.get_transitive_dependencies(2) == {3}
        assert scheme.get_transitive_dependencies(3) == set()

    def test_sort_by_dependency_order(self):
        """Subset sorting matches topological order."""
        scheme = make_mutable([("e", [1, 2, 3])])
        scheme.dependencies = {1: {2}, 2: {3}, 3: set()}
        result = scheme.sort_by_dependency_order([1, 3])
        assert result == [3, 1]

    def test_sort_by_dependency_order_missing_var(self):
        """Missing variable raises DependencyViolationError."""
        scheme = make_mutable([("e", [1, 2])])
        scheme.dependencies = {1: {2}, 2: set()}
        with pytest.raises(DependencyViolationError, match="not found"):
            scheme.sort_by_dependency_order([1, 99])

    def test_verify_dependencies_self_loop(self):
        """Self-dependency detected."""
        scheme = make_mutable([("e", [1])])
        scheme.dependencies = {1: {1}}
        with pytest.raises(DependencyViolationError, match="Self-dependency"):
            scheme.verify_dependencies()

    def test_verify_dependencies_universal_with_deps(self):
        """Universal variable with dependencies raises."""
        scheme = make_mutable([("a", [1]), ("e", [2])])
        scheme.dependencies = {1: {2}, 2: set()}
        with pytest.raises(DependencyViolationError, match="Universal variable"):
            scheme.verify_dependencies()

    def test_verify_dependencies_future_block(self):
        """Depending on a later block variable raises."""
        scheme = make_mutable([("e", [1]), ("a", [2])])
        scheme.dependencies = {1: {2}, 2: set()}
        with pytest.raises(
            DependencyViolationError, match="Quantifier order violation"
        ):
            scheme.verify_dependencies()

    def test_repr(self):
        """__repr__ produces readable output."""
        scheme = make_mutable([("e", [1, 2])])
        scheme.dependencies = {1: {2}, 2: set()}
        r = repr(scheme)
        assert "MutableDependencyScheme" in r
        assert "vars=2" in r
        assert "edges=1" in r

    def test_prefix_scope(self):
        """prefix_scope correctly computed from quantifier blocks."""
        # ∀x1 ∃y1 ∀x2 ∃y2
        scheme = make_mutable([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])
        assert scheme.prefix_scope[1] == set()
        assert scheme.prefix_scope[2] == {1}
        assert scheme.prefix_scope[3] == {1, 2}
        assert scheme.prefix_scope[4] == {1, 2, 3}


# ===========================================================================
# MutableDependencyScheme
# ===========================================================================


class TestMutableDependencyScheme:
    """Tests for MutableDependencyScheme (runtime-learned dependencies)."""

    def test_2qbf_simple(self):
        """∀x1 ∃y1: y1 can depend on x1."""
        scheme = make_mutable([("a", [1]), ("e", [2])])
        allowed = scheme.get_allowed_variables(2)
        assert 1 in allowed
        assert 2 not in allowed

    def test_strict_qbf(self):
        """∀x1 ∃y1 ∀x2 ∃y2: strict scope rules."""
        scheme = make_mutable([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])
        assert scheme.get_allowed_variables(2) == {1}
        assert scheme.get_allowed_variables(4) == {1, 2, 3}

    def test_mixed_blocks(self):
        """∃y0 ∀x1 ∃y1: y0 has no predecessors."""
        scheme = make_mutable([("e", [1]), ("a", [2]), ("e", [3])])
        assert scheme.get_allowed_variables(1) == set()
        assert scheme.get_allowed_variables(3) == {1, 2}

    def test_order_violation(self):
        """Depending on a future-scope variable raises."""
        scheme = make_mutable([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])
        with pytest.raises(DependencyViolationError):
            scheme.update_dependencies(2, {3})

    def test_intra_block_and_cycles(self):
        """Same-block deps allowed, direct cycles rejected."""
        scheme = make_mutable([("e", [1, 2, 3])])

        # Initially, peers can depend on each other
        assert 2 in scheme.get_allowed_variables(1)
        assert 1 in scheme.get_allowed_variables(2)

        # 1 depends on 2
        scheme.update_dependencies(1, {2})

        # Now 2 -> 1 would create a cycle
        with pytest.raises(DependencyViolationError):
            scheme.update_dependencies(2, {1})

    def test_transitive_cycle_prevention(self):
        """Transitive cycle A->B->C->A blocked."""
        scheme = make_mutable([("e", [1, 2, 3])])
        scheme.update_dependencies(1, {2})
        scheme.update_dependencies(2, {3})
        with pytest.raises(DependencyViolationError):
            scheme.update_dependencies(3, {1})

    def test_topological_order_after_updates(self):
        """Order reflects learned edges."""
        scheme = make_mutable([("e", [1, 2])])
        scheme.update_dependencies(1, {2})
        order = scheme.get_topological_order()
        assert order == [2, 1]

    def test_update_then_get_allowed_excludes_descendants(self):
        """After 1->2, peer exclusion prevents 2 from seeing 1."""
        scheme = make_mutable([("e", [1, 2, 3])])
        scheme.update_dependencies(1, {2})
        # 2 can no longer depend on 1 (would be a cycle)
        allowed_2 = scheme.get_allowed_variables(2)
        assert 1 not in allowed_2
        # But 3 can still depend on both
        allowed_3 = scheme.get_allowed_variables(3)
        assert 1 in allowed_3
        assert 2 in allowed_3


# ===========================================================================
# StaticDependencyScheme / TrivialDependencyScheme
# ===========================================================================


class TestStaticDependencyScheme:
    """Tests for StaticDependencyScheme and TrivialDependencyScheme."""

    def test_trivial_computes_full_prefix(self):
        """Every existential depends on all prior variables."""
        scheme = make_trivial([("a", [1]), ("e", [2]), ("a", [3]), ("e", [4])])
        assert scheme.dependencies[2] == {1}
        assert scheme.dependencies[4] == {1, 2, 3}

    def test_trivial_update_raises(self):
        """update_dependencies raises TypeError for static schemes."""
        scheme = make_trivial([("a", [1]), ("e", [2])])
        with pytest.raises(TypeError, match="static"):
            scheme.update_dependencies(2, {1})

    def test_trivial_universal_no_deps(self):
        """Universals have no outgoing dependencies."""
        scheme = make_trivial([("a", [1]), ("e", [2]), ("a", [3])])
        assert 1 not in scheme.dependencies
        assert 3 not in scheme.dependencies

    def test_trivial_topological_order(self):
        """Order matches quantifier prefix order for trivial scheme."""
        scheme = make_trivial([("a", [1]), ("e", [2, 3])])
        order = scheme.get_topological_order()
        # 2 and 3 both depend on 1, so 1 comes first
        assert order.index(1) < order.index(2)
        assert order.index(1) < order.index(3)

    def test_trivial_existential_first_block(self):
        """Existential in first block has no dependencies."""
        scheme = make_trivial([("e", [1, 2]), ("a", [3]), ("e", [4])])
        # First block existentials: 1 depends on nothing, 2 depends on 1
        assert scheme.dependencies[1] == set()
        assert scheme.dependencies[2] == {1}
        # Second existential block: 4 depends on 1, 2, 3
        assert scheme.dependencies[4] == {1, 2, 3}

    def test_trivial_get_allowed_variables(self):
        """get_allowed_variables returns the pre-computed deps for static schemes."""
        scheme = make_trivial([("a", [1]), ("e", [2, 3])])
        assert scheme.get_allowed_variables(2) == {1}
        assert scheme.get_allowed_variables(3) == {1, 2}
