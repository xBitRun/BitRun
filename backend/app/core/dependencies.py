"""FastAPI dependencies for dependency injection"""

import logging
import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .errors import ErrorCode, auth_error
from .security import CryptoService, TokenData, get_crypto_service, verify_token
from ..db.database import get_db
from ..db.repositories import UserRepository
from ..db.models import UserDB
from ..services.redis_service import get_redis_service

logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # Don't auto-raise, let us handle it
)


async def _check_token_blacklist(token_data: TokenData) -> bool:
    """
    Check whether token JTI is blacklisted.

    Returns:
        True if token is blacklisted, False otherwise.

    Raises:
        HTTPException 503 in production if blacklist check is unavailable.
    """
    if not token_data.jti:
        return False

    try:
        redis = await get_redis_service()
        return await redis.is_token_blacklisted(token_data.jti)
    except Exception as e:
        settings = get_settings()
        logger.error(f"Redis unavailable for token blacklist check: {e}")
        if settings.environment == "production":
            raise auth_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
            )
        return False


async def get_current_user_id(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> str:
    """
    Dependency to get current authenticated user ID from JWT token.

    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(token, token_type="access")
        if await _check_token_blacklist(token_data):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data.sub
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user_id(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> Optional[str]:
    """
    Dependency to optionally get current user ID.
    Returns None if not authenticated (doesn't raise).
    """
    if not token:
        return None

    try:
        token_data = verify_token(token, token_type="access")
        if await _check_token_blacklist(token_data):
            return None
        return token_data.sub
    except JWTError:
        return None


async def get_current_token_data(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
) -> TokenData:
    """
    Dependency to get full token data including JTI.

    Raises:
        HTTPException 401: If token is missing or invalid
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(token, token_type="access")
        if await _check_token_blacklist(token_data):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== Rate Limiting ====================


async def rate_limit_auth(request: Request) -> None:
    """
    Rate limiter for authentication endpoints.

    Limits to 5 requests per minute per IP address to prevent
    brute force attacks on login/register endpoints.

    Raises:
        HTTPException 429: If rate limit exceeded
        HTTPException 503: In production if Redis is unavailable
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"

    try:
        redis = await get_redis_service()
        allowed, remaining = await redis.check_rate_limit(
            identifier=f"auth:{client_ip}", max_requests=5, window_seconds=60
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for auth endpoint from IP: {client_ip}"
            )
            raise auth_error(
                ErrorCode.AUTH_RATE_LIMITED,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis unavailable for rate limiting: {e}")
        # In production, fail securely
        if settings.environment == "production":
            raise auth_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
            )
        # In dev/staging, allow request without rate limiting
        logger.warning(
            f"Skipping rate limit check in {settings.environment} (Redis unavailable)"
        )


# Rate limit dependency for use with Depends()
RateLimitAuthDep = Annotated[None, Depends(rate_limit_auth)]


async def rate_limit_api(request: Request) -> None:
    """
    General rate limiter for API endpoints.

    Limits to 100 requests per minute per IP address.

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"

    try:
        redis = await get_redis_service()
        allowed, remaining = await redis.check_rate_limit(
            identifier=f"api:{client_ip}",
            max_requests=100,
            window_seconds=60,
        )

        if not allowed:
            logger.warning(f"API rate limit exceeded from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis unavailable for API rate limiting: {e}")
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again.",
                headers={"Retry-After": "5"},
            )


async def rate_limit_strategy(request: Request) -> None:
    """
    Rate limiter for strategy execution endpoints.

    Limits to 10 requests per minute per IP address to prevent
    excessive strategy triggering.

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"

    try:
        redis = await get_redis_service()
        allowed, remaining = await redis.check_rate_limit(
            identifier=f"strategy:{client_ip}",
            max_requests=10,
            window_seconds=60,
        )

        if not allowed:
            logger.warning(f"Strategy rate limit exceeded from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many strategy execution requests. Please try again later.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis unavailable for strategy rate limiting: {e}")
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again.",
                headers={"Retry-After": "5"},
            )


async def rate_limit_account(request: Request) -> None:
    """
    Rate limiter for account operation endpoints.

    Limits to 20 requests per minute per IP address.

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"

    try:
        redis = await get_redis_service()
        allowed, remaining = await redis.check_rate_limit(
            identifier=f"account:{client_ip}",
            max_requests=20,
            window_seconds=60,
        )

        if not allowed:
            logger.warning(f"Account rate limit exceeded from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many account operation requests. Please try again later.",
                headers={"Retry-After": "60"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis unavailable for account rate limiting: {e}")
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again.",
                headers={"Retry-After": "5"},
            )


RateLimitApiDep = Annotated[None, Depends(rate_limit_api)]
RateLimitStrategyDep = Annotated[None, Depends(rate_limit_strategy)]
RateLimitAccountDep = Annotated[None, Depends(rate_limit_account)]


# Type aliases for cleaner dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]
CryptoDep = Annotated[CryptoService, Depends(get_crypto_service)]
CurrentUserDep = Annotated[str, Depends(get_current_user_id)]
OptionalUserDep = Annotated[Optional[str], Depends(get_optional_user_id)]
CurrentTokenDep = Annotated[TokenData, Depends(get_current_token_data)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]


# ==================== Admin Role Dependencies ====================


async def require_platform_admin(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Dependency that requires platform_admin role.

    Raises:
        HTTPException 403: If user is not a platform admin
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required",
        )
    return user


async def require_channel_admin(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Dependency that requires channel_admin or platform_admin role.

    Raises:
        HTTPException 403: If user is not a channel or platform admin
    """
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or user.role not in ("channel_admin", "platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Channel admin access required",
        )
    return user


# Type aliases for admin dependencies
PlatformAdminDep = Annotated[UserDB, Depends(require_platform_admin)]
ChannelAdminDep = Annotated[UserDB, Depends(require_channel_admin)]
