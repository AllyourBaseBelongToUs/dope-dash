"""Feedback API for MCP integration.

This module provides endpoints for AI agents to request feedback
from users via the dope-dash dashboard.

Architecture:
    MCP Server (dope-dash-mcp) --> WebSocket --> dope-dash Backend
                                                      |
                                                      v
                                              Dashboard Frontend
                                                      |
                                                      v
                                              User submits feedback
                                                      |
                                                      v
                                              Response via WebSocket
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


# ============== Models ==============

class FeedbackRequest(BaseModel):
    """Request from MCP server for user feedback."""
    request_id: str
    message: str
    options: Optional[list[str]] = None
    timeout: int = 300
    project_directory: Optional[str] = None


class FeedbackSubmission(BaseModel):
    """User's feedback submission."""
    feedback: str
    images: Optional[list[dict]] = None
    settings: Optional[dict] = None


class FeedbackResponse(BaseModel):
    """Response sent back to MCP server."""
    request_id: str
    feedback: str
    images: Optional[list[dict]] = None
    settings: Optional[dict] = None
    submitted_at: str
    timed_out: bool = False


# ============== State Management with Thread Safety ==============

# Lock for thread-safe access to shared state
_state_lock = asyncio.Lock()

# Pending feedback requests waiting for user response
# Key: request_id, Value: asyncio.Future that will be resolved when user responds
pending_requests: dict[str, asyncio.Future] = {}

# Connected dashboard clients for broadcasting feedback requests
dashboard_clients: set[WebSocket] = set()


async def add_pending_request(request_id: str, future: asyncio.Future) -> None:
    """Thread-safe add to pending requests."""
    async with _state_lock:
        pending_requests[request_id] = future


async def remove_pending_request(request_id: str) -> None:
    """Thread-safe remove from pending requests."""
    async with _state_lock:
        pending_requests.pop(request_id, None)


async def get_pending_request(request_id: str) -> Optional[asyncio.Future]:
    """Thread-safe get from pending requests."""
    async with _state_lock:
        return pending_requests.get(request_id)


async def add_dashboard_client(ws: WebSocket) -> None:
    """Thread-safe add dashboard client."""
    async with _state_lock:
        dashboard_clients.add(ws)


async def remove_dashboard_client(ws: WebSocket) -> None:
    """Thread-safe remove dashboard client."""
    async with _state_lock:
        dashboard_clients.discard(ws)


async def get_dashboard_clients() -> set[WebSocket]:
    """Thread-safe get all dashboard clients (copy)."""
    async with _state_lock:
        return dashboard_clients.copy()


# ============== Validation Helpers ==============

async def safe_receive_json(websocket: WebSocket) -> Optional[dict]:
    """Safely receive and parse JSON from WebSocket.

    Returns None on error and sends error response to client.
    """
    try:
        data = await websocket.receive_json()
        if not isinstance(data, dict):
            await websocket.send_json({
                "type": "error",
                "message": "Invalid message format: expected object"
            })
            return None
        return data
    except json.JSONDecodeError:
        await websocket.send_json({
            "type": "error",
            "message": "Invalid JSON"
        })
        return None
    except Exception as e:
        logger.error(f"WebSocket receive error: {e}")
        return None


def parse_feedback_request(data: dict) -> Optional[FeedbackRequest]:
    """Parse and validate feedback request.

    Returns None on validation error.
    """
    try:
        return FeedbackRequest(**data)
    except ValidationError as e:
        logger.warning(f"Invalid feedback request: {e}")
        return None


# ============== WebSocket for Dashboard ==============

