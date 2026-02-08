"""Decision record repository for database operations"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select, func, cast, type_coerce
from sqlalchemy.types import Text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DecisionRecordDB


class DecisionRepository:
    """Repository for DecisionRecord CRUD operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        strategy_id: uuid.UUID,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        chain_of_thought: str = "",
        market_assessment: str = "",
        decisions: Optional[list] = None,
        overall_confidence: int = 0,
        ai_model: str = "",
        tokens_used: int = 0,
        latency_ms: int = 0,
        # Debate fields
        is_debate: bool = False,
        debate_models: Optional[list] = None,
        debate_responses: Optional[list] = None,
        debate_consensus_mode: Optional[str] = None,
        debate_agreement_score: Optional[float] = None,
        # Market data snapshot
        market_snapshot: Optional[list] = None,
        # Account state snapshot
        account_snapshot: Optional[dict] = None,
    ) -> DecisionRecordDB:
        """Create a new decision record"""
        record = DecisionRecordDB(
            strategy_id=strategy_id,
            timestamp=datetime.now(UTC),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=raw_response,
            chain_of_thought=chain_of_thought,
            market_assessment=market_assessment,
            decisions=decisions or [],
            overall_confidence=overall_confidence,
            ai_model=ai_model,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            # Market data snapshot
            market_snapshot=market_snapshot,
            # Account state snapshot
            account_snapshot=account_snapshot,
            # Debate fields
            is_debate=is_debate,
            debate_models=debate_models,
            debate_responses=debate_responses,
            debate_consensus_mode=debate_consensus_mode,
            debate_agreement_score=debate_agreement_score,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_by_id(
        self,
        decision_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[DecisionRecordDB]:
        """Get decision record by ID.

        If *user_id* is provided, the query joins through the strategy table
        to verify the record belongs to the requesting user.
        """
        from ..models import StrategyDB

        stmt = select(DecisionRecordDB).where(DecisionRecordDB.id == decision_id)

        if user_id is not None:
            stmt = stmt.join(
                StrategyDB,
                DecisionRecordDB.strategy_id == StrategyDB.id,
            ).where(StrategyDB.user_id == user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _apply_filters(self, query, strategy_id: uuid.UUID, execution_filter: str = "all", action_filter: Optional[str] = None):
        """Apply common filters to a query."""
        query = query.where(DecisionRecordDB.strategy_id == strategy_id)
        if execution_filter == "executed":
            query = query.where(DecisionRecordDB.executed == True)
        elif execution_filter == "skipped":
            query = query.where(DecisionRecordDB.executed == False)
        if action_filter:
            # Whitelist validation to prevent SQL injection
            VALID_ACTIONS = {"long", "short", "close_long", "close_short", "hold"}
            if action_filter not in VALID_ACTIONS:
                return query.where(False)  # Return empty result for invalid actions
            # PostgreSQL JSONB: decisions column contains an element with matching action
            query = query.where(
                cast(DecisionRecordDB.decisions, Text).contains(f'"action": "{action_filter}"')
            )
        return query

    async def get_by_strategy(
        self,
        strategy_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        execution_filter: str = "all",
        action_filter: Optional[str] = None,
    ) -> list[DecisionRecordDB]:
        """
        Get decision records for a strategy.

        Returns newest first.
        """
        query = select(DecisionRecordDB)
        query = self._apply_filters(query, strategy_id, execution_filter, action_filter)
        query = query.order_by(DecisionRecordDB.timestamp.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_strategy(
        self,
        strategy_id: uuid.UUID,
        execution_filter: str = "all",
        action_filter: Optional[str] = None,
    ) -> int:
        """Count decision records for a strategy."""
        query = select(func.count(DecisionRecordDB.id))
        query = self._apply_filters(query, strategy_id, execution_filter, action_filter)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_recent(
        self,
        user_id: uuid.UUID,
        limit: int = 20
    ) -> list[DecisionRecordDB]:
        """
        Get recent decision records across all user's strategies.

        Requires join with strategies table.
        """
        from ..models import StrategyDB

        query = (
            select(DecisionRecordDB)
            .join(StrategyDB, DecisionRecordDB.strategy_id == StrategyDB.id)
            .where(StrategyDB.user_id == user_id)
            .order_by(DecisionRecordDB.timestamp.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_executed(
        self,
        decision_id: uuid.UUID,
        execution_results: list
    ) -> bool:
        """Mark a decision as executed with results"""
        record = await self.get_by_id(decision_id)
        if not record:
            return False

        record.executed = True
        record.execution_results = execution_results

        await self.session.flush()
        return True

    async def get_stats(
        self,
        strategy_id: uuid.UUID
    ) -> dict:
        """Get decision statistics for a strategy"""
        # Total decisions
        total_result = await self.session.execute(
            select(func.count(DecisionRecordDB.id)).where(
                DecisionRecordDB.strategy_id == strategy_id
            )
        )
        total = total_result.scalar() or 0

        # Executed decisions
        executed_result = await self.session.execute(
            select(func.count(DecisionRecordDB.id)).where(
                DecisionRecordDB.strategy_id == strategy_id,
                DecisionRecordDB.executed == True
            )
        )
        executed = executed_result.scalar() or 0

        # Average confidence
        avg_conf_result = await self.session.execute(
            select(func.avg(DecisionRecordDB.overall_confidence)).where(
                DecisionRecordDB.strategy_id == strategy_id
            )
        )
        avg_confidence = avg_conf_result.scalar() or 0

        # Average latency
        avg_latency_result = await self.session.execute(
            select(func.avg(DecisionRecordDB.latency_ms)).where(
                DecisionRecordDB.strategy_id == strategy_id
            )
        )
        avg_latency = avg_latency_result.scalar() or 0

        # Total tokens
        total_tokens_result = await self.session.execute(
            select(func.coalesce(func.sum(DecisionRecordDB.tokens_used), 0)).where(
                DecisionRecordDB.strategy_id == strategy_id
            )
        )
        total_tokens = total_tokens_result.scalar() or 0

        # Action counts — stream decisions column to avoid loading all into memory
        decisions_result = await self.session.stream(
            select(DecisionRecordDB.decisions).where(
                DecisionRecordDB.strategy_id == strategy_id
            )
        )
        action_counts: dict[str, int] = {}
        async for (decisions_list,) in decisions_result:
            for d in (decisions_list or []):
                action = d.get("action", "unknown") if isinstance(d, dict) else "unknown"
                action_counts[action] = action_counts.get(action, 0) + 1

        return {
            "total_decisions": total,
            "executed_decisions": executed,
            "average_confidence": round(avg_confidence, 1),
            "average_latency_ms": round(avg_latency, 0),
            "total_tokens": int(total_tokens),
            "action_counts": action_counts,
        }

    async def delete_old_records(
        self,
        strategy_id: uuid.UUID,
        keep_count: int = 100
    ) -> int:
        """
        Delete old decision records, keeping the most recent ones.

        Returns number of deleted records.
        """
        # Get IDs to keep
        keep_query = (
            select(DecisionRecordDB.id)
            .where(DecisionRecordDB.strategy_id == strategy_id)
            .order_by(DecisionRecordDB.timestamp.desc())
            .limit(keep_count)
        )
        keep_result = await self.session.execute(keep_query)
        keep_ids = [row[0] for row in keep_result.all()]

        if not keep_ids:
            return 0

        # Delete records not in keep list
        delete_query = (
            select(DecisionRecordDB)
            .where(
                DecisionRecordDB.strategy_id == strategy_id,
                DecisionRecordDB.id.not_in(keep_ids)
            )
        )
        delete_result = await self.session.execute(delete_query)
        records_to_delete = list(delete_result.scalars().all())

        for record in records_to_delete:
            await self.session.delete(record)

        await self.session.flush()
        return len(records_to_delete)
