# Dope Dash

A real-time multi-agent control center for monitoring and managing AI agent fleets. Built with Next.js, FastAPI, and PostgreSQL.

## Overview

Dope Dash provides:
- Real-time agent monitoring with WebSocket updates
- Agent pool management with state machine control
- Quota tracking and rate limit detection
- Command palette for quick actions
- Portfolio view for multi-project management
- Analytics and reporting capabilities

## Project Structure

```
dope-dash/
├── frontend/          # Next.js application
│   ├── src/
│   │   ├── app/      # App router pages
│   │   ├── components/  # React components
│   │   └── lib/      # Utilities and shared code
│   └── package.json
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── models/   # Database models
│   │   ├── services/ # Business logic
│   │   └── core/     # Configuration
│   └── requirements.txt
├── shared/           # Shared types and utilities
│   ├── types/
│   └── utils/
├── docker-compose.yml
└── Makefile
```

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Docker and Docker Compose
- `python3-venv` package (install with `apt install python3.12-venv` on Ubuntu)

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd dope-dash
```

2. Install dependencies:
```bash
make install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start development servers:
```bash
make dev
```

The frontend will be available at http://localhost:3000
The backend API will be available at http://localhost:8000

### Docker Development

Start all services with Docker:
```bash
make docker-up
```

View logs:
```bash
make docker-logs
```

Stop services:
```bash
make docker-down
```

## Available Commands

```bash
make help           # Show all available commands
make install        # Install all dependencies
make dev            # Start frontend and backend dev servers
make build          # Build frontend for production
make test           # Run all tests
make lint           # Run linters
make format         # Format code
make clean          # Clean build artifacts
```

## Development

### Frontend (Next.js)
- Located in `frontend/`
- Uses App Router
- Styling with Tailwind CSS
- UI components with Radix UI
- State management with Zustand

### Backend (FastAPI)
- Located in `backend/`
- Async/await with SQLAlchemy
- WebSocket support for real-time updates
- PostgreSQL database with Alembic migrations
- Redis for caching and pub/sub

### Testing
- Frontend E2E tests with Playwright
- Backend unit tests with pytest

## License

MIT
