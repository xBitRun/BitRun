#!/bin/bash

# BITRUN Development Environment Startup Script
# Usage: ./scripts/start-dev.sh [--no-backend] [--no-frontend]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    BITRUN Development Environment     ${NC}"
echo -e "${BLUE}========================================${NC}"

# Parse arguments
START_BACKEND=true
START_FRONTEND=true

for arg in "$@"; do
    case $arg in
        --no-backend)
            START_BACKEND=false
            ;;
        --no-frontend)
            START_FRONTEND=false
            ;;
    esac
done

# Function to check if a port is in use
check_port() {
    lsof -i:$1 >/dev/null 2>&1
}

# Step 1: Start Docker services
echo -e "\n${YELLOW}[1/4] Starting Docker services (PostgreSQL & Redis)...${NC}"
cd "$PROJECT_ROOT"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker Desktop first.${NC}"
    exit 1
fi

docker compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 3

# Check PostgreSQL
if docker compose exec -T postgres pg_isready -U postgres -d bitrun > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
    docker compose logs postgres
    exit 1
fi

# Check Redis
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
    docker compose logs redis
    exit 1
fi

# Step 2: Run database migrations
echo -e "\n${YELLOW}[2/4] Running database migrations...${NC}"
cd "$PROJECT_ROOT/backend"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

if [ -f "alembic.ini" ]; then
    alembic upgrade head
    echo -e "${GREEN}✓ Database migrations complete${NC}"
else
    echo -e "${YELLOW}⚠ Alembic not initialized yet, skipping migrations${NC}"
fi

# Step 3: Start backend
if [ "$START_BACKEND" = true ]; then
    echo -e "\n${YELLOW}[3/4] Starting backend server...${NC}"
    
    if check_port 8000; then
        echo -e "${YELLOW}Port 8000 is already in use, killing existing process...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    cd "$PROJECT_ROOT/backend"
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Start in background
    nohup python run.py > /tmp/bitrun-backend.log 2>&1 &
    BACKEND_PID=$!
    
    sleep 2
    if kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
        echo -e "  URL: http://localhost:8000"
        echo -e "  Docs: http://localhost:8000/api/docs"
    else
        echo -e "${RED}✗ Backend failed to start${NC}"
        cat /tmp/bitrun-backend.log
        exit 1
    fi
else
    echo -e "\n${YELLOW}[3/4] Skipping backend (--no-backend)${NC}"
fi

# Step 4: Start frontend
if [ "$START_FRONTEND" = true ]; then
    echo -e "\n${YELLOW}[4/4] Starting frontend server...${NC}"
    
    if check_port 3000; then
        echo -e "${YELLOW}Port 3000 is already in use${NC}"
        echo -e "${GREEN}✓ Frontend already running at http://localhost:3000${NC}"
    else
        cd "$PROJECT_ROOT/frontend"
        nohup npm run dev > /tmp/bitrun-frontend.log 2>&1 &
        FRONTEND_PID=$!
        
        sleep 3
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
            echo -e "  URL: http://localhost:3000"
        else
            echo -e "${RED}✗ Frontend failed to start${NC}"
            cat /tmp/bitrun-frontend.log
        fi
    fi
else
    echo -e "\n${YELLOW}[4/4] Skipping frontend (--no-frontend)${NC}"
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   Development environment is ready!   ${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "\nServices:"
echo -e "  - PostgreSQL: localhost:5432"
echo -e "  - Redis:      localhost:6379"
if [ "$START_BACKEND" = true ]; then
    echo -e "  - Backend:    http://localhost:8000"
fi
if [ "$START_FRONTEND" = true ]; then
    echo -e "  - Frontend:   http://localhost:3000"
fi
echo -e "\nTo stop services:"
echo -e "  docker compose down"
echo -e "  lsof -ti:8000 | xargs kill -9"
echo -e "  lsof -ti:3000 | xargs kill -9"
