"""Authentication routes with database integration"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field

from ...core.config import get_settings
from ...core.dependencies import (
    CurrentTokenDep,
    CurrentUserDep,
    DbSessionDep,
    RateLimitAuthDep,
)
from ...core.errors import ErrorCode, auth_error
from ...core.security import (
    TokenData,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from ...db.repositories.user import UserRepository
from ...db.repositories.wallet import WalletRepository
from ...services.invite_service import InviteService
from ...services.redis_service import get_redis_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================


class UserCreate(BaseModel):
    """User registration request"""

    email: EmailStr
    # bcrypt has a 72-byte limit on passwords; enforce max_length to avoid silent truncation
    password: str = Field(..., min_length=8, max_length=72)
    name: str = Field(..., min_length=1, max_length=100)
    # Invitation code is required for registration
    invite_code: str = Field(
        ..., min_length=6, max_length=20, description="Invitation code (required)"
    )


class UserResponse(BaseModel):
    """User response (without sensitive data)"""

    id: str
    email: str
    name: str
    is_active: bool
    role: str = "user"
    channel_id: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: Optional[UserResponse] = None  # Inline user info to avoid extra /me call


class RefreshRequest(BaseModel):
    """Token refresh request"""

    refresh_token: str


class ProfileUpdateRequest(BaseModel):
    """Profile update request"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)


class ChangePasswordRequest(BaseModel):
    """Change password request"""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)


# ==================== Routes ====================


def _token_ttl_seconds(token_data: TokenData) -> int:
    """Calculate remaining token lifetime in seconds for blacklist TTL."""
    ttl = int((token_data.exp - datetime.now(timezone.utc)).total_seconds())
    return max(1, ttl)


async def _is_token_blacklisted(token_data: TokenData) -> bool:
    """Check whether the given token is blacklisted."""
    if not token_data.jti:
        return False
    redis = await get_redis_service()
    return await redis.is_token_blacklisted(token_data.jti)


async def _blacklist_token(token_data: TokenData) -> None:
    """Blacklist a token by JTI until it naturally expires."""
    if not token_data.jti:
        return
    redis = await get_redis_service()
    await redis.blacklist_token(
        token_data.jti, expires_in=_token_ttl_seconds(token_data)
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate, db: DbSessionDep, _rate_limit: RateLimitAuthDep = None
):
    """
    Register a new user.

    - Requires valid invitation code
    - Validates email uniqueness
    - Hashes password with bcrypt
    - Creates user wallet
    - Returns user info (without password)
    """
    invite_service = InviteService(db)

    # Create user with invite code
    user, error = await invite_service.create_user_with_invite(
        email=user_data.email,
        password=user_data.password,
        name=user_data.name,
        invite_code=user_data.invite_code,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error,
        )

    # Create wallet for user
    wallet_repo = WalletRepository(db)
    await wallet_repo.create(user.id)

    await db.commit()

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        role=user.role,
        channel_id=str(user.channel_id) if user.channel_id else None,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSessionDep,
    _rate_limit: RateLimitAuthDep = None,
):
    """
    Login with email and password.

    Uses OAuth2 password flow (username field = email).
    Returns access and refresh tokens.
    """
    settings = get_settings()
    repo = UserRepository(db)

    # Authenticate user
    user = await repo.authenticate(form_data.username, form_data.password)
    if not user:
        raise auth_error(
            ErrorCode.AUTH_INVALID_CREDENTIALS,
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            role=user.role,
            channel_id=str(user.channel_id) if user.channel_id else None,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, _rate_limit: RateLimitAuthDep = None):
    """
    Refresh access token using refresh token.

    Returns a new token pair.
    """
    # Verify refresh token
    try:
        token_data = verify_token(request.refresh_token, token_type="refresh")
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        if await _is_token_blacklisted(token_data):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redis unavailable for refresh-token blacklist check: {e}")
        if settings.environment == "production":
            raise auth_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
            )

    # Create new tokens
    access_token = create_access_token(token_data.sub)
    new_refresh_token = create_refresh_token(token_data.sub)

    # Rotate refresh tokens: blacklist the old refresh token so it cannot be reused.
    try:
        await _blacklist_token(token_data)
    except Exception as e:
        logger.error(f"Failed to blacklist old refresh token: {e}")
        if settings.environment == "production":
            raise auth_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
            )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(
    token_data: CurrentTokenDep,
):
    """
    Logout user.

    Access token JTI is blacklisted until expiry.
    Client should discard local tokens after this call.
    """
    settings = get_settings()
    try:
        await _blacklist_token(token_data)
    except Exception as e:
        logger.error(f"Failed to blacklist access token on logout: {e}")
        if settings.environment == "production":
            raise auth_error(
                ErrorCode.SERVICE_UNAVAILABLE,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"},
            )
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
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        role=user.role,
        channel_id=str(user.channel_id) if user.channel_id else None,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
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
        role=user.role,
        channel_id=str(user.channel_id) if user.channel_id else None,
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
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    # Verify current password (async to avoid blocking event loop)
    from ...core.security import verify_password_async

    if not await verify_password_async(request.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Check new password is different
    if await verify_password_async(request.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # Change password
    success = await repo.change_password(uuid.UUID(user_id), request.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )

    await db.commit()

    return {"message": "Password changed successfully"}
