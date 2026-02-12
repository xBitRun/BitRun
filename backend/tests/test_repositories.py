"""
Tests for database repository layer.

Covers: UserRepository, AccountRepository, StrategyRepository, DecisionRepository,
        QuantStrategyRepository
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
    QuantStrategyDB,
)
from app.db.repositories.user import UserRepository
from app.db.repositories.account import AccountRepository
from app.db.repositories.strategy import StrategyRepository
from app.db.repositories.decision import DecisionRepository
from app.db.repositories.quant_strategy import QuantStrategyRepository


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
# StrategyRepository Tests
# ============================================================================

class TestStrategyRepository:
    """Tests for StrategyRepository"""

    @pytest.mark.asyncio
    async def test_create_strategy(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test creating a new strategy"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id,
            name="Test Strategy",
            prompt="Buy low, sell high",
            description="A simple strategy",
            trading_mode="conservative",
        )
        
        assert strategy is not None
        assert strategy.name == "Test Strategy"
        assert strategy.prompt == "Buy low, sell high"
        assert strategy.status == "draft"
        assert strategy.total_pnl == 0.0

    @pytest.mark.asyncio
    async def test_create_strategy_with_account(
        self, db_session: AsyncSession, test_user: UserDB, 
        test_account: ExchangeAccountDB
    ):
        """Test creating strategy linked to account"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id,
            name="Linked Strategy",
            prompt="Test",
            account_id=test_account.id,
        )
        
        assert strategy.account_id == test_account.id

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
        
        await repo.create(user_id=test_user.id, name="Strategy 1", prompt="Test")
        await repo.create(user_id=test_user.id, name="Strategy 2", prompt="Test")
        await db_session.commit()
        
        strategies = await repo.get_by_user(test_user.id)
        
        assert len(strategies) >= 2

    @pytest.mark.asyncio
    async def test_get_by_user_filter_status(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test filtering strategies by status"""
        repo = StrategyRepository(db_session)
        
        s1 = await repo.create(user_id=test_user.id, name="Draft", prompt="Test")
        s2 = await repo.create(user_id=test_user.id, name="Active", prompt="Test")
        s2.status = "active"
        await db_session.commit()
        
        drafts = await repo.get_by_user(test_user.id, status="draft")
        
        assert all(s.status == "draft" for s in drafts)

    @pytest.mark.asyncio
    async def test_get_active_strategies(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test getting all active strategies"""
        repo = StrategyRepository(db_session)
        
        s1 = await repo.create(user_id=test_user.id, name="Active", prompt="Test")
        s1.status = "active"
        await repo.create(user_id=test_user.id, name="Draft", prompt="Test")
        await db_session.commit()
        
        active = await repo.get_active_strategies()
        
        assert all(s.status == "active" for s in active)

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
            prompt="New prompt"
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.prompt == "New prompt"

    @pytest.mark.asyncio
    async def test_update_status(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test updating strategy status"""
        repo = StrategyRepository(db_session)
        
        result = await repo.update_status(test_strategy.id, "active")
        
        assert result is True
        
        strategy = await repo.get_by_id(test_strategy.id)
        assert strategy.status == "active"

    @pytest.mark.asyncio
    async def test_update_status_with_error(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test updating strategy status with error message"""
        repo = StrategyRepository(db_session)
        
        result = await repo.update_status(
            test_strategy.id, "error", "API connection failed"
        )
        
        assert result is True
        
        strategy = await repo.get_by_id(test_strategy.id)
        assert strategy.status == "error"
        assert strategy.error_message == "API connection failed"

    @pytest.mark.asyncio
    async def test_update_performance_win(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test updating performance after winning trade"""
        repo = StrategyRepository(db_session)
        
        result = await repo.update_performance(
            test_strategy.id, pnl_change=100.0, is_win=True
        )
        
        assert result is True
        
        strategy = await repo.get_by_id(test_strategy.id)
        assert strategy.total_pnl == 100.0
        assert strategy.total_trades == 1
        assert strategy.winning_trades == 1
        assert strategy.losing_trades == 0

    @pytest.mark.asyncio
    async def test_update_performance_loss(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test updating performance after losing trade"""
        repo = StrategyRepository(db_session)
        
        result = await repo.update_performance(
            test_strategy.id, pnl_change=-50.0, is_win=False
        )
        
        assert result is True
        
        strategy = await repo.get_by_id(test_strategy.id)
        assert strategy.total_pnl == -50.0
        assert strategy.total_trades == 1
        assert strategy.winning_trades == 0
        assert strategy.losing_trades == 1
        assert strategy.max_drawdown == 50.0

    @pytest.mark.asyncio
    async def test_delete_strategy(
        self, db_session: AsyncSession, test_user: UserDB
    ):
        """Test deleting strategy"""
        repo = StrategyRepository(db_session)
        
        strategy = await repo.create(
            user_id=test_user.id,
            name="To Delete",
            prompt="Test"
        )
        await db_session.commit()
        strategy_id = strategy.id
        
        result = await repo.delete(strategy_id, test_user.id)
        
        assert result is True
        
        deleted = await repo.get_by_id(strategy_id)
        assert deleted is None


# ============================================================================
# DecisionRepository Tests
# ============================================================================

class TestDecisionRepository:
    """Tests for DecisionRepository"""

    @pytest.mark.asyncio
    async def test_create_decision(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test creating a decision record"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            strategy_id=test_strategy.id,
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
        assert decision.strategy_id == test_strategy.id
        assert decision.overall_confidence == 75
        assert len(decision.decisions) == 1

    @pytest.mark.asyncio
    async def test_create_debate_decision(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test creating a debate decision record"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            strategy_id=test_strategy.id,
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
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test getting decision by ID"""
        repo = DecisionRepository(db_session)
        
        created = await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        decision = await repo.get_by_id(created.id)
        
        assert decision is not None
        assert decision.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_strategy(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test getting decisions for a strategy"""
        repo = DecisionRepository(db_session)
        
        # Create multiple decisions
        for i in range(3):
            await repo.create(
                strategy_id=test_strategy.id,
                system_prompt=f"System {i}",
                user_prompt=f"User {i}",
                raw_response="{}",
            )
        await db_session.commit()
        
        decisions = await repo.get_by_strategy(test_strategy.id)
        
        assert len(decisions) >= 3

    @pytest.mark.asyncio
    async def test_get_by_strategy_executed_only(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test filtering for executed decisions only"""
        repo = DecisionRepository(db_session)
        
        d1 = await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        d1.executed = True
        
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
        )
        await db_session.commit()
        
        executed = await repo.get_by_strategy(
            test_strategy.id, execution_filter="executed"
        )
        
        assert all(d.executed for d in executed)

    @pytest.mark.asyncio
    async def test_get_recent(
        self, db_session: AsyncSession, test_strategy: StrategyDB,
        test_user: UserDB
    ):
        """Test getting recent decisions across strategies"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        await db_session.commit()
        
        recent = await repo.get_recent(test_user.id, limit=10)
        
        assert len(recent) >= 1

    @pytest.mark.asyncio
    async def test_mark_executed(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test marking decision as executed"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            strategy_id=test_strategy.id,
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
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test getting decision statistics"""
        repo = DecisionRepository(db_session)
        
        # Create decisions with varying properties
        d1 = await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            overall_confidence=80,
            latency_ms=500,
        )
        d1.executed = True
        
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
            overall_confidence=60,
            latency_ms=300,
        )
        await db_session.commit()
        
        stats = await repo.get_stats(test_strategy.id)
        
        assert stats["total_decisions"] >= 2
        assert stats["executed_decisions"] >= 1
        assert stats["average_confidence"] > 0
        assert stats["average_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_delete_old_records(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test deleting old decision records"""
        repo = DecisionRepository(db_session)
        
        # Create more records than keep_count
        for i in range(5):
            await repo.create(
                strategy_id=test_strategy.id,
                system_prompt=f"System {i}",
                user_prompt=f"User {i}",
                raw_response="{}",
            )
        await db_session.commit()
        
        deleted_count = await repo.delete_old_records(
            test_strategy.id, keep_count=2
        )
        
        # Should delete 3 records (5 - 2 = 3)
        assert deleted_count == 3
        
        remaining = await repo.get_by_strategy(test_strategy.id)
        assert len(remaining) == 2

    @pytest.mark.asyncio
    async def test_delete_old_records_empty_strategy(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test deleting old records when strategy has no decisions"""
        repo = DecisionRepository(db_session)
        
        deleted_count = await repo.delete_old_records(
            test_strategy.id, keep_count=10
        )
        
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_count_by_strategy(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test counting decisions for a strategy"""
        repo = DecisionRepository(db_session)
        
        for i in range(3):
            await repo.create(
                strategy_id=test_strategy.id,
                system_prompt=f"System {i}",
                user_prompt=f"User {i}",
                raw_response="{}",
            )
        await db_session.commit()
        
        count = await repo.count_by_strategy(test_strategy.id)
        
        assert count >= 3

    @pytest.mark.asyncio
    async def test_get_by_strategy_skipped_only(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test filtering for skipped (non-executed) decisions only"""
        repo = DecisionRepository(db_session)
        
        # Create executed decision
        d1 = await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
        )
        d1.executed = True
        
        # Create non-executed decision
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
        )
        await db_session.commit()
        
        skipped = await repo.get_by_strategy(
            test_strategy.id, execution_filter="skipped"
        )
        
        assert all(not d.executed for d in skipped)

    @pytest.mark.asyncio
    async def test_get_by_strategy_action_filter(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test filtering decisions by action type"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            decisions=[{"action": "long", "symbol": "BTC"}],
        )
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
            decisions=[{"action": "hold", "symbol": "BTC"}],
        )
        await db_session.commit()
        
        long_decisions = await repo.get_by_strategy(
            test_strategy.id, action_filter="long"
        )
        
        # Should only include decisions with "long" action
        assert len(long_decisions) >= 1

    @pytest.mark.asyncio
    async def test_get_by_strategy_invalid_action_filter(
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test that invalid action filter returns empty results (SQL injection protection)"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            decisions=[{"action": "long", "symbol": "BTC"}],
        )
        await db_session.commit()
        
        # Invalid action should return empty results
        results = await repo.get_by_strategy(
            test_strategy.id, action_filter="invalid_action; DROP TABLE"
        )
        
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_by_id_with_user_id(
        self, db_session: AsyncSession, test_strategy: StrategyDB,
        test_user: UserDB
    ):
        """Test getting decision by ID with user ID verification"""
        repo = DecisionRepository(db_session)
        
        decision = await repo.create(
            strategy_id=test_strategy.id,
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
        self, db_session: AsyncSession, test_strategy: StrategyDB
    ):
        """Test get_stats correctly counts actions"""
        repo = DecisionRepository(db_session)
        
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System",
            user_prompt="User",
            raw_response="{}",
            decisions=[
                {"action": "long", "symbol": "BTC"},
                {"action": "long", "symbol": "ETH"},
            ],
        )
        await repo.create(
            strategy_id=test_strategy.id,
            system_prompt="System 2",
            user_prompt="User 2",
            raw_response="{}",
            decisions=[{"action": "hold", "symbol": "BTC"}],
        )
        await db_session.commit()
        
        stats = await repo.get_stats(test_strategy.id)
        
        assert "action_counts" in stats
        assert stats["action_counts"].get("long", 0) >= 2
        assert stats["action_counts"].get("hold", 0) >= 1


# ============================================================================
# QuantStrategyRepository Tests
# ============================================================================

class TestQuantStrategyRepository:
    """Tests for QuantStrategyRepository"""

    @pytest.mark.asyncio
    async def test_create_quant_strategy(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        strategy = await repo.create(
            user_id=test_user.id,
            name="Grid BTC",
            strategy_type="grid",
            symbol="BTC",
            config={"upper_price": 60000, "lower_price": 50000, "grid_count": 10},
            description="Test grid strategy",
        )
        assert strategy is not None
        assert strategy.name == "Grid BTC"
        assert strategy.strategy_type == "grid"
        assert strategy.symbol == "BTC"
        assert strategy.status == "draft"

    @pytest.mark.asyncio
    async def test_create_with_capital(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        strategy = await repo.create(
            user_id=test_user.id,
            name="DCA ETH",
            strategy_type="dca",
            symbol="ETH",
            config={"order_amount": 100},
            allocated_capital=5000.0,
        )
        assert strategy.allocated_capital == 5000.0
        assert strategy.allocated_capital_percent is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        created = await repo.create(
            user_id=test_user.id, name="RSI SOL",
            strategy_type="rsi", symbol="SOL", config={},
        )
        result = await repo.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    @pytest.mark.asyncio
    async def test_get_by_id_with_user(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        created = await repo.create(
            user_id=test_user.id, name="RSI BTC",
            strategy_type="rsi", symbol="BTC", config={},
        )
        # Correct user
        result = await repo.get_by_id(created.id, user_id=test_user.id)
        assert result is not None
        # Wrong user
        result = await repo.get_by_id(created.id, user_id=uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        repo = QuantStrategyRepository(db_session)
        result = await repo.get_by_id(uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_user(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        for i in range(3):
            await repo.create(
                user_id=test_user.id, name=f"Strat {i}",
                strategy_type="grid", symbol="BTC", config={},
            )
        results = await repo.get_by_user(test_user.id)
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_get_by_user_filter_status(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        await repo.create(
            user_id=test_user.id, name="Active Grid",
            strategy_type="grid", symbol="BTC", config={},
        )
        results = await repo.get_by_user(test_user.id, status="draft")
        assert all(s.status == "draft" for s in results)

    @pytest.mark.asyncio
    async def test_get_by_user_filter_type(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        await repo.create(
            user_id=test_user.id, name="DCA Filter",
            strategy_type="dca", symbol="ETH", config={},
        )
        results = await repo.get_by_user(test_user.id, strategy_type="dca")
        assert all(s.strategy_type == "dca" for s in results)

    @pytest.mark.asyncio
    async def test_get_active_strategies(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Active Strat",
            strategy_type="grid", symbol="BTC", config={},
        )
        await repo.update_status(s.id, "active")
        actives = await repo.get_active_strategies()
        assert any(a.id == s.id for a in actives)

    @pytest.mark.asyncio
    async def test_update(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Update Me",
            strategy_type="grid", symbol="BTC", config={},
        )
        updated = await repo.update(s.id, test_user.id, name="Updated Name")
        assert updated is not None
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_not_found(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        result = await repo.update(uuid.uuid4(), test_user.id, name="X")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_status(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Status Test",
            strategy_type="dca", symbol="ETH", config={},
        )
        result = await repo.update_status(s.id, "active")
        assert result is True

    @pytest.mark.asyncio
    async def test_update_status_with_error(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Error Test",
            strategy_type="rsi", symbol="SOL", config={},
        )
        result = await repo.update_status(s.id, "error", error_message="API failed")
        assert result is True

    @pytest.mark.asyncio
    async def test_update_runtime_state(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Runtime Test",
            strategy_type="grid", symbol="BTC", config={},
        )
        result = await repo.update_runtime_state(s.id, {"filled_grids": [1, 2]})
        assert result is True

    @pytest.mark.asyncio
    async def test_update_performance(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Perf Test",
            strategy_type="grid", symbol="BTC", config={},
        )
        result = await repo.update_performance(s.id, pnl_change=100.0, is_win=True)
        assert result is True
        refreshed = await repo.get_by_id(s.id)
        assert refreshed.total_pnl == 100.0
        assert refreshed.winning_trades == 1

    @pytest.mark.asyncio
    async def test_update_performance_loss(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Loss Test",
            strategy_type="dca", symbol="ETH", config={},
        )
        result = await repo.update_performance(s.id, pnl_change=-50.0, is_win=False)
        assert result is True
        refreshed = await repo.get_by_id(s.id)
        assert refreshed.losing_trades == 1
        assert refreshed.max_drawdown == 50.0

    @pytest.mark.asyncio
    async def test_update_performance_not_found(self, db_session: AsyncSession):
        repo = QuantStrategyRepository(db_session)
        result = await repo.update_performance(uuid.uuid4(), 10.0, True)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        s = await repo.create(
            user_id=test_user.id, name="Delete Me",
            strategy_type="grid", symbol="BTC", config={},
        )
        result = await repo.delete(s.id, test_user.id)
        assert result is True
        assert await repo.get_by_id(s.id) is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session: AsyncSession, test_user: UserDB):
        repo = QuantStrategyRepository(db_session)
        result = await repo.delete(uuid.uuid4(), test_user.id)
        assert result is False
