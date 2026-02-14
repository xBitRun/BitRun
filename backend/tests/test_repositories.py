"""
Tests for database repository layer.

Covers: UserRepository, AccountRepository, StrategyRepository (unified),
        DecisionRepository (agent-scoped), AgentRepository
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Base,
    UserDB,
    ExchangeAccountDB,
    StrategyDB,
    DecisionRecordDB,
    AgentDB,
)
from app.db.repositories.user import UserRepository
from app.db.repositories.account import AccountRepository
from app.db.repositories.strategy import StrategyRepository
from app.db.repositories.decision import DecisionRepository
from app.db.repositories.agent import AgentRepository


# ============================================================================
# UserRepository Tests
# ============================================================================

class TestUserRepository:
    """Tests for UserRepository"""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a new user"""
        repo = UserRepository(db_session)
        
        user = await repo.create(
            email="newuser@example.com",
            password="securepassword123",
            name="New User"
        )
        
        assert user is not None
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.is_active is True
        assert user.password_hash != "securepassword123"  # Should be hashed

    @pytest.mark.asyncio
    async def test_create_user_lowercase_email(self, db_session: AsyncSession):
        """Test that email is lowercased on creation"""
        repo = UserRepository(db_session)
        
        user = await repo.create(
            email="TestUser@Example.COM",
            password="password",
            name="Test"
        )
        
        assert user.email == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession, test_user: UserDB):
        """Test getting user by ID"""
        repo = UserRepository(db_session)
        
        user = await repo.get_by_id(test_user.id)
        
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test getting non-existent user by ID"""
        repo = UserRepository(db_session)
        
        user = await repo.get_by_id(uuid.uuid4())
        
        assert user is None

    @pytest.mark.asyncio
    async def test_get_by_email(self, db_session: AsyncSession, test_user: UserDB):
        """Test getting user by email"""
        repo = UserRepository(db_session)
        
        user = await repo.get_by_email(test_user.email)
        
        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_by_email_case_insensitive(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test that email lookup is case insensitive"""
        repo = UserRepository(db_session)
        
        user = await repo.get_by_email(test_user.email.upper())
        
        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_success(self, db_session: AsyncSession):
        """Test successful authentication"""
        repo = UserRepository(db_session)
        
        # Create user with known password
        await repo.create(
            email="auth@test.com",
            password="correctpassword",
            name="Auth User"
        )
        await db_session.commit()
        
        user = await repo.authenticate("auth@test.com", "correctpassword")
        
        assert user is not None
        assert user.email == "auth@test.com"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session: AsyncSession):
        """Test authentication with wrong password"""
        repo = UserRepository(db_session)
        
        await repo.create(
            email="auth2@test.com",
            password="correctpassword",
            name="Auth User"
        )
        await db_session.commit()
        
        user = await repo.authenticate("auth2@test.com", "wrongpassword")
        
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, db_session: AsyncSession):
        """Test authentication with non-existent user"""
        repo = UserRepository(db_session)
        
        user = await repo.authenticate("nonexistent@test.com", "password")
        
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, db_session: AsyncSession):
        """Test authentication with inactive user"""
        repo = UserRepository(db_session)
        
        # Create user and deactivate
        user = await repo.create(
            email="inactive@test.com",
            password="password",
            name="Inactive User"
        )
        user.is_active = False
        await db_session.commit()
        
        result = await repo.authenticate("inactive@test.com", "password")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_user(self, db_session: AsyncSession, test_user: UserDB):
        """Test updating user fields"""
        repo = UserRepository(db_session)
        
        updated = await repo.update(test_user.id, name="Updated Name")
        
        assert updated is not None
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, db_session: AsyncSession):
        """Test updating non-existent user"""
        repo = UserRepository(db_session)
        
        result = await repo.update(uuid.uuid4(), name="Test")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_ignores_disallowed_fields(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test that update ignores fields not in allowed list"""
        repo = UserRepository(db_session)
        original_email = test_user.email
        
        await repo.update(test_user.id, email="hacker@evil.com", name="Good Name")
        
        # Email should not change
        user = await repo.get_by_id(test_user.id)
        assert user.email == original_email
        assert user.name == "Good Name"

    @pytest.mark.asyncio
    async def test_change_password(self, db_session: AsyncSession):
        """Test changing user password"""
        repo = UserRepository(db_session)
        
        user = await repo.create(
            email="changepass@test.com",
            password="oldpassword",
            name="Test"
        )
        await db_session.commit()
        
        result = await repo.change_password(user.id, "newpassword")
        
        assert result is True
        
        # Verify new password works
        await db_session.commit()
        auth_user = await repo.authenticate("changepass@test.com", "newpassword")
        assert auth_user is not None

    @pytest.mark.asyncio
    async def test_change_password_not_found(self, db_session: AsyncSession):
        """Test changing password for non-existent user"""
        repo = UserRepository(db_session)
        
        result = await repo.change_password(uuid.uuid4(), "newpassword")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_user(self, db_session: AsyncSession):
        """Test deleting user"""
        repo = UserRepository(db_session)
        
        user = await repo.create(
            email="todelete@test.com",
            password="password",
            name="Delete Me"
        )
        await db_session.commit()
        user_id = user.id
        
        result = await repo.delete(user_id)
        
        assert result is True
        
        # Verify user is deleted
        deleted = await repo.get_by_id(user_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, db_session: AsyncSession):
        """Test deleting non-existent user"""
        repo = UserRepository(db_session)
        
        result = await repo.delete(uuid.uuid4())
        
        assert result is False


# ============================================================================
# AccountRepository Tests
# ============================================================================

class TestAccountRepository:
    """Tests for AccountRepository"""

    @pytest.fixture
    def mock_crypto(self):
        """Mock crypto service for testing"""
        with patch("app.db.repositories.account.get_crypto_service") as mock:
            crypto = MagicMock()
            crypto.encrypt.side_effect = lambda x: f"encrypted_{x}" if x else None
            crypto.decrypt.side_effect = lambda x: x.replace("encrypted_", "") if x else None
            mock.return_value = crypto
            yield crypto

    @pytest.mark.asyncio
    async def test_create_account(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test creating a new exchange account"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Test Binance",
            exchange="binance",
            is_testnet=True,
            api_key="my_api_key",
            api_secret="my_api_secret",
        )
        
        assert account is not None
        assert account.name == "Test Binance"
        assert account.exchange == "binance"
        assert account.is_testnet is True
        assert account.encrypted_api_key == "encrypted_my_api_key"
        assert account.encrypted_api_secret == "encrypted_my_api_secret"

    @pytest.mark.asyncio
    async def test_create_account_lowercase_exchange(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test that exchange name is lowercased"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Test",
            exchange="BINANCE",
        )
        
        assert account.exchange == "binance"

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, db_session: AsyncSession, test_account: ExchangeAccountDB, mock_crypto
    ):
        """Test getting account by ID"""
        repo = AccountRepository(db_session)
        
        account = await repo.get_by_id(test_account.id)
        
        assert account is not None
        assert account.id == test_account.id

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_filter(
        self, db_session: AsyncSession, test_account: ExchangeAccountDB, 
        test_user: UserDB, mock_crypto
    ):
        """Test getting account with user ID filter"""
        repo = AccountRepository(db_session)
        
        # Should find account with correct user
        account = await repo.get_by_id(test_account.id, test_user.id)
        assert account is not None
        
        # Should not find account with different user
        account = await repo.get_by_id(test_account.id, uuid.uuid4())
        assert account is None

    @pytest.mark.asyncio
    async def test_get_by_user(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test getting all accounts for a user"""
        repo = AccountRepository(db_session)
        
        # Create multiple accounts
        await repo.create(user_id=test_user.id, name="Account 1", exchange="binance")
        await repo.create(user_id=test_user.id, name="Account 2", exchange="okx")
        await db_session.commit()
        
        accounts = await repo.get_by_user(test_user.id)
        
        assert len(accounts) >= 2

    @pytest.mark.asyncio
    async def test_get_by_user_filter_exchange(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test filtering accounts by exchange"""
        repo = AccountRepository(db_session)
        
        await repo.create(user_id=test_user.id, name="Binance 1", exchange="binance")
        await repo.create(user_id=test_user.id, name="OKX 1", exchange="okx")
        await db_session.commit()
        
        binance_accounts = await repo.get_by_user(test_user.id, exchange="binance")
        
        assert all(a.exchange == "binance" for a in binance_accounts)

    @pytest.mark.asyncio
    async def test_update_account(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test updating account fields"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Original",
            exchange="binance",
        )
        await db_session.commit()
        
        updated = await repo.update(
            account.id, test_user.id, name="Updated Name"
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_account_credentials(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test updating account credentials"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Test",
            exchange="binance",
            api_key="old_key",
        )
        await db_session.commit()
        
        updated = await repo.update(
            account.id, test_user.id, api_key="new_key"
        )
        
        assert updated is not None
        assert updated.encrypted_api_key == "encrypted_new_key"

    @pytest.mark.asyncio
    async def test_update_connection_status(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test updating connection status"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Test",
            exchange="binance",
        )
        await db_session.commit()
        
        updated = await repo.update_connection_status(
            account.id, is_connected=True
        )
        
        assert updated is not None
        assert updated.is_connected is True
        assert updated.last_connected_at is not None

    @pytest.mark.asyncio
    async def test_update_connection_status_with_error(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test updating connection status with error"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Test",
            exchange="binance",
        )
        await db_session.commit()
        
        updated = await repo.update_connection_status(
            account.id, is_connected=False, error="Connection refused"
        )
        
        assert updated is not None
        assert updated.is_connected is False
        assert updated.connection_error == "Connection refused"

    @pytest.mark.asyncio
    async def test_get_decrypted_credentials(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test getting decrypted credentials"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="Test",
            exchange="binance",
            api_key="my_key",
            api_secret="my_secret",
        )
        await db_session.commit()
        
        credentials = await repo.get_decrypted_credentials(account.id, test_user.id)
        
        assert credentials is not None
        assert credentials["api_key"] == "my_key"
        assert credentials["api_secret"] == "my_secret"

    @pytest.mark.asyncio
    async def test_delete_account(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test deleting account"""
        repo = AccountRepository(db_session)
        
        account = await repo.create(
            user_id=test_user.id,
            name="To Delete",
            exchange="binance",
        )
        await db_session.commit()
        account_id = account.id
        
        result = await repo.delete(account_id, test_user.id)
        
        assert result is True
        
        deleted = await repo.get_by_id(account_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_account_not_found(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test deleting non-existent account returns False"""
        repo = AccountRepository(db_session)
        
        result = await repo.delete(uuid.uuid4(), test_user.id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_update_account_not_found(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test updating non-existent account returns None"""
        repo = AccountRepository(db_session)
        
        result = await repo.update(uuid.uuid4(), test_user.id, name="New Name")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_connection_status_not_found(
        self, db_session: AsyncSession, mock_crypto
    ):
        """Test updating connection status for non-existent account returns None"""
        repo = AccountRepository(db_session)
        
        result = await repo.update_connection_status(
            uuid.uuid4(), is_connected=True
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_decrypted_credentials_not_found(
        self, db_session: AsyncSession, test_user: UserDB, mock_crypto
    ):
        """Test getting credentials for non-existent account returns None"""
        repo = AccountRepository(db_session)
        
        credentials = await repo.get_decrypted_credentials(
            uuid.uuid4(), test_user.id
        )
        
        assert credentials is None

    @pytest.mark.asyncio
    async def test_get_decrypted_credentials_decrypt_failure(
        self, db_session: AsyncSession, test_user: UserDB, caplog
    ):
        """Test decryption failure returns None and logs error"""
        import logging
        
        with patch("app.db.repositories.account.get_crypto_service") as mock:
            crypto = MagicMock()
            crypto.encrypt.side_effect = lambda x: f"encrypted_{x}" if x else None
            # Decrypt raises exception
            crypto.decrypt.side_effect = Exception("Decryption failed")
            mock.return_value = crypto
            
            repo = AccountRepository(db_session)
            
            account = await repo.create(
                user_id=test_user.id,
                name="Test",
                exchange="binance",
                api_key="my_key",
            )
            await db_session.commit()
            
            with caplog.at_level(logging.ERROR):
                credentials = await repo.get_decrypted_credentials(
                    account.id, test_user.id
                )
            
            assert credentials is None
            assert any("Failed to decrypt" in record.message for record in caplog.records)


# ============================================================================
# StrategyRepository Tests (unified model - pure logic template)
# ============================================================================

class TestStrategyRepository:
    """Tests for StrategyRepository (unified strategy model)"""

    @pytest.mark.asyncio
    async def test_create_ai_strategy(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test creating a new AI strategy"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Test AI Strategy",
            symbols=["BTC", "ETH"],
            config={"prompt": "Buy low, sell high", "trading_mode": "conservative"},
            description="A simple AI strategy",
        )
        
        assert strategy is not None
        assert strategy.name == "Test AI Strategy"
        assert strategy.type == "ai"
        assert strategy.symbols == ["BTC", "ETH"]
        assert strategy.config["prompt"] == "Buy low, sell high"
        assert strategy.visibility == "private"

    @pytest.mark.asyncio
    async def test_create_grid_strategy(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test creating a grid strategy"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id,
            type="grid",
            name="Grid BTC",
            symbols=["BTC"],
            config={"upper_price": 60000, "lower_price": 50000, "grid_count": 10, "total_investment": 1000},
        )
        
        assert strategy.type == "grid"
        assert strategy.symbols == ["BTC"]
        assert strategy.config["grid_count"] == 10

    @pytest.mark.asyncio
    async def test_create_strategy_with_marketplace_fields(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test creating strategy with marketplace/pricing fields"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Public Strategy",
            symbols=["BTC"],
            config={"prompt": "test"},
            visibility="public",
            category="trend_following",
            tags=["BTC", "momentum"],
            is_paid=True,
            price_monthly=9.99,
            pricing_model="monthly",
        )
        
        assert strategy.visibility == "public"
        assert strategy.category == "trend_following"
        assert strategy.tags == ["BTC", "momentum"]
        assert strategy.is_paid is True
        assert strategy.price_monthly == 9.99
        assert strategy.pricing_model == "monthly"

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test getting strategy by ID"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.get_by_id(test_strategy.id)
        
        assert strategy is not None
        assert strategy.id == test_strategy.id

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_filter(
        self, db_session: AsyncSession, test_strategy: StrategyDB,
        test_user: UserDB
    ):
        """Test getting strategy with user filter"""
        repo = StrategyRepository(db_session)
        
        # Should find with correct user
        strategy = await repo.get_by_id(test_strategy.id, test_user.id)
        assert strategy is not None
        
        # Should not find with different user
        strategy = await repo.get_by_id(test_strategy.id, uuid.uuid4())
        assert strategy is None

    @pytest.mark.asyncio
    async def test_get_by_user(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test getting all strategies for user"""
        repo = StrategyRepository(db_session)
        
        await repo.create(
            user_id=test_user.id, type="ai", name="Strategy 1",
            symbols=["BTC"], config={"prompt": "test"},
        )
        await repo.create(
            user_id=test_user.id, type="grid", name="Strategy 2",
            symbols=["ETH"], config={"upper_price": 100, "lower_price": 50},
        )
        await db_session.commit()
        
        strategies = await repo.get_by_user(test_user.id)
        
        assert len(strategies) >= 2

    @pytest.mark.asyncio
    async def test_get_by_user_filter_type(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test filtering strategies by type"""
        repo = StrategyRepository(db_session)
        
        await repo.create(
            user_id=test_user.id, type="ai", name="AI Strat",
            symbols=["BTC"], config={"prompt": "test"},
        )
        await repo.create(
            user_id=test_user.id, type="grid", name="Grid Strat",
            symbols=["BTC"], config={},
        )
        await db_session.commit()
        
        ai_strategies = await repo.get_by_user(test_user.id, type_filter="ai")
        
        assert all(s.type == "ai" for s in ai_strategies)

    @pytest.mark.asyncio
    async def test_update_strategy(
        self, db_session: AsyncSession, test_strategy: StrategyDB,
        test_user: UserDB
    ):
        """Test updating strategy fields"""
        repo = StrategyRepository(db_session)
        
        updated = await repo.update(
            test_strategy.id, test_user.id,
            name="Updated Name",
            description="New description",
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "New description"

    @pytest.mark.asyncio
    async def test_update_config(
        self, db_session: AsyncSession, test_strategy: StrategyDB,
        test_user: UserDB
    ):
        """Test updating strategy config creates version snapshot"""
        repo = StrategyRepository(db_session)
        
        updated = await repo.update(
            test_strategy.id, test_user.id,
            config={"prompt": "New AI prompt for trading"},
        )
        
        assert updated is not None
        assert updated.config["prompt"] == "New AI prompt for trading"

    @pytest.mark.asyncio
    async def test_update_strategy_not_found(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test updating non-existent strategy returns None"""
        repo = StrategyRepository(db_session)
        
        result = await repo.update(uuid.uuid4(), test_user.id, name="Test")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fork_public_strategy(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test forking a public strategy"""
        repo = StrategyRepository(db_session)
        
        # Create a public strategy
        source = await repo.create(
            user_id=test_user.id, type="ai", name="Public Strategy",
            symbols=["BTC"], config={"prompt": "test"},
            visibility="public",
        )
        await db_session.commit()
        
        # Fork it to a different user
        forker_id = uuid.uuid4()
        forked = await repo.fork(source.id, forker_id)
        
        assert forked is not None
        assert forked.user_id == forker_id
        assert forked.name == "Public Strategy"
        assert forked.forked_from == source.id
        assert forked.visibility == "private"  # forked strategies are private

    @pytest.mark.asyncio
    async def test_fork_private_strategy_fails(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test that forking a private strategy returns None"""
        repo = StrategyRepository(db_session)
        
        source = await repo.create(
            user_id=test_user.id, type="ai", name="Private Strategy",
            symbols=["BTC"], config={"prompt": "test"},
            visibility="private",
        )
        await db_session.commit()
        
        forked = await repo.fork(source.id, uuid.uuid4())
        
        assert forked is None

    @pytest.mark.asyncio
    async def test_delete_strategy(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test deleting strategy"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id, type="ai", name="To Delete",
            symbols=["BTC"], config={"prompt": "test"},
        )
        await db_session.commit()
        strategy_id = strategy.id
        
        result = await repo.delete(strategy_id, test_user.id)
        
        assert result is True
        
        deleted = await repo.get_by_id(strategy_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_strategy_not_found(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test deleting non-existent strategy returns False"""
        repo = StrategyRepository(db_session)
        
        result = await repo.delete(uuid.uuid4(), test_user.id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_version_history(
        self, db_session: AsyncSession, test_strategy: StrategyDB,
        test_user: UserDB
    ):
        """Test that updating config creates version snapshots"""
        repo = StrategyRepository(db_session)
        
        # Make a config change
        await repo.update(
            test_strategy.id, test_user.id,
            config={"prompt": "Updated prompt v2"},
            change_note="Updated trading logic",
        )
        await db_session.commit()
        
        versions = await repo.get_versions(test_strategy.id, test_user.id)
        
        assert len(versions) >= 1
        # Version should contain the OLD state (snapshot before change)
        assert versions[0].version == 1


# ============================================================================
# DecisionRepository Tests (now agent-scoped)
# ============================================================================

class TestDecisionRepository:
    """Tests for DecisionRepository (decisions are linked to agents, not strategies)"""

    @pytest.mark.asyncio
    async def test_create_decision(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test creating a decision record"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System prompt",
            user_prompt="User prompt",
            raw_response='{"decisions": []}',
            chain_of_thought="Analysis...",
            market_assessment="Bullish",
            decisions=[{"action": "buy", "symbol": "BTC"}],
            overall_confidence=75,
            ai_model="gpt-4",
            tokens_used=1000,
            latency_ms=500,
        )
        
        assert decision is not None
        assert decision.agent_id == test_agent.id
        assert decision.overall_confidence == 75
        assert len(decision.decisions) == 1

    @pytest.mark.asyncio
    async def test_create_debate_decision(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test creating a debate decision record"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            is_debate=True,
            debate_models=["gpt-4", "claude-3"],
            debate_responses=[{"model": "gpt-4"}, {"model": "claude-3"}],
            debate_consensus_mode="majority",
            debate_agreement_score=0.85,
        )
        
        assert decision.is_debate is True
        assert len(decision.debate_models) == 2
        assert decision.debate_agreement_score == 0.85

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test getting decision by ID"""
        repo = DecisionRepository(db_session)
        
        created = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        decision = await repo.get_by_id(created.id)
        
        assert decision is not None
        assert decision.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_agent(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test getting decisions for an agent"""
        repo = DecisionRepository(db_session)
        
        for i in range(3):
            await repo.create(
                agent_id=test_agent.id,
                system_prompt=f"System {i}",
                user_prompt=f"User {i}",
                raw_response="{}",
            )
        await db_session.commit()
        
        decisions = await repo.get_by_agent(test_agent.id)
        
        assert len(decisions) >= 3

    @pytest.mark.asyncio
    async def test_get_by_agent_executed_only(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test filtering for executed decisions only"""
        repo = DecisionRepository(db_session)
        
        d1 = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        d1.executed = True
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
        )
        await db_session.commit()
        
        executed = await repo.get_by_agent(
            test_agent.id, execution_filter="executed"
        )
        
        assert all(d.executed for d in executed)

    @pytest.mark.asyncio
    async def test_get_recent(
        self, db_session: AsyncSession, test_agent: AgentDB,
        test_user: UserDB
    ):
        """Test getting recent decisions across user's agents"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        recent = await repo.get_recent(test_user.id, limit=10)
        
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_mark_executed(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test marking decision as executed"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        results = [{"order_id": "123", "status": "filled"}]
        result = await repo.mark_executed(decision.id, results)
        
        assert result is True
        
        updated = await repo.get_by_id(decision.id)
        assert updated.executed is True
        assert updated.execution_results == results

    @pytest.mark.asyncio
    async def test_get_stats(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test getting decision statistics for an agent"""
        repo = DecisionRepository(db_session)
        
        d1 = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            overall_confidence=80,
            latency_ms=500,
        )
        d1.executed = True
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
            overall_confidence=60,
            latency_ms=300,
        )
        await db_session.commit()
        
        stats = await repo.get_stats(test_agent.id)
        
        assert stats["total_decisions"] >= 2
        assert stats["executed_decisions"] >= 1
        assert stats["average_confidence"] > 0
        assert stats["average_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_delete_old_records(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test deleting old decision records"""
        repo = DecisionRepository(db_session)
        
        for i in range(5):
            await repo.create(
                agent_id=test_agent.id,
                system_prompt=f"System {i}",
                user_prompt=f"User {i}",
                raw_response="{}",
            )
        await db_session.commit()
        
        deleted_count = await repo.delete_old_records(
            test_agent.id, keep_count=2
        )
        
        # Should delete 3 records (5 - 2 = 3)
        assert deleted_count == 3
        
        remaining = await repo.get_by_agent(test_agent.id)
        assert len(remaining) == 2

    @pytest.mark.asyncio
    async def test_delete_old_records_empty_agent(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test deleting old records when agent has no decisions"""
        repo = DecisionRepository(db_session)
        
        deleted_count = await repo.delete_old_records(
            test_agent.id, keep_count=10
        )
        
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_count_by_agent(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test counting decisions for an agent"""
        repo = DecisionRepository(db_session)
        
        for i in range(3):
            await repo.create(
                agent_id=test_agent.id,
                system_prompt=f"System {i}",
                user_prompt=f"User {i}",
                raw_response="{}",
            )
        await db_session.commit()
        
        count = await repo.count_by_agent(test_agent.id)
        
        assert count >= 3

    @pytest.mark.asyncio
    async def test_get_by_agent_skipped_only(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test filtering for skipped (non-executed) decisions only"""
        repo = DecisionRepository(db_session)
        
        d1 = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        d1.executed = True
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
        )
        await db_session.commit()
        
        skipped = await repo.get_by_agent(
            test_agent.id, execution_filter="skipped"
        )
        
        assert all(not d.executed for d in skipped)

    @pytest.mark.asyncio
    async def test_get_by_agent_action_filter(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test filtering decisions by action type"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            decisions=[{"action": "long", "symbol": "BTC"}],
        )
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
            decisions=[{"action": "hold", "symbol": "BTC"}],
        )
        await db_session.commit()
        
        long_decisions = await repo.get_by_agent(
            test_agent.id, action_filter="long"
        )
        
        assert len(long_decisions) >= 1

    @pytest.mark.asyncio
    async def test_get_by_agent_invalid_action_filter(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test that invalid action filter returns empty results"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            decisions=[{"action": "long", "symbol": "BTC"}],
        )
        await db_session.commit()
        
        results = await repo.get_by_agent(
            test_agent.id, action_filter="invalid_action; DROP TABLE"
        )
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_id(
        self, db_session: AsyncSession, test_agent: AgentDB,
        test_user: UserDB
    ):
        """Test getting decision by ID with user ID verification"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        # Should find with correct user
        result = await repo.get_by_id(decision.id, user_id=test_user.id)
        assert result is not None
        
        # Should not find with wrong user
        result = await repo.get_by_id(decision.id, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_executed_not_found(
        self, db_session: AsyncSession
    ):
        """Test marking non-existent decision returns False"""
        repo = DecisionRepository(db_session)
        
        result = await repo.mark_executed(uuid.uuid4(), [{"status": "filled"}])
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_stats_action_counts(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test get_stats correctly counts actions"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            decisions=[
                {"action": "long", "symbol": "BTC"},
                {"action": "long", "symbol": "ETH"},
            ],
        )
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
            decisions=[{"action": "hold", "symbol": "BTC"}],
        )
        await db_session.commit()
        
        stats = await repo.get_stats(test_agent.id)
        
        assert "action_counts" in stats
        assert stats["action_counts"].get("long", 0) >= 2
        assert stats["action_counts"].get("hold", 0) >= 1

    @pytest.mark.asyncio
    async def test_backward_compat_aliases(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test that deprecated aliases still work"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            agent_id=test_agent.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        # get_by_strategy is a deprecated alias for get_by_agent
        decisions = await repo.get_by_strategy(test_agent.id)
        assert len(decisions) >= 1
        
        # count_by_strategy is a deprecated alias for count_by_agent
        count = await repo.count_by_strategy(test_agent.id)
        assert count >= 1


# ============================================================================
# AgentRepository Tests
# ============================================================================

class TestAgentRepository:
    """Tests for AgentRepository (execution instances)"""

    @pytest.mark.asyncio
    async def test_create_agent(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test creating a new agent"""
        repo = AgentRepository(db_session)
        
        agent = await repo.create(
            user_id=test_user.id,
            name="My Agent",
            strategy_id=test_strategy.id,
            ai_model="deepseek:deepseek-chat",
            execution_mode="mock",
            mock_initial_balance=10000.0,
        )
        
        assert agent is not None
        assert agent.name == "My Agent"
        assert agent.strategy_id == test_strategy.id
        assert agent.ai_model == "deepseek:deepseek-chat"
        assert agent.execution_mode == "mock"
        assert agent.status == "draft"
        assert agent.total_pnl == 0.0

    @pytest.mark.asyncio
    async def test_create_live_agent(
        self, db_session: AsyncSession, test_user: UserDB,
        test_strategy: StrategyDB, test_account: ExchangeAccountDB
    ):
        """Test creating a live mode agent"""
        repo = AgentRepository(db_session)
        
        agent = await repo.create(
            user_id=test_user.id,
            name="Live Agent",
            strategy_id=test_strategy.id,
            execution_mode="live",
            account_id=test_account.id,
            ai_model="openai:gpt-4",
            allocated_capital=5000.0,
        )
        
        assert agent.execution_mode == "live"
        assert agent.account_id == test_account.id
        assert agent.allocated_capital == 5000.0

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test getting agent by ID"""
        repo = AgentRepository(db_session)
        
        agent = await repo.get_by_id(test_agent.id)
        
        assert agent is not None
        assert agent.id == test_agent.id

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_filter(
        self, db_session: AsyncSession, test_agent: AgentDB, test_user: UserDB
    ):
        """Test getting agent with user filter"""
        repo = AgentRepository(db_session)
        
        # Should find with correct user
        agent = await repo.get_by_id(test_agent.id, user_id=test_user.id)
        assert agent is not None
        
        # Should not find with different user
        agent = await repo.get_by_id(test_agent.id, user_id=uuid.uuid4())
        assert agent is None

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Test getting non-existent agent returns None"""
        repo = AgentRepository(db_session)
        
        agent = await repo.get_by_id(uuid.uuid4())
        
        assert agent is None

    @pytest.mark.asyncio
    async def test_get_by_user(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test getting all agents for a user"""
        repo = AgentRepository(db_session)
        
        await repo.create(
            user_id=test_user.id, name="Agent 1",
            strategy_id=test_strategy.id, execution_mode="mock",
        )
        await repo.create(
            user_id=test_user.id, name="Agent 2",
            strategy_id=test_strategy.id, execution_mode="mock",
        )
        await db_session.commit()
        
        agents = await repo.get_by_user(test_user.id)
        
        assert len(agents) >= 2

    @pytest.mark.asyncio
    async def test_get_by_user_filter_status(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test filtering agents by status"""
        repo = AgentRepository(db_session)
        
        a1 = await repo.create(
            user_id=test_user.id, name="Draft Agent",
            strategy_id=test_strategy.id,
        )
        a2 = await repo.create(
            user_id=test_user.id, name="Active Agent",
            strategy_id=test_strategy.id,
        )
        await repo.update_status(a2.id, "active")
        await db_session.commit()
        
        drafts = await repo.get_by_user(test_user.id, status="draft")
        
        assert all(a.status == "draft" for a in drafts)

    @pytest.mark.asyncio
    async def test_get_by_user_filter_execution_mode(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test filtering agents by execution mode"""
        repo = AgentRepository(db_session)
        
        await repo.create(
            user_id=test_user.id, name="Mock Agent",
            strategy_id=test_strategy.id, execution_mode="mock",
        )
        await db_session.commit()
        
        mock_agents = await repo.get_by_user(test_user.id, execution_mode="mock")
        
        assert all(a.execution_mode == "mock" for a in mock_agents)

    @pytest.mark.asyncio
    async def test_get_active_agents(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test getting all active agents"""
        repo = AgentRepository(db_session)
        
        a = await repo.create(
            user_id=test_user.id, name="Active Agent",
            strategy_id=test_strategy.id,
        )
        await repo.update_status(a.id, "active")
        await db_session.commit()
        
        active = await repo.get_active_agents()
        
        assert any(ag.id == a.id for ag in active)
        assert all(ag.status == "active" for ag in active)

    @pytest.mark.asyncio
    async def test_update_agent(
        self, db_session: AsyncSession, test_agent: AgentDB, test_user: UserDB
    ):
        """Test updating agent fields"""
        repo = AgentRepository(db_session)
        
        updated = await repo.update(
            test_agent.id, test_user.id,
            name="Updated Agent Name",
            ai_model="openai:gpt-4",
        )
        
        assert updated is not None
        assert updated.name == "Updated Agent Name"
        assert updated.ai_model == "openai:gpt-4"

    @pytest.mark.asyncio
    async def test_update_agent_not_found(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test updating non-existent agent returns None"""
        repo = AgentRepository(db_session)
        
        result = await repo.update(uuid.uuid4(), test_user.id, name="X")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test updating agent status"""
        repo = AgentRepository(db_session)
        
        result = await repo.update_status(test_agent.id, "active")
        
        assert result is True
        
        agent = await repo.get_by_id(test_agent.id)
        assert agent.status == "active"

    @pytest.mark.asyncio
    async def test_update_status_with_error(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test updating agent status with error message"""
        repo = AgentRepository(db_session)
        
        result = await repo.update_status(
            test_agent.id, "error", error_message="API failed"
        )
        
        assert result is True
        
        agent = await repo.get_by_id(test_agent.id)
        assert agent.status == "error"
        assert agent.error_message == "API failed"

    @pytest.mark.asyncio
    async def test_update_performance_win(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test updating agent performance after winning trade"""
        repo = AgentRepository(db_session)
        
        result = await repo.update_performance(
            test_agent.id, pnl_change=100.0, is_win=True
        )
        
        assert result is True
        
        agent = await repo.get_by_id(test_agent.id)
        assert agent.total_pnl == 100.0
        assert agent.total_trades == 1
        assert agent.winning_trades == 1
        assert agent.losing_trades == 0

    @pytest.mark.asyncio
    async def test_update_performance_loss(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test updating agent performance after losing trade"""
        repo = AgentRepository(db_session)
        
        result = await repo.update_performance(
            test_agent.id, pnl_change=-50.0, is_win=False
        )
        
        assert result is True
        
        agent = await repo.get_by_id(test_agent.id)
        assert agent.total_pnl == -50.0
        assert agent.total_trades == 1
        assert agent.winning_trades == 0
        assert agent.losing_trades == 1
        assert agent.max_drawdown == 50.0

    @pytest.mark.asyncio
    async def test_update_performance_not_found(
        self, db_session: AsyncSession
    ):
        """Test updating performance for non-existent agent returns False"""
        repo = AgentRepository(db_session)
        
        result = await repo.update_performance(uuid.uuid4(), 10.0, True)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_update_runtime_state(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test updating quant agent runtime state"""
        repo = AgentRepository(db_session)
        
        result = await repo.update_runtime_state(
            test_agent.id, {"filled_grids": [1, 2, 3]}
        )
        
        assert result is True
        
        agent = await repo.get_by_id(test_agent.id)
        assert agent.runtime_state == {"filled_grids": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_delete_agent(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test deleting agent"""
        repo = AgentRepository(db_session)
        
        agent = await repo.create(
            user_id=test_user.id, name="To Delete",
            strategy_id=test_strategy.id,
        )
        await db_session.commit()
        agent_id = agent.id
        
        result = await repo.delete(agent_id, test_user.id)
        
        assert result is True
        
        deleted = await repo.get_by_id(agent_id)
        assert deleted is None

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test deleting non-existent agent returns False"""
        repo = AgentRepository(db_session)
        
        result = await repo.delete(uuid.uuid4(), test_user.id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_win_rate_property(
        self, db_session: AsyncSession, test_agent: AgentDB
    ):
        """Test win rate calculated property on AgentDB"""
        repo = AgentRepository(db_session)
        
        # Multiple wins and losses
        await repo.update_performance(test_agent.id, 100.0, True)
        await repo.update_performance(test_agent.id, 50.0, True)
        await repo.update_performance(test_agent.id, -30.0, False)
        
        agent = await repo.get_by_id(test_agent.id)
        # 2 wins / 3 trades = 66.67%
        assert abs(agent.win_rate - 66.67) < 0.1

    @pytest.mark.asyncio
    async def test_get_effective_capital_fixed(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test effective capital calculation (fixed amount)"""
        repo = AgentRepository(db_session)
        
        agent = await repo.create(
            user_id=test_user.id, name="Fixed Capital",
            strategy_id=test_strategy.id,
            allocated_capital=5000.0,
        )
        
        result = agent.get_effective_capital(account_equity=20000.0)
        assert result == 5000.0

    @pytest.mark.asyncio
    async def test_get_effective_capital_percent(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test effective capital calculation (percentage)"""
        repo = AgentRepository(db_session)
        
        agent = await repo.create(
            user_id=test_user.id, name="Percent Capital",
            strategy_id=test_strategy.id,
            allocated_capital_percent=0.25,
        )
        
        result = agent.get_effective_capital(account_equity=20000.0)
        assert result == 5000.0

    @pytest.mark.asyncio
    async def test_get_effective_capital_none(
        self, db_session: AsyncSession, test_user: UserDB, test_strategy: StrategyDB
    ):
        """Test effective capital returns None when not configured"""
        repo = AgentRepository(db_session)
        
        agent = await repo.create(
            user_id=test_user.id, name="No Capital",
            strategy_id=test_strategy.id,
        )
        
        result = agent.get_effective_capital(account_equity=20000.0)
        assert result is None
