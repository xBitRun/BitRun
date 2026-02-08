#!/bin/bash
#
# BITRUN Docker Development Script
# 
# Usage:
#   ./scripts/docker-dev.sh         - Start all services with hot reload
#   ./scripts/docker-dev.sh build   - Rebuild and start
#   ./scripts/docker-dev.sh down    - Stop all services
#   ./scripts/docker-dev.sh logs    - Follow logs
#   ./scripts/docker-dev.sh shell   - Open shell in backend container

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Docker compose files
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.dev.yml"

print_header() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║        BITRUN Docker Development          ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker daemon is not running${NC}"
        echo -e "${YELLOW}Please start Docker Desktop and try again${NC}"
        exit 1
    fi
}

start_services() {
    local build_flag=""
    if [ "$1" == "build" ]; then
        build_flag="--build"
        echo -e "${YELLOW}Building images...${NC}"
    fi
    
    echo -e "${GREEN}Starting all services...${NC}"
    docker compose $COMPOSE_FILES up $build_flag -d
    
    echo ""
    echo -e "${GREEN}Services started successfully!${NC}"
    echo ""
    echo -e "${BLUE}URLs:${NC}"
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/api/docs"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo "  View logs:    docker compose $COMPOSE_FILES logs -f"
    echo "  Backend logs: docker compose $COMPOSE_FILES logs -f backend"
    echo "  Stop:         docker compose $COMPOSE_FILES down"
    echo ""
    echo -e "${YELLOW}Hot reload is enabled - edit code and see changes instantly!${NC}"
}

stop_services() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    docker compose $COMPOSE_FILES down
    echo -e "${GREEN}All services stopped${NC}"
}

show_logs() {
    local service=$1
    if [ -n "$service" ]; then
        docker compose $COMPOSE_FILES logs -f "$service"
    else
        docker compose $COMPOSE_FILES logs -f
    fi
}

open_shell() {
    local service=${1:-backend}
    echo -e "${BLUE}Opening shell in ${service}...${NC}"
    docker compose $COMPOSE_FILES exec "$service" /bin/sh
}

show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    docker compose $COMPOSE_FILES ps
}

run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"
    docker compose $COMPOSE_FILES exec backend alembic upgrade head
    echo -e "${GREEN}Migrations complete${NC}"
}

print_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  (none)     Start all services with hot reload"
    echo "  build      Rebuild images and start"
    echo "  down       Stop all services"
    echo "  logs       Follow all logs"
    echo "  logs <svc> Follow logs for specific service"
    echo "  shell      Open shell in backend container"
    echo "  shell <svc> Open shell in specific container"
    echo "  status     Show service status"
    echo "  migrate    Run database migrations"
    echo "  help       Show this help message"
}

# Main
print_header
check_docker

case "${1:-}" in
    "")
        start_services
        ;;
    build)
        start_services "build"
        ;;
    down|stop)
        stop_services
        ;;
    logs)
        show_logs "$2"
        ;;
    shell|sh)
        open_shell "$2"
        ;;
    status|ps)
        show_status
        ;;
    migrate)
        run_migrations
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        print_help
        exit 1
        ;;
esac
