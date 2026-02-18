from src.dependency_schemes.base import DependencyScheme
from src.instance import Instance


class EmptyDependencyScheme(DependencyScheme):
    """
    A dependency scheme with no dependencies other than the default quantifier-based ones
    (if the base class enforces strict ordering, which it does via verification).
    The compute method creates no additional edges.
    """

    def __init__(self, instance: Instance):
        super().__init__(instance)

    def compute(self):
        # No extra dependencies to add
        pass
