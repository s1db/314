from typing import Dict, Set
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
    ) -> Dict[int, CandidateFunction]:
        """
        Learns candidate functions for all existential variables using Decision Trees,
        restricted by the provided dependency scheme.
        """
        if samples.size == 0:
            logger.warning("No samples provided to DependencyGuidedGuesser.")
            return {}

        y_vars = instance.get_existential_vars()
        candidates: Dict[int, CandidateFunction] = {}

        # Map variable ID to column index in samples
        var_to_col = {
            var: i
            for i, var in enumerate(
                instance.get_existential_vars() + instance.get_universal_vars()
            )
        }

        data_matrix = samples.astype(int)

        for target_y in y_vars:
            # STRICTLY use the dependencies from the scheme
            # These are the variables that target_y IS ALLOWED to depend on (and effectively DOES depend on according to the scheme)
            allowed_vars = dependency_scheme.get_dependencies(target_y)

            feature_cols = []
            feature_map = []  # index -> var_id

            for var in allowed_vars:
                if var in var_to_col:
                    feature_cols.append(var_to_col[var])
                    feature_map.append(var)
                else:
                    logger.warning(
                        f"Dependency variable {var} for target {target_y} not found in samples."
                    )

            y_col_idx = var_to_col[target_y]
            y = data_matrix[:, y_col_idx]

            if not feature_cols:
                # Fallback: Learn constant function
                logger.debug(
                    f"No dependencies for variable {target_y}. Learning constant function."
                )
                count_ones = np.sum(y)
                count_zeros = len(y) - count_ones
                if count_ones > count_zeros:
                    candidates[target_y] = function_manager.get_true()
                else:
                    candidates[target_y] = function_manager.get_false()
                continue

            X = data_matrix[:, feature_cols]

            clf = SklearnDTC(criterion="gini", random_state=42)
            clf.fit(X, y)

            # Extract Function
            candidate_func, _ = self._extract_paths_and_deps(
                clf.tree_, clf.classes_, feature_map, function_manager
            )

            candidates[target_y] = candidate_func

        return candidates
