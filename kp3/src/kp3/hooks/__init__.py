"""Hooks for KP3 events.

Hook execution is managed via the database (passage_ref_hooks table).
The refs service loads hooks from the DB and executes them via execute_hook_action().

Custom hooks can be implemented by:
1. Adding a new action_type to the passage_ref_hooks table
2. Implementing the handler in refs.py _execute_hook_action()
"""

# Currently no built-in hooks are exported.
# Custom integrations can register hooks in the database.

__all__: list[str] = []
