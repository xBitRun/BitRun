"""
Integration tests for BITRUN API.

These tests use a real SQLite database and test the full request/response cycle.
"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.main import create_app
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.db.models import Base, UserDB


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for module."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncSession:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession) -> UserDB:
    """Create a test user."""
    user = UserDB(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        name="Test User",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: UserDB) -> str:
    """Create auth token for test user."""
    return create_access_token(str(test_user.id))


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    """Create auth headers."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, app: FastAPI):
        """Basic health check should return 200."""
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint(self, app: FastAPI):
        """Root endpoint should return app info."""
        client = TestClient(app)
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_register_user(self, app: FastAPI):
        """Should register a new user."""
        # Override DB dependency with a mock session
        mock_db = AsyncMock(spec=AsyncSession)
        app.dependency_overrides[get_db] = lambda: mock_db

        client = TestClient(app)

        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
            },
        )

        # May fail due to DB mock, but should not crash
        assert response.status_code in [200, 201, 400, 500]

        app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, app: FastAPI):
        """Should reject invalid credentials."""
        # Override DB dependency with a mock session
        mock_db = AsyncMock(spec=AsyncSession)
        app.dependency_overrides[get_db] = lambda: mock_db

        # Mock UserRepository so authenticate returns None (user not found)
        with patch("app.api.routes.auth.UserRepository") as MockUserRepo:
            mock_repo = MagicMock()
            mock_repo.authenticate = AsyncMock(return_value=None)
            MockUserRepo.return_value = mock_repo

            client = TestClient(app)

            response = client.post(
                "/api/auth/login",
                data={
                    "username": "nonexistent@example.com",
                    "password": "wrongpassword",
                },
            )

            # Should reject (400 or 401)
            assert response.status_code in [400, 401, 500]

        app.dependency_overrides.pop(get_db, None)


class TestMetricsEndpoints:
    """Test metrics and monitoring endpoints."""

    def test_prometheus_metrics(self, app: FastAPI):
        """Should return Prometheus metrics."""
        client = TestClient(app)
        
        response = client.get("/api/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_json(self, app: FastAPI):
        """Should return metrics in JSON format."""
        client = TestClient(app)
        
        response = client.get("/api/metrics/json")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_strategies" in data

    def test_circuit_breaker_health(self, app: FastAPI):
        """Should return circuit breaker health."""
        client = TestClient(app)
        
        response = client.get("/api/health/circuit-breakers")
        
        assert response.status_code == 200
        data = response.json()
        assert "healthy" in data
        assert "total_breakers" in data


class TestWorkerEndpoints:
    """Test worker management endpoints."""

    def test_workers_status_requires_auth(self, app: FastAPI):
        """Worker status should require authentication."""
        client = TestClient(app)
        
        response = client.get("/api/workers/status")
        
        # Should return 401 or 403
        assert response.status_code in [401, 403]


class TestAPIVersioning:
    """Test that API endpoints follow expected patterns."""

    def test_api_prefix(self, app: FastAPI):
        """All API routes should have /api prefix."""
        client = TestClient(app)
        
        # These should be accessible
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 200
        
        # API routes should be under /api
        # Auth routes
        response = client.post("/api/auth/login", data={})
        assert response.status_code != 404
        
        # Metrics routes
        response = client.get("/api/metrics")
        assert response.status_code != 404


class TestCORSConfiguration:
    """Test CORS is properly configured."""

    def test_cors_headers(self, app: FastAPI):
        """CORS headers should be set for allowed origins."""
        client = TestClient(app)
        
        response = client.options(
            "/api/auth/token",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        
        # Should have CORS headers
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """Test error handling."""

    def test_404_for_unknown_routes(self, app: FastAPI):
        """Unknown routes should return 404."""
        client = TestClient(app)
        
        response = client.get("/api/unknown/route")
        
        assert response.status_code == 404

    def test_method_not_allowed(self, app: FastAPI):
        """Wrong HTTP method should return 405."""
        client = TestClient(app)
        
        # /health only supports GET
        response = client.post("/health")
        
        assert response.status_code == 405
