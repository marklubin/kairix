"""
Test scenarios for agent_prompts module:

1. Test QUERY_INSTRUCTIONS:
   - Test instruction format
   - Test instruction completeness
   - Test placeholder handling
   - Test multi-line structure

2. Test INSIGHT_EXTRACTION_INSTRUCTIONS:
   - Test extraction guidelines
   - Test formatting requirements
   - Test example handling
   - Test instruction clarity

3. Test CONVERSATIONALIST_INSTRUCTIONS:
   - Test comprehensive instructions
   - Test tone guidelines
   - Test response formatting
   - Test context awareness rules

4. Test perception list formatting:
   - Test _perception_list function
   - Test empty perception list
   - Test single perception
   - Test multiple perceptions
   - Test confidence display
   - Test source attribution

5. Test conversationalist message creation:
   - Test instruction generation
   - Test perception integration
   - Test user message handling
   - Test template substitution

6. Test prompt composition:
   - Test complete prompt assembly
   - Test variable substitution
   - Test escaping special characters
   - Test prompt length

7. Test instruction customization:
   - Test persona name substitution
   - Test perception formatting
   - Test dynamic content
   - Test conditional sections

8. Test edge cases:
   - Test very long perceptions
   - Test special characters in content
   - Test empty user messages
   - Test missing perceptions

9. Test consistency:
   - Test instruction style consistency
   - Test terminology consistency
   - Test format consistency
   - Test tone consistency

10. Test prompt effectiveness:
    - Test clarity of instructions
    - Test completeness of guidelines
    - Test ambiguity prevention
    - Test example quality
"""