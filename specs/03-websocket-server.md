# Spec: WebSocket Server

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
- [ ] WebSocket accepts connections on port 8001
- [ ] Events broadcast to all connected clients
- [ ] Events persist to database
- [ ] Client disconnections handled cleanly
- [ ] Server accessible from Windows host (192.168.206.128:8001)

## Dependencies
02-database-schema

## End State
WebSocket server ready for dashboard connections
