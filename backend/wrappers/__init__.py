"""
Agent integration wrappers for dope-dash.

This package contains wrapper scripts for integrating various AI agents
(Ralph Inferno, Claude Code, Cursor IDE) with the dope-dash event
streaming system.
"""

from .ralph_wrapper import RalphWrapper, main as ralph_main
from .claude_wrapper import ClaudeWrapper, main as claude_main
from .cursor_wrapper import CursorWrapper, main as cursor_main
from .terminal_wrapper import TerminalWrapper, main as terminal_main

__all__ = [
    "RalphWrapper",
    "ralph_main",
    "ClaudeWrapper",
    "claude_main",
    "CursorWrapper",
    "cursor_main",
    "TerminalWrapper",
    "terminal_main",
]
