"""Hooks for KP3 events.

Hook execution is now managed via the database (passage_ref_hooks table).
The refs service loads hooks from the DB and executes them via execute_hook_action().
"""

from kp3.hooks.letta_sync import LettaSyncError, update_letta_block

__all__ = ["LettaSyncError", "update_letta_block"]
