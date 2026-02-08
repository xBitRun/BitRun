"""FastAPI dependencies for dependency injection"""

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .errors import ErrorCode, auth_error
from .security import CryptoService, TokenData, get_crypto_service, verify_token
from ..db.database import get_db
from ..services.redis_service import get_redis_service

logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False  # Don't auto-raise, let us handle it
)


async def check_token_blacklist(token_data: TokenData) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        token_data: Verified token data containing JTI

    Returns:
        True if token is blacklisted or check failed in production
        False if token is not blacklisted

    Raises:
        HTTPException: In production when Redis is unavailable (fail-secure)
    """
    if not token_data.jti:
        return False

    settings = get_settings()

    try:
        redis = await get_redis_service()
        return await redis.is_token_blacklisted(token_data.jti)
    except Exception as e:
        # Log the Redis failure
        logger.error(f"Redis unavailable for token blacklist check: {e}")

        # In production, fail securely - reject the request
        if settings.environment == "production":
            logger.warning(
                f"Rejecting request due to Redis unavailability in production "
                f"(token JTI: {token_data.jti[:8]}...)"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable. Please try again.",
                headers={"Retry-After": "5"},
            )

        # In development/staging, log warning but allow request
        logger.warning(
            f"Allowing request without blacklist check in {settings.environment} "
            f"(Redis unavailable)"
        )
        return False


async def get_current_user_id(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> str:
    """
    Dependency to get current authenticated user ID from JWT token.

    Checks if token is blacklisted (logged out).

    Raises:
        HTTPException 401: If token is missing, invalid, or blacklisted
        HTTPException 503: In production if Redis is unavailable
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(token, token_type="access")

        # Check if token is blacklisted
        if await check_token_blacklist(token_data):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token_data.sub
    except HTTPException:
        # Re-raise HTTPExceptions (including 503 from blacklist check)
        raise
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user_id(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> Optional[str]:
    """
    Dependency to optionally get current user ID.
    Returns None if not authenticated (doesn't raise).
    """
    if not token:
        return None

    try:
        token_data = verify_token(token, token_type="access")
        return token_data.sub
    except JWTError:
        return None


async def get_current_token_data(
    token: Annotated[Optional[str], Depends(oauth2_scheme)]
) -> TokenData:
    """
    Dependency to get full token data including JTI.

    Use this when you need access to the JTI for blacklisting.

    Raises:
        HTTPException 401: If token is missing or invalid
        HTTPException 503: In production if Redis is unavailable
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(token, token_type="access")

        # Check if token is blacklisted
        if await check_token_blacklist(token_data):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return token_data
    except HTTPException:
        # Re-raise HTTPExceptions (including 503 from blacklist check)
        raise
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
            identifier=f"auth:{client_ip}",
            max_requests=5,
            window_seconds=60
        )

        if not allowed:
            logger.warning(f"Rate limit exceeded for auth endpoint from IP: {client_ip}")
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
        logger.warning(f"Skipping rate limit check in {settings.environment} (Redis unavailable)")


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
