import pytest
from pathlib import Path
from src.solver import Solver
from src.dependency_schemes.mutable import MutableDependencyScheme
from src.dependency_schemes.standard import StandardDependencyScheme
from src.guessing_schemes.manthan import ManthanGuesser
from src.guessing_schemes.dependency_guided import DependencyGuidedGuesser
from src.fault_localization_schemes import QuantifiedMaxSATScheme
from src.repair_schemes.unsat_core import UnsatCoreRepairScheme


def test_guesser_selection():
    instance_path = Path("test_instances/bfns/toy_2qbf.qdimacs")

    # Test MutableDependencyScheme pairs with ManthanGuesser
    solver_mutable = Solver(
        instance_path=instance_path,
        fl_scheme_cls=QuantifiedMaxSATScheme,
        repair_scheme_cls=UnsatCoreRepairScheme,
        dependency_scheme_cls=MutableDependencyScheme,
    )
    assert isinstance(solver_mutable.learner, ManthanGuesser)
    assert not isinstance(solver_mutable.learner, DependencyGuidedGuesser)

    # Test Static dependency scheme (Standard) pairs with DependencyGuidedGuesser
    solver_static = Solver(
        instance_path=instance_path,
        fl_scheme_cls=QuantifiedMaxSATScheme,
        repair_scheme_cls=UnsatCoreRepairScheme,
        dependency_scheme_cls=StandardDependencyScheme,
    )
    assert isinstance(solver_static.learner, DependencyGuidedGuesser)


def test_manthan_guesser_strict_assertion():
    from src.dependency_schemes.standard import StandardDependencyScheme
    from src.instance_parsers.qbf import QBFParser
    import numpy as np
    from src.candidate_function import FunctionManager

    instance = QBFParser.from_file(
        Path("test_instances/bfns/toy_2qbf.qdimacs"), StandardDependencyScheme
    )
    guesser = ManthanGuesser()
    manager = FunctionManager()
    samples = np.array([[0, 0, 0]])

    # Should raise AssertionError when used with static scheme
    with pytest.raises(AssertionError):
        guesser.guess_candidates(instance, samples, manager, instance.dependency_scheme)


if __name__ == "__main__":
    pytest.main([__file__])
