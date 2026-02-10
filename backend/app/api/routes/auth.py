"""Authentication routes with database integration"""

import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field

from ...core.config import get_settings
from ...core.dependencies import CurrentTokenDep, CurrentUserDep, DbSessionDep, RateLimitAuthDep
from ...core.errors import ErrorCode, auth_error
from ...core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from ...db.repositories.user import UserRepository
from ...services.redis_service import get_redis_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== Request/Response Models ====================

class UserCreate(BaseModel):
    """User registration request"""
    email: EmailStr
    # bcrypt has a 72-byte limit on passwords; enforce max_length to avoid silent truncation
    password: str = Field(..., min_length=8, max_length=72)
    name: str = Field(..., min_length=1, max_length=100)


class UserResponse(BaseModel):
    """User response (without sensitive data)"""
    id: str
    email: str
    name: str
    is_active: bool


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request with optional refresh token"""
    refresh_token: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    """Profile update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)


# ==================== Routes ====================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: DbSessionDep, _: RateLimitAuthDep):
    """
    Register a new user.

    Rate limited: 5 requests per minute per IP.

    - Validates email uniqueness
    - Hashes password with bcrypt
    - Returns user info (without password)
    """
    repo = UserRepository(db)

    # Check if email exists
    existing = await repo.get_by_email(user_data.email)
    if existing:
        raise auth_error(
            ErrorCode.AUTH_EMAIL_EXISTS,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Create user
    user = await repo.create(
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
    )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSessionDep,
    _: RateLimitAuthDep
):
    """
    Login with email and password.

    Rate limited: 5 requests per minute per IP.
    Account locked after 5 failed attempts within 15 minutes.
    Uses OAuth2 password flow (username field = email).
    Returns access and refresh tokens.
    """
    settings = get_settings()
    repo = UserRepository(db)
    email = form_data.username

    # Obtain Redis service once and reuse throughout the handler
    redis = None
    try:
        redis = await get_redis_service()
    except Exception:
        if settings.environment == "production":
            raise auth_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
            )

    # Check if account is locked (single pipeline: GET + TTL)
    if redis:
        try:
            is_locked, remaining_time = await redis.check_account_lockout(email)
            if is_locked:
                remaining_minutes = remaining_time // 60 + 1
                raise auth_error(
                    ErrorCode.AUTH_ACCOUNT_LOCKED,
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(remaining_time)},
                    remaining_minutes=remaining_minutes,
                )
        except HTTPException:
            raise
        except Exception:
            pass  # Non-critical in dev, already handled above for prod

    # Authenticate user
    user = await repo.authenticate(email, form_data.password)
    if not user:
        # Track failed login attempt
        if redis:
            try:
                failure_count = await redis.track_login_failure(email)
                remaining_attempts = max(0, 5 - failure_count)

                if remaining_attempts == 0:
                    raise auth_error(
                        ErrorCode.AUTH_ACCOUNT_LOCKED,
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        headers={"Retry-After": "900"},
                        remaining_minutes=15,
                    )

                raise auth_error(
                    ErrorCode.AUTH_INVALID_CREDENTIALS,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    headers={"WWW-Authenticate": "Bearer"},
                    remaining_attempts=remaining_attempts,
                )
            except HTTPException:
                raise
            except Exception:
                pass  # Fall through to generic error

        raise auth_error(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Clear login failures on successful login
    if redis:
        try:
            await redis.clear_login_failures(email)
        except Exception:
            pass  # Non-critical, continue with login

    # Create tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token.

    Implements token rotation: the old refresh token is blacklisted
    and a new token pair is issued.
    """
    settings = get_settings()

    # Verify refresh token
    try:
        token_data = verify_token(request.refresh_token, token_type="refresh")
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if refresh token is blacklisted
    try:
        redis = await get_redis_service()

        if token_data.jti and await redis.is_token_blacklisted(token_data.jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Token rotation: blacklist the old refresh token
        if token_data.jti:
            now = datetime.now(timezone.utc)
            remaining_seconds = int((token_data.exp - now).total_seconds())
            if remaining_seconds > 0:
                await redis.blacklist_token(token_data.jti, expires_in=remaining_seconds + 60)

    except HTTPException:
        raise
    except Exception as e:
        # In production, fail securely if Redis is unavailable
        if settings.environment == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
                headers={"Retry-After": "5"},
            )
        # In dev/staging, log but continue
        import logging
        logging.getLogger(__name__).warning(f"Redis unavailable for refresh token check: {e}")

    # Create new tokens
    access_token = create_access_token(token_data.sub)
    new_refresh_token = create_refresh_token(token_data.sub)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    token_data: CurrentTokenDep,
    body: LogoutRequest = Body(default=LogoutRequest()),
):
    """
    Logout user by blacklisting tokens.

    The access token's JTI is added to a Redis blacklist with
    TTL matching the token's remaining lifetime.

    If a refresh_token is provided in the request body, it will also
    be blacklisted to ensure complete logout across all sessions.
    """
    try:
        redis = await get_redis_service()
        now = datetime.now(timezone.utc)

        # Blacklist access token
        access_remaining = int((token_data.exp - now).total_seconds())
        if access_remaining > 0 and token_data.jti:
            await redis.blacklist_token(token_data.jti, expires_in=access_remaining + 60)

        # Blacklist refresh token if provided
        if body.refresh_token:
            try:
                refresh_data = verify_token(body.refresh_token, token_type="refresh")
                if refresh_data.jti:
                    refresh_remaining = int((refresh_data.exp - now).total_seconds())
                    if refresh_remaining > 0:
                        await redis.blacklist_token(refresh_data.jti, expires_in=refresh_remaining + 60)
            except JWTError:
                # Invalid refresh token - ignore, still logout successfully
                pass

        # Delete user session
        await redis.delete_user_session(token_data.sub)

        return {"message": "Logged out successfully"}

    except Exception:
        # Even if Redis fails, logout should succeed client-side
        return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Get current authenticated user.

    Requires valid JWT access token in Authorization header.
    """
    repo = UserRepository(db)

    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Update current user's profile.

    Only allows updating non-sensitive fields like name.
    """
    repo = UserRepository(db)

    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Build update kwargs from non-None fields
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name

    if update_data:
        user = await repo.update(uuid.UUID(user_id), **update_data)
        await db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
    )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """
    Change current user's password.

    Requires current password for verification.
    """
    repo = UserRepository(db)

    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Verify current password (async to avoid blocking event loop)
    from ...core.security import verify_password_async
    if not await verify_password_async(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Check new password is different
    if await verify_password_async(request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    # Change password
    success = await repo.change_password(uuid.UUID(user_id), request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

    await db.commit()

    return {"message": "Password changed successfully"}
