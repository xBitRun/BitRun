#!/bin/bash
#
# BITRUN Installation Script
# https://github.com/xBitRun/BitRun
#
# Usage:
#   # Local/Development (no SSL)
#   curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/scripts/install.sh | bash
#
#   # Production (with SSL and domain)
#   curl -fsSL https://raw.githubusercontent.com/xBitRun/BitRun/main/scripts/install.sh | bash -s -- --prod
#
#   # Custom installation directory
#   curl -fsSL ... | bash -s -- /opt/bitrun
#   curl -fsSL ... | bash -s -- --prod /opt/bitrun
#
# After installation, use scripts/deploy.sh for service management:
#   ./scripts/deploy.sh start|stop|restart|logs|status|migrate|backup
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default configuration
INSTALL_DIR=""
PRODUCTION_MODE=false
FRONTEND_DOMAIN=""
BACKEND_DOMAIN=""
GITHUB_RAW="https://raw.githubusercontent.com/xBitRun/BitRun/main"
COMPOSE_FILE="docker-compose.prod.yml"

# ==================== Argument Parsing ====================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prod)
                PRODUCTION_MODE=true
                shift
                ;;
            -*)
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
                ;;
            *)
                if [ -z "$INSTALL_DIR" ]; then
                    INSTALL_DIR="$1"
                fi
                shift
                ;;
        esac
    done

    # Set default installation directory
    if [ -z "$INSTALL_DIR" ]; then
        if [ "$PRODUCTION_MODE" = true ]; then
            INSTALL_DIR="${BITRUN_DIR:-/opt/bitrun}"
        else
            INSTALL_DIR="$HOME/bitrun"
        fi
    fi
}

# ==================== Print Header ====================

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}BITRUN${NC} — Installation Script                             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  AI-Powered Trading Agent Platform                         ${CYAN}║${NC}"
    if [ "$PRODUCTION_MODE" = true ]; then
        echo -e "${CYAN}║${NC}  ${YELLOW}Mode: Production (with SSL)${NC}                              ${CYAN}║${NC}"
    else
        echo -e "${CYAN}║${NC}  ${BLUE}Mode: Development (localhost)${NC}                             ${CYAN}║${NC}"
    fi
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ==================== Helper Functions ====================

log_info()    { echo -e "${GREEN}✓${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
log_error()   { echo -e "${RED}✗${NC} $1"; }
log_step()    { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }
log_substep() { echo -e "   ${CYAN}→${NC} $1"; }

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 is not installed"
        exit 1
    fi
}

# ==================== Detect Package Manager ====================

detect_package_manager() {
    if command -v dnf &>/dev/null; then
        PKG_MANAGER="dnf"
        PKG_UPDATE="dnf makecache -q 2>/dev/null || true"
        PKG_INSTALL="dnf install -y -q"
    elif command -v yum &>/dev/null; then
        PKG_MANAGER="yum"
        PKG_UPDATE="yum makecache -q 2>/dev/null || true"
        PKG_INSTALL="yum install -y -q"
    elif command -v apt-get &>/dev/null; then
        PKG_MANAGER="apt-get"
        PKG_UPDATE="apt-get update -qq"
        PKG_INSTALL="apt-get install -y -qq"
    elif command -v apk &>/dev/null; then
        PKG_MANAGER="apk"
        PKG_UPDATE="apk update"
        PKG_INSTALL="apk add --no-cache"
    else
        PKG_MANAGER="unknown"
    fi
}

# ==================== Preflight Checks ====================

preflight_checks() {
    log_step "Step 1: Preflight Checks"

    # Production mode requires root
    if [ "$PRODUCTION_MODE" = true ] && [ "$EUID" -ne 0 ]; then
        log_error "Production mode requires root privileges"
        echo "  Please run with: sudo $0 --prod"
        exit 1
    fi

    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ] && [ "$ARCH" != "aarch64" ]; then
        log_error "Unsupported architecture: $ARCH"
        exit 1
    fi

    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "OS: $NAME $VERSION_ID"
    fi

    log_info "Architecture: $ARCH"
    log_info "Install directory: $INSTALL_DIR"

    # Production mode: check DNS
    if [ "$PRODUCTION_MODE" = true ]; then
        check_dns_resolution
    fi

    log_info "Preflight checks passed"
}

# ==================== DNS Resolution Check (Production Only) ====================

