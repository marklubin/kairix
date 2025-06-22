from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Generic, TypeVar

T_CMD_DATA = TypeVar("T_CMD_DATA")


class KairixCommand(Generic[T_CMD_DATA], ABC):

    @abstractmethod
    def register(self, command: ArgumentParser):
        pass

    @abstractmethod
    def selected(self, options: Namespace) -> T_CMD_DATA:
        pass
