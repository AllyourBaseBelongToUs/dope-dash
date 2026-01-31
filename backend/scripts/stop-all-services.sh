#!/bin/bash
# Ralph Monitoring Dashboard - Microservices Stop Script
# Stops all backend services gracefully

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Ralph Monitoring Dashboard${NC}"
echo -e "${BLUE}Microservices Stop Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Change to backend directory
cd "$(dirname "$0")/.."

PIDS_DIR=".pids"

if [ ! -d "$PIDS_DIR" ]; then
    echo -e "${YELLOW}No PID directory found. Services may not be running.${NC}"
    exit 0
fi

echo -e "${YELLOW}Stopping all services...${NC}"
echo ""

# Function to stop a service by PID file
stop_service() {
    local name=$1
    local pid_file="$PIDS_DIR/$2"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "Stopping ${name} (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            # Wait up to 5 seconds for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo -e "${GREEN}✓${NC} ${name} stopped"
                    break
                fi
                sleep 0.5
            done
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
                echo -e "${YELLOW}⚠${NC} ${name} force killed"
            fi
        else
            echo -e "${YELLOW}⚠${NC} ${name} (PID $pid) not running"
        fi
        rm -f "$pid_file"
    else
        echo -e "${YELLOW}⚠${NC} No PID file for ${name}"
    fi
}

# Stop services in reverse order
stop_service "Analytics API" "analytics"
stop_service "Control API" "control"
stop_service "WebSocket Server" "websocket"
stop_service "Core API" "core"

echo ""
echo -e "${GREEN}All services stopped.${NC}"
echo ""
