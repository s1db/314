from typing import List, Tuple
from functools import cache
import logging

logger = logging.getLogger(__name__)


class Instance:
    def __init__(
        self,
        num_vars: int,
        num_clauses: int,
        quantifiers: List[Tuple[str, List[int]]],
        clauses: List[List[int]],
        dependency_scheme_class,
    ):
        self.num_vars = num_vars
        self.num_clauses = num_clauses
        self.quantifiers = quantifiers
        self.clauses = clauses

        # Handle unquantified variables
        all_vars = set(range(1, self.num_vars + 1))
        quantified_vars = set()
        for _, vars in self.quantifiers:
            quantified_vars.update(vars)

        unquantified = all_vars - quantified_vars
        if unquantified:
            sorted_unquantified = sorted(list(unquantified))
            logger.warning(
                f"Found unquantified variables: {sorted_unquantified}. "
                "Adding them to the outermost existential block."
            )

            if not self.quantifiers:
                self.quantifiers = [("e", sorted_unquantified)]
            elif self.quantifiers[0][0] == "e":
                # Extend the existing first existential block
                # Tuples are immutable, so we replace the tuple
                existing_vars = self.quantifiers[0][1]
                # Merge and sort unique variables to be clean
                new_vars = sorted(list(set(existing_vars) | unquantified))
                self.quantifiers[0] = ("e", new_vars)
            else:
                # First block is universal, so prepend a new existential block
                self.quantifiers.insert(0, ("e", sorted_unquantified))

        self.validate()

        self.dependency_scheme = dependency_scheme_class(self)

    def validate(self) -> None:
        if self.num_clauses != len(self.clauses):
            raise ValueError(
                f"Number of clauses ({self.num_clauses}) does not match the stored count ({len(self.clauses)})"
            )
        # Count unique variables quantified
        quantified_vars = sum(len(q[1]) for q in self.quantifiers)
        if self.num_vars != quantified_vars:
            # warn instead of raise
            logger.warning(
                f"Number of variables ({self.num_vars}) does not match quantified count ({quantified_vars})"
            )

    @cache
    def get_existential_vars(self) -> List[int]:
        return [
            var for q_type, vars in self.quantifiers if q_type == "e" for var in vars
        ]

    @cache
    def get_universal_vars(self) -> List[int]:
        return [
            var for q_type, vars in self.quantifiers if q_type == "a" for var in vars
        ]

    def __repr__(self) -> str:
        return (
            f"Instance(vars={self.num_vars}, clauses={self.num_clauses}, "
            f"quantifiers={len(self.quantifiers)})"
        )
