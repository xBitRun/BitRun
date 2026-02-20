#!/bin/bash
#
# BITRUN Production Deployment Script
# Separated domains: app.qemind.xyz (frontend) + api.qemind.xyz (backend)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/deploy-production.sh | bash
#
# Prerequisites:
#   - Aliyun ECS instance (Ubuntu 20.04+)
#   - DNS records configured:
#     * app.qemind.xyz → Server IP
#     * api.qemind.xyz → Server IP
#   - Ports 80, 443, 22 open in security group
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
FRONTEND_DOMAIN="app.qemind.xyz"
BACKEND_DOMAIN="api.qemind.xyz"
INSTALL_DIR="${BITRUN_DIR:-/opt/bitrun}"
GITHUB_RAW="https://raw.githubusercontent.com/xBitRun/BitRun/main"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          BITRUN — Production Deployment                    ║"
echo "║     Frontend: app.qemind.xyz + Backend: api.qemind.xyz     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ==================== Preflight Checks ====================

preflight_checks() {
    echo -e "${YELLOW}Running preflight checks...${NC}"

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Error: Please run as root (use sudo)${NC}"
        exit 1
    fi

    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ] && [ "$ARCH" != "aarch64" ]; then
        echo -e "${RED}Error: Unsupported architecture: $ARCH${NC}"
        exit 1
    fi

    # Check DNS resolution
    echo -e "${YELLOW}Checking DNS resolution...${NC}"
    SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

    # DNS resolution function - tries multiple methods
    resolve_dns() {
        local domain=$1
        local ip=""
        # Try dig first (most reliable)
        if command -v dig &>/dev/null; then
            ip=$(dig +short "$domain" 2>/dev/null | tail -1)
        # Try host command
        elif command -v host &>/dev/null; then
            ip=$(host "$domain" 2>/dev/null | grep "has address" | head -1 | awk '{print $NF}')
        # Try nslookup
        elif command -v nslookup &>/dev/null; then
            ip=$(nslookup "$domain" 2>/dev/null | grep "^Address:" | tail -1 | awk '{print $2}')
        # Try getent (Linux)
        elif command -v getent &>/dev/null; then
            ip=$(getent hosts "$domain" 2>/dev/null | awk '{print $1}')
        fi
        echo "$ip"
    }

    FRONTEND_IP=$(resolve_dns $FRONTEND_DOMAIN)
    BACKEND_IP=$(resolve_dns $BACKEND_DOMAIN)

    if [ -z "$FRONTEND_IP" ] || [ -z "$BACKEND_IP" ]; then
        echo -e "${RED}Error: DNS records not found for domains${NC}"
        echo "  Please configure DNS records first:"
        echo "    $FRONTEND_DOMAIN → $SERVER_IP"
        echo "    $BACKEND_DOMAIN → $SERVER_IP"
        exit 1
    fi

    if [ "$FRONTEND_IP" != "$SERVER_IP" ] || [ "$BACKEND_IP" != "$SERVER_IP" ]; then
        echo -e "${YELLOW}Warning: DNS IPs don't match server IP${NC}"
        echo "  Server IP: $SERVER_IP"
        echo "  $FRONTEND_DOMAIN → $FRONTEND_IP"
        echo "  $BACKEND_DOMAIN → $BACKEND_IP"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    echo -e "${GREEN}✓ DNS resolution OK${NC}"
    echo -e "${GREEN}✓ Preflight checks passed${NC}"
}

# ==================== System Preparation ====================

prepare_system() {
    echo -e "${YELLOW}Preparing system...${NC}"

    # Update package list
    apt-get update -qq
    apt-get install -y -qq curl wget git ca-certificates gnupg lsb-release

    # Set timezone
    timedatectl set-timezone Asia/Shanghai 2>/dev/null || true

    # Increase file descriptor limits
    if ! grep -q "bitrun" /etc/security/limits.conf 2>/dev/null; then
        cat >> /etc/security/limits.conf << EOF
# BITRUN limits
* soft nofile 65535
* hard nofile 65535
EOF
    fi

    echo -e "${GREEN}✓ System prepared${NC}"
}

# ==================== Install Docker ====================

