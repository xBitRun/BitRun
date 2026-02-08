"""
Pytest configuration and fixtures for BITRUN tests.
"""

import asyncio
from datetime import UTC, datetime
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, UserDB, StrategyDB, ExchangeAccountDB
from app.core.security import hash_password


# Use an in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> UserDB:
    """Create a test user in the database."""
    user = UserDB(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        name="Test User",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_account(db_session: AsyncSession, test_user: UserDB) -> ExchangeAccountDB:
    """Create a test exchange account."""
    account = ExchangeAccountDB(
        id=uuid4(),
        user_id=test_user.id,
        name="Test Binance Account",
        exchange="binance",
        encrypted_api_key="encrypted_api_key_data",
        encrypted_api_secret="encrypted_api_secret_data",
        is_testnet=True,
        is_connected=True,
        last_connected_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture
async def test_strategy(
    db_session: AsyncSession,
    test_user: UserDB,
    test_account: ExchangeAccountDB,
) -> StrategyDB:
    """Create a test strategy."""
    strategy = StrategyDB(
        id=uuid4(),
        user_id=test_user.id,
        account_id=test_account.id,
        name="Test Strategy",
        prompt="Test prompt for trading",
        status="draft",
        config={
            "execution_interval_minutes": 30,
            "max_positions": 3,
            "symbols": ["BTC", "ETH"],
        },
        created_at=datetime.now(UTC),
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest.fixture
def sample_decision_response() -> dict:
    """Sample AI decision response for testing."""
    return {
        "chain_of_thought": "Market shows bullish momentum...",
        "market_assessment": "Overall bullish trend",
        "decisions": [
            {
                "symbol": "BTC",
                "action": "open_long",
                "leverage": 5,
                "position_size_usd": 1000,
                "entry_price": 50000,
                "stop_loss": 48000,
                "take_profit": 55000,
                "confidence": 75,
                "risk_usd": 100,
                "reasoning": "Strong support at 50k"
            }
        ],
        "overall_confidence": 75
    }


@pytest.fixture
def sample_account_state() -> dict:
    """Sample account state for testing."""
    return {
        "equity": 10000.0,
        "available_balance": 8000.0,
        "total_margin_used": 2000.0,
        "unrealized_pnl": 500.0,
        "positions": []
    }


@pytest.fixture
def mock_trader():
    """Create a mock trader for testing."""
    from app.traders.base import AccountState, OrderResult, Position
    
    trader = AsyncMock()
    trader.exchange_name = "mock"
    trader.testnet = True
    trader._initialized = True
    
    trader.initialize = AsyncMock(return_value=True)
    trader.close = AsyncMock()
    
    trader.get_account_state = AsyncMock(return_value=AccountState(
        equity=10000.0,
        available_balance=8000.0,
        total_margin_used=2000.0,
        unrealized_pnl=500.0,
        positions=[],
    ))
    
    trader.get_positions = AsyncMock(return_value=[])
    trader.get_position = AsyncMock(return_value=None)
    trader.get_market_price = AsyncMock(return_value=50000.0)
    
    trader.place_market_order = AsyncMock(return_value=OrderResult(
        success=True,
        order_id="test_order_123",
        filled_size=0.1,
        filled_price=50000.0,
        status="filled",
    ))
    
    trader.place_limit_order = AsyncMock(return_value=OrderResult(
        success=True,
        order_id="test_limit_123",
        status="open",
    ))
    
    trader.cancel_order = AsyncMock(return_value=True)
    trader.cancel_all_orders = AsyncMock(return_value=0)
    trader.close_position = AsyncMock(return_value=OrderResult(success=True))
    trader.set_leverage = AsyncMock(return_value=True)
    
    return trader


@pytest.fixture
def mock_redis():
    """Create a mock Redis service for testing."""
    redis = MagicMock()
    redis.redis = AsyncMock()
    
    # Mock common Redis operations
    redis.ping = AsyncMock(return_value=True)
    redis.set = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    
    # Mock setex (used for expiring keys)
    redis.redis.setex = AsyncMock()
    redis.redis.get = AsyncMock(return_value=None)
    redis.redis.sadd = AsyncMock()
    redis.redis.smembers = AsyncMock(return_value=set())
    redis.redis.delete = AsyncMock()
    
    # Mock JWT blacklist operations
    redis.blacklist_token = AsyncMock(return_value=True)
    redis.is_token_blacklisted = AsyncMock(return_value=False)
    
    # Mock login failure tracking
    redis.is_account_locked = AsyncMock(return_value=False)
    redis.track_login_failure = AsyncMock(return_value=1)
    redis.clear_login_failures = AsyncMock(return_value=True)
    
    return redis


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client for testing."""
    client = AsyncMock()
    
    client.generate = AsyncMock(return_value={
        "content": '{"chain_of_thought": "test", "decisions": []}',
        "tokens_used": 100,
        "model": "test-model",
    })
    
    return client
