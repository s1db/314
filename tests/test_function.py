import pytest
from src.candidate_function import CandidateFunction, FunctionManager, NodeType

@pytest.fixture
def manager():
    return FunctionManager()

def test_structural_hashing(manager):
    l1 = manager.get_lit(1)
    l2 = manager.get_lit(1)
    assert l1 is l2, "Literals should be deduplicated"

    f1 = manager.get_and([l1, manager.get_lit(2)])
    f2 = manager.get_and([manager.get_lit(1), manager.get_lit(2)])
    assert f1 is f2, "Identical AND nodes should be deduplicated"

def test_simplification_and(manager):
    l1 = manager.get_lit(1)
    l2 = manager.get_lit(2)
    l3 = manager.get_lit(3)
    
    # Test Flattening: And(1, And(2, 3)) -> And(1, 2, 3)
    inner = manager.get_and([l2, l3])
    outer = manager.get_and([l1, inner])
    
    assert len(outer.children) == 3
    assert outer.node_type == NodeType.AND
    
    # Test Deduplication: And(1, 1) -> 1
    dup = manager.get_and([l1, l1])
    assert dup is l1

    # Test Single Child: And(1) -> 1
    single = manager.get_and([l1])
    assert single is l1

def test_ite_evaluation(manager):
    # ITE(1, 2, 3)
    cond = manager.get_lit(1)
    tb = manager.get_lit(2)
    fb = manager.get_lit(3)
    ite = manager.get_ite(cond, tb, fb)
    
    # If 1 is True, result is 2
    assert ite.evaluate({1: True, 2: True, 3: False})
    assert not ite.evaluate({1: True, 2: False, 3: True})
    
    # If 1 is False, result is 3
    assert ite.evaluate({1: False, 2: False, 3: True})
    assert not ite.evaluate({1: False, 2: True, 3: False})

def test_substitute(manager):
    # f = And(1, 2)
    # substitute 1 -> 3
    l1 = manager.get_lit(1)
    l2 = manager.get_lit(2)
    f = manager.get_and([l1, l2])
    
    l3 = manager.get_lit(3)
    mapping = {1: l3}
    f_sub = f.substitute(manager, mapping)
    
    assert f_sub.node_type == NodeType.AND
    # Children should be 3 and 2
    supports = f_sub.support
    assert 3 in supports
    assert 2 in supports
    assert 1 not in supports

def test_not_nnf(manager):
    # ~(And(1, 2)) -> Or(-1, -2)
    l1 = manager.get_lit(1)
    l2 = manager.get_lit(2)
    f = manager.get_and([l1, l2])
    
    not_f = f.Not(manager)
    assert not_f.node_type == NodeType.OR
    
    # Check children are -1 and -2
    c1, c2 = not_f.children
    # Children order might vary due to set sorting, check values
    assert {c.value for c in not_f.children} == {-1, -2}

