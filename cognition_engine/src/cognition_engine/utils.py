from typing import Callable


def Claude(fn: Callable):
    """Decorator that marks methods for Claude to implement or review.
    
    Currently acts as a pass-through decorator that doesn't modify behavior.
    """
    return fn