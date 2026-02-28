"""Dope Dash MCP Server - AI Agent Feedback Integration.

This MCP server provides a tool for AI agents to request feedback
from users via the dope-dash dashboard.

Architecture:
    Claude (AI Agent) --> MCP Tool --> WebSocket --> dope-dash Backend
                                                      |
                                                      v
                                              Dashboard Frontend
                                                      |
                                                      v
                                              User submits feedback
                                                      |
                                                      v
                                              Response via WebSocket

Usage in Claude Code:
    The AI agent calls `interactive_feedback` tool when it needs user input.
    The request is sent to dope-dash, displayed in the dashboard, and the
    user's response is returned to the agent.
"""

import asyncio
import json
import logging
import os
import socket
import uuid
from typing import Any, Optional

import websockets
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create MCP server instance
app = Server("dope-dash-feedback")

# Default timeout for feedback requests (seconds)
DEFAULT_TIMEOUT = int(os.environ.get("DOPE_DASH_FEEDBACK_TIMEOUT", "300"))


# ============== Network Detection ==============

def get_tailscale_ip() -> Optional[str]:
    """Get this machine's Tailscale IP if connected.

    Tailscale uses CGNAT range 100.64.0.0/10 (100.64.x.x - 100.127.x.x)
    """
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            # Check if IP is in Tailscale's CGNAT range (100.64.0.0/10)
            parts = ip.split(".")
            if len(parts) == 4 and parts[0] == "100":
                second = int(parts[1])
                if 64 <= second <= 127:
                    logger.info(f"[MCP] Detected Tailscale IP: {ip}")
                    return ip
    except Exception as e:
        logger.debug(f"[MCP] Could not detect Tailscale IP: {e}")
    return None


def get_best_ws_url() -> str:
    """Determine the best WebSocket URL for connecting to dope-dash.

    Priority:
    1. DOPE_DASH_WS_URL environment variable (explicit override)
    2. Tailscale IP (if connected)
    3. localhost (fallback for local dev)
    """
    # Check for explicit override
    env_url = os.environ.get("DOPE_DASH_WS_URL")
    if env_url:
        logger.info(f"[MCP] Using env var WebSocket URL: {env_url}")
        return env_url

    # Check for Tailscale
    ts_ip = get_tailscale_ip()
    if ts_ip:
        url = f"ws://{ts_ip}:8005/feedback/ws/mcp"
        logger.info(f"[MCP] Using Tailscale WebSocket URL: {url}")
        return url

    # Fallback to localhost (step-5 port spacing: WebSocket on 8005)
    url = "ws://localhost:8005/feedback/ws/mcp"
    logger.info(f"[MCP] Using localhost WebSocket URL: {url}")
    return url


# WebSocket URL for dope-dash feedback endpoint
DOPE_DASH_WS_URL = get_best_ws_url()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="interactive_feedback",
            description=(
                "Request interactive feedback from the user via the dope-dash dashboard. "
                "Use this when you need clarification, approval, or user input to proceed. "
                "The request will be displayed in the dashboard and the user can respond "
                "with text feedback or select from provided options."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            "The message to display to the user. "
                            "Be clear about what you need from them."
                        ),
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional list of predefined options for the user to choose from. "
                            "If provided, the user will see buttons instead of a text field."
                        ),
                    },
                    "timeout": {
                        "type": "integer",
                        "description": (
                            "Timeout in seconds to wait for user response. "
                            f"Default: {DEFAULT_TIMEOUT}"
                        ),
                        "default": DEFAULT_TIMEOUT,
                    },
                    "project_directory": {
                        "type": "string",
                        "description": (
                            "Optional project directory context for the feedback request."
                        ),
                    },
                },
                "required": ["message"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls from AI agents."""
    if name != "interactive_feedback":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    message = arguments.get("message", "")
    options = arguments.get("options")
    timeout = arguments.get("timeout", DEFAULT_TIMEOUT)
    project_directory = arguments.get("project_directory")

    request_id = str(uuid.uuid4())

    logger.info(f"[MCP] Feedback request {request_id}: {message[:50]}...")

    try:
        # Connect to dope-dash WebSocket
        async with websockets.connect(DOPE_DASH_WS_URL) as ws:
            # Send feedback request
            request_payload = {
                "type": "feedback_request",
                "request_id": request_id,
                "message": message,
                "options": options,
                "timeout": timeout,
                "project_directory": project_directory,
            }

            await ws.send(json.dumps(request_payload))
            logger.info(f"[MCP] Sent request {request_id} to dope-dash")

            # Wait for response with timeout
            try:
                response_raw = await asyncio.wait_for(
                    ws.recv(),
                    timeout=timeout + 10  # Extra buffer for network latency
                )
                response = json.loads(response_raw)

                logger.info(f"[MCP] Received response for {request_id}")

                if response.get("timed_out"):
                    return [TextContent(
                        type="text",
                        text="The feedback request timed out. The user did not respond in time."
                    )]

                feedback = response.get("feedback", "")

                if not feedback:
                    return [TextContent(
                        type="text",
                        text="The user submitted an empty response."
                    )]

                return [TextContent(
                    type="text",
                    text=f"User feedback: {feedback}"
                )]

            except asyncio.TimeoutError:
                logger.warning(f"[MCP] Request {request_id} timed out waiting for response")
                return [TextContent(
                    type="text",
                    text="The feedback request timed out. The user did not respond in time."
                )]

    except websockets.exceptions.ConnectionRefusedError:
        logger.error("[MCP] Could not connect to dope-dash WebSocket")
        return [TextContent(
            type="text",
            text=(
                "Could not connect to dope-dash dashboard. "
                "Please ensure the dope-dash backend is running and accessible."
            )
        )]

    except Exception as e:
        logger.error(f"[MCP] Error during feedback request: {e}")
        return [TextContent(
            type="text",
            text=f"An error occurred while requesting feedback: {str(e)}"
        )]


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the MCP server."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
