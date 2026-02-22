"""Tests for strategy update protection when active agents exist.

This module tests that:
1. Marketplace fields (visibility, category, tags, etc.) can always be updated
2. Strategy config fields (name, description, symbols, config) are blocked when active agents exist
3. Version restore is blocked when active agents exist
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.status import HTTP_409_CONFLICT

from app.api.routes.strategies import restore_version, update_strategy
from app.models.strategy import StrategyUpdate, StrategyVisibility


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_user_id():
    """Return a fixed user ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_strategy_id():
    """Return a fixed strategy ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_agent():
    """Create a mock active agent."""
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.name = "Test Agent"
    agent.status = "active"
    agent.strategy_id = uuid.uuid4()
    return agent


@pytest.fixture
def mock_paused_agent():
    """Create a mock paused agent."""
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.name = "Paused Agent"
    agent.status = "paused"
    agent.strategy_id = uuid.uuid4()
    return agent


class TestUpdateStrategyWithActiveAgents:
    """Tests for update_strategy endpoint with active agent protection."""

    @pytest.mark.asyncio
    async def test_update_marketplace_field_with_active_agent_succeeds(
        self, mock_db, mock_user_id, mock_strategy_id, mock_agent
    ):
        """Updating visibility (marketplace field) should succeed even with active agent."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_strategy = MagicMock()
            mock_strategy.id = uuid.UUID(mock_strategy_id)
            mock_strategy.type = "ai"
            mock_repo.get_by_id.return_value = mock_strategy
            mock_repo.update.return_value = mock_strategy

            # Setup mock agent repo - return active agent
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = [mock_agent]

            # Update only visibility (marketplace field)
            update_data = StrategyUpdate(visibility=StrategyVisibility.PUBLIC)

            # Should NOT raise - marketplace fields can be updated
            result = await update_strategy(
                strategy_id=mock_strategy_id,
                data=update_data,
                db=mock_db,
                user_id=mock_user_id,
            )

            # Verify update was called
            mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_config_with_active_agent_fails(
        self, mock_db, mock_user_id, mock_strategy_id, mock_agent
    ):
        """Updating config (strategy config field) should fail with active agent."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Setup mock agent repo - return active agent
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = [mock_agent]

            # Update config (strategy config field)
            update_data = StrategyUpdate(config={"key": "value"})

            # Should raise HTTPException with 409
            with pytest.raises(HTTPException) as exc_info:
                await update_strategy(
                    strategy_id=mock_strategy_id,
                    data=update_data,
                    db=mock_db,
                    user_id=mock_user_id,
                )

            assert exc_info.value.status_code == HTTP_409_CONFLICT
            assert "Cannot modify strategy config" in exc_info.value.detail
            assert "Test Agent" in exc_info.value.detail
            assert "Pause the agent first" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_name_with_active_agent_fails(
        self, mock_db, mock_user_id, mock_strategy_id, mock_agent
    ):
        """Updating name (strategy config field) should fail with active agent."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Setup mock agent repo - return active agent
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = [mock_agent]

            # Update name (strategy config field)
            update_data = StrategyUpdate(name="New Name")

            # Should raise HTTPException with 409
            with pytest.raises(HTTPException) as exc_info:
                await update_strategy(
                    strategy_id=mock_strategy_id,
                    data=update_data,
                    db=mock_db,
                    user_id=mock_user_id,
                )

            assert exc_info.value.status_code == HTTP_409_CONFLICT
            assert "Cannot modify strategy config" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_symbols_with_active_agent_fails(
        self, mock_db, mock_user_id, mock_strategy_id, mock_agent
    ):
        """Updating symbols (strategy config field) should fail with active agent."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Setup mock agent repo - return active agent
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = [mock_agent]

            # Update symbols (strategy config field)
            update_data = StrategyUpdate(symbols=["BTC", "ETH"])

            # Should raise HTTPException with 409
            with pytest.raises(HTTPException) as exc_info:
                await update_strategy(
                    strategy_id=mock_strategy_id,
                    data=update_data,
                    db=mock_db,
                    user_id=mock_user_id,
                )

            assert exc_info.value.status_code == HTTP_409_CONFLICT
            assert "Cannot modify strategy config" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_config_with_paused_agent_succeeds(
        self, mock_db, mock_user_id, mock_strategy_id, mock_paused_agent
    ):
        """Updating config should succeed when agent is paused (not active)."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_strategy = MagicMock()
            mock_strategy.id = uuid.UUID(mock_strategy_id)
            mock_strategy.type = "ai"
            mock_repo.get_by_id.return_value = mock_strategy
            mock_repo.update.return_value = mock_strategy

            # Setup mock agent repo - return empty list (no active agents)
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = []

            # Update config (strategy config field)
            update_data = StrategyUpdate(config={"key": "value"})

            # Should NOT raise - no active agents
            result = await update_strategy(
                strategy_id=mock_strategy_id,
                data=update_data,
                db=mock_db,
                user_id=mock_user_id,
            )

            # Verify update was called
            mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_no_agents_succeeds(
        self, mock_db, mock_user_id, mock_strategy_id
    ):
        """Updating any field should succeed when no agents exist."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_strategy = MagicMock()
            mock_strategy.id = uuid.UUID(mock_strategy_id)
            mock_strategy.type = "ai"
            mock_repo.get_by_id.return_value = mock_strategy
            mock_repo.update.return_value = mock_strategy

            # Setup mock agent repo - return empty list
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = []

            # Update config (strategy config field)
            update_data = StrategyUpdate(config={"key": "value"}, name="New Name")

            # Should NOT raise - no agents
            result = await update_strategy(
                strategy_id=mock_strategy_id,
                data=update_data,
                db=mock_db,
                user_id=mock_user_id,
            )

            # Verify update was called
            mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_multiple_active_agents_shows_count(
        self, mock_db, mock_user_id, mock_strategy_id
    ):
        """Error message should show count when multiple active agents exist."""
        # Create multiple active agents
        agents = []
        for i in range(5):
            agent = MagicMock()
            agent.id = uuid.uuid4()
            agent.name = f"Agent {i + 1}"
            agent.status = "active"
            agents.append(agent)

        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Setup mock agent repo - return 5 active agents
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = agents

            # Update config
            update_data = StrategyUpdate(config={"key": "value"})

            # Should raise HTTPException with 409
            with pytest.raises(HTTPException) as exc_info:
                await update_strategy(
                    strategy_id=mock_strategy_id,
                    data=update_data,
                    db=mock_db,
                    user_id=mock_user_id,
                )

            assert exc_info.value.status_code == HTTP_409_CONFLICT
            # Should show count
            assert "5 agents are active" in exc_info.value.detail
            # Should show first 3 agent names
            assert "Agent 1" in exc_info.value.detail
            assert "Agent 2" in exc_info.value.detail
            assert "Agent 3" in exc_info.value.detail
            # Should show ellipsis for more agents
            assert "..." in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_both_marketplace_and_config_fails(
        self, mock_db, mock_user_id, mock_strategy_id, mock_agent
    ):
        """Updating both marketplace and config fields should fail with active agent."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Setup mock agent repo - return active agent
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = [mock_agent]

            # Update both config and visibility
            update_data = StrategyUpdate(
                config={"key": "value"},
                visibility=StrategyVisibility.PUBLIC,
            )

            # Should raise because config is being modified
            with pytest.raises(HTTPException) as exc_info:
                await update_strategy(
                    strategy_id=mock_strategy_id,
                    data=update_data,
                    db=mock_db,
                    user_id=mock_user_id,
                )

            assert exc_info.value.status_code == HTTP_409_CONFLICT


