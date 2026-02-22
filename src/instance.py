from typing import List, Tuple, Type
from functools import cache
import logging

from src.dependency_schemes.base import DependencyScheme

logger = logging.getLogger(__name__)


class Instance:
    def __init__(
        self,
        num_vars: int,
        num_clauses: int,
        quantifiers: List[Tuple[str, List[int]]],
        clauses: List[List[int]],
        dependency_scheme_class: Type[DependencyScheme],
    ):
        self.num_vars = num_vars
        self.num_clauses = num_clauses
        self.quantifiers = quantifiers
        self.clauses = clauses

        self.validate()

        # Pass only the data the scheme needs, not the full Instance
        self.dependency_scheme = dependency_scheme_class(
            quantifiers=self.quantifiers,
            num_vars=self.num_vars,
        )

    def validate(self) -> None:
        if self.num_clauses != len(self.clauses):
            raise ValueError(
                f"Number of clauses ({self.num_clauses}) does not match the stored count ({len(self.clauses)})"
            )
        # Count unique variables quantified
        quantified_vars = sum(len(q[1]) for q in self.quantifiers)
        if self.num_vars != quantified_vars:
            raise ValueError(
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
