"""Security hardening tests for auth/dependency token handling."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.routes import auth as auth_routes
from app.api.routes.auth import RefreshRequest
from app.core import dependencies
from app.core.security import TokenData


def _make_token_data(
    token_type: str = "access", jti: str | None = "test-jti"
) -> TokenData:
    now = datetime.now(timezone.utc)
    return TokenData(
        sub="user-123",
        exp=now + timedelta(minutes=30),
        iat=now,
        type=token_type,
        jti=jti,
    )


@pytest.mark.asyncio
async def test_oauth2_token_url_uses_versioned_path():
    """OpenAPI token URL should point to /api/v1 auth endpoint."""
    assert (
        dependencies.oauth2_scheme.model.flows.password.tokenUrl == "/api/v1/auth/login"
    )


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_blacklisted_token(monkeypatch):
    """Protected HTTP dependencies should reject revoked access tokens."""
    token_data = _make_token_data(token_type="access", jti="revoked-jti")
    mock_redis = AsyncMock()
    mock_redis.is_token_blacklisted = AsyncMock(return_value=True)

    monkeypatch.setattr(
        dependencies, "verify_token", lambda *_args, **_kwargs: token_data
    )

    async def _mock_get_redis_service():
        return mock_redis

    monkeypatch.setattr(dependencies, "get_redis_service", _mock_get_redis_service)

    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user_id("access-token")

    assert exc.value.status_code == 401
    assert "revoked" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_get_optional_user_id_returns_none_for_blacklisted_token(monkeypatch):
    """Optional auth dependency should return anonymous when token is revoked."""
    token_data = _make_token_data(token_type="access", jti="revoked-jti")
    mock_redis = AsyncMock()
    mock_redis.is_token_blacklisted = AsyncMock(return_value=True)

    monkeypatch.setattr(
        dependencies, "verify_token", lambda *_args, **_kwargs: token_data
    )

    async def _mock_get_redis_service():
        return mock_redis

    monkeypatch.setattr(dependencies, "get_redis_service", _mock_get_redis_service)

    result = await dependencies.get_optional_user_id("access-token")
    assert result is None


@pytest.mark.asyncio
async def test_logout_blacklists_current_access_token(monkeypatch):
    """Logout should revoke the current access token JTI."""
    token_data = _make_token_data(token_type="access", jti="logout-jti")
    mock_redis = AsyncMock()
    mock_redis.blacklist_token = AsyncMock(return_value=True)

    async def _mock_get_redis_service():
        return mock_redis

    monkeypatch.setattr(auth_routes, "get_redis_service", _mock_get_redis_service)
    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: SimpleNamespace(
            environment="development", jwt_access_token_expire_minutes=60
        ),
    )

    result = await auth_routes.logout(token_data)

    assert result["message"] == "Logged out successfully"
    mock_redis.blacklist_token.assert_awaited_once()
    assert mock_redis.blacklist_token.await_args.args[0] == "logout-jti"
    assert mock_redis.blacklist_token.await_args.kwargs["expires_in"] > 0


@pytest.mark.asyncio
async def test_refresh_rejects_blacklisted_refresh_token(monkeypatch):
    """Refresh endpoint should reject revoked refresh tokens."""
    token_data = _make_token_data(token_type="refresh", jti="old-refresh-jti")
    mock_redis = AsyncMock()
    mock_redis.is_token_blacklisted = AsyncMock(return_value=True)

    monkeypatch.setattr(
        auth_routes, "verify_token", lambda *_args, **_kwargs: token_data
    )

    async def _mock_get_redis_service():
        return mock_redis

    monkeypatch.setattr(auth_routes, "get_redis_service", _mock_get_redis_service)
    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: SimpleNamespace(
            environment="development", jwt_access_token_expire_minutes=60
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await auth_routes.refresh_token(RefreshRequest(refresh_token="refresh-token"))

    assert exc.value.status_code == 401
    assert "revoked" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_refresh_rotates_and_blacklists_old_refresh_token(monkeypatch):
    """Successful refresh should issue a new pair and revoke old refresh token."""
    token_data = _make_token_data(token_type="refresh", jti="old-refresh-jti")
    mock_redis = AsyncMock()
    mock_redis.is_token_blacklisted = AsyncMock(return_value=False)
    mock_redis.blacklist_token = AsyncMock(return_value=True)

    monkeypatch.setattr(
        auth_routes, "verify_token", lambda *_args, **_kwargs: token_data
    )
    monkeypatch.setattr(auth_routes, "create_access_token", lambda _sub: "new-access")
    monkeypatch.setattr(auth_routes, "create_refresh_token", lambda _sub: "new-refresh")

    async def _mock_get_redis_service():
        return mock_redis

    monkeypatch.setattr(auth_routes, "get_redis_service", _mock_get_redis_service)
    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: SimpleNamespace(
            environment="development", jwt_access_token_expire_minutes=60
        ),
    )

    response = await auth_routes.refresh_token(
        RefreshRequest(refresh_token="refresh-token")
    )

    assert response.access_token == "new-access"
    assert response.refresh_token == "new-refresh"
    mock_redis.blacklist_token.assert_awaited_once()
    assert mock_redis.blacklist_token.await_args.args[0] == "old-refresh-jti"


@pytest.mark.asyncio
async def test_refresh_token_cannot_be_reused_after_rotation(monkeypatch):
    """Old refresh token should be rejected on second use (replay attempt)."""
    token_data = _make_token_data(token_type="refresh", jti="replay-refresh-jti")
    blacklisted_jtis: set[str] = set()

    class _FakeRedis:
        async def is_token_blacklisted(self, jti: str) -> bool:
            return jti in blacklisted_jtis

        async def blacklist_token(self, jti: str, expires_in: int = 3600) -> bool:
            blacklisted_jtis.add(jti)
            return True

    fake_redis = _FakeRedis()

    monkeypatch.setattr(
        auth_routes, "verify_token", lambda *_args, **_kwargs: token_data
    )
    monkeypatch.setattr(auth_routes, "create_access_token", lambda _sub: "new-access")
    monkeypatch.setattr(auth_routes, "create_refresh_token", lambda _sub: "new-refresh")

    async def _mock_get_redis_service():
        return fake_redis

    monkeypatch.setattr(auth_routes, "get_redis_service", _mock_get_redis_service)
    monkeypatch.setattr(
        auth_routes,
        "get_settings",
        lambda: SimpleNamespace(
            environment="development", jwt_access_token_expire_minutes=60
        ),
    )

    first = await auth_routes.refresh_token(
        RefreshRequest(refresh_token="refresh-token")
    )
    assert first.access_token == "new-access"
    assert first.refresh_token == "new-refresh"

    with pytest.raises(HTTPException) as exc:
        await auth_routes.refresh_token(RefreshRequest(refresh_token="refresh-token"))

    assert exc.value.status_code == 401
    assert "revoked" in str(exc.value.detail).lower()
