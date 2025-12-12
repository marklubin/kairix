"""General utility functions for the Kairix system.

Provides common utilities including environment variable handling,
decorators, and message formatting.
"""

from os import getenv
from typing import Callable


def Claude(fn: Callable): # type: ignore
    """Decorator that marks methods for Claude to implement or review.
    
    Currently acts as a pass-through decorator that doesn't modify behavior.
    """
    return fn


def get_or_raise(key: str) -> str:
    """Get environment variable or raise error if not found.
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        KeyError: If environment variable is not set
    """
    value = getenv(key)
    if value is None:
        raise KeyError(f"Missing required configuration for: {key}")
    return value




class MessageTurnFormatter:
    """Formatter for conversation turns between user and persona.
    
    Provides consistent formatting for conversational exchanges.
    
    Attributes:
        user_name: Display name for the user
        persona_name: Display name for the AI persona
    """

    def __init__(self, user_name: str, persona_name: str):
        """Initialize the formatter with user and persona names.
        
        Args:
            user_name: Display name for the user
            persona_name: Display name for the AI persona
        """
        self.user_name = user_name
        self.persona_name = persona_name

    def format_turn(self, user_message: str, persona_message: str) -> str:
        """Format a single conversation turn.
        
        Args:
            user_message: The user's message
            persona_message: The persona's response
            
        Returns:
            Formatted conversation turn as a string
        """
        return f"""
        {self.user_name}:\t {user_message}\n
        
        {self.persona_name}:\t {persona_message}

        """
