#!/bin/bash
# BITRUN Railway Startup Script
# Handles database URL conversion, migrations, and server startup

set -e

echo "🚀 Starting BITRUN Backend on Railway..."
echo "📅 $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# Railway provides PORT, default to 8000
export PORT=${PORT:-8000}
echo "📍 Port: $PORT"
echo "🌍 Environment: ${ENVIRONMENT:-development}"

# ============================================================
# Convert DATABASE_URL to asyncpg format
# Railway provides: postgresql://user:pass@host:port/db
# We need: postgresql+asyncpg://user:pass@host:port/db
# ============================================================
if [ -n "$DATABASE_URL" ]; then
    if [[ "$DATABASE_URL" != *"+asyncpg"* ]]; then
        export DATABASE_URL="${DATABASE_URL/postgresql:\/\//postgresql+asyncpg:\/\/}"
        echo "✅ DATABASE_URL converted to asyncpg format"
    else
        echo "✅ DATABASE_URL already in asyncpg format"
    fi
else
    echo "⚠️  DATABASE_URL not set, using default"
fi

# ============================================================
# Convert REDIS_URL if needed
# Railway provides: redis://default:pass@host:port
# Ensure compatibility with our Redis service
# ============================================================
if [ -n "$REDIS_URL" ]; then
    echo "✅ REDIS_URL configured"
else
    echo "⚠️  REDIS_URL not set, using default"
fi

# ============================================================
# Generate secrets if not provided (for demo/testing only)
# In production, these MUST be set via Railway environment variables
# ============================================================
if [ -z "$JWT_SECRET" ]; then
    export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "⚠️  JWT_SECRET auto-generated (set explicitly for production)"
fi

if [ -z "$DATA_ENCRYPTION_KEY" ]; then
    export DATA_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "⚠️  DATA_ENCRYPTION_KEY auto-generated (set explicitly for production)"
fi

# ============================================================
# Wait for database to be ready
# Uses asyncpg (already installed) for a proper connection check
# ============================================================
echo "⏳ Waiting for database..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if python3 -c "
import asyncio, sys, os

async def check():
    url = os.environ.get('DATABASE_URL', '')
    # asyncpg expects postgresql:// not postgresql+asyncpg://
    url = url.replace('+asyncpg://', '://')
    if not url:
        sys.exit(1)
    import asyncpg
    conn = await asyncpg.connect(url)
    await conn.execute('SELECT 1')
    await conn.close()

try:
    asyncio.run(check())
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ Database is ready"
        break
    fi

    retry_count=$((retry_count + 1))
    echo "⏳ Database not ready, retrying... ($retry_count/$max_retries)"
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo "❌ Database connection failed after $max_retries attempts"
    echo "   DATABASE_URL is set: $([ -n \"$DATABASE_URL\" ] && echo 'yes' || echo 'no')"
    exit 1
fi

# ============================================================
# Run database migrations
# ============================================================
echo "📦 Running database migrations..."
cd /app
alembic upgrade head
echo "✅ Migrations completed"

# ============================================================
# Start the server
# ============================================================
echo "🚀 Starting uvicorn on port $PORT..."
exec uvicorn app.api.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    --log-level info
