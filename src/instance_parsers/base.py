from abc import ABC, abstractmethod
from typing import Union
from pathlib import Path
from src.instance import Instance


class InstanceParser(ABC):
    @staticmethod
    @abstractmethod
    def from_file(path: Union[str, Path]) -> Instance:
        pass
