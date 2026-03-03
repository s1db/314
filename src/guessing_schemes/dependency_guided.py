from typing import Dict
import numpy as np
import logging
from sklearn.tree import DecisionTreeClassifier as SklearnDTC

from src.instance import Instance
from src.candidate_function import CandidateFunction, FunctionManager
from src.guessing_schemes.manthan import ManthanGuesser
from src.dependency_schemes.base import DependencyScheme

logger = logging.getLogger(__name__)


class DependencyGuidedGuesser(ManthanGuesser):
    """
    A guesser that uses a pre-computed dependency scheme to determine the features
    for the decision tree learner. Instead of learning dependencies, it strictly
    follows the dependencies provided by the scheme.
    """

    def __init__(self):
        super().__init__()
        # This guesser does NOT update dependencies based on what the tree learned,
        # because the dependencies are fixed by the scheme.
        self.updates_dependencies = False

    def guess_candidates(
        self,
        instance: Instance,
        samples: np.ndarray,
        function_manager: FunctionManager,
        dependency_scheme: DependencyScheme,
        initial_candidates: Dict[int, CandidateFunction] | None = None,
    ) -> Dict[int, CandidateFunction]:
        """
        Learns candidate functions for all existential variables using Decision Trees,
        restricted by the provided dependency scheme.
        """
        if samples.size == 0:
            logger.warning("No samples provided to DependencyGuidedGuesser.")
            return {}

        y_vars = instance.get_existential_vars()
        candidates: Dict[int, CandidateFunction] = (
            initial_candidates.copy() if initial_candidates else {}
        )

        # Map variable ID to column index in samples
        var_to_col = {
            var: i
            for i, var in enumerate(
                sorted(instance.get_existential_vars() + instance.get_universal_vars())
            )
        }

        data_matrix = samples.astype(int)

        for target_y in y_vars:
            # Skip if already resolved and not repairable
            if target_y in candidates and not candidates[target_y].repairable:
                continue

            # STRICTLY use the dependencies from the scheme for the initial guess (the "guided" part)
            allowed_vars = dependency_scheme.get_dependencies(target_y)

            feature_cols = []
            feature_map = []  # index -> var_id

            for var in allowed_vars:
                if var in var_to_col:
                    feature_cols.append(var_to_col[var])
                    feature_map.append(var)

            y_col_idx = var_to_col[target_y]
            y = data_matrix[:, y_col_idx]

            if not feature_cols:
                # Fallback: Learn constant function
                logger.debug(
                    f"No dependencies for variable {target_y}. Learning constant function."
                )
                counts = np.bincount(y)
                most_common = np.argmax(counts)
                candidates[target_y] = (
                    function_manager.get_true()
                    if most_common == 1
                    else function_manager.get_false()
                )
                continue

            X = data_matrix[:, feature_cols]

            clf = SklearnDTC(criterion="gini", random_state=42)
            clf.fit(X, y)

            # Extract Function using inherited method
            candidate_func, _ = self._tree_to_candidate(
                0, clf.tree_, clf.classes_, feature_map, function_manager
            )

            candidates[target_y] = candidate_func

        return candidates
