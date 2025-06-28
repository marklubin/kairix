"""Wrapper to adapt Kairix personas to the PersonaProtocol interface.

This keeps the core persona implementation completely decoupled from
the API adapter layer.
"""

from typing import AsyncIterator, cast
from kairix_core.cognition.persona import Persona
from kairix_core.types.cognition import Stimulus, StimulusType


class PersonaWrapper:
    """Wraps a Kairix Persona to match the PersonaProtocol interface."""
    
    def __init__(self, persona: Persona):
        self.persona = persona
    
    def respond(self, message: str, context: dict) -> AsyncIterator[str]:
        """Adapt persona.react() to the protocol interface."""
        # Create stimulus from message and context
        # Store context in the content as formatted string since Stimulus doesn't have metadata
        if context.get("conversation_history"):
            full_content = f"{context['conversation_history']}\nUser: {message}"
        else:
            full_content = message
            
        stimulus = Stimulus(
            content=full_content,
            type=StimulusType.user_message
        )
        
        # Forward to the actual persona
        # Cast is needed because mypy doesn't understand async generators well
        return cast(AsyncIterator[str], self.persona.react(stimulus))


class PersonaFactory:
    """Factory for creating wrapped personas with specific configurations."""
    
    def __init__(self):
        self._builders = {}
    
    def register(self, name: str, builder):
        """Register a persona builder function."""
        self._builders[name] = builder
    
    def create(self, name: str) -> PersonaWrapper:
        """Create a wrapped persona by name."""
        if name not in self._builders:
            raise ValueError(f"No persona registered with name: {name}")
        
        persona = self._builders[name]()
        return PersonaWrapper(persona)
    
    def list_available(self) -> list[str]:
        """List all registered persona names."""
        return list(self._builders.keys())