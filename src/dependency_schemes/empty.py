from src.dependency_schemes.base import DependencyScheme
from src.instance import Instance


class EmptyDependencyScheme(DependencyScheme):
    def __init__(self, instance: Instance):
        super().__init__(instance)

    def compute(self):
        # does not compute any dependencies.
        # ideal for when the dependencies need to be learned.
        pass
