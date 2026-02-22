"""Notification routes"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ...core.dependencies import CurrentUserDep
from ...services.notifications import (
    get_notification_service,
    Notification,
    NotificationType,
    NotificationChannel,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================


class NotificationStatus(BaseModel):
    """Notification service status"""

    enabled: bool
    configured_channels: list[str]


class TestNotificationRequest(BaseModel):
    """Request to send a test notification"""

    channel: Optional[str] = Field(
        None,
        description="Channel to test (telegram, discord, email). If not specified, tests all configured channels.",
    )
    message: str = Field(
        default="This is a test notification from BITRUN.",
        description="Test message to send",
    )


class TestNotificationResponse(BaseModel):
    """Test notification result"""

    success: bool
    results: dict[str, bool]


class ConfigureChannelRequest(BaseModel):
    """Request to configure a notification channel"""

    channel: str = Field(
        ..., description="Channel to configure (telegram, discord, email)"
    )
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    # Discord
    discord_webhook_url: Optional[str] = None
    # Email
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_to: Optional[str] = None


# ==================== Routes ====================


@router.get("/status", response_model=NotificationStatus)
async def get_notification_status(
    user_id: CurrentUserDep,
):
    """
    Get notification service status.

    Returns which channels are configured and enabled.
    """
    service = get_notification_service()

    configured_channels = []
    for channel, provider in service.providers.items():
        if provider.is_configured():
            configured_channels.append(channel.value)

    return NotificationStatus(
        enabled=service.is_any_configured(),
        configured_channels=configured_channels,
    )


@router.post("/test", response_model=TestNotificationResponse)
async def test_notification(
    data: TestNotificationRequest,
    user_id: CurrentUserDep,
):
    """
    Send a test notification.

    Use this to verify your notification configuration is working.
    """
    service = get_notification_service()

    if not service.is_any_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No notification channels configured",
        )

    # Create test notification
    notification = Notification(
        type=NotificationType.SYSTEM,
        title="Test Notification",
        message=data.message,
        data={
            "User": user_id[:8] + "...",
            "Test": "Successful",
        },
        priority="normal",
    )

    # Determine channels to test
    channels = None
    if data.channel:
        try:
            channels = [NotificationChannel(data.channel)]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channel: {data.channel}. Valid options: telegram, discord, email",
            )

    # Send test notification
    results = await service.send(notification, channels)

    # Convert to string keys for response
    results_dict = {channel.value: success for channel, success in results.items()}

    return TestNotificationResponse(
        success=any(results.values()),
        results=results_dict,
    )


@router.get("/channels")
async def list_channels(
    user_id: CurrentUserDep,
):
    """
    List all available notification channels and their configuration status.
    """
    service = get_notification_service()

    channels = []
    for channel in NotificationChannel:
        provider = service.providers.get(channel)
        channels.append(
            {
                "id": channel.value,
                "name": channel.value.title(),
                "configured": provider.is_configured() if provider else False,
                "description": _get_channel_description(channel),
            }
        )

    return {"channels": channels}


def _get_channel_description(channel: NotificationChannel) -> str:
    """Get description for a channel"""
    descriptions = {
        NotificationChannel.TELEGRAM: "Receive notifications via Telegram bot",
        NotificationChannel.DISCORD: "Receive notifications via Discord webhook",
        NotificationChannel.EMAIL: "Receive notifications via email",
    }
    return descriptions.get(channel, "")
