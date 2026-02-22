"""
WebSocket API routes.

Provides WebSocket endpoints for real-time updates.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from ..websocket import (
    get_connection_manager,
)
from ...core.config import get_settings
from ...core.security import verify_token
from ...services.redis_service import get_redis_service

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


async def validate_websocket_token(token: str) -> Optional[str]:
    """
    Validate JWT token for WebSocket connection.

    Args:
        token: JWT token string

    Returns:
        user_id if token is valid and not blacklisted, None otherwise
    """
    try:
        # Verify token using the standard security function
        token_data = verify_token(token, token_type="access")

        # Check if token is blacklisted
        if token_data.jti:
            try:
                redis = await get_redis_service()
                if await redis.is_token_blacklisted(token_data.jti):
                    logger.warning(
                        f"WebSocket connection attempted with blacklisted token: {token_data.jti[:8]}..."
                    )
                    return None
            except Exception as e:
                settings = get_settings()
                if settings.environment == "production":
                    # Fail-closed in production: reject token if we can't verify blacklist
                    logger.error(
                        f"Redis unavailable for token blacklist check in production, rejecting connection: {e}"
                    )
                    return None
                else:
                    # Fail-open in development: allow connection if Redis is down
                    logger.warning(
                        f"Redis unavailable for token blacklist check (dev mode, allowing): {e}"
                    )

        return token_data.sub
    except JWTError as e:
        logger.warning(f"Invalid WebSocket JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating WebSocket token: {e}")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT token for authentication"),
):
    """
    WebSocket endpoint for real-time updates.

    Query params:
        token: JWT token for authentication (optional for public channels)

    Client messages:
        - {"type": "subscribe", "channel": "strategy:<id>"}
        - {"type": "unsubscribe", "channel": "strategy:<id>"}
        - {"type": "ping"}

    Server messages:
        - {"type": "decision", "data": {...}}
        - {"type": "position_update", "data": {...}}
        - {"type": "account_update", "data": {...}}
        - {"type": "price_update", "data": {...}}
        - {"type": "strategy_status", "data": {...}}
        - {"type": "notification", "data": {...}}
        - {"type": "pong"}

    Channels:
        - strategy:<strategy_id> - Strategy decisions and status
        - account:<account_id> - Account and position updates
        - price:<exchange>:<symbol> - Public price updates (e.g. price:hyperliquid:BTC)
        - system - System-wide notifications
    """
    manager = get_connection_manager()

    # Validate token and get user_id (if provided)
    user_id = None
    if token:
        user_id = await validate_websocket_token(token)
        if not user_id:
            # Token was provided but invalid - send error and close
            await websocket.accept()
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {"message": "Invalid or expired authentication token"},
                }
            )
            await websocket.close(code=4001, reason="Authentication failed")
            return

    # Accept connection (may return None if limit exceeded)
    connection_id = await manager.connect(websocket, user_id)
    if not connection_id:
        return  # Connection was rejected due to limits

    # Subscribe to user-specific channel if authenticated
    if user_id:
        await manager.subscribe(connection_id, f"user:{user_id}")

    # Subscribe to system channel
    await manager.subscribe(connection_id, "system")

    try:
        while True:
            # Wait for messages
            raw_message = await websocket.receive_text()
            await manager.handle_message(connection_id, raw_message)

    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(connection_id)


@router.get("/ws/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns:
        Connection count and channel subscriber counts
    """
    manager = get_connection_manager()

    return {
        "total_connections": manager.get_connection_count(),
        "channels": {
            "system": manager.get_channel_subscribers("system"),
        },
    }
