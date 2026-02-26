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
        # Use sorted order to match solver's all_vars
        all_vars = sorted(
            instance.get_existential_vars() + instance.get_universal_vars()
        )
        var_to_col = {var: i for i, var in enumerate(all_vars)}

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

            y = data_matrix[:, var_to_col[target_y]]

            if not feature_cols:
                # If no features, the variable must be a constant (True/False).
                # Predict whichever value is more common in the samples.
                # Often triggered when outermost existential variables are not constrained by any other variables.
                counts = np.bincount(y)
                most_common = np.argmax(counts)
                candidates[target_y] = (
                    function_manager.get_true()
                    if most_common == 1
                    else function_manager.get_false()
                )
                dependency_scheme.update_dependencies(target_y, set())
                continue

            X = data_matrix[:, feature_cols]

            # 2. Learn Decision Tree
            try:
                clf = SklearnDTC(criterion="gini", random_state=42)
                clf.fit(X, y)

                # 3. Extract Function & Dependencies
                candidate_func, used_vars = self._tree_to_candidate(
                    0, clf.tree_, clf.classes_, feature_map, function_manager
                )

                candidates[target_y] = candidate_func

                # Update dependencies with what the tree actually used
                dependency_scheme.update_dependencies(target_y, used_vars)
                dependency_scheme.verify_dependencies()

            except Exception as e:
                logger.error(f"Failed to learn candidate for {target_y}: {e}")
                candidates[target_y] = function_manager.get_false()

        return candidates

    def _tree_to_candidate(
        self,
        node_id: int,
        tree,
        classes,
        feature_map: List[int],
        manager: FunctionManager,
    ) -> Tuple[CandidateFunction, Set[int]]:
        """
        Recursively converts the sklearn decision tree structure to a CandidateFunction
        using ITE nodes. Returns (CandidateFunction, Set of used variable IDs).
        """
        children_left = tree.children_left
        children_right = tree.children_right
        feature = tree.feature
        value = tree.value

        if children_left[node_id] == children_right[node_id]:
            # Leaf node
            counts = value[node_id][0]
            if len(classes) == 1:
                is_class_1 = bool(classes[0])
            else:
                is_class_1 = counts[1] > counts[0]

            return (manager.get_true() if is_class_1 else manager.get_false()), set()

        # Split node
        feature_idx = feature[node_id]
        var_id = feature_map[feature_idx]

        cond = manager.get_lit(abs(var_id))

        # Right (1) is True branch, Left (0) is False branch (feature <= 0.5)
        true_branch, true_vars = self._tree_to_candidate(
            children_right[node_id], tree, classes, feature_map, manager
        )
        false_branch, false_vars = self._tree_to_candidate(
            children_left[node_id], tree, classes, feature_map, manager
        )

        node = manager.get_ite(cond, true_branch, false_branch)
        used_vars = {abs(var_id)} | true_vars | false_vars
        return node, used_vars
