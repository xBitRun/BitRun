#!/bin/bash
#
# BITRUN Quick Start Script
# One-click deployment for development or quick testing
#
# Usage:
#   ./scripts/quick-start.sh          # Start with Docker Compose
#   ./scripts/quick-start.sh --dev    # Start in development mode
#   ./scripts/quick-start.sh --prod   # Start in production mode
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ==================== Banner ====================

print_banner() {
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════════════════════════╗"
    echo "  ║                                                           ║"
    echo "  ║    ██████╗ ██╗████████╗██████╗ ██╗   ██╗███╗   ██╗        ║"
    echo "  ║    ██╔══██╗██║╚══██╔══╝██╔══██╗██║   ██║████╗  ██║        ║"
    echo "  ║    ██████╔╝██║   ██║   ██████╔╝██║   ██║██╔██╗ ██║        ║"
    echo "  ║    ██╔══██╗██║   ██║   ██╔══██╗██║   ██║██║╚██╗██║        ║"
    echo "  ║    ██████╔╝██║   ██║   ██║  ██║╚██████╔╝██║ ╚████║        ║"
    echo "  ║    ╚═════╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝        ║"
    echo "  ║                                                           ║"
    echo "  ║              AI-Powered Trading Agent                     ║"
    echo "  ║                                                           ║"
    echo "  ╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ==================== Helper Functions ====================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# ==================== Prerequisite Installation ====================

install_docker() {
    log_info "Docker not found. Attempting to install..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - use official Docker script
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker "$USER"
        log_success "Docker installed. Please log out and back in, then run this script again."
        exit 0
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - recommend Docker Desktop
        log_error "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        exit 1
    else
        log_error "Unsupported OS. Please install Docker manually: https://docs.docker.com/get-docker/"
        exit 1
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! check_command "docker"; then
        log_warning "Docker not found."
        read -p "Would you like to install Docker? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            log_error "Docker is required. Please install it from https://docs.docker.com/get-docker/"
            exit 1
        fi
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker and try again."
        exit 1
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif check_command "docker-compose"; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose is required. It should be included with Docker Desktop."
        exit 1
    fi

    log_success "All prerequisites met."
}

# ==================== Development Mode ====================

start_development() {
    log_info "Delegating to start-dev.sh for local development..."
    exec "$SCRIPT_DIR/start-dev.sh"
}

# ==================== Production Mode ====================

start_production() {
    log_info "Starting in production mode..."

    # Use the production deploy script
    if [ -f "scripts/deploy.sh" ]; then
        chmod +x scripts/deploy.sh
        ./scripts/deploy.sh start
    else
        log_error "deploy.sh not found. Please check your installation."
        exit 1
    fi
}

# ==================== Default Mode (Simple) ====================

start_default() {
    log_info "Starting BITRUN..."

    # Create minimal .env if not exists
    if [ ! -f "backend/.env" ] && [ -f "backend/.env.example" ]; then
        log_info "Creating backend/.env from template..."
        cp backend/.env.example backend/.env
        log_warning "Please update backend/.env with your API keys"
    fi

    if [ ! -f "frontend/.env.local" ] && [ -f "frontend/.env.local.example" ]; then
        log_info "Creating frontend/.env.local from template..."
        cp frontend/.env.local.example frontend/.env.local
    fi

    # Start all services including app containers
    $DOCKER_COMPOSE --profile app up -d

    # Wait for services
    log_info "Waiting for services to start..."
    sleep 15

    # Run migrations
    log_info "Running database migrations..."
    $DOCKER_COMPOSE --profile app exec -T backend alembic upgrade head 2>/dev/null || true

    log_success "BITRUN is ready!"
    echo ""
    echo "=========================================="
    echo "           BITRUN is running!"
    echo "=========================================="
    echo ""
    echo "Access the application:"
    echo ""
    echo "  Frontend:  http://localhost:3000"
    echo "  Backend:   http://localhost:8000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo ""
    echo "Default login:"
    echo "  Register a new account at http://localhost:3000/register"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    $DOCKER_COMPOSE --profile app logs -f"
    echo "  Stop:         $DOCKER_COMPOSE --profile app down"
    echo "  Restart:      $DOCKER_COMPOSE --profile app restart"
    echo ""
    log_info "Configure your AI API keys in backend/.env to start trading!"
}

# ==================== Stop ====================

stop_services() {
    log_info "Stopping BITRUN..."

    if [ -f "docker-compose.prod.yml" ] && [ -f ".env" ]; then
        $DOCKER_COMPOSE -f docker-compose.prod.yml down
    else
        $DOCKER_COMPOSE --profile app down
    fi

    log_success "BITRUN stopped."
}

# ==================== Help ====================

show_help() {
    echo "BITRUN Quick Start Script"
    echo ""
    echo "Usage: ./scripts/quick-start.sh [option]"
    echo ""
    echo "Options:"
    echo "  (no option)   Start with default settings"
    echo "  --dev         Start in development mode with hot reload"
    echo "  --prod        Start in production mode"
    echo "  --stop        Stop all services"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/quick-start.sh          # Quick start"
    echo "  ./scripts/quick-start.sh --dev    # Development mode"
    echo "  ./scripts/quick-start.sh --prod   # Production mode"
    echo "  ./scripts/quick-start.sh --stop   # Stop services"
    echo ""
}

# ==================== Main ====================

main() {
    print_banner

    case "${1:-}" in
        --dev|-d)
            check_prerequisites
            start_development
            ;;
        --prod|-p)
            check_prerequisites
            start_production
            ;;
        --stop|-s)
            stop_services
            ;;
        --help|-h)
            show_help
            ;;
        "")
            check_prerequisites
            start_default
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
