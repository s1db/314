import numpy as np
import logging
from unittest.mock import create_autospec
from src.guessing_schemes.manthan import ManthanGuesser
from src.instance import Instance
from src.candidate_function import FunctionManager
from src.dependency_schemes.learned import LearnedDependencyScheme

# Configure logging
logging.basicConfig(level=logging.DEBUG)


def test_manthan_guesser_simple():
    # 1. Setup Mock Instance
    # Variables: 1 (University - "input"), 2 (Existential - "output")
    # Rule: 2 = NOT 1
    instance = create_autospec(Instance)
    instance.get_universal_vars.return_value = [1]
    instance.get_existential_vars.return_value = [2]

    # 2. Setup Samples
    # Samples:
    # 1=False (0) -> 2=True (1)
    # 1=True (1) -> 2=False (0)
    # 4 samples
    samples = np.array([[0, 1], [1, 0], [0, 1], [1, 0]], dtype=int)

    # Variables corresponding to columns
    variables = [1, 2]

    # 4. Run Guesser
    guesser = ManthanGuesser()
    manager = FunctionManager()

    # Mock Dependency Scheme
    dep_scheme = create_autospec(LearnedDependencyScheme)
    # potential_dependencies is a dict
    dep_scheme.potential_dependencies = {2: {1}}

    candidates = guesser.guess_candidates(instance, samples, manager, dep_scheme)

    # 5. Assertions
    assert 2 in candidates
    func = candidates[2]
    print(f"Learned function for 2: {func}")

    # Should be NOT 1
    # Representation: (NOT 1)
    # Check support
    assert func.support == {1}


def test_manthan_guesser_dependency_logic():
    # Variables: 1(A), 2(E), 3(E)
    # 3 depends on 2. 2 depends on 1.
    # Truth: 2 = 1. 3 = 2 (so 3=1).
    instance = create_autospec(Instance)
    instance.get_universal_vars.return_value = [1]
    instance.get_existential_vars.return_value = [2, 3]

    # Samples columns: [1, 2, 3]
    # 1=0, 2=0, 3=0
    # 1=1, 2=1, 3=1
    samples = np.array([[0, 0, 0], [1, 1, 1], [0, 0, 0], [1, 1, 1]])
    variables = [1, 2, 3]

    # 2 allowed to see 1
    # 3 allowed to see 1, 2
    dep_scheme = create_autospec(LearnedDependencyScheme)
    dep_scheme.potential_dependencies = {2: {1}, 3: {1, 2}}

    guesser = ManthanGuesser()
    manager = FunctionManager()

    candidates = guesser.guess_candidates(instance, samples, manager, dep_scheme)

    # Check 2
    func2 = candidates[2]
    assert func2.support == {1}

    # Check 3
    func3 = candidates[3]
    print(f"Learned function for 3: {func3}")

    did_update_3 = False
    if 2 in func3.support:
        did_update_3 = True

    if did_update_3:
        dep_scheme.verify_dependencies.assert_called()
    else:
        pass
