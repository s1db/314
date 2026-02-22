from src.dependency_schemes.mutable import MutableDependencyScheme
from typing import List, Dict, Set, Tuple
import numpy as np
import logging
from sklearn.tree import DecisionTreeClassifier as SklearnDTC

from src.instance import Instance
from src.candidate_function import CandidateFunction, FunctionManager
from src.guessing_schemes.base import BaseCandidateFunctionGuesser
from src.dependency_schemes.base import DependencyScheme

logger = logging.getLogger(__name__)


class ManthanGuesser(BaseCandidateFunctionGuesser):
    def __init__(self):
        super().__init__()
        self.updates_dependencies = True

    def guess_candidates(
        self,
        instance: Instance,
        samples: np.ndarray,
        function_manager: FunctionManager,
        dependency_scheme: DependencyScheme,
        initial_candidates: Dict[int, CandidateFunction] | None = None,
    ) -> Dict[int, CandidateFunction]:
        """
        Learns candidate functions for all existential variables using Decision Trees.
        Updates dependencies based on learned functions.
        """
        assert isinstance(dependency_scheme, MutableDependencyScheme)
        if samples.size == 0:
            logger.warning("No samples provided to ManthanGuesser.")
            return {}

        y_vars = instance.get_existential_vars()
        candidates: Dict[int, CandidateFunction] = (
            initial_candidates.copy() if initial_candidates else {}
        )

        # Map variable ID to column index in samples
        var_to_col = {
            var: i
            for i, var in enumerate(
                instance.get_existential_vars() + instance.get_universal_vars()
            )
        }

        # Use samples directly (it's already a boolean matrix)
        # We assume samples columns correspond to 'variables' list order.
        data_matrix = samples.astype(int)

        # Iterate through each existential variable
        for target_y in y_vars:
            # Skip if already resolved and not repairable (e.g. by preprocessing)
            if target_y in candidates and not candidates[target_y].repairable:
                logger.debug(
                    f"Skipping variable {target_y} as it is already resolved and non-repairable."
                )
                continue

            # Use potential dependencies (preceding vars in QBF prefix)
            allowed_vars = dependency_scheme.prefix_scope.get(target_y, set())

            # Map features to columns in data_matrix
            # We need a list of (col_idx, var_id)
            feature_cols = []
            feature_map = []  # index -> var_id

            for var in allowed_vars:
                if var in var_to_col:
                    feature_cols.append(var_to_col[var])
                    feature_map.append(var)

            if not feature_cols:
                # Fallback: Constant function? Or use X?
                # If no potential dependencies (e.g., first E-block),
                # it should depend on previous X-vars.
                # If potential_dependencies is correct, it includes X-vars.
                # If empty, it means no previous variables.
                pass

            X = data_matrix[:, feature_cols]
            y = data_matrix[:, var_to_col[target_y]]

            # 2. Learn Decision Tree
            try:
                clf = SklearnDTC(criterion="gini", random_state=42)
                clf.fit(X, y)

                # 3. Extract Function & Dependencies
                candidate_func, used_vars = self._extract_paths_and_deps(
                    clf.tree_, clf.classes_, feature_map, function_manager
                )

                candidates[target_y] = candidate_func

                # Update dependencies with what the tree actually used
                dependency_scheme.update_dependencies(target_y, used_vars)
                dependency_scheme.verify_dependencies()

            except Exception as e:
                logger.error(f"Failed to learn candidate for {target_y}: {e}")
                candidates[target_y] = function_manager.get_or([])  # False

        return candidates

    def _extract_paths_and_deps(
        self, tree, classes, feature_map: List[int], manager: FunctionManager
    ) -> Tuple[CandidateFunction, Set[int]]:
        """
        Extracts paths to leaf nodes with class 1.
        Returns the CandidateFunction and the Set of variables used in the function.
        """
        children_left = tree.children_left
        children_right = tree.children_right
        feature = tree.feature
        value = tree.value

        positive_paths: List[CandidateFunction] = []
        used_variables: Set[int] = set()

        def dfs(
            node_id: int,
            current_path_literals: List[CandidateFunction],
            current_path_vars: Set[int],
        ):
            if children_left[node_id] == children_right[node_id]:
                # Leaf node
                counts = value[node_id][0]
                is_class_1 = False
                if len(classes) == 1:
                    if classes[0]:
                        is_class_1 = True
                else:
                    if counts[1] > counts[0]:
                        is_class_1 = True

                if is_class_1:
                    path_node = (
                        manager.get_and(current_path_literals)
                        if current_path_literals
                        else manager.get_and([])
                    )
                    positive_paths.append(path_node)
                    used_variables.update(current_path_vars)
                return

            # Split node
            feature_idx = feature[node_id]
            var_id = feature_map[feature_idx]

            # Left (0) -> NOT var
            lit_neg = manager.get_lit(-abs(var_id))
            dfs(
                children_left[node_id],
                current_path_literals + [lit_neg],
                current_path_vars | {abs(var_id)},
            )

            # Right (1) -> var
            lit_pos = manager.get_lit(abs(var_id))
            dfs(
                children_right[node_id],
                current_path_literals + [lit_pos],
                current_path_vars | {abs(var_id)},
            )

        dfs(0, [], set())

        return manager.get_or(positive_paths), used_variables
