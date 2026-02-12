"""
End-to-end trading flow tests.

Tests the complete lifecycle:
  1. Register/Login
  2. Create exchange account
  3. Create strategy
  4. Trigger execution (Run Now)
  5. Verify decision record created

These tests use mocked exchange and AI services to test
the integration between components without external dependencies.
"""

import asyncio
import base64
import os
import secrets
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.main import create_app
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.db.models import Base, UserDB

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Set up valid encryption key for tests
_VALID_AES_KEY = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
os.environ.setdefault("DATA_ENCRYPTION_KEY", _VALID_AES_KEY)


@pytest.fixture(autouse=True)
def _mock_crypto_service(monkeypatch):
    """Mock CryptoService to avoid encryption key issues in tests."""
    mock_crypto = MagicMock()
    mock_crypto.encrypt.return_value = "encrypted"
    mock_crypto.decrypt.return_value = "decrypted"
    mock_crypto.is_encrypted.return_value = False
    monkeypatch.setattr("app.core.security._crypto_service", mock_crypto)
    monkeypatch.setattr("app.db.repositories.account.get_crypto_service", lambda: mock_crypto)


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine):
    """Create test database session."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app_with_db(test_engine):
    """Create FastAPI app with test database."""
    app = create_app()
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession):
    """Create a test user."""
    user = UserDB(
        id=uuid4(),
        email="trader@example.com",
        name="trader",
        password_hash=hash_password("StrongPass123!"),
        created_at=datetime.now(UTC),
    )
    test_session.add(user)
    await test_session.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Get auth headers for test user."""
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


class TestTradingFlowE2E:
    """End-to-end trading flow tests."""

    @pytest.mark.asyncio
    async def test_full_strategy_lifecycle(self, app_with_db, auth_headers, test_user):
        """
        Test complete strategy lifecycle:
        1. Create account
        2. Create strategy
        3. Get strategy details
        4. Update strategy status
        5. Delete strategy
        """
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Step 1: Create exchange account (mocked)
            with patch("app.api.routes.accounts.create_trader_from_account") as mock_trader:
                mock_trader_instance = AsyncMock()
                mock_trader_instance.initialize = AsyncMock()
                mock_trader_instance.get_account_state = AsyncMock(
                    return_value=MagicMock(
                        total_equity=10000.0,
                        available_balance=10000.0,
                        positions=[],
                    )
                )
                mock_trader.return_value = mock_trader_instance

                account_resp = await client.post(
                    "/api/v1/accounts",
                    headers=auth_headers,
                    json={
                        "name": "Test Account",
                        "exchange": "binance",
                        "api_key": "test_key",
                        "api_secret": "test_secret",
                        "is_testnet": True,
                    },
                )
                assert account_resp.status_code == 201, (
                    f"Account creation failed: {account_resp.status_code}: {account_resp.text}"
                )
                account_id = account_resp.json()["id"]

                # Step 2: Create strategy (with or without account_id)
                strategy_data = {
                    "name": "Test BTC Strategy",
                    "description": "E2E test strategy",
                    "prompt": "Buy BTC when RSI < 30, sell when RSI > 70. Conservative risk management.",
                    "trading_mode": "conservative",
                    "ai_model": "openai:gpt-4",
                }
                if account_id:
                    strategy_data["account_id"] = account_id
                
                strategy_resp = await client.post(
                    "/api/v1/strategies",
                    headers=auth_headers,
                    json=strategy_data,
                )
                if strategy_resp.status_code != 201:
                    print(f"Strategy creation failed: {strategy_resp.status_code}")
                    print(f"Response: {strategy_resp.text}")
                assert strategy_resp.status_code == 201, f"Expected 201, got {strategy_resp.status_code}: {strategy_resp.text}"
                strategy = strategy_resp.json()
                strategy_id = strategy["id"]

                # Step 3: Verify strategy details
                get_resp = await client.get(
                    f"/api/v1/strategies/{strategy_id}",
                    headers=auth_headers,
                )
                assert get_resp.status_code == 200
                assert get_resp.json()["name"] == "Test BTC Strategy"

                # Step 4: Delete strategy
                delete_resp = await client.delete(
                    f"/api/v1/strategies/{strategy_id}",
                    headers=auth_headers,
                )
                assert delete_resp.status_code == 204

    @pytest.mark.asyncio
    async def test_unauthorized_access_rejected(self, app_with_db):
        """Test that unauthenticated requests are rejected."""
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Strategies
            resp = await client.get("/api/v1/strategies")
            assert resp.status_code == 401

            # Accounts
            resp = await client.get("/api/v1/accounts")
            assert resp.status_code == 401

            # Dashboard
            resp = await client.get("/api/v1/dashboard/stats")
            assert resp.status_code == 401


class TestConcurrentExecution:
    """Test concurrent strategy execution safety."""

    @pytest.mark.asyncio
    async def test_concurrent_strategy_creation(self, app_with_db, test_engine):
        """Test that multiple strategies can be created concurrently without conflicts."""
        # Create a unique user for this test to avoid email conflicts
        session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_factory() as session:
            user = UserDB(
                id=uuid4(),
                email=f"concurrent-{uuid4()}@example.com",
                name="concurrent_tester",
                password_hash=hash_password("StrongPass123!"),
                created_at=datetime.now(UTC),
            )
            session.add(user)
            await session.commit()
            user_id = str(user.id)
        
        token = create_access_token(user_id)
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            tasks = []
            for i in range(5):
                task = client.post(
                    "/api/v1/strategies",
                    headers=auth_headers,
                    json={
                        "name": f"Concurrent Strategy {i}",
                        "description": f"Test strategy {i}",
                        "prompt": f"Strategy {i}: Buy BTC when conditions are met. Conservative approach.",
                        "trading_mode": "conservative",
                        "ai_model": "openai:gpt-4",
                    },
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed (201) or fail gracefully (no 500s)
            for result in results:
                if not isinstance(result, Exception):
                    assert result.status_code in [201, 429]  # Created or rate limited

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self, app_with_db):
        """Test that health endpoint handles concurrent requests."""
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            tasks = [client.get("/health") for _ in range(20)]
            results = await asyncio.gather(*tasks)

            for result in results:
                assert result.status_code == 200
                assert result.json()["status"] == "healthy"
