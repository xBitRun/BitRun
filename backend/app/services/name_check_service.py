"""跨实体名称检查服务

提供策略和代理名称的跨实体唯一性检查。
确保同一用户下的 Strategy 和 Agent 名称互斥。
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentDB, StrategyDB


class NameCheckService:
    """跨实体名称检查服务

    确保 Strategy 和 Agent 共享同一个命名空间，
    同一用户下名称唯一，不同用户可以使用相同名称。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def name_exists_for_user(
        self,
        name: str,
        user_id: uuid.UUID,
        exclude_strategy_id: Optional[uuid.UUID] = None,
        exclude_agent_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        检查名称是否在用户的策略或代理中已存在。

        跨实体检查：Strategy 和 Agent 共享同一个命名空间。

        Args:
            name: 要检查的名称
            user_id: 用户 ID
            exclude_strategy_id: 排除的策略 ID（用于更新时排除自身）
            exclude_agent_id: 排除的代理 ID（用于更新时排除自身）

        Returns:
            bool: 名称是否已存在
        """
        # 检查 StrategyDB
        strategy_query = select(StrategyDB).where(
            StrategyDB.user_id == user_id,
            StrategyDB.name == name,
        )
        if exclude_strategy_id:
            strategy_query = strategy_query.where(StrategyDB.id != exclude_strategy_id)

        strategy_result = await self.session.execute(strategy_query)
        if strategy_result.scalar_one_or_none() is not None:
            return True

        # 检查 AgentDB
        agent_query = select(AgentDB).where(
            AgentDB.user_id == user_id,
            AgentDB.name == name,
        )
        if exclude_agent_id:
            agent_query = agent_query.where(AgentDB.id != exclude_agent_id)

        agent_result = await self.session.execute(agent_query)
        if agent_result.scalar_one_or_none() is not None:
            return True

        return False

    async def generate_unique_name(
        self,
        name: str,
        user_id: uuid.UUID,
        exclude_strategy_id: Optional[uuid.UUID] = None,
        exclude_agent_id: Optional[uuid.UUID] = None,
        max_attempts: int = 1000,
    ) -> str:
        """
        生成跨实体唯一的名称。

        如果名称已存在，自动添加数字后缀。

        Args:
            name: 期望的名称
            user_id: 用户 ID
            exclude_strategy_id: 排除的策略 ID（用于更新时排除自身）
            exclude_agent_id: 排除的代理 ID（用于更新时排除自身）
            max_attempts: 最大尝试次数

        Returns:
            str: 唯一的名称
        """
        from ..core.name_utils import add_numeric_suffix, parse_name_with_suffix

        # 如果原名称可用，直接返回
        if not await self.name_exists_for_user(
            name, user_id, exclude_strategy_id, exclude_agent_id
        ):
            return name

        # 解析原名称的基础部分
        base_name, _ = parse_name_with_suffix(name)

        # 从 suffix=1 开始尝试
        suffix = 1
        while suffix <= max_attempts:
            candidate = add_numeric_suffix(base_name, suffix)
            if not await self.name_exists_for_user(
                candidate, user_id, exclude_strategy_id, exclude_agent_id
            ):
                return candidate
            suffix += 1

        # 如果超过最大尝试次数，使用时间戳作为后缀
        import time

        timestamp = int(time.time())
        return add_numeric_suffix(base_name, timestamp)

    async def market_name_exists(
        self,
        name: str,
        exclude_strategy_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        检查名称是否在公开的策略市场中已存在。

        用于策略发布到市场时的全局名称检查。

        Args:
            name: 要检查的名称
            exclude_strategy_id: 排除的策略 ID（用于更新时排除自身）

        Returns:
            bool: 名称是否已在市场中存在
        """
        query = select(StrategyDB).where(
            StrategyDB.visibility == "public",
            StrategyDB.name == name,
        )
        if exclude_strategy_id:
            query = query.where(StrategyDB.id != exclude_strategy_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
