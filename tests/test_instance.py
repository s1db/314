import pytest
from typing import List, Tuple
from src.instance import Instance
from src.dependency_schemes.trivial import TrivialDependencyScheme


class MockQBFInstance(Instance):
    def __init__(self, quantifiers: List[Tuple[str, List[int]]]):
        # Calculate num_vars from quantifiers
        num_vars = sum(len(vars) for _, vars in quantifiers)
        super().__init__(num_vars, 0, quantifiers, [], TrivialDependencyScheme)


def test_instance_initialization_success():
    quantifiers = [("e", [1, 2])]
    clauses = [[1, 2]]

    class MockScheme:
        def __init__(self, instance: Instance) -> None:
            self.instance = instance

        @classmethod
        def build(cls, instance: Instance) -> "MockScheme":
            return cls(instance)

    inst = Instance(2, 1, quantifiers, clauses, MockScheme)  # type: ignore[arg-type]

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
        @classmethod
        def build(cls, instance: Instance) -> "MockScheme":
            return cls()

    # Claim 1 clause, provide 0 — validate() raises before build() is called
    with pytest.raises(ValueError, match="Number of clauses"):
        Instance(1, 1, quantifiers, clauses, MockScheme)  # type: ignore[arg-type]


def test_instance_validation_var_mismatch():
    quantifiers = [("e", [1])]
    clauses = []

    class MockScheme:
        @classmethod
        def build(cls, instance: Instance) -> "MockScheme":
            return cls()

    # Claim 2 vars, provide 1 — Instance logs a warning (does not raise)
    # This matches the actual behaviour in instance.py validate().
    inst = Instance(2, 0, quantifiers, clauses, MockScheme)  # type: ignore[arg-type]
    assert inst.num_vars == 2
