#!/bin/bash
#
# BITRUN One-Click Installation Script (Development/Local)
# https://github.com/xBitRun/BitRun
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/install.sh | bash
#
# Or with custom directory:
#   curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/install.sh | bash -s -- /opt/bitrun
#
# For production deployment with SSL:
#   curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/deploy-production.sh | bash
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default installation directory
INSTALL_DIR="${1:-$HOME/bitrun}"
COMPOSE_FILE="docker-compose.prod.yml"
GITHUB_RAW="https://raw.githubusercontent.com/xBitRun/BitRun/main"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                 BITRUN — One-Click Installer               ║"
echo "║               AI-Powered Trading Platform                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ==================== Check Docker ====================

check_docker() {
    echo -e "${YELLOW}Checking Docker...${NC}"

    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed.${NC}"
        echo ""
        echo "  Install Docker:"
        echo "    Linux:  curl -fsSL https://get.docker.com | sh"
        echo "    macOS:  https://www.docker.com/products/docker-desktop"
        echo ""
        exit 1
    fi

    if ! docker info &> /dev/null 2>&1; then
        echo -e "${RED}Error: Docker daemon is not running.${NC}"
        echo "Please start Docker and try again."
        exit 1
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        echo -e "${RED}Error: Docker Compose is not available.${NC}"
        echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi

    echo -e "${GREEN}✓ Docker is ready${NC}"
    echo -e "  ${BLUE}Docker:$NC $(docker --version | cut -d' ' -f3 | tr -d ',')"
    echo -e "  ${BLUE}Compose:$NC $($COMPOSE_CMD version --short 2>/dev/null || echo 'unknown')"
}

# ==================== Setup Directory ====================

setup_directory() {
    echo -e "${YELLOW}Setting up installation directory: ${INSTALL_DIR}${NC}"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    echo -e "${GREEN}✓ Directory ready${NC}"
}

# ==================== Download Files ====================

download_files() {
    echo -e "${YELLOW}Downloading configuration files...${NC}"

    # Download docker-compose.prod.yml
    curl -fsSL "$GITHUB_RAW/$COMPOSE_FILE" -o docker-compose.yml 2>/dev/null || {
        echo -e "${YELLOW}Could not download from GitHub, checking for local file...${NC}"
        if [ ! -f "docker-compose.yml" ] && [ ! -f "$COMPOSE_FILE" ]; then
            echo -e "${RED}Error: No docker-compose file found.${NC}"
            echo "Please ensure you have docker-compose.yml in $INSTALL_DIR"
            exit 1
        fi
    }

    # Download nginx config
    mkdir -p nginx
    curl -fsSL "$GITHUB_RAW/nginx/nginx.conf" -o nginx/nginx.conf 2>/dev/null || true

    # Download .env.example
    curl -fsSL "$GITHUB_RAW/.env.example" -o .env.example 2>/dev/null || true

    echo -e "${GREEN}✓ Files downloaded${NC}"
}

# ==================== Generate Environment ====================

generate_env() {
    echo -e "${YELLOW}Generating environment configuration...${NC}"

    # Skip if .env already exists
    if [ -f ".env" ]; then
        echo -e "${GREEN}✓ .env file already exists, skipping generation${NC}"
        return
    fi

    # Generate secrets
    JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-$(date +%s)")
    DATA_ENCRYPTION_KEY=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-$(date +%s)")
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' 2>/dev/null || echo "bitrun_$(date +%s)")
    REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' 2>/dev/null || echo "redis_$(date +%s)")

    # Create .env file
    cat > .env << EOF
# BITRUN Configuration (Auto-generated)
# Generated at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ==================== Required Secrets ====================
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
JWT_SECRET=${JWT_SECRET}
DATA_ENCRYPTION_KEY=${DATA_ENCRYPTION_KEY}
REDIS_PASSWORD=${REDIS_PASSWORD}

# ==================== Database ====================
POSTGRES_DB=bitrun
POSTGRES_USER=bitrun

# ==================== Server Ports ====================
# Change these if you have port conflicts
HTTP_PORT=80
BACKEND_PORT=8000
FRONTEND_PORT=3000

# ==================== URLs ====================
# Update these for your domain
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws

# ==================== Worker ====================
WORKER_ENABLED=true

# ==================== Notifications (Optional) ====================
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=

# ==================== Timezone ====================
TZ=Asia/Shanghai
EOF

    echo -e "${GREEN}✓ Environment configured${NC}"
    echo -e "  ${BLUE}Secrets generated and saved to .env${NC}"
}

