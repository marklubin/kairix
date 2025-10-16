"""Tests for MCPJungle startup requirements."""
import ast
import re
from pathlib import Path


def test_mcpjungle_startup_is_mandatory():
    """Test that MCPJungle.start() is called without a try/except that would allow failures."""
    # Read the server.py file
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Check that MCPJungle.start() is called
    assert "mcpjungle_manager.start()" in content or "await mcpjungle_manager.start()" in content, \
        "MCPJungle.start() must be called in server.py"

    # Parse the file to analyze the structure
    tree = ast.parse(content)

    # Find the lifespan function
    lifespan_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan":
            lifespan_func = node
            break

    assert lifespan_func is not None, "lifespan function not found"

    # Find await mcpjungle_manager.start() in the function
    mcpjungle_start_found = False
    mcpjungle_in_try_except = False

    for node in ast.walk(lifespan_func):
        if isinstance(node, ast.Await):
            if isinstance(node.value, ast.Call):
                if hasattr(node.value.func, 'attr') and node.value.func.attr == 'start':
                    if hasattr(node.value.func, 'value') and hasattr(node.value.func.value, 'id'):
                        if node.value.func.value.id == 'mcpjungle_manager':
                            mcpjungle_start_found = True

                            # Check if this call is within a Try node's body (not in except/finally)
                            # We need to walk up the tree to check parent context
                            # For simplicity, we'll use string matching instead

    assert mcpjungle_start_found, "await mcpjungle_manager.start() not found in lifespan function"

    # Check that the MCPJungle start is NOT wrapped in a try/except by looking at the indentation
    # and surrounding context
    lines = content.split('\n')
    mcpjungle_line_num = None
    for i, line in enumerate(lines):
        if 'await mcpjungle_manager.start()' in line:
            mcpjungle_line_num = i
            break

    assert mcpjungle_line_num is not None, "Could not find MCPJungle start line"

    # Check that there's no try: statement immediately before with less indentation
    # and no except: block immediately after
    mcpjungle_indent = len(lines[mcpjungle_line_num]) - len(lines[mcpjungle_line_num].lstrip())

    # Look backwards to find if there's a try statement at the same or less indentation
    has_try_before = False
    for i in range(mcpjungle_line_num - 1, max(0, mcpjungle_line_num - 10), -1):
        line = lines[i].strip()
        if line.startswith('try:'):
            line_indent = len(lines[i]) - len(lines[i].lstrip())
            if line_indent < mcpjungle_line_num:
                has_try_before = True
                break

    # Look forward to check for except blocks that would catch MCPJungle failures
    has_except_after = False
    if has_try_before:
        for i in range(mcpjungle_line_num + 1, min(len(lines), mcpjungle_line_num + 10)):
            line = lines[i].strip()
            # Check if we encounter ModelManager or other code first (meaning no immediate except)
            if 'ModelManager' in line or 'SystemPromptManager' in line:
                break
            if line.startswith('except') and 'mcp' in line.lower():
                has_except_after = True
                break

    assert not (has_try_before and has_except_after), \
        "MCPJungle.start() appears to be wrapped in a try/except that would allow the server to continue on failure"


def test_mcpjungle_initialized_before_model_manager():
    """Test that MCPJungle is started before ModelManager."""
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Find line numbers
    mcpjungle_line = None
    model_manager_line = None

    for i, line in enumerate(content.split('\n')):
        if 'mcpjungle_manager.start()' in line or 'await mcpjungle_manager.start()' in line:
            mcpjungle_line = i
        if 'ModelManager()' in line and 'from' not in line:
            model_manager_line = i

    assert mcpjungle_line is not None, "MCPJungle.start() not found"
    assert model_manager_line is not None, "ModelManager() initialization not found"
    assert mcpjungle_line < model_manager_line, \
        f"MCPJungle (line {mcpjungle_line}) must be initialized before ModelManager (line {model_manager_line})"


def test_mcpjungle_stop_called_in_finally():
    """Test that MCPJungle.stop() is called in the finally block."""
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Check that stop is called
    assert "mcpjungle_manager.stop()" in content or "await mcpjungle_manager.stop()" in content, \
        "mcpjungle_manager.stop() must be called"

    # Check that it's in a finally block (basic string check)
    # Look for the finally block in the lifespan function
    lines = content.split('\n')
    in_finally = False
    stop_in_finally = False

    for line in lines:
        if 'finally:' in line:
            in_finally = True
        elif in_finally and 'mcpjungle_manager.stop()' in line:
            stop_in_finally = True
            break
        elif in_finally and line.strip() and not line.strip().startswith('#') and 'if' not in line.lower():
            # If we hit another code block, we've left the relevant finally
            if line[0] not in [' ', '\t'] and 'stop' not in line:
                in_finally = False

    assert stop_in_finally, "mcpjungle_manager.stop() should be called in the finally block"


def test_mcpjungle_marked_as_required():
    """Test that code comments indicate MCPJungle is required."""
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Find the MCPJungle initialization section (where it's instantiated, not just declared)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'MCPJungleManager(port=' in line:
            # Check surrounding lines for "required" indicator
            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
            assert 'required' in context.lower(), \
                "MCPJungle initialization should be marked as 'required' in comments or code"
            break
    else:
        # If we didn't find the instantiation line, fail
        assert False, "MCPJungleManager(port=...) instantiation not found in server.py"
