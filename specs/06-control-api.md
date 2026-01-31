# Spec: Control API

## Status: ✅ COMPLETED

## Objective
Create REST API for sending commands to agents

## Tasks
1. Create backend/server/control.py (FastAPI, port 8002)
2. Implement POST /api/control/:session_id/command endpoint
3. Support commands: pause, resume, skip, stop
4. Create command queue per session
5. Implement command acknowledgment system
6. Add GET /api/control/:session_id/status endpoint
7. Create command result tracking
8. Handle offline agents (queue commands)
9. Add authentication headers (X-Session-Token)
10. Document API with OpenAPI/Swagger

## Acceptance Criteria
- [x] Commands accepted on port 8002
- [x] Agents receive commands via stdin/unix socket
- [x] Command status tracked end-to-end
- [x] Offline agents queue commands
- [x] API docs available at /docs

## Implementation Notes
- **Service Startup:** `uvicorn backend.server.control:app --host 0.0.0.0 --port 8002`
- **Commands Supported:** pause, resume, skip, stop
- **API Docs:** Swagger UI available at /docs endpoint
- **NO DOCKER:** Direct uvicorn service startup

## Dependencies
05-dashboard-mvp

## End State
Dashboard can send commands to active agents ✅
