"""Abstract base class for CLI commands in the Kairix system.

Provides a generic interface for implementing command-line commands
using the Command pattern with argparse integration.
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Generic, TypeVar

T_CMD_DATA = TypeVar("T_CMD_DATA")


class KairixCommand(Generic[T_CMD_DATA], ABC):
    """Generic abstract base class for CLI commands.
    
    This class follows the Command pattern and integrates with Python's
    argparse library for command-line argument parsing.
    
    Type Parameters:
        T_CMD_DATA: The type of data returned by the command execution
    """

    @abstractmethod
    def register(self, command: ArgumentParser) -> None:
        """Register command arguments with the argument parser.
        
        This method should add any command-specific arguments to the parser.
        
        Args:
            command: ArgumentParser instance to add arguments to
        """
        pass

    @abstractmethod
    def selected(self, options: Namespace) -> T_CMD_DATA:
        """Execute the command with parsed arguments.
        
        This method is called when the command is selected for execution.
        
        Args:
            options: Parsed command-line arguments
            
        Returns:
            Command-specific data of type T_CMD_DATA
        """
        pass
