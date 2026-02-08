#!/bin/bash
# ============================================================
# BITRUN Railway 一键部署脚本
# 使用 Railway CLI 创建项目并部署所有服务
# ============================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}BITRUN — Railway 一键部署${NC}                               ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  AI-Powered Trading Agent Platform                       ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

log_info()    { echo -e "${GREEN}✅${NC} $1"; }
log_warn()    { echo -e "${YELLOW}⚠️ ${NC} $1"; }
log_error()   { echo -e "${RED}❌${NC} $1"; }
log_step()    { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }
log_substep() { echo -e "   ${CYAN}→${NC} $1"; }

# ============================================================
# Step 0: Check prerequisites
# ============================================================
check_prerequisites() {
    log_step "Step 0: 检查环境"

    # Check Railway CLI
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLI 未安装"
        echo ""
        echo "  安装方式:"
        echo "    macOS:   brew install railway"
        echo "    npm:     npm install -g @railway/cli"
        echo "    shell:   curl -fsSL https://railway.app/install.sh | sh"
        echo ""
        echo "  安装后运行: railway login"
        exit 1
    fi
    log_info "Railway CLI: $(railway --version 2>/dev/null || echo 'installed')"

    # Check login status
    if ! railway whoami &> /dev/null 2>&1; then
        log_warn "尚未登录 Railway"
        echo ""
        echo "  请先登录: railway login"
        exit 1
    fi
    log_info "已登录: $(railway whoami 2>/dev/null)"

    # Check git
    if ! command -v git &> /dev/null; then
        log_error "Git 未安装"
        exit 1
    fi
    log_info "Git: $(git --version)"

    # Check if we're in the project root
    if [ ! -f "$PROJECT_ROOT/Dockerfile.railway" ]; then
        log_error "请在 BITRUN 项目根目录运行此脚本"
        exit 1
    fi
    log_info "项目目录: $PROJECT_ROOT"
}

# ============================================================
# Step 1: Generate secrets
# ============================================================
generate_secrets() {
    log_step "Step 1: 生成安全密钥"

    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python 未安装, 无法生成密钥"
        exit 1
    fi

    JWT_SECRET=$($PYTHON_CMD -c "import secrets; print(secrets.token_urlsafe(32))")
    DATA_ENCRYPTION_KEY=$($PYTHON_CMD -c "import secrets; print(secrets.token_urlsafe(32))")

    log_info "JWT_SECRET: ${JWT_SECRET:0:8}...${JWT_SECRET: -4} (已生成)"
    log_info "DATA_ENCRYPTION_KEY: ${DATA_ENCRYPTION_KEY:0:8}...${DATA_ENCRYPTION_KEY: -4} (已生成)"
}

# ============================================================
# Step 2: Create Railway project
# ============================================================
create_project() {
    log_step "Step 2: 创建 Railway 项目"

    echo ""
    echo -e "  ${BOLD}请在 Railway Dashboard 中完成以下操作:${NC}"
    echo ""
    echo "  1. 打开 https://railway.app/new"
    echo "  2. 选择 'Empty Project' 创建空项目"
    echo "  3. 记下项目名称/URL"
    echo ""
    read -p "  项目创建完成后按 Enter 继续..."

    # Link to the project
    echo ""
    echo -e "  ${BOLD}现在将本地仓库关联到 Railway 项目:${NC}"
    echo ""

    cd "$PROJECT_ROOT"
    railway link

    log_info "项目已关联"
}

# ============================================================
# Step 3: Add databases
# ============================================================
add_databases() {
    log_step "Step 3: 添加数据库服务"

    echo ""
    echo -e "  ${BOLD}请在 Railway Dashboard 中添加数据库:${NC}"
    echo ""
    echo "  1. 在项目中点击 '+ New' → 'Database' → 'Add PostgreSQL'"
    echo "  2. 再次点击 '+ New' → 'Database' → 'Add Redis'"
    echo ""
    echo "  Railway 会自动创建数据库并生成连接 URL"
    echo ""
    read -p "  数据库添加完成后按 Enter 继续..."

    log_info "PostgreSQL + Redis 已添加"
}

# ============================================================
# Step 4: Deploy Backend
# ============================================================
deploy_backend() {
    log_step "Step 4: 部署后端服务 (Backend)"

    echo ""
    echo -e "  ${BOLD}请在 Railway Dashboard 中创建后端服务:${NC}"
    echo ""
    echo "  1. 点击 '+ New' → 'GitHub Repo' → 选择本项目仓库"
    echo "  2. 服务创建后，进入 Settings 设置:"
    echo "     - Build: Dockerfile Path → Dockerfile.railway"
    echo "     - Deploy: Health Check Path → /health"
    echo ""
    echo "  3. 进入 Variables 设置以下环境变量:"
    echo ""
    echo -e "     ${BOLD}自动注入 (引用数据库服务):${NC}"
    echo "     DATABASE_URL  → \${{Postgres.DATABASE_URL}}"
    echo "     REDIS_URL     → \${{Redis.REDIS_URL}}"
    echo ""
    echo -e "     ${BOLD}手动设置:${NC}"
    echo "     ENVIRONMENT         → production"
    echo "     JWT_SECRET           → $JWT_SECRET"
    echo "     DATA_ENCRYPTION_KEY  → $DATA_ENCRYPTION_KEY"
    echo "     CORS_ORIGINS         → (前端部署后填写, 先留空)"
    echo "     WORKER_ENABLED       → true"
    echo ""
    read -p "  后端服务配置完成后按 Enter 继续..."

    # Wait for backend to deploy and get its URL
    echo ""
    echo -e "  ${BOLD}等待后端部署完成...${NC}"
    echo ""
    echo "  请在 Railway Dashboard 查看后端部署状态"
    echo "  部署成功后，进入 Settings → Networking → Generate Domain"
    echo "  获取后端公网域名 (如: bitrun-backend-xxx.up.railway.app)"
    echo ""
    read -p "  请输入后端域名 (不含 https://): " BACKEND_DOMAIN

    if [ -z "$BACKEND_DOMAIN" ]; then
        log_warn "未输入域名, 将使用占位符"
        BACKEND_DOMAIN="your-backend.up.railway.app"
    fi

    BACKEND_URL="https://$BACKEND_DOMAIN"
    API_URL="$BACKEND_URL/api"
    WS_URL="wss://$BACKEND_DOMAIN/api/ws"

    log_info "后端 API: $API_URL"
    log_info "WebSocket: $WS_URL"
}

