"""
Notification Service - Multi-channel notification delivery.

Supports:
- Telegram
- Discord
- Email (Resend)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import aiohttp

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channels"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    EMAIL = "email"


class NotificationType(str, Enum):
    """Notification types"""
    DECISION = "decision"
    TRADE_EXECUTED = "trade_executed"
    STRATEGY_STATUS = "strategy_status"
    RISK_ALERT = "risk_alert"
    SYSTEM = "system"


@dataclass
class Notification:
    """Notification data"""
    type: NotificationType
    title: str
    message: str
    recipient_email: Optional[str] = None  # For email notifications
    data: Optional[dict] = None
    priority: str = "normal"  # low, normal, high, urgent


class NotificationProvider(ABC):
    """Abstract base class for notification providers"""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured"""
        pass


class TelegramProvider(NotificationProvider):
    """Telegram notification provider"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send(self, notification: Notification) -> bool:
        if not self.is_configured():
            logger.warning("Telegram not configured, skipping notification")
            return False

        # Format message
        emoji = self._get_emoji(notification.type)
        message = f"{emoji} *{notification.title}*\n\n{notification.message}"

        # Add data details if present
        if notification.data:
            details = []
            for key, value in notification.data.items():
                details.append(f"• {key}: `{value}`")
            if details:
                message += "\n\n" + "\n".join(details)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True,
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info(f"Telegram notification sent: {notification.title}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"Telegram send failed: {error}")
                        return False
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            return False

    def _get_emoji(self, type: NotificationType) -> str:
        emoji_map = {
            NotificationType.DECISION: "🤖",
            NotificationType.TRADE_EXECUTED: "💰",
            NotificationType.STRATEGY_STATUS: "📊",
            NotificationType.RISK_ALERT: "⚠️",
            NotificationType.SYSTEM: "ℹ️",
        }
        return emoji_map.get(type, "📢")


class DiscordProvider(NotificationProvider):
    """Discord notification provider via webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    async def send(self, notification: Notification) -> bool:
        if not self.is_configured():
            logger.warning("Discord not configured, skipping notification")
            return False

        # Build embed
        color = self._get_color(notification.type, notification.priority)

        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": color,
            "footer": {"text": f"BITRUN • {notification.type.value}"},
        }

        # Add fields for data
        if notification.data:
            fields = []
            for key, value in notification.data.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True,
                })
            embed["fields"] = fields

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json={"embeds": [embed]},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status in (200, 204):
                        logger.info(f"Discord notification sent: {notification.title}")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"Discord send failed: {error}")
                        return False
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
            return False

    def _get_color(self, type: NotificationType, priority: str) -> int:
        if priority == "urgent":
            return 0xFF0000  # Red
        if priority == "high":
            return 0xFF9900  # Orange

        color_map = {
            NotificationType.DECISION: 0x5865F2,  # Discord blurple
            NotificationType.TRADE_EXECUTED: 0x57F287,  # Green
            NotificationType.STRATEGY_STATUS: 0x3498DB,  # Blue
            NotificationType.RISK_ALERT: 0xFEE75C,  # Yellow
            NotificationType.SYSTEM: 0x99AAB5,  # Gray
        }
        return color_map.get(type, 0x99AAB5)


class ResendEmailProvider(NotificationProvider):
    """Email notification provider via Resend API"""

    def __init__(self, api_key: str, from_email: str):
        self.api_key = api_key
        self.from_email = from_email

    def is_configured(self) -> bool:
        return all([self.api_key, self.from_email])

    async def send(self, notification: Notification) -> bool:
        if not self.is_configured():
            logger.warning("Resend email not configured, skipping notification")
            return False

        if not notification.recipient_email:
            logger.warning("No recipient email in notification, skipping email")
            return False

        try:
            import resend

            resend.api_key = self.api_key

            # Plain text version
            text_content = f"{notification.title}\n\n{notification.message}"
            if notification.data:
                text_content += "\n\nDetails:\n"
                for key, value in notification.data.items():
                    text_content += f"  {key}: {value}\n"

            # HTML version
            details_html = ""
            if notification.data:
                items = "".join(
                    f"<li><strong>{k}:</strong> {v}</li>"
                    for k, v in notification.data.items()
                )
                details_html = f"<hr><h4>Details</h4><ul>{items}</ul>"

            html_content = f"""
            <html>
            <body>
                <h2>{notification.title}</h2>
                <p>{notification.message}</p>
                {details_html}
                <hr>
                <p style="color: gray; font-size: 12px;">Sent by BITRUN</p>
            </body>
            </html>
            """

            # Send via Resend API (recipient from notification)
            params = {
                "from": self.from_email,
                "to": [notification.recipient_email],
                "subject": f"[BITRUN] {notification.title}",
                "html": html_content,
                "text": text_content,
            }

            # Resend SDK is synchronous, run in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: resend.Emails.send(params))

            logger.info(f"Resend email sent to {notification.recipient_email}: {notification.title}")
            return True

        except ImportError:
            logger.error("resend package not installed, email notifications unavailable")
            return False
        except Exception as e:
            logger.error(f"Resend email notification error: {e}")
            return False


