"""
Test scenarios for types.cognition module:

1. Test StimulusType enum:
   - Verify all enum values are accessible
   - Test string representation of enum values
   - Test enum comparison and equality
   - Verify exhaustive list of stimulus types

2. Test Stimulus dataclass:
   - Test creation with all StimulusType values
   - Test string content handling
   - Test __rich__ method returns proper Panel
   - Test with empty content
   - Test with very long content
   - Test dataclass field access

3. Test Perception dataclass:
   - Test creation with required fields only
   - Test creation with custom confidence value
   - Test confidence default value (1.0)
   - Test confidence validation (should be 0.0-1.0)
   - Test __str__ method formatting
   - Test __rich__ method returns proper Panel
   - Test source field with various values
   - Test multi-line content formatting
"""