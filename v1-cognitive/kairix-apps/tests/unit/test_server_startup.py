"""Tests for MCPEz startup requirements."""
import ast
import re
from pathlib import Path


def test_mcpez_startup_is_mandatory():
    """Test that MCPEz.start() is called without a try/except that would allow failures."""
    # Read the server.py file
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Check that MCPEz.start() is called
    assert "mcpez_manager.start()" in content or "await mcpez_manager.start()" in content, \
        "MCPEz.start() must be called in server.py"

    # Parse the file to analyze the structure
    tree = ast.parse(content)

    # Find the lifespan function
    lifespan_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan":
            lifespan_func = node
            break

    assert lifespan_func is not None, "lifespan function not found"

    # Find await mcpez_manager.start() in the function
    mcpez_start_found = False
    mcpez_in_try_except = False

    for node in ast.walk(lifespan_func):
        if isinstance(node, ast.Await):
            if isinstance(node.value, ast.Call):
                if hasattr(node.value.func, 'attr') and node.value.func.attr == 'start':
                    if hasattr(node.value.func, 'value') and hasattr(node.value.func.value, 'id'):
                        if node.value.func.value.id == 'mcpez_manager':
                            mcpez_start_found = True

                            # Check if this call is within a Try node's body (not in except/finally)
                            # We need to walk up the tree to check parent context
                            # For simplicity, we'll use string matching instead

    assert mcpez_start_found, "await mcpez_manager.start() not found in lifespan function"

    # Check that the MCPEz start is NOT wrapped in a try/except by looking at the indentation
    # and surrounding context
    lines = content.split('\n')
    mcpez_line_num = None
    for i, line in enumerate(lines):
        if 'await mcpez_manager.start()' in line:
            mcpez_line_num = i
            break

    assert mcpez_line_num is not None, "Could not find MCPEz start line"

    # Check that there's no try: statement immediately before with less indentation
    # and no except: block immediately after
    mcpez_indent = len(lines[mcpez_line_num]) - len(lines[mcpez_line_num].lstrip())

    # Look backwards to find if there's a try statement at the same or less indentation
    has_try_before = False
    for i in range(mcpez_line_num - 1, max(0, mcpez_line_num - 10), -1):
        line = lines[i].strip()
        if line.startswith('try:'):
            line_indent = len(lines[i]) - len(lines[i].lstrip())
            if line_indent < mcpez_line_num:
                has_try_before = True
                break

    # Look forward to check for except blocks that would catch MCPEz failures
    has_except_after = False
    if has_try_before:
        for i in range(mcpez_line_num + 1, min(len(lines), mcpez_line_num + 10)):
            line = lines[i].strip()
            # Check if we encounter ModelManager or other code first (meaning no immediate except)
            if 'ModelManager' in line or 'SystemPromptManager' in line:
                break
            if line.startswith('except') and 'mcp' in line.lower():
                has_except_after = True
                break

    assert not (has_try_before and has_except_after), \
        "MCPEz.start() appears to be wrapped in a try/except that would allow the server to continue on failure"


def test_mcpez_initialized_before_model_manager():
    """Test that MCPEz is started before ModelManager."""
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Find line numbers
    mcpez_line = None
    model_manager_line = None

    for i, line in enumerate(content.split('\n')):
        if 'mcpez_manager.start()' in line or 'await mcpez_manager.start()' in line:
            mcpez_line = i
        if 'ModelManager()' in line and 'from' not in line:
            model_manager_line = i

    assert mcpez_line is not None, "MCPEz.start() not found"
    assert model_manager_line is not None, "ModelManager() initialization not found"
    assert mcpez_line < model_manager_line, \
        f"MCPEz (line {mcpez_line}) must be initialized before ModelManager (line {model_manager_line})"


def test_mcpez_stop_called_in_finally():
    """Test that MCPEz.stop() is called in the finally block."""
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Check that stop is called
    assert "mcpez_manager.stop()" in content or "await mcpez_manager.stop()" in content, \
        "mcpez_manager.stop() must be called"

    # Check that it's in a finally block (basic string check)
    # Look for the finally block in the lifespan function
    lines = content.split('\n')
    in_finally = False
    stop_in_finally = False

    for line in lines:
        if 'finally:' in line:
            in_finally = True
        elif in_finally and 'mcpez_manager.stop()' in line:
            stop_in_finally = True
            break
        elif in_finally and line.strip() and not line.strip().startswith('#') and 'if' not in line.lower():
            # If we hit another code block, we've left the relevant finally
            if line[0] not in [' ', '\t'] and 'stop' not in line:
                in_finally = False

    assert stop_in_finally, "mcpez_manager.stop() should be called in the finally block"


def test_mcpez_marked_as_required():
    """Test that code comments indicate MCPEz is required."""
    server_file = Path(__file__).parent.parent.parent / "src" / "kairix_apps" / "server.py"
    content = server_file.read_text()

    # Find the MCPEz initialization section (where it's instantiated, not just declared)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'MCPEzManager(port=' in line:
            # Check surrounding lines for "required" indicator
            context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
            assert 'required' in context.lower(), \
                "MCPEz initialization should be marked as 'required' in comments or code"
            break
    else:
        # If we didn't find the instantiation line, fail
        assert False, "MCPEzManager(port=...) instantiation not found in server.py"
