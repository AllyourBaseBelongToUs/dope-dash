# Spec: Project Setup

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
9. Create docker-compose.yml for local development
10. Create README.md with project overview
11. Create Makefile for common commands
12. Set up pre-commit hooks
13. Install Playwright for E2E testing (playwright install)
14. Create .env.example with all required variables
15. Set up TypeScript configuration for both frontend/backend

## Acceptance Criteria
- [ ] All directories created
- [ ] Virtual environment activates successfully
- [ ] Dependencies install without errors
- [ ] Git commits work
- [ ] Docker compose starts services
- [ ] Playwright browsers installed

## Dependencies
None (first spec)

## End State
Development environment ready for Phase 1 implementation