# ==================== Pull Images ====================

pull_images() {
    echo -e "${YELLOW}Pulling Docker images (this may take a few minutes)...${NC}"

    if [ -f "docker-compose.yml" ]; then
        $COMPOSE_CMD -f docker-compose.yml pull 2>/dev/null || {
            echo -e "${YELLOW}Could not pull pre-built images, will build locally...${NC}"
        }
    fi

    echo -e "${GREEN}✓ Images ready${NC}"
}

# ==================== Start Services ====================

start_services() {
    echo -e "${YELLOW}Starting BITRUN services...${NC}"

    if [ -f "docker-compose.yml" ]; then
        $COMPOSE_CMD -f docker-compose.yml up -d
    elif [ -f "$COMPOSE_FILE" ]; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    else
        echo -e "${RED}Error: No docker-compose file found${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Services started${NC}"
}

# ==================== Wait for Services ====================

wait_for_services() {
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend is ready${NC}"
            break
        fi
        echo "  Waiting for backend... ($attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    if [ $attempt -gt $max_attempts ]; then
        echo -e "${YELLOW}Backend is still starting, please wait a moment...${NC}"
    fi
}

# ==================== Run Migrations ====================

run_migrations() {
    echo -e "${YELLOW}Running database migrations...${NC}"

    local max_retries=10
    local retry=0

    while [ $retry -lt $max_retries ]; do
        if $COMPOSE_CMD exec -T postgres pg_isready -U bitrun -d bitrun &>/dev/null; then
            break
        fi
        retry=$((retry + 1))
        sleep 2
    done

    $COMPOSE_CMD exec -T backend alembic upgrade head 2>/dev/null || {
        echo -e "${YELLOW}Migration may have already been applied${NC}"
    }

    echo -e "${GREEN}✓ Database migrations completed${NC}"
}

# ==================== Get Server IP ====================

get_server_ip() {
    # Try to get public IP first
    local public_ip=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || curl -s --max-time 3 icanhazip.com 2>/dev/null || echo "")

    # If no public IP, try local IP
    if [ -z "$public_ip" ]; then
        if command -v ip &> /dev/null; then
            public_ip=$(ip route get 1 2>/dev/null | awk '{print $7}' | head -1)
        elif command -v hostname &> /dev/null; then
            public_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
        fi
    fi

    echo "${public_ip:-127.0.0.1}"
}

# ==================== Print Success ====================

print_success() {
    local SERVER_IP=$(get_server_ip)

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              🎉 Installation Complete! 🎉                  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Web Interface:${NC} http://${SERVER_IP}:3000"
    echo -e "${BLUE}API Endpoint:${NC}  http://${SERVER_IP}:8000"
    echo -e "${BLUE}API Docs:${NC}       http://${SERVER_IP}:8000/docs"
    echo -e "${BLUE}Install Dir:${NC}    $INSTALL_DIR"
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  💡 Keep Updated: Run this command to stay current         ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/install.sh | bash${NC}"
    echo ""
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo "  cd $INSTALL_DIR"
    echo "  $COMPOSE_CMD logs -f          # View logs"
    echo "  $COMPOSE_CMD restart          # Restart services"
    echo "  $COMPOSE_CMD down             # Stop services"
    echo "  $COMPOSE_CMD pull && $COMPOSE_CMD up -d  # Update to latest"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Open http://${SERVER_IP}:3000 in your browser"
    echo "  2. Register an account"
    echo "  3. Configure AI Models (DeepSeek, OpenAI, etc.)"
    echo "  4. Connect your Exchange (Binance, OKX, etc.)"
    echo "  5. Create your first AI trading agent!"
    echo ""
    echo -e "${YELLOW}Note:${NC} If accessing from local machine, use http://127.0.0.1:3000"
    echo ""
    echo -e "${RED}⚠️  Risk Warning: AI trading carries significant risks.${NC}"
    echo -e "${RED}    Only use funds you can afford to lose!${NC}"
    echo ""
}

# ==================== Main ====================

main() {
    check_docker
    setup_directory
    download_files
    generate_env
    pull_images
    start_services
    wait_for_services
    run_migrations
    print_success
}

main
