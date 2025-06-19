from typing import Callable


def Claude(fn: Callable): # type: ignore
    """Decorator that marks methods for Claude to implement or review.
    
    Currently acts as a pass-through decorator that doesn't modify behavior.
    """
    return fn




class MessageTurnFormatter:

    def __init__(self, user_name, persona_name):
        self.user_name = user_name
        self.persona_name = persona_name

    def format_turn(self, user_message, persona_message):
        return f"""
        {self.user_name}:\t {user_message}\n
        
        {self.persona_name}:\t {persona_message}

        """
