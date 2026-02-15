#!/bin/bash

# BITRUN Development Environment Startup Script
# Usage:
#   ./scripts/start-dev.sh                  Start all services
#   ./scripts/start-dev.sh --logs           Start services and tail logs
#   ./scripts/start-dev.sh --no-backend     Skip backend
#   ./scripts/start-dev.sh --no-frontend    Skip frontend
#   ./scripts/start-dev.sh --stop           Stop all services
#   ./scripts/start-dev.sh --restart        Restart all services
#   ./scripts/start-dev.sh --tail           Tail logs (services must be running)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==================== Helper Functions ====================

# Check if a port is in use
check_port() {
    lsof -i:$1 >/dev/null 2>&1
}

# Kill process on a given port
kill_port() {
    if check_port "$1"; then
        echo -e "${YELLOW}Killing process on port $1...${NC}"
        lsof -ti:"$1" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# Venv Python path (set by ensure_backend_venv, used by all subsequent Python calls)
VENV_PYTHON=""

# Ensure Python venv and dependencies are ready
ensure_backend_venv() {
    cd "$PROJECT_ROOT/backend"

    # Check python3 availability
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}python3 is not installed. Please install Python 3.10+ first.${NC}"
        exit 1
    fi

    # Auto-create venv if missing
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Use absolute path to venv python — never rely on PATH/activate
    VENV_PYTHON="$PROJECT_ROOT/backend/venv/bin/python3"

    # Install/update dependencies only when requirements.txt changes
    local req_hash
    req_hash=$(md5 -q requirements.txt 2>/dev/null || md5sum requirements.txt | cut -d' ' -f1)
    if [ ! -f "venv/.deps-hash" ] || [ "$req_hash" != "$(cat venv/.deps-hash)" ]; then
        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        "$VENV_PYTHON" -m pip install -q -r requirements.txt
        echo "$req_hash" > venv/.deps-hash
    fi

    # Auto-create .env from template if missing
    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✓ Created backend/.env (update API keys as needed)${NC}"
    fi

    echo -e "${GREEN}✓ Python environment ready${NC}"
}

# ==================== Stop ====================

stop_services() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    Stopping BITRUN Dev Services        ${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Stop local backend
    if check_port 8000; then
        echo -e "${YELLOW}Stopping backend (port 8000)...${NC}"
        lsof -ti:8000 | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✓ Backend stopped${NC}"
    else
        echo -e "${GREEN}✓ Backend not running${NC}"
    fi

    # Stop local frontend
    if check_port 3000; then
        echo -e "${YELLOW}Stopping frontend (port 3000)...${NC}"
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    else
        echo -e "${GREEN}✓ Frontend not running${NC}"
    fi

    # Stop Docker infrastructure
    cd "$PROJECT_ROOT"
    if command -v docker &> /dev/null && docker compose ps --status running 2>/dev/null | grep -q "bitrun"; then
        echo -e "${YELLOW}Stopping Docker services...${NC}"
        docker compose down
        echo -e "${GREEN}✓ Docker services stopped${NC}"
    else
        echo -e "${GREEN}✓ Docker services not running${NC}"
    fi

    echo -e "\n${GREEN}All services stopped.${NC}"
}

# ==================== Tail Logs ====================

tail_logs() {
    local LOG_FILES=()

    # Check which log files exist
    if [ -f /tmp/bitrun-backend.log ]; then
        LOG_FILES+=("/tmp/bitrun-backend.log")
    fi
    if [ -f /tmp/bitrun-frontend.log ]; then
        LOG_FILES+=("/tmp/bitrun-frontend.log")
    fi

    if [ ${#LOG_FILES[@]} -eq 0 ]; then
        echo -e "${RED}No log files found. Start services first: ./scripts/start-dev.sh${NC}"
        exit 1
    fi

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    Following logs (Ctrl+C to exit)    ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "${YELLOW}Files:${NC}"
    for f in "${LOG_FILES[@]}"; do
        echo -e "  - $f"
    done
    echo ""

    # Use tail -f with multiple files
    tail -f "${LOG_FILES[@]}"
}

# ==================== Start ====================

start_services() {
    local START_BACKEND=true
    local START_FRONTEND=true

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

    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    BITRUN Development Environment      ${NC}"
    echo -e "${BLUE}========================================${NC}"

    # Step 1: Start Docker infrastructure (postgres & redis only)
    echo -e "\n${YELLOW}[1/4] Starting Docker services (PostgreSQL & Redis)...${NC}"
    cd "$PROJECT_ROOT"

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed. Please install Docker Desktop first.${NC}"
        exit 1
    fi

    docker compose up -d postgres redis

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

    # Step 2: Setup backend environment & run database migrations
    echo -e "\n${YELLOW}[2/4] Setting up backend & running migrations...${NC}"
    ensure_backend_venv

    if [ -f "alembic.ini" ]; then
        if "$VENV_PYTHON" -m alembic upgrade head 2>&1; then
            echo -e "${GREEN}✓ Database migrations complete${NC}"
        else
            echo -e "${YELLOW}⚠ Migration failed, attempting stamp head to recover...${NC}"
            if "$VENV_PYTHON" -m alembic stamp head 2>&1; then
                echo -e "${GREEN}✓ Database stamped to head (tables already exist)${NC}"
            else
                echo -e "${RED}✗ Migration recovery failed${NC}"
                echo -e "${YELLOW}  Try: docker compose down -v && restart to clean database${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠ Alembic not initialized yet, skipping migrations${NC}"
    fi

    # Step 3: Start backend
    if [ "$START_BACKEND" = true ]; then
        echo -e "\n${YELLOW}[3/4] Starting backend server...${NC}"

        kill_port 8000

        ensure_backend_venv

        # Start in background
        nohup "$VENV_PYTHON" run.py > /tmp/bitrun-backend.log 2>&1 &
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

        kill_port 3000

        cd "$PROJECT_ROOT/frontend"
        if [ ! -d "node_modules" ]; then
            echo -e "${YELLOW}Installing frontend dependencies...${NC}"
            npm install
        fi
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
    else
        echo -e "\n${YELLOW}[4/4] Skipping frontend (--no-frontend)${NC}"
    fi

    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}   Development environment is ready!    ${NC}"
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
    echo -e "\nTo stop: ./scripts/start-dev.sh --stop"
    echo -e "To view logs: ./scripts/start-dev.sh --tail"
}

# ==================== Main ====================

case "${1:-}" in
    --stop)
        stop_services
        ;;
    --restart)
        stop_services
        echo ""
        start_services "${@:2}"
        ;;
    --tail|--logs)
        tail_logs
        ;;
    --help|-h)
        echo "BITRUN Development Environment"
        echo ""
        echo "Usage: ./scripts/start-dev.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  (default)       Start all services"
        echo "  --stop          Stop all services"
        echo "  --restart       Restart all services"
        echo "  --tail          Tail logs (services must be running)"
        echo "  --help          Show this help"
        echo ""
        echo "Options:"
        echo "  --no-backend    Skip starting backend"
        echo "  --no-frontend   Skip starting frontend"
        ;;
    *)
        start_services "$@"
        ;;
esac
