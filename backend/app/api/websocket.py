"""
WebSocket handler for real-time updates.

Provides real-time push notifications for:
- Trading decisions
- Position updates
- Account balance changes
- Strategy status changes
- System notifications
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Dict, Optional, Set, Tuple
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types"""

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"

    # Server -> Client
    DECISION = "decision"
    POSITION_UPDATE = "position_update"
    ACCOUNT_UPDATE = "account_update"
    PRICE_UPDATE = "price_update"
    STRATEGY_STATUS = "strategy_status"
    NOTIFICATION = "notification"
    ERROR = "error"
    PONG = "pong"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"


class WSMessage(BaseModel):
    """WebSocket message structure"""

    type: MessageType
    channel: Optional[str] = None
    data: Optional[dict] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(UTC)
        super().__init__(**data)

    def to_json(self) -> str:
        return self.model_dump_json()


# TTL for channel authorization cache entries (seconds)
_CHANNEL_AUTH_CACHE_TTL = 300  # 5 minutes


@dataclass
class Connection:
    """WebSocket connection wrapper"""

    websocket: WebSocket
    user_id: Optional[UUID] = None
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_ping: datetime = field(default_factory=lambda: datetime.now(UTC))
    # Cache of (channel -> (authorized: bool, checked_at: datetime))
    _auth_cache: Dict[str, Tuple[bool, datetime]] = field(default_factory=dict)

    async def send(self, message: WSMessage) -> bool:
        """Send message to this connection.

        Returns False if the send fails (connection likely dead).
        """
        try:
            await self.websocket.send_text(message.to_json())
            return True
        except (WebSocketDisconnect, RuntimeError) as e:
            # Connection is dead – caller should clean up
            logger.debug(f"Connection dead during send: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Features:
    - User-specific connections
    - Channel subscriptions
    - Broadcast to channels
    - Connection health monitoring
    - Per-user and global connection limits
    """

    # Connection limits
    MAX_CONNECTIONS_PER_USER = 5
    MAX_TOTAL_CONNECTIONS = 500

    def __init__(self):
        self._connections: Dict[str, Connection] = {}  # connection_id -> Connection
        self._user_connections: Dict[str, Set[str]] = (
            {}
        )  # user_id -> set of connection_ids
        self._channel_subscribers: Dict[str, Set[str]] = (
            {}
        )  # channel -> set of connection_ids
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Accept a new WebSocket connection.

        Returns:
            Connection ID, or None if connection limit exceeded
        """
        # Check global connection limit
        if len(self._connections) >= self.MAX_TOTAL_CONNECTIONS:
            logger.warning(
                f"Global WebSocket connection limit reached ({self.MAX_TOTAL_CONNECTIONS})"
            )
            await websocket.accept()
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {
                        "message": "Server connection limit reached. Please try again later."
                    },
                }
            )
            await websocket.close(code=4003, reason="Connection limit reached")
            return None

        # Check per-user connection limit
        if user_id:
            existing = len(self._user_connections.get(user_id, set()))
            if existing >= self.MAX_CONNECTIONS_PER_USER:
                logger.warning(
                    f"Per-user WebSocket limit reached for user {user_id} ({existing}/{self.MAX_CONNECTIONS_PER_USER})"
                )
                await websocket.accept()
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {
                            "message": "Too many connections. Please close other tabs first."
                        },
                    }
                )
                await websocket.close(
                    code=4003, reason="Per-user connection limit reached"
                )
                return None

        await websocket.accept()

        connection_id = f"{id(websocket)}_{datetime.now(UTC).timestamp()}"
        connection = Connection(
            websocket=websocket,
            user_id=UUID(user_id) if user_id else None,
        )

        async with self._lock:
            self._connections[connection_id] = connection

            if user_id:
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = set()
                self._user_connections[user_id].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a connection"""
        async with self._lock:
            connection = self._connections.pop(connection_id, None)
            if not connection:
                return

            # Remove from user connections
            if connection.user_id:
                user_id = str(connection.user_id)
                if user_id in self._user_connections:
                    self._user_connections[user_id].discard(connection_id)
                    if not self._user_connections[user_id]:
                        del self._user_connections[user_id]

            # Remove from all channel subscriptions
            for channel in connection.subscriptions:
                if channel in self._channel_subscribers:
                    self._channel_subscribers[channel].discard(connection_id)
                    if not self._channel_subscribers[channel]:
                        del self._channel_subscribers[channel]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(
        self,
        connection_id: str,
        channel: str,
    ) -> bool:
        """Subscribe a connection to a channel.

        Security: ``strategy:<id>`` and ``account:<id>`` channels are
        restricted to the resource owner.  Ownership is verified via the
        connection's ``user_id``.
        """
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            # ── Authorization check for protected channels ──
            if channel.startswith("strategy:") or channel.startswith("account:"):
                if not connection.user_id:
                    await self.send_to_connection(
                        connection_id,
                        WSMessage(
                            type=MessageType.ERROR,
                            data={
                                "message": "Authentication required for this channel"
                            },
                        ),
                    )
                    return False

                # Check per-connection auth cache first (avoids DB query)
                cached = connection._auth_cache.get(channel)
                if cached:
                    authorized, checked_at = cached
                    age = (datetime.now(UTC) - checked_at).total_seconds()
                    if age < _CHANNEL_AUTH_CACHE_TTL:
                        if not authorized:
                            await self.send_to_connection(
                                connection_id,
                                WSMessage(
                                    type=MessageType.ERROR,
                                    data={"message": "Not authorized for this channel"},
                                ),
                            )
                            return False
                        # authorized and fresh – skip DB query
                    else:
                        cached = None  # expired

                if not cached:
                    resource_id = channel.split(":", 1)[1]
                    is_owner = await self._check_channel_ownership(
                        str(connection.user_id), channel, resource_id
                    )
                    # Store result in cache
                    connection._auth_cache[channel] = (is_owner, datetime.now(UTC))
                    if not is_owner:
                        await self.send_to_connection(
                            connection_id,
                            WSMessage(
                                type=MessageType.ERROR,
                                data={"message": "Not authorized for this channel"},
                            ),
                        )
                        return False

            connection.subscriptions.add(channel)

            if channel not in self._channel_subscribers:
                self._channel_subscribers[channel] = set()
            self._channel_subscribers[channel].add(connection_id)

        # Send confirmation
        await self.send_to_connection(
            connection_id, WSMessage(type=MessageType.SUBSCRIBED, channel=channel)
        )

        logger.debug(f"Connection {connection_id} subscribed to {channel}")
        return True

    @staticmethod
    async def _check_channel_ownership(
        user_id: str, channel: str, resource_id: str
    ) -> bool:
        """Verify the user owns the strategy/account referenced by the channel."""
        try:
            from ..db.database import AsyncSessionLocal
            import uuid as _uuid

            async with AsyncSessionLocal() as session:
                if channel.startswith("strategy:"):
                    # Check both AI and quant strategies
                    from ..db.repositories.strategy import StrategyRepository
                    from ..db.repositories.quant_strategy import QuantStrategyRepository

                    repo = StrategyRepository(session)
                    strategy = await repo.get_by_id(
                        _uuid.UUID(resource_id), _uuid.UUID(user_id)
                    )
                    if strategy:
                        return True

                    qrepo = QuantStrategyRepository(session)
                    qstrategy = await qrepo.get_by_id(
                        _uuid.UUID(resource_id), _uuid.UUID(user_id)
                    )
                    return qstrategy is not None

                elif channel.startswith("account:"):
                    from ..db.repositories.account import AccountRepository

                    repo = AccountRepository(session)
                    account = await repo.get_by_id(
                        _uuid.UUID(resource_id), _uuid.UUID(user_id)
                    )
                    return account is not None

        except Exception as e:
            logger.warning(f"Channel ownership check failed for {channel}: {e}")
            return False

        return False

    async def unsubscribe(
        self,
        connection_id: str,
        channel: str,
    ) -> bool:
        """Unsubscribe a connection from a channel"""
        async with self._lock:
            connection = self._connections.get(connection_id)
            if not connection:
                return False

            connection.subscriptions.discard(channel)

            if channel in self._channel_subscribers:
                self._channel_subscribers[channel].discard(connection_id)
                if not self._channel_subscribers[channel]:
                    del self._channel_subscribers[channel]

        # Send confirmation
        await self.send_to_connection(
            connection_id, WSMessage(type=MessageType.UNSUBSCRIBED, channel=channel)
        )

        return True

    async def send_to_connection(
        self,
        connection_id: str,
        message: WSMessage,
    ) -> bool:
        """Send message to a specific connection"""
        connection = self._connections.get(connection_id)
        if not connection:
            return False
        return await connection.send(message)

    async def send_to_user(
        self,
        user_id: str,
        message: WSMessage,
    ) -> int:
        """
        Send message to all connections of a user.

        Returns:
            Number of connections message was sent to
        """
        connection_ids = self._user_connections.get(user_id, set())
        count = 0
        dead_connections: list[str] = []
        for conn_id in list(connection_ids):
            if await self.send_to_connection(conn_id, message):
                count += 1
            else:
                dead_connections.append(conn_id)

        # Auto-cleanup dead connections
        for conn_id in dead_connections:
            await self.disconnect(conn_id)

        return count

    async def broadcast_to_channel(
        self,
        channel: str,
        message: WSMessage,
    ) -> int:
        """
        Broadcast message to all subscribers of a channel.

        Returns:
            Number of connections message was sent to
        """
        message.channel = channel
        connection_ids = self._channel_subscribers.get(channel, set())
        count = 0
        dead_connections: list[str] = []
        for conn_id in list(connection_ids):  # Copy to avoid mutation during iteration
            if await self.send_to_connection(conn_id, message):
                count += 1
            else:
                dead_connections.append(conn_id)

        # Auto-cleanup dead connections
        for conn_id in dead_connections:
            await self.disconnect(conn_id)

        return count

    async def broadcast_all(self, message: WSMessage) -> int:
        """Broadcast to all connections"""
        count = 0
        for conn_id in list(self._connections.keys()):
            if await self.send_to_connection(conn_id, message):
                count += 1
        return count

    def get_connection_count(self) -> int:
        """Get total number of connections"""
        return len(self._connections)

    def get_channel_subscribers(self, channel: str) -> int:
        """Get number of subscribers for a channel"""
        return len(self._channel_subscribers.get(channel, set()))

    async def handle_message(
        self,
        connection_id: str,
        raw_message: str,
    ) -> None:
        """Handle incoming message from client"""
        try:
            data = json.loads(raw_message)
            msg_type = data.get("type", "")

            if msg_type == MessageType.PING.value:
                # Update last ping
                connection = self._connections.get(connection_id)
                if connection:
                    connection.last_ping = datetime.now(UTC)
                await self.send_to_connection(
                    connection_id, WSMessage(type=MessageType.PONG)
                )

            elif msg_type == MessageType.SUBSCRIBE.value:
                channel = data.get("channel")
                if channel:
                    await self.subscribe(connection_id, channel)

            elif msg_type == MessageType.UNSUBSCRIBE.value:
                channel = data.get("channel")
                if channel:
                    await self.unsubscribe(connection_id, channel)

        except json.JSONDecodeError:
            await self.send_to_connection(
                connection_id,
                WSMessage(type=MessageType.ERROR, data={"message": "Invalid JSON"}),
            )
        except Exception as e:
            logger.error(f"Error handling message: {e}")


# Global connection manager instance
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager"""
    return manager