install_docker() {
    echo -e "${YELLOW}Installing Docker...${NC}"

    if command -v docker &> /dev/null; then
        echo -e "${GREEN}✓ Docker already installed: $(docker --version | cut -d' ' -f3 | tr -d ',')${NC}"
        return
    fi

    # Install Docker using official script
    curl -fsSL https://get.docker.com | sh

    # Start Docker
    systemctl enable docker
    systemctl start docker

    # Add current user to docker group (if not root)
    if [ -n "$SUDO_USER" ]; then
        usermod -aG docker "$SUDO_USER"
    fi

    echo -e "${GREEN}✓ Docker installed${NC}"
}

# ==================== Install Certbot ====================

install_certbot() {
    echo -e "${YELLOW}Installing Certbot for SSL...${NC}"

    if command -v certbot &> /dev/null; then
        echo -e "${GREEN}✓ Certbot already installed${NC}"
        return
    fi

    apt-get install -y -qq certbot

    # Create certbot webroot directory
    mkdir -p /var/www/certbot

    echo -e "${GREEN}✓ Certbot installed${NC}"
}

# ==================== Configure Firewall ====================

configure_firewall() {
    echo -e "${YELLOW}Configuring firewall...${NC}"

    if command -v ufw &> /dev/null; then
        # Ubuntu/Debian with UFW
        ufw --force reset
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp comment 'SSH'
        ufw allow 80/tcp comment 'HTTP'
        ufw allow 443/tcp comment 'HTTPS'
        ufw --force enable
        echo -e "${GREEN}✓ UFW configured${NC}"
    else
        echo -e "${YELLOW}No firewall detected. Please configure manually:${NC}"
        echo "  - Open ports: 22, 80, 443"
        echo "  - Aliyun Security Group: Ensure these ports are open"
    fi
}

# ==================== Setup BITRUN ====================

setup_bitrun() {
    echo -e "${YELLOW}Setting up BITRUN...${NC}"

    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Download docker-compose file
    curl -fsSL "$GITHUB_RAW/docker-compose.prod.yml" -o docker-compose.yml

    # Download nginx config
    mkdir -p nginx
    curl -fsSL "$GITHUB_RAW/nginx/nginx.prod.conf" -o nginx/nginx.prod.conf

    # Generate environment file only on first deploy
    if [ -f ".env" ]; then
        echo -e "${GREEN}✓ Using existing .env file (preserving your configuration)${NC}"
        echo -e "${BLUE}  To reset: rm $INSTALL_DIR/.env && re-run this script${NC}"
        return
    fi

    echo -e "${YELLOW}Generating environment configuration (first-time setup)...${NC}"

    # Generate secure random secrets
    JWT_SECRET=$(openssl rand -base64 32)
    DATA_ENCRYPTION_KEY=$(openssl rand -base64 32)
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')
    REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')

    cat > .env << EOF
# BITRUN Production Configuration
# Generated at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
#
# Frontend: https://${FRONTEND_DOMAIN}
# Backend:  https://${BACKEND_DOMAIN}
#
# ⚠️  This file contains sensitive secrets - NEVER commit to git!

# ==================== Domains ====================
FRONTEND_DOMAIN=${FRONTEND_DOMAIN}
BACKEND_DOMAIN=${BACKEND_DOMAIN}

# ==================== Required Secrets ====================
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
JWT_SECRET=${JWT_SECRET}
DATA_ENCRYPTION_KEY=${DATA_ENCRYPTION_KEY}
REDIS_PASSWORD=${REDIS_PASSWORD}

# ==================== Database ====================
POSTGRES_DB=bitrun
POSTGRES_USER=bitrun

# ==================== Ports ====================
HTTP_PORT=80
HTTPS_PORT=443

# ==================== URLs ====================
CORS_ORIGINS=https://${FRONTEND_DOMAIN}
NEXT_PUBLIC_API_URL=https://${BACKEND_DOMAIN}/api/v1
NEXT_PUBLIC_WS_URL=wss://${BACKEND_DOMAIN}/api/v1/ws

# ==================== Worker ====================
WORKER_ENABLED=true

# ==================== System ====================
TZ=Asia/Shanghai
EOF

    # Set restrictive permissions
    chmod 600 .env

    echo -e "${GREEN}✓ Generated .env with secure random secrets${NC}"
}

# ==================== Obtain SSL Certificates ====================

