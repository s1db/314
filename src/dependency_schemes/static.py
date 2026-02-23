from abc import abstractmethod
from typing import Set

from src.dependency_schemes.base import DependencyScheme


class StaticDependencyScheme(DependencyScheme):
    """
    Base class for dependency schemes whose graphs are computed once
    at construction time and are immutable during solving.

    Subclasses (Trivial, Standard, Triangle, etc.) implement compute()
    to populate self.dependencies.
    """

    def get_allowed_variables(self, target_variable: int) -> Set[int]:
        """
        For static schemes, the allowed variables are exactly
        the pre-computed dependencies.
        """
        return self.dependencies.get(target_variable, set())

    def update_dependencies(
        self, target_variable: int, used_variables: Set[int]
    ) -> None:
        """Static schemes cannot be mutated at runtime."""
        raise TypeError(f"{type(self).__name__} is static and cannot be mutated.")

    @abstractmethod
    def compute(self) -> None:
        pass