# ============================================================
# Step 5: Deploy Frontend
# ============================================================
deploy_frontend() {
    log_step "Step 5: 部署前端服务 (Frontend)"

    echo ""
    echo -e "  ${BOLD}请在 Railway Dashboard 中创建前端服务:${NC}"
    echo ""
    echo "  1. 点击 '+ New' → 'GitHub Repo' → 选择同一个仓库"
    echo "  2. 服务创建后，进入 Settings 设置:"
    echo "     - Root Directory → /frontend"
    echo "     - Build: 使用默认 Dockerfile"
    echo ""
    echo "  3. 进入 Variables 设置以下环境变量:"
    echo ""
    echo "     NEXT_PUBLIC_API_URL  → $API_URL"
    echo "     NEXT_PUBLIC_WS_URL   → $WS_URL"
    echo "     NEXT_PUBLIC_APP_NAME → BITRUN"
    echo ""
    read -p "  前端服务配置完成后按 Enter 继续..."

    echo ""
    echo "  请等待前端部署完成后，进入 Settings → Networking → Generate Domain"
    echo "  获取前端公网域名"
    echo ""
    read -p "  请输入前端域名 (不含 https://): " FRONTEND_DOMAIN

    if [ -z "$FRONTEND_DOMAIN" ]; then
        log_warn "未输入域名, 将使用占位符"
        FRONTEND_DOMAIN="your-frontend.up.railway.app"
    fi

    FRONTEND_URL="https://$FRONTEND_DOMAIN"

    log_info "前端 URL: $FRONTEND_URL"
}

# ============================================================
# Step 6: Update CORS
# ============================================================
update_cors() {
    log_step "Step 6: 配置跨域 (CORS)"

    echo ""
    echo -e "  ${BOLD}请更新后端服务的 CORS 配置:${NC}"
    echo ""
    echo "  1. 在 Railway Dashboard 中进入后端服务"
    echo "  2. 进入 Variables"
    echo "  3. 设置/更新:"
    echo "     CORS_ORIGINS → $FRONTEND_URL"
    echo ""
    echo "  4. 后端服务会自动重新部署"
    echo ""
    read -p "  CORS 配置完成后按 Enter 继续..."

    log_info "CORS 已配置"
}

# ============================================================
# Step 7: Verify deployment
# ============================================================
verify_deployment() {
    log_step "Step 7: 验证部署"

    echo ""
    echo -e "  ${BOLD}正在检查服务状态...${NC}"
    echo ""

    # Check backend health
    log_substep "检查后端健康状态..."
    if curl -sf "$BACKEND_URL/health" > /dev/null 2>&1; then
        HEALTH=$(curl -s "$BACKEND_URL/health")
        log_info "后端健康: $HEALTH"
    else
        log_warn "后端尚未就绪 (可能仍在部署中, 请稍后手动检查)"
        log_substep "手动检查: curl $BACKEND_URL/health"
    fi

    # Check frontend
    log_substep "检查前端状态..."
    if curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
        log_info "前端可访问"
    else
        log_warn "前端尚未就绪 (可能仍在部署中, 请稍后手动检查)"
        log_substep "手动检查: curl $FRONTEND_URL"
    fi
}

# ============================================================
# Summary
# ============================================================
print_summary() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}🎉 BITRUN 部署完成!${NC}                                    ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}服务地址:${NC}"
    echo "  ├── 前端:     $FRONTEND_URL"
    echo "  ├── 后端 API: $API_URL"
    echo "  ├── WebSocket: $WS_URL"
    echo "  └── 健康检查: $BACKEND_URL/health"
    echo ""
    echo -e "  ${BOLD}下一步:${NC}"
    echo "  1. 访问 $FRONTEND_URL 注册账户"
    echo "  2. 在「模型管理」中配置 AI Provider API Key"
    echo "  3. 在「交易所」中添加交易所 API Key"
    echo "  4. 创建第一个交易策略!"
    echo ""
    echo -e "  ${BOLD}重要提示:${NC}"
    echo "  - 请妥善保管以下密钥 (丢失后需重新生成, 将导致已有数据无法解密):"
    echo "    JWT_SECRET:           $JWT_SECRET"
    echo "    DATA_ENCRYPTION_KEY:  $DATA_ENCRYPTION_KEY"
    echo ""
    echo -e "  ${BOLD}监控:${NC}"
    echo "  - Railway Dashboard: https://railway.app/dashboard"
    echo "  - 后端日志: Railway Dashboard → Backend → Deployments → View Logs"
    echo ""
}

# ============================================================
# Main
# ============================================================
main() {
    print_header
    check_prerequisites
    generate_secrets
    create_project
    add_databases
    deploy_backend
    deploy_frontend
    update_cors
    verify_deployment
    print_summary
}

# Run
main "$@"
