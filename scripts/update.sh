#!/bin/bash
#
# BITRUN Incremental Update Script (Production)
#
# Usage:
#   ./scripts/update.sh
#   ./scripts/update.sh --no-backup
#

set -Eeuo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=""
DO_BACKUP=true

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
BITRUN Update Script

Usage:
  ./scripts/update.sh [options]

Options:
  --no-backup   Skip database backup before migration
  -h, --help    Show this help message
EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-backup)
                DO_BACKUP=false
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

check_prerequisites() {
    command -v git >/dev/null 2>&1 || { log_error "git is required"; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "docker is required"; exit 1; }

    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose is required"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    if [[ -f ".env.production" ]]; then
        ENV_FILE=".env.production"
    elif [[ -f ".env" ]]; then
        ENV_FILE=".env"
    else
        log_error "No env file found. Expected .env.production or .env"
        exit 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    log_info "Using env file: $ENV_FILE"
}

backup_database() {
    local backup_dir="$PROJECT_ROOT/backups"
    local backup_file="$backup_dir/bitrun_update_$(date +%Y%m%d_%H%M%S).sql.gz"

    mkdir -p "$backup_dir"
    log_info "Creating database backup: $backup_file"

    if $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        pg_dump -U "${POSTGRES_USER:-bitrun}" "${POSTGRES_DB:-bitrun}" | gzip > "$backup_file"; then
        log_success "Backup completed"
    else
        log_error "Backup failed"
        exit 1
    fi
}

update_source_code() {
    if [[ ! -d ".git" ]]; then
        log_error "Current directory is not a git repository: $PROJECT_ROOT"
        exit 1
    fi

    log_info "Fetching latest code..."
    git fetch --all --prune

    local branch
    branch="$(git rev-parse --abbrev-ref HEAD)"
    log_info "Current branch: $branch"

    if git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
        git pull --ff-only origin "$branch"
    elif git show-ref --verify --quiet "refs/remotes/origin/main"; then
        log_warn "Remote branch origin/$branch not found, falling back to origin/main"
        git pull --ff-only origin main
    elif git show-ref --verify --quiet "refs/remotes/origin/master"; then
        log_warn "Remote branch origin/$branch not found, falling back to origin/master"
        git pull --ff-only origin master
    else
        log_error "No usable remote branch found on origin"
        exit 1
    fi

    log_success "Code updated"
}

deploy_containers() {
    log_info "Building images..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build

    log_info "Starting updated services..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

    log_success "Services updated"
}

run_migrations() {
    log_info "Running database migrations..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend alembic upgrade head
    log_success "Migrations completed"
}

check_status() {
    log_info "Container status:"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

    if [[ -x "$SCRIPT_DIR/health-check.sh" ]]; then
        log_info "Running health check..."
        "$SCRIPT_DIR/health-check.sh" || log_warn "Health check reported warnings/errors"
    else
        log_warn "Health check script not executable: $SCRIPT_DIR/health-check.sh"
    fi
}

main() {
    parse_args "$@"
    check_prerequisites

    if [[ "$DO_BACKUP" == true ]]; then
        backup_database
    else
        log_warn "Skipping database backup (--no-backup)"
    fi

    update_source_code
    deploy_containers
    run_migrations
    check_status

    log_success "Update completed successfully"
}

main "$@"
