"""
Tests for name deduplication feature.

Covers:
- name_utils: Name parsing and suffix generation utilities
- NameCheckService: Cross-entity name checking service
- Repository integration: Strategy and Agent name deduplication
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.core.name_utils import (
    add_numeric_suffix,
    parse_name_with_suffix,
    generate_unique_name_sync,
)
from app.db.models import Base, UserDB, StrategyDB, AgentDB, ExchangeAccountDB
from app.db.repositories.strategy import StrategyRepository
from app.db.repositories.agent import AgentRepository
from app.db.repositories.quant_strategy import QuantStrategyRepository
from app.services.name_check_service import NameCheckService
from app.core.security import hash_password


# ============================================================================
# name_utils Tests
# ============================================================================

class TestNameUtils:
    """Tests for name_utils functions"""

    def test_parse_name_without_suffix(self):
        """Parse name without suffix returns original name and 0"""
        base, suffix = parse_name_with_suffix("BTC策略")
        assert base == "BTC策略"
        assert suffix == 0

    def test_parse_name_with_suffix(self):
        """Parse name with suffix extracts base and suffix"""
        base, suffix = parse_name_with_suffix("BTC策略-1")
        assert base == "BTC策略"
        assert suffix == 1

    def test_parse_name_with_large_suffix(self):
        """Parse name with large suffix"""
        base, suffix = parse_name_with_suffix("My Strategy-100")
        assert base == "My Strategy"
        assert suffix == 100

    def test_parse_name_with_multiple_dashes(self):
        """Parse name with multiple dashes - only last suffix is extracted"""
        base, suffix = parse_name_with_suffix("My-Cool-Strategy-5")
        assert base == "My-Cool-Strategy"
        assert suffix == 5

    def test_add_suffix_zero(self):
        """Adding suffix 0 returns original name"""
        result = add_numeric_suffix("BTC策略", 0)
        assert result == "BTC策略"

    def test_add_suffix_one(self):
        """Adding suffix 1 appends -1"""
        result = add_numeric_suffix("BTC策略", 1)
        assert result == "BTC策略-1"

    def test_add_suffix_large(self):
        """Adding large suffix"""
        result = add_numeric_suffix("BTC策略", 100)
        assert result == "BTC策略-100"

    def test_generate_unique_name_no_conflict(self):
        """No conflict returns original name"""
        def no_conflict(name: str, user_id: str) -> bool:
            return False

        result = generate_unique_name_sync("BTC策略", "user123", no_conflict)
        assert result == "BTC策略"

    def test_generate_unique_name_single_conflict(self):
        """Single conflict appends -1"""
        call_count = [0]

        def single_conflict(name: str, user_id: str) -> bool:
            call_count[0] += 1
            return name == "BTC策略"

        result = generate_unique_name_sync("BTC策略", "user123", single_conflict)
        assert result == "BTC策略-1"
        assert call_count[0] == 2  # Original check + one for "BTC策略-1"

    def test_generate_unique_name_multiple_conflicts(self):
        """Multiple conflicts increment suffix"""
        existing = {"BTC策略", "BTC策略-1", "BTC策略-2"}

        def multiple_conflicts(name: str, user_id: str) -> bool:
            return name in existing

        result = generate_unique_name_sync("BTC策略", "user123", multiple_conflicts)
        assert result == "BTC策略-3"

    def test_generate_unique_name_chinese(self):
        """Chinese names work correctly"""
        existing = {"网格策略", "网格策略-1"}

        def chinese_conflicts(name: str, user_id: str) -> bool:
            return name in existing

        result = generate_unique_name_sync("网格策略", "user123", chinese_conflicts)
        assert result == "网格策略-2"


# ============================================================================
# NameCheckService Tests
# ============================================================================

class TestNameCheckService:
    """Tests for NameCheckService"""

    @pytest_asyncio.fixture
    async def second_user(self, db_session: AsyncSession) -> UserDB:
        """Create a second test user"""
        user = UserDB(
            id=uuid4(),
            email="second@example.com",
            password_hash=hash_password("password123"),
            name="Second User",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest.mark.asyncio
    async def test_name_not_exists_for_user(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ):
        """Name does not exist for user returns False"""
        service = NameCheckService(db_session)
        exists = await service.name_exists_for_user("New Strategy", test_user.id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_name_exists_in_strategy(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Name exists in StrategyDB returns True"""
        service = NameCheckService(db_session)
        exists = await service.name_exists_for_user(test_strategy.name, test_user.id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_name_exists_in_agent(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_agent: AgentDB,
    ):
        """Name exists in AgentDB returns True"""
        service = NameCheckService(db_session)
        exists = await service.name_exists_for_user(test_agent.name, test_user.id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_name_exists_excludes_strategy(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Exclude strategy ID allows same name"""
        service = NameCheckService(db_session)
        exists = await service.name_exists_for_user(
            test_strategy.name,
            test_user.id,
            exclude_strategy_id=test_strategy.id,
        )
        assert exists is False

    @pytest.mark.asyncio
    async def test_name_exists_excludes_agent(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_agent: AgentDB,
    ):
        """Exclude agent ID allows same name"""
        service = NameCheckService(db_session)
        exists = await service.name_exists_for_user(
            test_agent.name,
            test_user.id,
            exclude_agent_id=test_agent.id,
        )
        assert exists is False

    @pytest.mark.asyncio
    async def test_different_users_no_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
        second_user: UserDB,
    ):
        """Different users can use same name"""
        service = NameCheckService(db_session)
        exists = await service.name_exists_for_user(test_strategy.name, second_user.id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_generate_unique_name_no_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ):
        """No conflict returns original name"""
        service = NameCheckService(db_session)
        result = await service.generate_unique_name("Unique Name", test_user.id)
        assert result == "Unique Name"

    @pytest.mark.asyncio
    async def test_generate_unique_name_with_strategy_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Conflict with strategy appends suffix"""
        service = NameCheckService(db_session)
        result = await service.generate_unique_name(test_strategy.name, test_user.id)
        assert result == f"{test_strategy.name}-1"

    @pytest.mark.asyncio
    async def test_generate_unique_name_with_agent_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_agent: AgentDB,
    ):
        """Conflict with agent appends suffix"""
        service = NameCheckService(db_session)
        result = await service.generate_unique_name(test_agent.name, test_user.id)
        assert result == f"{test_agent.name}-1"

    @pytest.mark.asyncio
    async def test_generate_unique_name_excludes_self(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Excluding own ID allows same name"""
        service = NameCheckService(db_session)
        result = await service.generate_unique_name(
            test_strategy.name,
            test_user.id,
            exclude_strategy_id=test_strategy.id,
        )
        assert result == test_strategy.name


# ============================================================================
# Strategy Repository Tests
# ============================================================================

class TestStrategyNameDeduplication:
    """Tests for Strategy name deduplication in repository"""

    @pytest.mark.asyncio
    async def test_create_strategy_no_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ):
        """Create strategy with no name conflict keeps original name"""
        repo = StrategyRepository(db_session)

        strategy = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Unique Strategy",
            symbols=["BTC"],
            config={"prompt": "Test prompt"},
        )

        assert strategy.name == "Unique Strategy"

    @pytest.mark.asyncio
    async def test_create_strategy_conflict_with_strategy(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Create strategy with name conflict appends suffix"""
        repo = StrategyRepository(db_session)

        new_strategy = await repo.create(
            user_id=test_user.id,
            type="ai",
            name=test_strategy.name,
            symbols=["ETH"],
            config={"prompt": "Different prompt"},
        )

        assert new_strategy.name == f"{test_strategy.name}-1"

    @pytest.mark.asyncio
    async def test_create_strategy_conflict_with_agent(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_agent: AgentDB,
    ):
        """Create strategy with agent name conflict appends suffix"""
        repo = StrategyRepository(db_session)

        strategy = await repo.create(
            user_id=test_user.id,
            type="ai",
            name=test_agent.name,
            symbols=["BTC"],
            config={"prompt": "Test prompt"},
        )

        assert strategy.name == f"{test_agent.name}-1"

    @pytest.mark.asyncio
    async def test_create_strategy_multiple_conflicts(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ):
        """Multiple conflicts increment suffix appropriately"""
        repo = StrategyRepository(db_session)

        # Create first strategy
        s1 = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Grid Strategy",
            symbols=["BTC"],
            config={"prompt": "Test 1"},
        )
        assert s1.name == "Grid Strategy"

        # Create second with same name
        s2 = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Grid Strategy",
            symbols=["ETH"],
            config={"prompt": "Test 2"},
        )
        assert s2.name == "Grid Strategy-1"

        # Create third with same name
        s3 = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Grid Strategy",
            symbols=["SOL"],
            config={"prompt": "Test 3"},
        )
        assert s3.name == "Grid Strategy-2"

    @pytest.mark.asyncio
    async def test_update_strategy_name_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Update strategy name with conflict appends suffix"""
        repo = StrategyRepository(db_session)

        # Create another strategy
        s2 = await repo.create(
            user_id=test_user.id,
            type="ai",
            name="Another Strategy",
            symbols=["ETH"],
            config={"prompt": "Test"},
        )

        # Try to rename first strategy to second's name
        updated = await repo.update(
            strategy_id=test_strategy.id,
            user_id=test_user.id,
            name=s2.name,
        )

        assert updated.name == "Another Strategy-1"

    @pytest.mark.asyncio
    async def test_update_strategy_same_name(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Update strategy with same name keeps it unchanged"""
        repo = StrategyRepository(db_session)

        updated = await repo.update(
            strategy_id=test_strategy.id,
            user_id=test_user.id,
            name=test_strategy.name,
        )

        assert updated.name == test_strategy.name

    @pytest.mark.asyncio
    async def test_fork_strategy_name_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Fork strategy with name conflict appends suffix"""
        repo = StrategyRepository(db_session)

        # Make original public
        test_strategy.visibility = "public"
        await db_session.commit()

        # Fork with same name
        forked = await repo.fork(
            source_id=test_strategy.id,
            user_id=test_user.id,
        )

        assert forked.name == f"{test_strategy.name}-1"


# ============================================================================
# Agent Repository Tests
# ============================================================================

class TestAgentNameDeduplication:
    """Tests for Agent name deduplication in repository"""

    @pytest_asyncio.fixture
    async def test_strategy_for_agent(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ) -> StrategyDB:
        """Create a strategy for agent testing"""
        strategy = StrategyDB(
            id=uuid4(),
            user_id=test_user.id,
            type="ai",
            name="Agent Test Strategy",
            description="For agent tests",
            symbols=["BTC"],
            config={"prompt": "Test"},
            created_at=datetime.now(UTC),
        )
        db_session.add(strategy)
        await db_session.commit()
        await db_session.refresh(strategy)
        return strategy

    @pytest.mark.asyncio
    async def test_create_agent_no_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy_for_agent: StrategyDB,
    ):
        """Create agent with no name conflict keeps original name"""
        repo = AgentRepository(db_session)

        agent = await repo.create(
            user_id=test_user.id,
            name="Unique Agent",
            strategy_id=test_strategy_for_agent.id,
            execution_mode="mock",
        )

        assert agent.name == "Unique Agent"

    @pytest.mark.asyncio
    async def test_create_agent_conflict_with_strategy(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy_for_agent: StrategyDB,
    ):
        """Create agent with strategy name conflict appends suffix"""
        repo = AgentRepository(db_session)

        agent = await repo.create(
            user_id=test_user.id,
            name=test_strategy_for_agent.name,
            strategy_id=test_strategy_for_agent.id,
            execution_mode="mock",
        )

        assert agent.name == f"{test_strategy_for_agent.name}-1"

    @pytest.mark.asyncio
    async def test_create_agent_conflict_with_agent(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy_for_agent: StrategyDB,
        test_agent: AgentDB,
    ):
        """Create agent with agent name conflict appends suffix"""
        repo = AgentRepository(db_session)

        new_agent = await repo.create(
            user_id=test_user.id,
            name=test_agent.name,
            strategy_id=test_strategy_for_agent.id,
            execution_mode="mock",
        )

        assert new_agent.name == f"{test_agent.name}-1"

    @pytest.mark.asyncio
    async def test_update_agent_name_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy_for_agent: StrategyDB,
    ):
        """Update agent name with conflict appends suffix"""
        repo = AgentRepository(db_session)

        # Create two agents
        a1 = await repo.create(
            user_id=test_user.id,
            name="Agent One",
            strategy_id=test_strategy_for_agent.id,
            execution_mode="mock",
        )

        a2 = await repo.create(
            user_id=test_user.id,
            name="Agent Two",
            strategy_id=test_strategy_for_agent.id,
            execution_mode="mock",
        )

        # Try to rename a1 to a2's name
        updated = await repo.update(
            agent_id=a1.id,
            user_id=test_user.id,
            name="Agent Two",
        )

        assert updated.name == "Agent Two-1"


# ============================================================================
# Quant Strategy Repository Tests
# ============================================================================

class TestQuantStrategyNameDeduplication:
    """Tests for Quant Strategy name deduplication"""

    @pytest.mark.asyncio
    async def test_create_quant_no_conflict(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ):
        """Create quant strategy with no conflict keeps original name"""
        repo = QuantStrategyRepository(db_session)

        agent = await repo.create(
            user_id=test_user.id,
            name="Grid Bot",
            strategy_type="grid",
            symbol="BTC",
            config={"grid_levels": 10},
        )

        assert agent.name == "Grid Bot"
        assert agent.strategy.name == "Grid Bot"

    @pytest.mark.asyncio
    async def test_create_quant_conflict_with_strategy(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_strategy: StrategyDB,
    ):
        """Create quant strategy with strategy name conflict appends suffix"""
        repo = QuantStrategyRepository(db_session)

        agent = await repo.create(
            user_id=test_user.id,
            name=test_strategy.name,
            strategy_type="grid",
            symbol="BTC",
            config={"grid_levels": 10},
        )

        assert agent.name == f"{test_strategy.name}-1"
        assert agent.strategy.name == f"{test_strategy.name}-1"

    @pytest.mark.asyncio
    async def test_create_quant_conflict_with_agent(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
        test_agent: AgentDB,
    ):
        """Create quant strategy with agent name conflict appends suffix"""
        repo = QuantStrategyRepository(db_session)

        agent = await repo.create(
            user_id=test_user.id,
            name=test_agent.name,
            strategy_type="dca",
            symbol="ETH",
            config={"interval_hours": 24},
        )

        assert agent.name == f"{test_agent.name}-1"

    @pytest.mark.asyncio
    async def test_update_quant_name_syncs_both(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ):
        """Update quant name syncs both agent and strategy"""
        repo = QuantStrategyRepository(db_session)

        # Create a quant strategy
        agent = await repo.create(
            user_id=test_user.id,
            name="DCA Bot",
            strategy_type="dca",
            symbol="BTC",
            config={"interval_hours": 24},
        )
        original_strategy_id = agent.strategy_id

        # Update name
        updated = await repo.update(
            agent_id=agent.id,
            user_id=test_user.id,
            name="Renamed DCA",
        )

        assert updated.name == "Renamed DCA"
        # Need to query fresh to get the strategy relationship loaded properly
        fresh = await repo.get_by_id(agent.id, test_user.id)
        assert fresh is not None
        assert fresh.strategy.name == "Renamed DCA"
        assert fresh.strategy_id == original_strategy_id


# ============================================================================
# Marketplace Name Check Tests
# ============================================================================

class TestMarketplaceNameCheck:
    """Tests for marketplace name conflict checking"""

    @pytest_asyncio.fixture
    async def public_strategy(
        self,
        db_session: AsyncSession,
        test_user: UserDB,
    ) -> StrategyDB:
        """Create a public strategy for marketplace testing"""
        strategy = StrategyDB(
            id=uuid4(),
            user_id=test_user.id,
            type="ai",
            name="Popular Strategy",
            description="A popular public strategy",
            symbols=["BTC"],
            config={"prompt": "Test"},
            visibility="public",
            created_at=datetime.now(UTC),
        )
        db_session.add(strategy)
        await db_session.commit()
        await db_session.refresh(strategy)
        return strategy

    @pytest.mark.asyncio
    async def test_market_name_exists(
        self,
        db_session: AsyncSession,
        public_strategy: StrategyDB,
    ):
        """Market name exists check finds public strategy"""
        service = NameCheckService(db_session)

        exists = await service.market_name_exists(public_strategy.name)
        assert exists is True

    @pytest.mark.asyncio
    async def test_market_name_not_exists(
        self,
        db_session: AsyncSession,
    ):
        """Market name does not exist for unknown name"""
        service = NameCheckService(db_session)

        exists = await service.market_name_exists("Unknown Strategy")
        assert exists is False

    @pytest.mark.asyncio
    async def test_market_name_excludes_self(
        self,
        db_session: AsyncSession,
        public_strategy: StrategyDB,
    ):
        """Market name check excludes specified strategy"""
        service = NameCheckService(db_session)

        exists = await service.market_name_exists(
            public_strategy.name,
            exclude_strategy_id=public_strategy.id,
        )
        assert exists is False

    @pytest.mark.asyncio
    async def test_private_strategy_not_in_market(
        self,
        db_session: AsyncSession,
        test_strategy: StrategyDB,
    ):
        """Private strategy is not found in market check"""
        service = NameCheckService(db_session)

        # Ensure strategy is private
        assert test_strategy.visibility == "private"

        exists = await service.market_name_exists(test_strategy.name)
        assert exists is False
