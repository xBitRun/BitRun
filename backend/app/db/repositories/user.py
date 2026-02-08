"""User repository for database operations"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import UserDB
from ...core.security import hash_password, verify_password


class UserRepository:
    """Repository for User CRUD operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        email: str,
        password: str,
        name: str
    ) -> UserDB:
        """
        Create a new user.
        
        Args:
            email: User email (unique)
            password: Plain text password (will be hashed)
            name: User display name
            
        Returns:
            Created UserDB instance
        """
        user = UserDB(
            email=email.lower(),
            password_hash=hash_password(password),
            name=name,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserDB]:
        """Get user by ID"""
        result = await self.session.execute(
            select(UserDB).where(UserDB.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[UserDB]:
        """Get user by email"""
        result = await self.session.execute(
            select(UserDB).where(UserDB.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def authenticate(self, email: str, password: str) -> Optional[UserDB]:
        """
        Authenticate user with email and password.
        
        Returns:
            UserDB if credentials are valid, None otherwise
        """
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        return user
    
    async def update(
        self,
        user_id: uuid.UUID,
        **kwargs
    ) -> Optional[UserDB]:
        """
        Update user fields.
        
        Supported fields: name, is_active
        """
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        allowed_fields = {"name", "is_active"}
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(user, key, value)
        
        await self.session.flush()
        await self.session.refresh(user)
        return user
    
    async def change_password(
        self,
        user_id: uuid.UUID,
        new_password: str
    ) -> bool:
        """Change user password"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.password_hash = hash_password(new_password)
        await self.session.flush()
        return True
    
    async def delete(self, user_id: uuid.UUID) -> bool:
        """Delete user (and cascade to related data)"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.session.delete(user)
        await self.session.flush()
        return True
