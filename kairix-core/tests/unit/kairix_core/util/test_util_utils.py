"""
Test scenarios for util.utils module:

1. Test Claude decorator:
   - Test function decoration
   - Test method decoration
   - Test class method decoration
   - Test decorator transparency
   - Test no behavior modification

2. Test get_or_raise function:
   - Test with existing env variable
   - Test with missing env variable
   - Test KeyError message format
   - Test empty string handling
   - Test whitespace handling

3. Test MessageTurnFormatter initialization:
   - Test with valid names
   - Test with empty names
   - Test with special characters
   - Test name persistence

4. Test format_turn method:
   - Test basic formatting
   - Test tab alignment
   - Test newline handling
   - Test empty messages
   - Test long messages
   - Test special characters

5. Test formatting consistency:
   - Test multiple turns
   - Test formatting preservation
   - Test whitespace handling
   - Test unicode support

6. Test edge cases:
   - Test None as names
   - Test None as messages
   - Test very long names
   - Test multiline messages

7. Test performance:
   - Test formatting speed
   - Test memory usage
   - Test string concatenation
   - Test large messages

8. Test error handling:
   - Test type errors
   - Test encoding errors
   - Test format errors
   - Test boundary conditions
"""