class NotificationService:
    """
    Main notification service that manages multiple providers.

    Usage:
        service = NotificationService()
        await service.send_decision_notification(decision_data)
    """

    def __init__(self):
        self.providers: dict[NotificationChannel, NotificationProvider] = {}
        self._initialized = False

    def configure(
        self,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        discord_webhook_url: Optional[str] = None,
        resend_api_key: Optional[str] = None,
        resend_from: Optional[str] = None,
    ) -> None:
        """Configure notification providers"""

        # Telegram
        if telegram_bot_token and telegram_chat_id:
            self.providers[NotificationChannel.TELEGRAM] = TelegramProvider(
                bot_token=telegram_bot_token,
                chat_id=telegram_chat_id,
            )
            logger.info("Telegram notifications enabled")

        # Discord
        if discord_webhook_url:
            self.providers[NotificationChannel.DISCORD] = DiscordProvider(
                webhook_url=discord_webhook_url,
            )
            logger.info("Discord notifications enabled")

        # Email (Resend) - recipient is dynamic, passed in notification
        if resend_api_key and resend_from:
            self.providers[NotificationChannel.EMAIL] = ResendEmailProvider(
                api_key=resend_api_key,
                from_email=resend_from,
            )
            logger.info("Resend email notifications enabled")

        self._initialized = True

    def is_any_configured(self) -> bool:
        """Check if any provider is configured"""
        return any(p.is_configured() for p in self.providers.values())

    async def send(
        self,
        notification: Notification,
        channels: Optional[list[NotificationChannel]] = None,
    ) -> dict[NotificationChannel, bool]:
        """
        Send notification to specified channels (or all configured).

        Returns dict mapping channel to success status.
        """
        results = {}

        target_channels = channels or list(self.providers.keys())

        for channel in target_channels:
            provider = self.providers.get(channel)
            if provider and provider.is_configured():
                try:
                    results[channel] = await provider.send(notification)
                except Exception as e:
                    logger.error(f"Error sending to {channel}: {e}")
                    results[channel] = False

        return results

    # Convenience methods for specific notification types

    async def send_decision_notification(
        self,
        strategy_name: str,
        decision_data: dict,
        recipient_email: Optional[str] = None,
        channels: Optional[list[NotificationChannel]] = None,
    ) -> dict[NotificationChannel, bool]:
        """Send notification about a trading decision"""

        decisions = decision_data.get("decisions", [])
        if not decisions:
            action = "HOLD"
        else:
            main_decision = decisions[0]
            action = main_decision.get("action", "hold").upper().replace("_", " ")

        notification = Notification(
            type=NotificationType.DECISION,
            title=f"New Decision: {strategy_name}",
            message=f"Action: {action}\nConfidence: {decision_data.get('overall_confidence', 0)}%",
            recipient_email=recipient_email,
            data={
                "Strategy": strategy_name,
                "Confidence": f"{decision_data.get('overall_confidence', 0)}%",
                "Latency": f"{decision_data.get('latency_ms', 0)}ms",
            },
            priority="normal",
        )

        return await self.send(notification, channels)

    async def send_trade_notification(
        self,
        strategy_name: str,
        symbol: str,
        action: str,
        size_usd: float,
        price: float,
        recipient_email: Optional[str] = None,
        channels: Optional[list[NotificationChannel]] = None,
    ) -> dict[NotificationChannel, bool]:
        """Send notification about an executed trade"""

        notification = Notification(
            type=NotificationType.TRADE_EXECUTED,
            title=f"Trade Executed: {symbol}",
            message=f"Strategy '{strategy_name}' executed {action}",
            recipient_email=recipient_email,
            data={
                "Symbol": symbol,
                "Action": action.upper(),
                "Size": f"${size_usd:,.2f}",
                "Price": f"${price:,.2f}",
            },
            priority="normal",
        )

        return await self.send(notification, channels)

    async def send_risk_alert(
        self,
        title: str,
        message: str,
        recipient_email: Optional[str] = None,
        details: Optional[dict] = None,
        channels: Optional[list[NotificationChannel]] = None,
    ) -> dict[NotificationChannel, bool]:
        """Send a risk alert notification"""

        notification = Notification(
            type=NotificationType.RISK_ALERT,
            title=f"⚠️ Risk Alert: {title}",
            message=message,
            recipient_email=recipient_email,
            data=details,
            priority="high",
        )

        return await self.send(notification, channels)

    async def send_strategy_status_notification(
        self,
        strategy_name: str,
        old_status: str,
        new_status: str,
        recipient_email: Optional[str] = None,
        error_message: Optional[str] = None,
        channels: Optional[list[NotificationChannel]] = None,
    ) -> dict[NotificationChannel, bool]:
        """Send notification about strategy status change"""

        priority = "high" if new_status == "error" else "normal"

        message = f"Strategy changed from {old_status} to {new_status}"
        if error_message:
            message += f"\n\nError: {error_message}"

        notification = Notification(
            type=NotificationType.STRATEGY_STATUS,
            title=f"Strategy Status: {strategy_name}",
            message=message,
            recipient_email=recipient_email,
            data={
                "Strategy": strategy_name,
                "Old Status": old_status,
                "New Status": new_status,
            },
            priority=priority,
        )

        return await self.send(notification, channels)


# Global notification service instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service"""
    global _notification_service

    if _notification_service is None:
        _notification_service = NotificationService()

        # Auto-configure from settings if available
        settings = get_settings()

        _notification_service.configure(
            telegram_bot_token=getattr(settings, 'telegram_bot_token', None),
            telegram_chat_id=getattr(settings, 'telegram_chat_id', None),
            discord_webhook_url=getattr(settings, 'discord_webhook_url', None),
            resend_api_key=getattr(settings, 'resend_api_key', None),
            resend_from=getattr(settings, 'resend_from', None),
        )

    return _notification_service
