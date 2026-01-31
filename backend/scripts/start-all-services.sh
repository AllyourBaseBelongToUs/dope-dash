#!/bin/bash
# Ralph Monitoring Dashboard - Microservices Startup Script
# Starts all backend services in the correct order

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Ralph Monitoring Dashboard${NC}"
echo -e "${BLUE}Microservices Startup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Change to backend directory
cd "$(dirname "$0")/.."
BACKEND_DIR=$(pwd)

# Create logs directory if it doesn't exist
mkdir -p logs
mkdir -p .pids

# Check PostgreSQL
echo -e "${YELLOW}Checking PostgreSQL...${NC}"
if pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL is running on port 5432"
else
    echo -e "${RED}✗${NC} PostgreSQL not running on port 5432"
    echo "Please start PostgreSQL first:"
    echo "  - Linux: sudo systemctl start postgresql"
    echo "  - macOS: brew services start postgresql"
    echo "  - Windows: Start PostgreSQL service"
    exit 1
fi

# Check Redis
echo -e "${YELLOW}Checking Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is running on port 6379"
else
    echo -e "${RED}✗${NC} Redis not running on port 6379"
    echo "Please start Redis first:"
    echo "  - Linux: sudo systemctl start redis"
    echo "  - macOS: brew services start redis"
    echo "  - Windows: Start Redis server"
    exit 1
fi

echo ""
echo -e "${BLUE}Starting all services...${NC}"
echo ""

# Function to stop all services on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping all services...${NC}"

    if [ -f .pids/core ]; then
        kill $(cat .pids/core) 2>/dev/null || true
        rm .pids/core
    fi

    if [ -f .pids/websocket ]; then
        kill $(cat .pids/websocket) 2>/dev/null || true
        rm .pids/websocket
    fi

    if [ -f .pids/control ]; then
        kill $(cat .pids/control) 2>/dev/null || true
        rm .pids/control
    fi

    if [ -f .pids/analytics ]; then
        kill $(cat .pids/analytics) 2>/dev/null || true
        rm .pids/analytics
    fi

    echo -e "${GREEN}✓${NC} All services stopped"
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup SIGINT SIGTERM

# Start Core API (port 8000)
echo -e "${YELLOW}Starting Core API (port 8000)...${NC}"
cd "$BACKEND_DIR"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/core-api.log 2>&1 &
CORE_PID=$!
echo $CORE_PID > .pids/core
echo -e "${GREEN}✓${NC} Core API started (PID: $CORE_PID)"
sleep 2

# Start WebSocket Server (port 8001)
echo -e "${YELLOW}Starting WebSocket Server (port 8001)...${NC}"
cd "$BACKEND_DIR"
python server/websocket.py > logs/websocket.log 2>&1 &
WS_PID=$!
echo $WS_PID > .pids/websocket
echo -e "${GREEN}✓${NC} WebSocket Server started (PID: $WS_PID)"
sleep 2

# Start Control API (port 8002)
echo -e "${YELLOW}Starting Control API (port 8002)...${NC}"
cd "$BACKEND_DIR"
python server/control.py > logs/control.log 2>&1 &
CTRL_PID=$!
echo $CTRL_PID > .pids/control
echo -e "${GREEN}✓${NC} Control API started (PID: $CTRL_PID)"
sleep 2

# Start Analytics API (port 8004)
echo -e "${YELLOW}Starting Analytics API (port 8004)...${NC}"
cd "$BACKEND_DIR"
python server/analytics.py > logs/analytics.log 2>&1 &
ANALYTICS_PID=$!
echo $ANALYTICS_PID > .pids/analytics
echo -e "${GREEN}✓${NC} Analytics API started (PID: $ANALYTICS_PID)"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}All services started successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Service URLs:"
echo -e "  Core API:     ${GREEN}http://192.168.206.128:8000${NC}"
echo -e "  WebSocket:     ${GREEN}ws://192.168.206.128:8001/ws${NC}"
echo -e "  Control:       ${GREEN}http://192.168.206.128:8002${NC}"
echo -e "  Dashboard:     ${GREEN}http://192.168.206.128:8003${NC}"
echo -e "  Analytics:     ${GREEN}http://192.168.206.128:8004${NC}"
echo ""
echo "Health Check:"
echo "  Core API:     curl http://localhost:8000/health"
echo "  WebSocket:     curl http://localhost:8001/health"
echo "  Control:       curl http://localhost:8002/health"
echo "  Analytics:     curl http://localhost:8004/health"
echo ""
echo "Logs:"
echo "  Core API:     tail -f logs/core-api.log"
echo "  WebSocket:     tail -f logs/websocket.log"
echo "  Control:       tail -f logs/control.log"
echo "  Analytics:     tail -f logs/analytics.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for services (keep script running)
wait
