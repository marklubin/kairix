from cognition_engine.utils import Claude


class TestClaudeDecorator:
    """Test suite for the @Claude decorator"""

    def test_claude_decorator_pass_through(self):
        """Test that @Claude decorator acts as a pass-through"""
        
        @Claude
        def test_function(x, y):
            return x + y
        
        # Function should work normally
        result = test_function(2, 3)
        assert result == 5
        
        # Function name should be preserved
        assert test_function.__name__ == "test_function"

    def test_claude_decorator_on_method(self):
        """Test @Claude decorator on class methods"""
        
        class TestClass:
            @Claude
            def method(self, value):
                return value * 2
        
        obj = TestClass()
        result = obj.method(5)
        assert result == 10

    def test_claude_decorator_async_function(self):
        """Test @Claude decorator on async functions"""
        
        @Claude
        async def async_function(value):
            return value ** 2
        
        # Run the async function
        import asyncio
        result = asyncio.run(async_function(4))
        assert result == 16

    def test_claude_decorator_preserves_docstring(self):
        """Test that @Claude decorator preserves function docstrings"""
        
        @Claude
        def documented_function():
            """This is a test docstring."""
            return "test"
        
        assert documented_function.__doc__ == "This is a test docstring."

    def test_claude_decorator_with_kwargs(self):
        """Test @Claude decorator with functions that use kwargs"""
        
        @Claude
        def kwargs_function(**kwargs):
            return kwargs.get('key', 'default')
        
        assert kwargs_function(key='value') == 'value'
        assert kwargs_function() == 'default'

    def test_claude_decorator_with_return_type_annotations(self):
        """Test @Claude decorator preserves type annotations"""
        
        @Claude
        def annotated_function(x: int, y: int) -> int:
            return x + y
        
        # Function should work normally
        result = annotated_function(10, 20)
        assert result == 30
        
        # Check annotations are preserved
        assert annotated_function.__annotations__ == {'x': int, 'y': int, 'return': int}