obtain_ssl_certificates() {
    echo -e "${YELLOW}Obtaining SSL certificates...${NC}"

    # Check if certificates already exist
    if [ -d "/etc/letsencrypt/live/$FRONTEND_DOMAIN" ] && [ -d "/etc/letsencrypt/live/$BACKEND_DOMAIN" ]; then
        echo -e "${GREEN}✓ SSL certificates already exist${NC}"
        return
    fi

    # Create webroot for certbot challenges
    mkdir -p /var/www/certbot

    # Start a temporary nginx for certificate validation
    cat > /tmp/certbot-nginx.conf << EOF
events {}
http {
    server {
        listen 80;
        server_name $FRONTEND_DOMAIN $BACKEND_DOMAIN;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
    }
}
EOF

    docker run -d --name certbot-nginx \
        -p 80:80 \
        -v /var/www/certbot:/var/www/certbot:ro \
        -v /tmp/certbot-nginx.conf:/etc/nginx/nginx.conf:ro \
        nginx:alpine

    sleep 3

    # Obtain certificate for frontend domain
    echo -e "${YELLOW}Obtaining certificate for $FRONTEND_DOMAIN...${NC}"
    certbot certonly --webroot \
        -w /var/www/certbot \
        -d $FRONTEND_DOMAIN \
        --non-interactive \
        --agree-tos \
        --email admin@$FRONTEND_DOMAIN

    # Obtain certificate for backend domain
    echo -e "${YELLOW}Obtaining certificate for $BACKEND_DOMAIN...${NC}"
    certbot certonly --webroot \
        -w /var/www/certbot \
        -d $BACKEND_DOMAIN \
        --non-interactive \
        --agree-tos \
        --email admin@$BACKEND_DOMAIN

    # Stop and remove temporary nginx
    docker stop certbot-nginx && docker rm certbot-nginx
    rm /tmp/certbot-nginx.conf

    # Setup auto-renewal
    (crontab -l 2>/dev/null | grep -v certbot; echo "0 3 * * * certbot renew --quiet --post-hook 'docker restart bitrun-nginx'") | crontab -

    echo -e "${GREEN}✓ SSL certificates obtained${NC}"
    echo -e "${GREEN}✓ Auto-renewal configured (daily at 3:00 AM)${NC}"
}

# ==================== Build and Start Services ====================

start_services() {
    echo -e "${YELLOW}Building and starting services...${NC}"

    cd "$INSTALL_DIR"

    # Build images
    echo -e "${YELLOW}Building Docker images (this may take a few minutes)...${NC}"
    docker compose build --no-cache

    # Start services
    echo -e "${YELLOW}Starting services...${NC}"
    docker compose up -d

    # Wait for services
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 15

    # Run migrations
    echo -e "${YELLOW}Running database migrations...${NC}"
    docker compose exec -T backend alembic upgrade head 2>/dev/null || true

    echo -e "${GREEN}✓ Services started${NC}"
}

# ==================== Print Success ====================

print_success() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              🎉 Deployment Complete! 🎉                    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Frontend:${NC}     https://$FRONTEND_DOMAIN"
    echo -e "${BLUE}Backend API:${NC}   https://$BACKEND_DOMAIN"
    echo -e "${BLUE}API Docs:${NC}      https://$BACKEND_DOMAIN/api/v1/docs"
    echo ""
    echo -e "${BLUE}Install Dir:${NC}   $INSTALL_DIR"
    echo -e "${BLUE}Env File:${NC}      $INSTALL_DIR/.env"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Quick Commands:${NC}"
    echo "  cd $INSTALL_DIR"
    echo "  docker compose logs -f           # View all logs"
    echo "  docker compose restart           # Restart services"
    echo "  docker compose up -d --build     # Rebuild and restart"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Open https://$FRONTEND_DOMAIN in your browser"
    echo "  2. Register an account"
    echo "  3. Configure AI Models (Settings → AI Providers)"
    echo "  4. Connect Exchange accounts"
    echo "  5. Create your first AI trading agent!"
    echo ""
    echo -e "${RED}⚠️  Risk Warning: AI trading carries significant risks.${NC}"
    echo -e "${RED}    Only use funds you can afford to lose!${NC}"
    echo ""
}

# ==================== Main ====================

main() {
    preflight_checks
    prepare_system
    install_docker
    install_certbot
    configure_firewall
    setup_bitrun
    obtain_ssl_certificates
    start_services
    print_success
}

main
