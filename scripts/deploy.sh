#!/bin/bash
#
# BITRUN Production Deployment Script
# Usage: ./scripts/deploy.sh [command]
#
# Commands:
#   start     - Build and start all services (default)
#   stop      - Stop all services
#   restart   - Restart all services
#   logs      - View logs
#   status    - Check service status
#   migrate   - Run database migrations
#   backup    - Backup database
#   help      - Show this help message
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

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
        log_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Generate random secret
generate_secret() {
    openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64
}

# ==================== Prerequisite Checks ====================

check_prerequisites() {
    log_info "Checking prerequisites..."

    check_command "docker"

    # Check Docker Compose (v2 or standalone)
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose is not installed."
        exit 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi

    log_success "All prerequisites met."
}

# ==================== Environment Setup ====================

setup_environment() {
    log_info "Setting up environment..."

    # Check if .env.production exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "$ENV_FILE not found. Creating from template..."

        # Create .env.production with generated secrets
        cat > "$ENV_FILE" << EOF
# BITRUN Production Environment
# Generated on $(date)

# ==================== Required Secrets ====================
# These are auto-generated. Replace with your own for production.

POSTGRES_PASSWORD=$(generate_secret | tr -d '/')
JWT_SECRET=$(generate_secret)
DATA_ENCRYPTION_KEY=$(generate_secret | head -c 32)

# ==================== Database ====================
POSTGRES_DB=bitrun
POSTGRES_USER=bitrun

# ==================== Ports ====================
BACKEND_PORT=8000
FRONTEND_PORT=3000

# ==================== URLs ====================
# Update these for your domain
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws

# ==================== AI API Keys ====================
# Add your API keys for the AI providers you want to use
DEEPSEEK_API_KEY=
QWEN_API_KEY=
ZHIPU_API_KEY=
MINIMAX_API_KEY=
KIMI_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
GROK_API_KEY=

# ==================== Worker ====================
WORKER_ENABLED=true

# ==================== Notifications (Optional) ====================
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=
EOF

        log_success "Created $ENV_FILE with generated secrets."
        log_warning "Please review and update $ENV_FILE with your settings."
    fi

    # Load environment file
    set -a
    source "$ENV_FILE"
    set +a

    # Validate required variables
    local required_vars=("POSTGRES_PASSWORD" "JWT_SECRET" "DATA_ENCRYPTION_KEY")
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required variable $var is not set in $ENV_FILE"
            exit 1
        fi
    done

    log_success "Environment configured."
}

# ==================== Build ====================

build_images() {
    log_info "Building Docker images..."

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

    log_success "Docker images built successfully."
}

# ==================== Database Migration ====================

wait_for_db() {
    local max_retries=30
    local retry=0
    log_info "Waiting for database to be ready..."
    while [ $retry -lt $max_retries ]; do
        if $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
            pg_isready -U "${POSTGRES_USER:-bitrun}" -d "${POSTGRES_DB:-bitrun}" &>/dev/null; then
            log_success "Database is ready."
            return 0
        fi
        retry=$((retry + 1))
        log_info "Waiting for database... ($retry/$max_retries)"
        sleep 2
    done
    log_error "Database did not become ready in time."
    return 1
}

run_migrations() {
    log_info "Running database migrations..."

    # Wait for database to be ready with retry
    wait_for_db || exit 1

    # Backup before migration (optional, skip if backup fails)
    log_info "Creating pre-migration backup..."
    backup_database 2>/dev/null && log_success "Pre-migration backup created." || log_warning "Pre-migration backup skipped (non-critical)."

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        alembic upgrade head

    log_success "Database migrations completed."
}

# ==================== Start Services ====================

start_services() {
    log_info "Starting services..."

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

    log_success "Services started."
}

# ==================== Stop Services ====================

stop_services() {
    log_info "Stopping services..."

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down

    log_success "Services stopped."
}

# ==================== Restart Services ====================

restart_services() {
    log_info "Restarting services..."

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart

    log_success "Services restarted."
}

# ==================== View Logs ====================

view_logs() {
    local service="${1:-}"

    if [ -n "$service" ]; then
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f "$service"
    else
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f
    fi
}

# ==================== Check Status ====================

check_status() {
    log_info "Checking service status..."

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

    echo ""

    # Run health checks
    "$SCRIPT_DIR/health-check.sh" 2>/dev/null || true
}

# ==================== Backup Database ====================

backup_database() {
    log_info "Backing up database..."

    local backup_dir="$PROJECT_ROOT/backups"
    local backup_file="$backup_dir/bitrun_$(date +%Y%m%d_%H%M%S).sql"

    mkdir -p "$backup_dir"

    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-bitrun}" "${POSTGRES_DB:-bitrun}" > "$backup_file"

    # Compress backup
    gzip "$backup_file"

    log_success "Database backed up to ${backup_file}.gz"
}

# ==================== Full Deployment ====================

full_deploy() {
    log_info "Starting full deployment..."
    echo ""

    check_prerequisites
    setup_environment
    build_images
    start_services

    # Wait for services to be healthy via Docker health checks
    log_info "Waiting for services to be healthy..."
    local max_wait=120
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps --format json 2>/dev/null | grep -q '"healthy"'; then
            break
        fi
        sleep 5
        waited=$((waited + 5))
        log_info "Waiting for health checks... (${waited}s/${max_wait}s)"
    done

    run_migrations

    echo ""
    log_success "=========================================="
    log_success "BITRUN deployed successfully!"
    log_success "=========================================="
    echo ""
    echo "Frontend: http://localhost:${FRONTEND_PORT:-3000}"
    echo "Backend:  http://localhost:${BACKEND_PORT:-8000}"
    echo "API Docs: http://localhost:${BACKEND_PORT:-8000}/docs"
    echo ""
    log_info "Run './scripts/deploy.sh logs' to view logs"
    log_info "Run './scripts/deploy.sh status' to check status"
    echo ""
}

# ==================== Help ====================

show_help() {
    echo "BITRUN Production Deployment Script"
    echo ""
    echo "Usage: ./scripts/deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Build and start all services (default)"
    echo "  stop      - Stop all services"
    echo "  restart   - Restart all services"
    echo "  logs      - View logs (optionally specify service: logs backend)"
    echo "  status    - Check service status"
    echo "  migrate   - Run database migrations"
    echo "  backup    - Backup database"
    echo "  build     - Build images only"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./scripts/deploy.sh           # Full deployment"
    echo "  ./scripts/deploy.sh start     # Start services"
    echo "  ./scripts/deploy.sh logs      # View all logs"
    echo "  ./scripts/deploy.sh logs backend  # View backend logs only"
    echo ""
}

# ==================== Main ====================

main() {
    local command="${1:-start}"
    shift 2>/dev/null || true

    case "$command" in
        start)
            full_deploy
            ;;
        stop)
            check_prerequisites
            setup_environment
            stop_services
            ;;
        restart)
            check_prerequisites
            setup_environment
            restart_services
            ;;
        logs)
            setup_environment
            view_logs "$@"
            ;;
        status)
            setup_environment
            check_status
            ;;
        migrate)
            check_prerequisites
            setup_environment
            run_migrations
            ;;
        backup)
            check_prerequisites
            setup_environment
            backup_database
            ;;
        build)
            check_prerequisites
            setup_environment
            build_images
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
