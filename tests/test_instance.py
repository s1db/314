import pytest
from typing import List, Tuple
from src.instance import Instance
from src.dependency_schemes.trivial_inter_block import TrivialInterBlockDependencyScheme


class MockQBFInstance(Instance):
    def __init__(self, quantifiers: List[Tuple[str, List[int]]]):
        # Calculate num_vars from quantifiers
        num_vars = sum(len(vars) for _, vars in quantifiers)
        super().__init__(
            num_vars, 0, quantifiers, [], TrivialInterBlockDependencyScheme
        )


def test_instance_initialization_success():
    quantifiers = [("e", [1, 2])]
    clauses = [[1, 2]]

    class MockScheme:
        def __init__(self, instance):
            self.instance = instance

    inst = Instance(2, 1, quantifiers, clauses, MockScheme)

    assert inst.num_vars == 2
    assert inst.num_clauses == 1
    assert inst.quantifiers == quantifiers
    assert inst.clauses == clauses
    assert isinstance(inst.dependency_scheme, MockScheme)
    assert inst.dependency_scheme.instance == inst


def test_instance_validation_clause_mismatch():
    quantifiers = [("e", [1])]
    clauses = []

    class MockScheme:
        def __init__(self, instance):
            pass

    # Claim 1 clause, provide 0
    with pytest.raises(ValueError, match="Number of clauses"):
        Instance(1, 1, quantifiers, clauses, MockScheme)


def test_instance_validation_var_mismatch():
    quantifiers = [("e", [1])]
    clauses = []

    class MockScheme:
        def __init__(self, instance):
            pass

    # Claim 2 vars, provide 1 (var 1). Var 2 is missing.
    # It should be added to existential block.
    inst = Instance(2, 0, quantifiers, clauses, MockScheme)
    
    # Check that variable 2 was added
    existential_vars = inst.get_existential_vars()
    assert 2 in existential_vars
    assert inst.quantifiers == [("e", [1, 2])]