check_dns_resolution() {
    log_substep "Checking DNS resolution..."

    SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

    # Prompt for domains if not set
    if [ -z "$FRONTEND_DOMAIN" ] || [ -z "$BACKEND_DOMAIN" ]; then
        echo ""
        echo -e "  ${YELLOW}Please enter your domain names:${NC}"
        read -p "  Frontend domain (e.g., app.example.com): " FRONTEND_DOMAIN
        read -p "  Backend domain (e.g., api.example.com): " BACKEND_DOMAIN

        if [ -z "$FRONTEND_DOMAIN" ] || [ -z "$BACKEND_DOMAIN" ]; then
            log_error "Both domains are required for production mode"
            exit 1
        fi
    fi

    # DNS resolution function
    resolve_dns() {
        local domain=$1
        local ip=""
        if command -v dig &>/dev/null; then
            ip=$(dig +short "$domain" 2>/dev/null | tail -1)
        elif command -v host &>/dev/null; then
            ip=$(host "$domain" 2>/dev/null | grep "has address" | head -1 | awk '{print $NF}')
        elif command -v nslookup &>/dev/null; then
            ip=$(nslookup "$domain" 2>/dev/null | grep "^Address:" | tail -1 | awk '{print $2}')
        elif command -v getent &>/dev/null; then
            ip=$(getent hosts "$domain" 2>/dev/null | awk '{print $1}')
        fi
        echo "$ip"
    }

    FRONTEND_IP=$(resolve_dns "$FRONTEND_DOMAIN")
    BACKEND_IP=$(resolve_dns "$BACKEND_DOMAIN")

    if [ -z "$FRONTEND_IP" ] || [ -z "$BACKEND_IP" ]; then
        log_error "DNS records not found"
        echo "  Please configure DNS records first:"
        echo "    $FRONTEND_DOMAIN → $SERVER_IP"
        echo "    $BACKEND_DOMAIN → $SERVER_IP"
        exit 1
    fi

    log_info "Frontend: $FRONTEND_DOMAIN → $FRONTEND_IP"
    log_info "Backend: $BACKEND_DOMAIN → $BACKEND_IP"

    if [ "$FRONTEND_IP" != "$SERVER_IP" ] || [ "$BACKEND_IP" != "$SERVER_IP" ]; then
        log_warn "DNS IPs don't match server IP ($SERVER_IP)"
        read -p "  Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# ==================== Install System Dependencies ====================

install_system_deps() {
    if [ "$PRODUCTION_MODE" = false ]; then
        return
    fi

    log_step "Step 2: Installing System Dependencies"

    detect_package_manager

    if [ "$PKG_MANAGER" = "unknown" ]; then
        log_warn "Unknown package manager, skipping system dependencies"
        return
    fi

    log_info "Package manager: $PKG_MANAGER"
    eval "$PKG_UPDATE"

    # Install required packages
    if [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        $PKG_INSTALL curl wget git ca-certificates gnupg2 tar procps-ng || true
        $PKG_INSTALL epel-release 2>/dev/null || true
    else
        $PKG_INSTALL curl wget git ca-certificates gnupg lsb-release || true
    fi

    # Set timezone
    timedatectl set-timezone Asia/Shanghai 2>/dev/null || ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime 2>/dev/null || true

    # Increase file descriptor limits
    if ! grep -q "bitrun" /etc/security/limits.conf 2>/dev/null; then
        cat >> /etc/security/limits.conf << EOF
# BITRUN limits
* soft nofile 65535
* hard nofile 65535
EOF
    fi

    log_info "System dependencies installed"
}

# ==================== Install Docker ====================

install_docker() {
    log_step "Step 3: Installing Docker"

    if command -v docker &> /dev/null; then
        log_info "Docker already installed: $(docker --version | cut -d' ' -f3 | tr -d ',')"
    else
        if [ "$PRODUCTION_MODE" = true ]; then
            log_substep "Installing Docker..."
            curl -fsSL https://get.docker.com | sh
            systemctl enable docker
            systemctl start docker
            log_info "Docker installed"
        else
            log_error "Docker is not installed"
            echo ""
            echo "  Install Docker:"
            echo "    Linux:  curl -fsSL https://get.docker.com | sh"
            echo "    macOS:  https://www.docker.com/products/docker-desktop"
            echo ""
            exit 1
        fi
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null 2>&1; then
        log_error "Docker daemon is not running"
        echo "Please start Docker and try again."
        exit 1
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Docker Compose is not available"
        exit 1
    fi

    log_info "Docker Compose: $($COMPOSE_CMD version --short 2>/dev/null || echo 'installed')"
}

# ==================== Install Certbot (Production Only) ====================

install_certbot() {
    if [ "$PRODUCTION_MODE" = false ]; then
        return
    fi

    log_step "Step 4: Installing Certbot for SSL"

    if command -v certbot &> /dev/null; then
        log_info "Certbot already installed"
        return
    fi

    if [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        $PKG_INSTALL certbot 2>/dev/null || {
            log_substep "Installing certbot via pip..."
            $PKG_INSTALL python3-pip 2>/dev/null || true
            pip3 install certbot --quiet
        }
    else
        $PKG_INSTALL certbot
    fi

    if ! command -v certbot &> /dev/null; then
        log_error "Failed to install certbot"
        exit 1
    fi

    mkdir -p /var/www/certbot
    log_info "Certbot installed"
}

# ==================== Configure Firewall (Production Only) ====================

configure_firewall() {
    if [ "$PRODUCTION_MODE" = false ]; then
        return
    fi

    log_step "Step 5: Configuring Firewall"

    if command -v firewall-cmd &> /dev/null; then
        systemctl start firewalld 2>/dev/null || true
        systemctl enable firewalld 2>/dev/null || true
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        firewall-cmd --reload
        log_info "Firewalld configured (ports: 22, 80, 443)"
    elif command -v ufw &> /dev/null; then
        ufw --force reset
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp comment 'SSH'
        ufw allow 80/tcp comment 'HTTP'
        ufw allow 443/tcp comment 'HTTPS'
        ufw --force enable
        log_info "UFW configured (ports: 22, 80, 443)"
    else
        log_warn "No firewall detected, please configure manually (ports: 22, 80, 443)"
    fi

    log_warn "Also ensure ports 22, 80, 443 are open in your cloud security group"
}

# ==================== Setup Installation Directory ====================

setup_directory() {
    local step_num
    if [ "$PRODUCTION_MODE" = true ]; then
        step_num="6"
    else
        step_num="2"
    fi
    log_step "Step $step_num: Setting Up Installation Directory"

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    log_info "Installation directory: $INSTALL_DIR"
}

# ==================== Download Configuration Files ====================

download_files() {
    local step_num
    if [ "$PRODUCTION_MODE" = true ]; then
        step_num="7"
    else
        step_num="3"
    fi
    log_step "Step $step_num: Downloading Configuration Files"

    # Download docker-compose file
    curl -fsSL "$GITHUB_RAW/$COMPOSE_FILE" -o docker-compose.yml 2>/dev/null || {
        if [ ! -f "docker-compose.yml" ] && [ ! -f "$COMPOSE_FILE" ]; then
            log_error "No docker-compose file found"
            exit 1
        fi
    }

    # Download nginx config
    mkdir -p nginx
    if [ "$PRODUCTION_MODE" = true ]; then
        curl -fsSL "$GITHUB_RAW/nginx/nginx.prod.conf" -o nginx/nginx.prod.conf 2>/dev/null || true

        # Replace domain placeholders with actual domains
        if [ -f "nginx/nginx.prod.conf" ] && [ -n "$FRONTEND_DOMAIN" ] && [ -n "$BACKEND_DOMAIN" ]; then
            log_substep "Configuring nginx with your domains..."
            sed -i.bak \
                -e "s|__FRONTEND_DOMAIN__|$FRONTEND_DOMAIN|g" \
                -e "s|__BACKEND_DOMAIN__|$BACKEND_DOMAIN|g" \
                nginx/nginx.prod.conf
            rm -f nginx/nginx.prod.conf.bak
            log_info "Nginx configured for $FRONTEND_DOMAIN and $BACKEND_DOMAIN"
        fi
    else
        curl -fsSL "$GITHUB_RAW/nginx/nginx.conf" -o nginx/nginx.conf 2>/dev/null || true
    fi

    log_info "Configuration files downloaded"
}

# ==================== Generate Environment File ====================

generate_env() {
    local step_num
    if [ "$PRODUCTION_MODE" = true ]; then
        step_num="8"
    else
        step_num="4"
    fi
    log_step "Step $step_num: Generating Environment Configuration"

    # Skip if .env already exists
    if [ -f ".env" ]; then
        log_info ".env already exists, preserving your configuration"
        log_warn "To reset: rm $INSTALL_DIR/.env && re-run this script"
        return
    fi

    # Generate secrets
    JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-$(date +%s)")
    DATA_ENCRYPTION_KEY=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-$(date +%s)")
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' 2>/dev/null || echo "bitrun_$(date +%s)")
    REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=' 2>/dev/null || echo "redis_$(date +%s)")
    ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=' 2>/dev/null || echo "admin$(date +%s)")

    if [ "$PRODUCTION_MODE" = true ]; then
        # Production environment
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

# ==================== Admin Account ====================
# Default admin credentials (CHANGE AFTER FIRST LOGIN!)
ADMIN_EMAIL=admin@${FRONTEND_DOMAIN#*.}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
ADMIN_NAME=Admin

# ==================== System ====================
TZ=Asia/Shanghai

# ==================== Frontend Brand Configuration ====================
NEXT_PUBLIC_BRAND_NAME=BITRUN
NEXT_PUBLIC_BRAND_SHORT_NAME=BITRUN
NEXT_PUBLIC_BRAND_TAGLINE=AI-Powered Trading Agent
NEXT_PUBLIC_BRAND_DESCRIPTION=Prompt-driven automated trading with AI decision making
NEXT_PUBLIC_BRAND_LOGO_DEFAULT=
NEXT_PUBLIC_BRAND_LOGO_COMPACT=
NEXT_PUBLIC_BRAND_LOGO_ICON=
NEXT_PUBLIC_BRAND_FAVICON=/logo.png
NEXT_PUBLIC_BRAND_THEME_PRESET=bitrun
NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE=
NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER=BITRUN
NEXT_PUBLIC_BRAND_TERMS_URL=/terms
NEXT_PUBLIC_BRAND_PRIVACY_URL=/privacy
NEXT_PUBLIC_BRAND_HOMEPAGE_URL=https://${FRONTEND_DOMAIN}
NEXT_PUBLIC_BRAND_DOCS_URL=
NEXT_PUBLIC_BRAND_SUPPORT_URL=

# ==================== Backend Brand (for notifications) ====================
BRAND_NAME=BITRUN
BRAND_TAGLINE=AI-Powered Trading Agent

# ==================== Optional Features ====================
# Proxy for geo-restricted exchange APIs
# PROXY_URL=http://host.docker.internal:7890

# Email notifications (Resend)
# RESEND_API_KEY=re_xxx
# RESEND_FROM=noreply@yourdomain.com

# Error tracking (Sentry)
# SENTRY_DSN=https://xxx@sentry.io/xxx
EOF

        chmod 600 .env
        log_info "Generated .env with secure random secrets"

        echo ""
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}⚠️  IMPORTANT: Default Admin Credentials${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${CYAN}  Email:    admin@${FRONTEND_DOMAIN#*.}${NC}"
        echo -e "${CYAN}  Password: ${ADMIN_PASSWORD}${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}  Please change the password after first login!${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""

    else
        # Development environment
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

# ==================== Ports ====================
HTTP_PORT=80
BACKEND_PORT=8000
FRONTEND_PORT=3000

# ==================== URLs ====================
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws

# ==================== Worker ====================
WORKER_ENABLED=true

# ==================== Notifications (Optional) ====================
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=

# ==================== System ====================
TZ=Asia/Shanghai
EOF

        chmod 600 .env
        log_info "Generated .env with random secrets"
    fi
}

# ==================== Obtain SSL Certificates (Production Only) ====================

obtain_ssl_certificates() {
    if [ "$PRODUCTION_MODE" = false ]; then
        return
    fi

    log_step "Step 9: Obtaining SSL Certificates"

    # Check if certificates already exist
    if [ -d "/etc/letsencrypt/live/$FRONTEND_DOMAIN" ] && [ -d "/etc/letsencrypt/live/$BACKEND_DOMAIN" ]; then
        log_info "SSL certificates already exist"
        return
    fi

    mkdir -p /var/www/certbot

    # Start temporary nginx for certificate validation
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

    # Obtain certificates
    log_substep "Obtaining certificate for $FRONTEND_DOMAIN..."
    certbot certonly --webroot -w /var/www/certbot -d "$FRONTEND_DOMAIN" --non-interactive --agree-tos --email "admin@$FRONTEND_DOMAIN"

    log_substep "Obtaining certificate for $BACKEND_DOMAIN..."
    certbot certonly --webroot -w /var/www/certbot -d "$BACKEND_DOMAIN" --non-interactive --agree-tos --email "admin@$BACKEND_DOMAIN"

    # Cleanup
    docker stop certbot-nginx && docker rm certbot-nginx
    rm /tmp/certbot-nginx.conf

    # Setup auto-renewal
    (crontab -l 2>/dev/null | grep -v certbot; echo "0 3 * * * certbot renew --quiet --post-hook 'docker restart bitrun-nginx 2>/dev/null || true'") | crontab -

    log_info "SSL certificates obtained"
    log_info "Auto-renewal configured (daily at 3:00 AM)"
}

# ==================== Build and Start Services ====================

start_services() {
    local step_num
    if [ "$PRODUCTION_MODE" = true ]; then
        step_num="10"
    else
        step_num="5"
    fi
    log_step "Step $step_num: Building and Starting Services"

    cd "$INSTALL_DIR"

    # Pull or build images
    log_substep "Pulling/building Docker images..."
    $COMPOSE_CMD pull 2>/dev/null || {
        log_substep "Building images (this may take a few minutes)..."
        $COMPOSE_CMD build
    }

    # Start services
    log_substep "Starting services..."
    $COMPOSE_CMD up -d

    # Wait for services
    log_substep "Waiting for services to be ready..."
    sleep 15
}

# ==================== Run Database Migrations ====================

run_migrations() {
    local step_num
    if [ "$PRODUCTION_MODE" = true ]; then
        step_num="11"
    else
        step_num="6"
    fi
    log_step "Step $step_num: Running Database Migrations"

    # Wait for database
    local max_retries=30
    local retry=0
    while [ $retry -lt $max_retries ]; do
        if $COMPOSE_CMD exec -T postgres pg_isready -U bitrun -d bitrun &>/dev/null; then
            break
        fi
        retry=$((retry + 1))
        sleep 2
    done

    if [ $retry -eq $max_retries ]; then
        log_warn "Database not ready after $max_retries attempts"
    fi

    # Run migrations
    $COMPOSE_CMD exec -T backend alembic upgrade head 2>/dev/null || {
        log_warn "Migration may have already been applied"
    }

    log_info "Database migrations completed"
}

# ==================== Print Success ====================

print_success() {
    local SERVER_IP
    if [ "$PRODUCTION_MODE" = true ]; then
        SERVER_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    else
        SERVER_IP="127.0.0.1"
    fi

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              🎉 Installation Complete! 🎉                  ${NC}║"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$PRODUCTION_MODE" = true ]; then
        echo -e "${BLUE}Frontend:${NC}     https://$FRONTEND_DOMAIN"
        echo -e "${BLUE}Backend API:${NC}   https://$BACKEND_DOMAIN"
        echo -e "${BLUE}API Docs:${NC}      https://$BACKEND_DOMAIN/api/v1/docs"
    else
        echo -e "${BLUE}Frontend:${NC}     http://${SERVER_IP}:3000"
        echo -e "${BLUE}Backend API:${NC}   http://${SERVER_IP}:8000"
        echo -e "${BLUE}API Docs:${NC}      http://${SERVER_IP}:8000/docs"
    fi

    echo ""
    echo -e "${BLUE}Install Dir:${NC}   $INSTALL_DIR"
    echo -e "${BLUE}Env File:${NC}      $INSTALL_DIR/.env"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Service Management:${NC}"
    echo "  cd $INSTALL_DIR"
    echo "  docker compose logs -f           # View all logs"
    echo "  docker compose restart           # Restart services"
    echo "  docker compose up -d --build     # Rebuild and restart"
    echo "  docker compose down              # Stop services"
    echo ""
    echo -e "${YELLOW}Or use the deploy script:${NC}"
    echo "  ./scripts/deploy.sh status       # Check service status"
    echo "  ./scripts/deploy.sh logs         # View logs"
    echo "  ./scripts/deploy.sh restart      # Restart services"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Open the frontend URL in your browser"
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
    parse_args "$@"
    print_header
    preflight_checks
    install_system_deps
    install_docker
    install_certbot
    configure_firewall
    setup_directory
    download_files
    generate_env
    obtain_ssl_certificates
    start_services
    run_migrations
    print_success
}

main "$@"