@router.websocket("/ws")
async def feedback_dashboard_websocket(websocket: WebSocket):
    """WebSocket endpoint for dashboard to receive feedback requests.

    Dashboard connects here to receive real-time feedback requests
    from AI agents via the MCP server.
    """
    await websocket.accept()
    await add_dashboard_client(websocket)
    client_id = str(uuid.uuid4())[:8]

    logger.info(f"Dashboard client {client_id} connected to feedback WebSocket")

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            # Keep connection alive, handle any client messages
            data = await safe_receive_json(websocket)
            if data is None:
                continue  # Error already sent to client

            # Handle heartbeat
            if data.get("type") == "heartbeat":
                await websocket.send_json({
                    "type": "heartbeat_response",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"Dashboard client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        await remove_dashboard_client(websocket)


# ============== WebSocket for MCP Server ==============

@router.websocket("/ws/mcp")
async def feedback_mcp_websocket(websocket: WebSocket):
    """WebSocket endpoint for MCP server to request feedback.

    The dope-dash-mcp server connects here when Claude calls
    the interactive_feedback tool.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())[:8]

    logger.info(f"MCP client {connection_id} connected to feedback WebSocket")

    try:
        while True:
            data = await safe_receive_json(websocket)
            if data is None:
                continue  # Error already sent to client

            if data.get("type") == "feedback_request":
                request = parse_feedback_request(data)
                if request is None:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid feedback request format"
                    })
                    continue

                response = await handle_feedback_request(request)
                await websocket.send_json(response.dict())

            elif data.get("type") == "heartbeat":
                await websocket.send_json({
                    "type": "heartbeat_response",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"MCP client {connection_id} disconnected")
    except Exception as e:
        logger.error(f"MCP WebSocket error: {e}")


async def handle_feedback_request(request: FeedbackRequest) -> FeedbackResponse:
    """Handle a feedback request from MCP server.

    1. Store the request as a pending Future
    2. Broadcast to all connected dashboard clients
    3. Wait for user response (with timeout)
    4. Return the response to MCP server
    """
    # Create a Future that will be resolved when user responds
    future: asyncio.Future = asyncio.Future()
    await add_pending_request(request.request_id, future)

    logger.info(f"Feedback request {request.request_id}: {request.message[:50]}...")

    try:
        # Broadcast to all connected dashboards
        broadcast_message = {
            "type": "feedback_request",
            "request_id": request.request_id,
            "message": request.message,
            "options": request.options,
            "timeout": request.timeout,
            "project_directory": request.project_directory,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Send to all connected dashboard clients (thread-safe copy)
        clients = await get_dashboard_clients()
        disconnected = set()
        for client in clients:
            try:
                await client.send_json(broadcast_message)
            except Exception:
                disconnected.add(client)

        # Clean up disconnected clients
        for client in disconnected:
            await remove_dashboard_client(client)

        if not await get_dashboard_clients():
            logger.warning(f"No dashboard clients connected for request {request.request_id}")
            return FeedbackResponse(
                request_id=request.request_id,
                feedback="",
                timed_out=True,
                submitted_at=datetime.utcnow().isoformat()
            )

        # Wait for user response with timeout
        result = await asyncio.wait_for(future, timeout=request.timeout)

        return FeedbackResponse(
            request_id=request.request_id,
            feedback=result.get("feedback", ""),
            images=result.get("images"),
            settings=result.get("settings"),
            submitted_at=datetime.utcnow().isoformat()
        )

    except asyncio.TimeoutError:
        logger.info(f"Feedback request {request.request_id} timed out")
        return FeedbackResponse(
            request_id=request.request_id,
            feedback="",
            timed_out=True,
            submitted_at=datetime.utcnow().isoformat()
        )

    finally:
        # Clean up
        await remove_pending_request(request.request_id)


# ============== REST Endpoint for User Submission ==============

@router.post("/{request_id}/submit")
async def submit_feedback(request_id: str, submission: FeedbackSubmission):
    """Submit user feedback for a pending request.

    Called by the dashboard frontend when user submits their feedback.
    """
    future = await get_pending_request(request_id)

    if future is None:
        raise HTTPException(status_code=404, detail="Request not found or expired")

    if future.done():
        raise HTTPException(status_code=400, detail="Request already completed")

    # Resolve the Future with the user's feedback
    future.set_result(submission.dict())

    logger.info(f"Feedback submitted for request {request_id}")

    return {"status": "ok", "request_id": request_id}


@router.get("/pending")
async def get_pending_requests():
    """Get all pending feedback requests.

    Useful for dashboard to sync state on reconnect.
    """
    return {
        "pending_count": len(pending_requests),
        "request_ids": list(pending_requests.keys())
    }


@router.get("/health")
async def feedback_health():
    """Health check for feedback service."""
    return {
        "status": "healthy",
        "pending_requests": len(pending_requests),
        "connected_dashboards": len(dashboard_clients)
    }
