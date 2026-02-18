"""Channel management routes"""

import uuid
from datetime import datetime, UTC
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field

from ...core.dependencies import CurrentUserDep, DbSessionDep
from ...db.repositories import UserRepository
from ...services.channel_service import ChannelService

router = APIRouter(prefix="/channels", tags=["Channels"])


# ==================== Request/Response Models ====================

class ChannelCreate(BaseModel):
    """Channel creation request"""
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=3, max_length=6, description="Unique channel code (3-6 chars)")
    commission_rate: float = Field(0.0, ge=0.0, le=1.0, description="Commission rate (0.0-1.0)")
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    admin_user_id: Optional[str] = Field(None, description="User ID to set as channel admin")


class ChannelUpdate(BaseModel):
    """Channel update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    commission_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    admin_user_id: Optional[str] = None


class ChannelStatusUpdate(BaseModel):
    """Channel status update request"""
    status: str = Field(..., description="Status: active, suspended, closed")


class ChannelResponse(BaseModel):
    """Channel response"""
    id: str
    name: str
    code: str
    commission_rate: float
    status: str
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    admin_user_id: Optional[str] = None
    total_users: int = 0
    total_revenue: float = 0.0
    total_commission: float = 0.0
    created_at: datetime
    updated_at: datetime


class ChannelWalletResponse(BaseModel):
    """Channel wallet response"""
    channel_id: str
    balance: float
    frozen_balance: float
    pending_commission: float
    total_commission: float
    total_withdrawn: float


class ChannelUserResponse(BaseModel):
    """Channel user response"""
    id: str
    email: str
    name: str
    created_at: datetime


class ChannelStatisticsResponse(BaseModel):
    """Channel statistics response"""
    total_users: int
    active_users: int
    total_revenue: float
    total_commission: float
    period_commission: float
    pending_commission: float
    available_balance: float
    frozen_balance: float


# ==================== Dependencies ====================

async def require_platform_admin(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Dependency that requires platform admin role"""
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or user.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required"
        )
    return user


async def require_channel_admin(
    db: DbSessionDep,
    user_id: CurrentUserDep,
):
    """Dependency that requires channel admin role"""
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if not user or user.role not in ("channel_admin", "platform_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Channel admin access required"
        )
    return user


PlatformAdminDep = Depends(require_platform_admin)
ChannelAdminDep = Depends(require_channel_admin)


# ==================== Platform Admin Routes ====================

