"""
Tests for NotificationService, TelegramProvider, DiscordProvider, EmailProvider.

Covers: configure(), send(), send_decision_notification(), error handling.
"""

import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.notifications import (
    DiscordProvider,
    ResendEmailProvider,
    Notification,
    NotificationChannel,
    NotificationService,
    NotificationType,
    TelegramProvider,
)


# ==================== Helpers ====================


def _make_notification(**kwargs) -> Notification:
    """Create a test notification with defaults."""
    defaults = {
        "type": NotificationType.DECISION,
        "title": "Test Title",
        "message": "Test message body",
        "data": None,
        "priority": "normal",
    }
    defaults.update(kwargs)
    return Notification(**defaults)


def _mock_aiohttp_session(status: int = 200, text: str = "OK"):
    """Build a mock aiohttp ClientSession with nested async-context-manager support."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.text = AsyncMock(return_value=text)

    # session.post(...) returns an async context manager
    mock_post_cm = MagicMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
    mock_post_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.post = MagicMock(return_value=mock_post_cm)

    # ClientSession() returns an async context manager
    mock_client_cm = MagicMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_client_cm.__aexit__ = AsyncMock(return_value=False)

    mock_client_cls = MagicMock(return_value=mock_client_cm)

    return mock_client_cls, mock_session, mock_response


# ==================== TelegramProvider ====================


class TestTelegramProvider:
    """Tests for TelegramProvider."""

    def test_is_configured_true(self):
        provider = TelegramProvider(bot_token="tok123", chat_id="chat456")
        assert provider.is_configured() is True

    def test_is_configured_false_missing_token(self):
        provider = TelegramProvider(bot_token="", chat_id="chat456")
        assert provider.is_configured() is False

    def test_is_configured_false_missing_chat_id(self):
        provider = TelegramProvider(bot_token="tok123", chat_id="")
        assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_success(self):
        provider = TelegramProvider(bot_token="tok", chat_id="cid")
        mock_client, mock_session, _ = _mock_aiohttp_session(status=200)

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(_make_notification())

        assert result is True
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_not_configured(self):
        provider = TelegramProvider(bot_token="", chat_id="")
        result = await provider.send(_make_notification())
        assert result is False

    @pytest.mark.asyncio
    async def test_send_with_data(self):
        provider = TelegramProvider(bot_token="tok", chat_id="cid")
        mock_client, mock_session, _ = _mock_aiohttp_session(status=200)

        notification = _make_notification(data={"Symbol": "BTC", "Price": "50000"})

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(notification)

        assert result is True
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "BTC" in payload["text"]

    @pytest.mark.asyncio
    async def test_send_http_error(self):
        provider = TelegramProvider(bot_token="tok", chat_id="cid")
        mock_client, _, _ = _mock_aiohttp_session(status=400, text="Bad Request")

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(_make_notification())

        assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error(self):
        provider = TelegramProvider(bot_token="tok", chat_id="cid")
        mock_client = MagicMock()
        mock_client.return_value.__aenter__.side_effect = ConnectionError("timeout")

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(_make_notification())

        assert result is False

    def test_get_emoji(self):
        provider = TelegramProvider(bot_token="t", chat_id="c")
        assert provider._get_emoji(NotificationType.DECISION) == "🤖"
        assert provider._get_emoji(NotificationType.TRADE_EXECUTED) == "💰"
        assert provider._get_emoji(NotificationType.RISK_ALERT) == "⚠️"


# ==================== DiscordProvider ====================


class TestDiscordProvider:
    """Tests for DiscordProvider."""

    def test_is_configured_true(self):
        provider = DiscordProvider(webhook_url="https://discord.com/api/webhooks/123")
        assert provider.is_configured() is True

    def test_is_configured_false(self):
        provider = DiscordProvider(webhook_url="")
        assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_success(self):
        provider = DiscordProvider(webhook_url="https://discord.com/api/webhooks/123")
        mock_client, mock_session, _ = _mock_aiohttp_session(status=204)

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(_make_notification())

        assert result is True

    @pytest.mark.asyncio
    async def test_send_not_configured(self):
        provider = DiscordProvider(webhook_url="")
        result = await provider.send(_make_notification())
        assert result is False

    @pytest.mark.asyncio
    async def test_send_with_data_fields(self):
        provider = DiscordProvider(webhook_url="https://discord.com/api/webhooks/123")
        mock_client, mock_session, _ = _mock_aiohttp_session(status=200)
        notification = _make_notification(data={"Symbol": "ETH", "Action": "BUY"})

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(notification)

        assert result is True
        call_kwargs = mock_session.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        embed = payload["embeds"][0]
        assert "fields" in embed
        assert len(embed["fields"]) == 2

    @pytest.mark.asyncio
    async def test_send_http_error(self):
        provider = DiscordProvider(webhook_url="https://discord.com/api/webhooks/123")
        mock_client, _, _ = _mock_aiohttp_session(status=500, text="Server Error")

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(_make_notification())

        assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error(self):
        provider = DiscordProvider(webhook_url="https://discord.com/api/webhooks/123")
        mock_client = MagicMock()
        mock_client.return_value.__aenter__.side_effect = ConnectionError("timeout")

        with patch("app.services.notifications.aiohttp.ClientSession", mock_client):
            result = await provider.send(_make_notification())

        assert result is False

    def test_get_color_urgent_priority(self):
        provider = DiscordProvider(webhook_url="url")
        assert provider._get_color(NotificationType.DECISION, "urgent") == 0xFF0000

    def test_get_color_high_priority(self):
        provider = DiscordProvider(webhook_url="url")
        assert provider._get_color(NotificationType.DECISION, "high") == 0xFF9900

    def test_get_color_by_type(self):
        provider = DiscordProvider(webhook_url="url")
        assert provider._get_color(NotificationType.TRADE_EXECUTED, "normal") == 0x57F287


# ==================== EmailProvider ====================


class TestResendEmailProvider:
    """Tests for ResendEmailProvider."""

    def _make_email_provider(self, **overrides):
        defaults = dict(
            api_key="re_test_key_123",
            from_email="from@example.com",
        )
        defaults.update(overrides)
        return ResendEmailProvider(**defaults)

    def test_is_configured_true(self):
        provider = self._make_email_provider()
        assert provider.is_configured() is True

    def test_is_configured_false_missing_api_key(self):
        provider = self._make_email_provider(api_key="")
        assert provider.is_configured() is False

    def test_is_configured_false_missing_from_email(self):
        provider = self._make_email_provider(from_email="")
        assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_not_configured(self):
        provider = self._make_email_provider(api_key="")
        result = await provider.send(_make_notification())
        assert result is False

    @pytest.mark.asyncio
    async def test_send_no_recipient(self):
        provider = self._make_email_provider()
        notification = _make_notification()
        # No recipient_email set
        result = await provider.send(notification)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self):
        provider = self._make_email_provider()
        mock_resend = MagicMock()
        mock_resend.Emails = MagicMock()
        mock_resend.Emails.send = MagicMock(return_value={"id": "123"})

        notification = _make_notification()
        notification.recipient_email = "to@example.com"

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = await provider.send(notification)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_data(self):
        provider = self._make_email_provider()
        mock_resend = MagicMock()
        mock_resend.Emails = MagicMock()
        mock_resend.Emails.send = MagicMock(return_value={"id": "123"})

        notification = _make_notification(data={"key": "value"})
        notification.recipient_email = "to@example.com"

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = await provider.send(notification)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_resend_error(self):
        provider = self._make_email_provider()
        mock_resend = MagicMock()
        mock_resend.Emails = MagicMock()
        mock_resend.Emails.send = MagicMock(side_effect=Exception("Resend error"))

        notification = _make_notification()
        notification.recipient_email = "to@example.com"

        with patch.dict(sys.modules, {"resend": mock_resend}):
            result = await provider.send(notification)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_import_error(self):
        provider = self._make_email_provider()
        notification = _make_notification()
        notification.recipient_email = "to@example.com"

        # Simulate resend not installed
        with patch.dict(sys.modules, {"resend": None}):
            result = await provider.send(notification)

        assert result is False


# ==================== NotificationService ====================


class TestNotificationService:
    """Tests for the main NotificationService."""

    def test_configure_telegram(self):
        service = NotificationService()
        service.configure(telegram_bot_token="tok", telegram_chat_id="cid")

        assert NotificationChannel.TELEGRAM in service.providers
        assert service._initialized is True

    def test_configure_discord(self):
        service = NotificationService()
        service.configure(discord_webhook_url="https://discord.com/hook")

        assert NotificationChannel.DISCORD in service.providers

    def test_configure_email(self):
        service = NotificationService()
        service.configure(
            resend_api_key="re_test_key_123",
            resend_from="from@example.com",
        )
        assert NotificationChannel.EMAIL in service.providers

    def test_configure_no_providers(self):
        service = NotificationService()
        service.configure()

        assert len(service.providers) == 0
        assert service._initialized is True

    def test_is_any_configured(self):
        service = NotificationService()
        service.configure(telegram_bot_token="tok", telegram_chat_id="cid")
        assert service.is_any_configured() is True

    def test_is_any_configured_none(self):
        service = NotificationService()
        service.configure()
        assert service.is_any_configured() is False

    @pytest.mark.asyncio
    async def test_send_to_all_channels(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        results = await service.send(_make_notification())

        assert results[NotificationChannel.TELEGRAM] is True
        mock_provider.send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_to_specific_channel(self):
        service = NotificationService()
        mock_tg = AsyncMock()
        mock_tg.is_configured.return_value = True
        mock_tg.send.return_value = True
        mock_dc = AsyncMock()
        mock_dc.is_configured.return_value = True
        mock_dc.send.return_value = True

        service.providers[NotificationChannel.TELEGRAM] = mock_tg
        service.providers[NotificationChannel.DISCORD] = mock_dc

        results = await service.send(
            _make_notification(),
            channels=[NotificationChannel.TELEGRAM],
        )

        assert NotificationChannel.TELEGRAM in results
        assert NotificationChannel.DISCORD not in results

    @pytest.mark.asyncio
    async def test_send_provider_exception(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.side_effect = RuntimeError("boom")
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        results = await service.send(_make_notification())

        assert results[NotificationChannel.TELEGRAM] is False

    @pytest.mark.asyncio
    async def test_send_decision_notification_with_decisions(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        decision_data = {
            "decisions": [{"action": "open_long"}],
            "overall_confidence": 85,
            "latency_ms": 120,
        }
        results = await service.send_decision_notification("BTC Strategy", decision_data)

        assert results[NotificationChannel.TELEGRAM] is True
        sent_notification = mock_provider.send.call_args[0][0]
        assert "OPEN LONG" in sent_notification.message
        assert sent_notification.type == NotificationType.DECISION

    @pytest.mark.asyncio
    async def test_send_decision_notification_no_decisions(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        decision_data = {"decisions": [], "overall_confidence": 0}
        results = await service.send_decision_notification("ETH Strategy", decision_data)

        sent_notification = mock_provider.send.call_args[0][0]
        assert "HOLD" in sent_notification.message

    @pytest.mark.asyncio
    async def test_send_trade_notification(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        results = await service.send_trade_notification(
            strategy_name="My Strat",
            symbol="ETH/USDT",
            action="buy",
            size_usd=1000.0,
            price=3500.0,
        )

        assert results[NotificationChannel.TELEGRAM] is True
        sent_notification = mock_provider.send.call_args[0][0]
        assert sent_notification.type == NotificationType.TRADE_EXECUTED

    @pytest.mark.asyncio
    async def test_send_risk_alert(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.DISCORD] = mock_provider

        results = await service.send_risk_alert(
            title="Drawdown",
            message="Max drawdown exceeded",
            details={"drawdown": "15%"},
        )

        assert results[NotificationChannel.DISCORD] is True
        sent_notification = mock_provider.send.call_args[0][0]
        assert sent_notification.priority == "high"
        assert sent_notification.type == NotificationType.RISK_ALERT

    @pytest.mark.asyncio
    async def test_send_strategy_status_notification(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        results = await service.send_strategy_status_notification(
            strategy_name="Alpha",
            old_status="running",
            new_status="error",
            error_message="Connection lost",
        )

        sent_notification = mock_provider.send.call_args[0][0]
        assert sent_notification.priority == "high"
        assert "error" in sent_notification.message.lower() or "Error" in sent_notification.message

    @pytest.mark.asyncio
    async def test_send_strategy_status_normal_priority(self):
        service = NotificationService()
        mock_provider = AsyncMock()
        mock_provider.is_configured.return_value = True
        mock_provider.send.return_value = True
        service.providers[NotificationChannel.TELEGRAM] = mock_provider

        results = await service.send_strategy_status_notification(
            strategy_name="Alpha",
            old_status="draft",
            new_status="running",
        )

        sent_notification = mock_provider.send.call_args[0][0]
        assert sent_notification.priority == "normal"
