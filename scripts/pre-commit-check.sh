#!/bin/bash
#
# Pre-commit check script for BitRun
# Runs build checks to prevent deployment failures
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔍 Running pre-commit checks..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_passed=true

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        check_passed=false
    fi
}

# Check 1: Frontend build
echo -e "${YELLOW}[1/2] Checking frontend build...${NC}"
cd "$PROJECT_ROOT/frontend"

if npm run build > /tmp/bitrun-frontend-build.log 2>&1; then
    print_status 0 "Frontend build passed"
else
    print_status 1 "Frontend build failed"
    echo ""
    echo "Build output (last 30 lines):"
    tail -30 /tmp/bitrun-frontend-build.log
fi

echo ""

# Check 2: Backend import
echo -e "${YELLOW}[2/2] Checking backend imports...${NC}"
cd "$PROJECT_ROOT/backend"

# Check if venv exists, create if not
if [ ! -f "venv/bin/python" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt --quiet
fi

if ./venv/bin/python -c "from app.api.main import app" > /tmp/bitrun-backend-import.log 2>&1; then
    print_status 0 "Backend import check passed"
else
    print_status 1 "Backend import check failed"
    echo ""
    cat /tmp/bitrun-backend-import.log
fi

echo ""
echo "====================================="

if [ "$check_passed" = true ]; then
    echo -e "${GREEN}✅ All pre-commit checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Pre-commit checks failed. Please fix the errors above.${NC}"
    exit 1
fi
