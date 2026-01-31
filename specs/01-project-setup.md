# Spec: Project Setup

## Status: ✅ COMPLETED

## Objective
Initialize dope-dash project structure with development environment

## Tasks
1. Create project root directory: ~/projects/dope-dash
2. Set up Python virtual environment: python3 -m venv venv
3. Create frontend directory: frontend/ (Next.js app)
4. Create backend directory: backend/ (FastAPI app)
5. Create shared directory: shared/ (types, utilities)
6. Initialize git repository with proper .gitignore
7. Set up package.json for frontend with dependencies
8. Set up requirements.txt for backend with dependencies
9. Create README.md with project overview
10. Create Makefile for common commands
11. Set up pre-commit hooks
12. Install Playwright for E2E testing (playwright install)
13. Create .env.example with all required variables
14. Set up TypeScript configuration for both frontend/backend

## Acceptance Criteria
- [x] All directories created
- [x] Virtual environment activates successfully
- [x] Dependencies install without errors
- [x] Git commits work
- [x] Backend services start (ports 8000-8004)
- [x] Frontend starts (port 8003)
- [x] Playwright browsers installed

## Implementation Notes
- **Service Startup:** All services start with direct uvicorn commands (NO DOCKER)
- **Port 8000:** Core API with query, reports, retention, portfolio, projects endpoints
- **Port 8001:** WebSocket Server for real-time events
- **Port 8002:** Control API for agent commands
- **Port 8003:** Next.js dashboard frontend
- **Port 8004:** Analytics API for metrics and trends
- **PostgreSQL:** Port 5432 with database connection pooling
- **Redis:** Port 6379 for caching

## Dependencies
None (first spec)

## End State
Development environment ready for Phase 1 implementation ✅
