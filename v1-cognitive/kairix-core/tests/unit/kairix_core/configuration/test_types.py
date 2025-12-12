"""
Test scenarios for configuration.types module:

1. Test ProviderName literal:
   - Verify all expected provider names are valid
   - Test invalid provider names raise appropriate errors
   - Ensure type checking works correctly

2. Test AgentConfig model:
   - Test creation with all fields
   - Test creation with only required fields (defaults applied)
   - Test validation of temperature range (0.0-2.0)
   - Test validation of max_tokens (positive integer)
   - Test model serialization/deserialization
   - Test invalid field types raise ValidationError

3. Test AgentConfigurationSet model:
   - Test creation with valid data
   - Test name uniqueness requirements
   - Test default_provider validation against ProviderName
   - Test agent_configs dictionary structure
   - Test serialization to/from JSON
   - Test deep copying of configurations
   - Test invalid provider name in default_provider
"""