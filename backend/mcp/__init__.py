"""Dope Dash MCP Server Package.

This package provides MCP (Model Context Protocol) server integration
for AI agents to communicate with the dope-dash dashboard.
"""

from .dope_dash_mcp import main, app, run_server

__all__ = ["main", "app", "run_server"]
