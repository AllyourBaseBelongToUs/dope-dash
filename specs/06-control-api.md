# Spec: Control API

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
- [ ] Commands accepted on port 8002
- [ ] Agents receive commands via stdin/unix socket
-. [ ] Command status tracked end-to-end
- [ ] Offline agents queue commands
- [ ] API docs available at /docs

## Dependencies
05-dashboard-mvp

## End State
Dashboard can send commands to active agents
