# Spec: WebSocket Server

## Status: ✅ COMPLETED

## Objective
Create FastAPI WebSocket server for real-time event broadcasting

## Tasks
1. Create backend/server/websocket.py with FastAPI app
2. Implement WebSocket endpoint /ws (port 8001)
3. Create connection manager class for active connections
4. Implement event broadcasting to all connected clients
5. Create event ingestion endpoint POST /api/events
6. Store events to PostgreSQL on receipt
7. Broadcast events to WebSocket clients in real-time
8. Handle connection/disconnection gracefully
9. Add ping/pong for connection health
10. Bind to 0.0.0.0:8001 for external access

## Acceptance Criteria
- [x] WebSocket accepts connections on port 8001
- [x] Events broadcast to all connected clients
- [x] Events persist to database
- [x] Client disconnections handled cleanly
- [x] Server accessible from Windows host (192.168.206.128:8001)

## Implementation Notes
- **Service Startup:** `uvicorn backend.server.websocket:app --host 0.0.0.0 --port 8001`
- **Auto-Retry:** Client auto-reconnects every 3 minutes if connection drops
- **Manual Retry:** Dashboard shows retry button when in polling mode
- **NO DOCKER:** Direct uvicorn service startup
- **Health Check:** Ping/pong mechanism for connection monitoring

## Dependencies
02-database-schema

## End State
WebSocket server ready for dashboard connections ✅
