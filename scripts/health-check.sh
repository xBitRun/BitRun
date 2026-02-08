#!/bin/bash
#
# BITRUN Health Check Script
# Checks the health of all services
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
TIMEOUT=5

# Track overall status
OVERALL_STATUS=0

# ==================== Helper Functions ====================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    OVERALL_STATUS=1
}

# Check if a service is reachable
check_http() {
    local url="$1"
    local name="$2"
    local expected_status="${3:-200}"

    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout "$TIMEOUT" "$url" 2>/dev/null)

    if [ "$status" = "$expected_status" ]; then
        log_success "$name is healthy (HTTP $status)"
        return 0
    elif [ "$status" = "000" ]; then
        log_error "$name is unreachable"
        return 1
    else
        log_warning "$name returned HTTP $status (expected $expected_status)"
        return 1
    fi
}

# Check if a TCP port is open
check_port() {
    local host="$1"
    local port="$2"
    local name="$3"

    if nc -z -w "$TIMEOUT" "$host" "$port" 2>/dev/null; then
        log_success "$name is listening on port $port"
        return 0
    else
        log_error "$name is not listening on port $port"
        return 1
    fi
}

# Check Docker container status
check_container() {
    local container="$1"
    local status

    if ! command -v docker &> /dev/null; then
        log_warning "Docker not available, skipping container check for $container"
        return 0
    fi

    status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)

    if [ "$status" = "running" ]; then
        # Check health if available
        local health
        health=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null)

        if [ "$health" = "healthy" ]; then
            log_success "Container $container is running and healthy"
        elif [ "$health" = "unhealthy" ]; then
            log_error "Container $container is running but unhealthy"
            return 1
        else
            log_success "Container $container is running"
        fi
        return 0
    elif [ -z "$status" ]; then
        log_error "Container $container not found"
        return 1
    else
        log_error "Container $container is $status"
        return 1
    fi
}

# ==================== Health Checks ====================

check_postgres() {
    log_info "Checking PostgreSQL..."

    check_container "bitrun-postgres"
    check_port "localhost" "5432" "PostgreSQL"
}

check_redis() {
    log_info "Checking Redis..."

    check_container "bitrun-redis"
    check_port "localhost" "6379" "Redis"

    # Check Redis ping
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h localhost ping 2>/dev/null | grep -q "PONG"; then
            log_success "Redis responds to PING"
        else
            log_warning "Redis PING failed"
        fi
    fi
}

check_backend() {
    log_info "Checking Backend API..."

    check_container "bitrun-backend"
    check_http "$BACKEND_URL/health" "Backend health endpoint"
    check_http "$BACKEND_URL/docs" "Backend API docs" "200"
}

check_frontend() {
    log_info "Checking Frontend..."

    check_container "bitrun-frontend"
    check_http "$FRONTEND_URL" "Frontend"
}

check_api_connectivity() {
    log_info "Checking API connectivity..."

    # Check if API returns valid JSON
    local response
    response=$(curl -s --connect-timeout "$TIMEOUT" "$BACKEND_URL/health" 2>/dev/null)

    if echo "$response" | grep -q "status"; then
        log_success "API returns valid health response"
    else
        log_warning "API health response may be invalid"
    fi
}

# ==================== Summary ====================

print_summary() {
    echo ""
    echo "=========================================="
    echo "          Health Check Summary"
    echo "=========================================="
    echo ""

    if [ $OVERALL_STATUS -eq 0 ]; then
        echo -e "${GREEN}All services are healthy!${NC}"
    else
        echo -e "${RED}Some services have issues.${NC}"
        echo "Please check the logs with: ./scripts/deploy.sh logs"
    fi

    echo ""
    echo "Service URLs:"
    echo "  Frontend: $FRONTEND_URL"
    echo "  Backend:  $BACKEND_URL"
    echo "  API Docs: $BACKEND_URL/docs"
    echo ""
}

# ==================== Main ====================

main() {
    echo ""
    echo "=========================================="
    echo "        BITRUN Health Check"
    echo "=========================================="
    echo ""

    check_postgres
    echo ""

    check_redis
    echo ""

    check_backend
    echo ""

    check_frontend
    echo ""

    check_api_connectivity

    print_summary

    exit $OVERALL_STATUS
}

main "$@"