# ==================== Event Publishers ====================


async def publish_decision(
    user_id: str,
    strategy_id: str,
    decision_data: dict,
) -> None:
    """Publish a new AI decision"""
    message = WSMessage(
        type=MessageType.DECISION,
        data={
            "strategy_id": strategy_id,
            "decision": decision_data,
        },
    )

    # Send to user
    await manager.send_to_user(user_id, message)

    # Broadcast to strategy channel
    await manager.broadcast_to_channel(f"strategy:{strategy_id}", message)


async def publish_position_update(
    user_id: str,
    account_id: str,
    positions: list[dict],
) -> None:
    """Publish position updates"""
    message = WSMessage(
        type=MessageType.POSITION_UPDATE,
        data={
            "account_id": account_id,
            "positions": positions,
        },
    )

    await manager.send_to_user(user_id, message)
    await manager.broadcast_to_channel(f"account:{account_id}", message)


async def publish_account_update(
    user_id: str,
    account_id: str,
    account_state: dict,
) -> None:
    """Publish account state update"""
    message = WSMessage(
        type=MessageType.ACCOUNT_UPDATE,
        data={
            "account_id": account_id,
            "state": account_state,
        },
    )

    await manager.send_to_user(user_id, message)


async def publish_price_update(
    exchange: str,
    symbol: str,
    price: float,
    bid: Optional[float] = None,
    ask: Optional[float] = None,
    source: str = "prefetch",
) -> None:
    """
    Publish public price update to a symbol channel.

    Channel format:
        price:<exchange>:<symbol>
    """
    channel = f"price:{exchange.lower()}:{symbol.upper()}"
    message = WSMessage(
        type=MessageType.PRICE_UPDATE,
        data={
            "exchange": exchange.lower(),
            "symbol": symbol.upper(),
            "price": price,
            "bid": bid,
            "ask": ask,
            "source": source,
        },
    )

    await manager.broadcast_to_channel(channel, message)


def has_price_subscribers(exchange: str, symbol: str) -> bool:
    """Check whether a price channel currently has subscribers."""
    channel = f"price:{exchange.lower()}:{symbol.upper()}"
    return manager.get_channel_subscribers(channel) > 0


async def publish_strategy_status(
    user_id: str,
    strategy_id: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    """Publish strategy status change"""
    message = WSMessage(
        type=MessageType.STRATEGY_STATUS,
        data={
            "strategy_id": strategy_id,
            "status": status,
            "error": error,
        },
    )

    await manager.send_to_user(user_id, message)
    await manager.broadcast_to_channel(f"strategy:{strategy_id}", message)


async def publish_notification(
    user_id: str,
    title: str,
    message_text: str,
    level: str = "info",
) -> None:
    """Publish a notification to user"""
    message = WSMessage(
        type=MessageType.NOTIFICATION,
        data={
            "title": title,
            "message": message_text,
            "level": level,
        },
    )

    await manager.send_to_user(user_id, message)
