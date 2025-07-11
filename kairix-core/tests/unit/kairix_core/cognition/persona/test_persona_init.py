"""
Test scenarios for cognition.persona base class:

1. Test Persona ABC:
   - Verify it cannot be instantiated directly
   - Test that subclasses must implement react method
   - Test react method signature requirements
   - Test async iterator return type

2. Test Persona subclass implementation:
   - Create mock persona subclass
   - Test async react method
   - Test stimulus input handling
   - Test async iteration over response
   - Test empty response handling
   - Test streaming response tokens

3. Test __all__ exports:
   - Verify Persona is exported
   - Verify ConversationalPersona is exported
   - Check import structure

4. Test error handling:
   - Test reaction to invalid stimulus
   - Test exception propagation
   - Test cleanup on error
"""