@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    request: ChannelCreate,
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """
    Create a new channel (platform admin only).

    Creates a channel and its associated wallet.
    """
    service = ChannelService(db)

    # Check if code already exists
    existing = await service.get_channel_by_code(request.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Channel code '{request.code}' already exists"
        )

    # Parse admin user ID
    admin_user_id = None
    if request.admin_user_id:
        admin_user_id = uuid.UUID(request.admin_user_id)

    channel = await service.create_channel(
        name=request.name,
        code=request.code,
        commission_rate=request.commission_rate,
        contact_name=request.contact_name,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        admin_user_id=admin_user_id,
    )

    await db.commit()

    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        code=channel.code,
        commission_rate=channel.commission_rate,
        status=channel.status,
        contact_name=channel.contact_name,
        contact_email=channel.contact_email,
        contact_phone=channel.contact_phone,
        admin_user_id=str(channel.admin_user_id) if channel.admin_user_id else None,
        total_users=channel.total_users,
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.get("", response_model=List[ChannelResponse])
async def list_channels(
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    List all channels (platform admin only).
    """
    service = ChannelService(db)
    channels = await service.list_channels(status=status, limit=limit, offset=offset)

    return [
        ChannelResponse(
            id=str(c.id),
            name=c.name,
            code=c.code,
            commission_rate=c.commission_rate,
            status=c.status,
            contact_name=c.contact_name,
            contact_email=c.contact_email,
            contact_phone=c.contact_phone,
            admin_user_id=str(c.admin_user_id) if c.admin_user_id else None,
            total_users=c.total_users,
            total_revenue=c.total_revenue,
            total_commission=c.total_commission,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in channels
    ]


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: DbSessionDep,
    admin_user = ChannelAdminDep,
):
    """Get channel by ID."""
    service = ChannelService(db)
    channel = await service.get_channel(uuid.UUID(channel_id))

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        code=channel.code,
        commission_rate=channel.commission_rate,
        status=channel.status,
        contact_name=channel.contact_name,
        contact_email=channel.contact_email,
        contact_phone=channel.contact_phone,
        admin_user_id=str(channel.admin_user_id) if channel.admin_user_id else None,
        total_users=channel.total_users,
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: str,
    request: ChannelUpdate,
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """Update channel (platform admin only)."""
    service = ChannelService(db)

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.commission_rate is not None:
        update_data["commission_rate"] = request.commission_rate
    if request.contact_name is not None:
        update_data["contact_name"] = request.contact_name
    if request.contact_email is not None:
        update_data["contact_email"] = request.contact_email
    if request.contact_phone is not None:
        update_data["contact_phone"] = request.contact_phone

    channel = await service.update_channel(uuid.UUID(channel_id), **update_data)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    # Handle admin user update separately
    if request.admin_user_id is not None:
        admin_user_id = uuid.UUID(request.admin_user_id) if request.admin_user_id else None
        channel = await service.set_channel_admin(uuid.UUID(channel_id), admin_user_id)

    await db.commit()

    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        code=channel.code,
        commission_rate=channel.commission_rate,
        status=channel.status,
        contact_name=channel.contact_name,
        contact_email=channel.contact_email,
        contact_phone=channel.contact_phone,
        admin_user_id=str(channel.admin_user_id) if channel.admin_user_id else None,
        total_users=channel.total_users,
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.put("/{channel_id}/status", response_model=ChannelResponse)
async def update_channel_status(
    channel_id: str,
    request: ChannelStatusUpdate,
    db: DbSessionDep,
    admin_user = PlatformAdminDep,
):
    """Update channel status (platform admin only)."""
    service = ChannelService(db)

    if request.status not in ("active", "suspended", "closed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be: active, suspended, or closed"
        )

    channel = await service.update_channel_status(uuid.UUID(channel_id), request.status)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    await db.commit()

    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        code=channel.code,
        commission_rate=channel.commission_rate,
        status=channel.status,
        contact_name=channel.contact_name,
        contact_email=channel.contact_email,
        contact_phone=channel.contact_phone,
        admin_user_id=str(channel.admin_user_id) if channel.admin_user_id else None,
        total_users=channel.total_users,
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


# ==================== Channel Admin Routes ====================

@router.get("/me", response_model=ChannelResponse)
async def get_my_channel(
    db: DbSessionDep,
    user = ChannelAdminDep,
):
    """Get current user's channel (channel admin only)."""
    service = ChannelService(db)
    channel = await service.get_channel_by_admin(user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not an admin of any channel"
        )

    return ChannelResponse(
        id=str(channel.id),
        name=channel.name,
        code=channel.code,
        commission_rate=channel.commission_rate,
        status=channel.status,
        contact_name=channel.contact_name,
        contact_email=channel.contact_email,
        contact_phone=channel.contact_phone,
        admin_user_id=str(channel.admin_user_id) if channel.admin_user_id else None,
        total_users=channel.total_users,
        total_revenue=channel.total_revenue,
        total_commission=channel.total_commission,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.get("/me/users", response_model=List[ChannelUserResponse])
async def get_my_channel_users(
    db: DbSessionDep,
    user = ChannelAdminDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get users in current user's channel (channel admin only)."""
    service = ChannelService(db)
    channel = await service.get_channel_by_admin(user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not an admin of any channel"
        )

    users = await service.get_channel_users(channel.id, limit=limit, offset=offset)

    return [
        ChannelUserResponse(
            id=str(u.id),
            email=u.email,
            name=u.name,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/me/wallet", response_model=ChannelWalletResponse)
async def get_my_channel_wallet(
    db: DbSessionDep,
    user = ChannelAdminDep,
):
    """Get current channel's wallet (channel admin only)."""
    service = ChannelService(db)
    channel = await service.get_channel_by_admin(user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not an admin of any channel"
        )

    wallet = await service.get_channel_wallet(channel.id)

    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel wallet not found"
        )

    return ChannelWalletResponse(
        channel_id=str(channel.id),
        balance=wallet.balance,
        frozen_balance=wallet.frozen_balance,
        pending_commission=wallet.pending_commission,
        total_commission=wallet.total_commission,
        total_withdrawn=wallet.total_withdrawn,
    )


@router.get("/me/statistics", response_model=ChannelStatisticsResponse)
async def get_my_channel_statistics(
    db: DbSessionDep,
    user = ChannelAdminDep,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Get current channel's statistics (channel admin only)."""
    service = ChannelService(db)
    channel = await service.get_channel_by_admin(user.id)

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not an admin of any channel"
        )

    stats = await service.get_channel_statistics(
        channel.id,
        start_date=start_date,
        end_date=end_date,
    )

    return ChannelStatisticsResponse(**stats)