class TestRestoreVersionWithActiveAgents:
    """Tests for restore_version endpoint with active agent protection."""

    @pytest.mark.asyncio
    async def test_restore_version_with_active_agent_fails(
        self, mock_db, mock_user_id, mock_strategy_id, mock_agent
    ):
        """Restoring version should fail with active agent."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo

            # Setup mock agent repo - return active agent
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = [mock_agent]

            # Should raise HTTPException with 409
            with pytest.raises(HTTPException) as exc_info:
                await restore_version(
                    strategy_id=mock_strategy_id,
                    version=1,
                    db=mock_db,
                    user_id=mock_user_id,
                )

            assert exc_info.value.status_code == HTTP_409_CONFLICT
            assert "Cannot restore version" in exc_info.value.detail
            assert "Test Agent" in exc_info.value.detail
            assert "Pause the agent first" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_restore_version_without_active_agent_succeeds(
        self, mock_db, mock_user_id, mock_strategy_id
    ):
        """Restoring version should succeed when no active agents exist."""
        with (
            patch(
                "app.api.routes.strategies.StrategyRepository"
            ) as mock_repo_class,
            patch(
                "app.api.routes.strategies.AgentRepository"
            ) as mock_agent_repo_class,
        ):
            # Setup mock strategy repo
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            mock_strategy = MagicMock()
            mock_repo.restore_version.return_value = mock_strategy

            # Setup mock agent repo - return empty list
            mock_agent_repo = AsyncMock()
            mock_agent_repo_class.return_value = mock_agent_repo
            mock_agent_repo.get_active_agents_by_strategy.return_value = []

            # Should NOT raise
            result = await restore_version(
                strategy_id=mock_strategy_id,
                version=1,
                db=mock_db,
                user_id=mock_user_id,
            )

            # Verify restore was called
            mock_repo.restore_version.assert_called_once()


class TestAgentRepositoryGetActiveByStrategy:
    """Tests for AgentRepository.get_active_agents_by_strategy method."""

    @pytest.mark.asyncio
    async def test_returns_only_active_agents_for_strategy(self):
        """Should return only active agents for the specified strategy."""
        from app.db.repositories.agent import AgentRepository

        # Create mock session
        mock_session = AsyncMock()

        # Create mock result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_agent = MagicMock()
        mock_agent.status = "active"
        mock_agent.strategy_id = uuid.uuid4()
        mock_scalars.all.return_value = [mock_agent]
        mock_result.scalars.return_value = mock_scalars

        mock_session.execute.return_value = mock_result

        repo = AgentRepository(mock_session)
        strategy_id = uuid.uuid4()

        result = await repo.get_active_agents_by_strategy(strategy_id)

        assert len(result) == 1
        assert result[0].status == "active"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_active_agents(self):
        """Should return empty list when no active agents exist."""
        from app.db.repositories.agent import AgentRepository

        # Create mock session
        mock_session = AsyncMock()

        # Create mock result with empty list
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars

        mock_session.execute.return_value = mock_result

        repo = AgentRepository(mock_session)
        strategy_id = uuid.uuid4()

        result = await repo.get_active_agents_by_strategy(strategy_id)

        assert result == []
