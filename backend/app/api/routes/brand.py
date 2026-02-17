"""Brand API routes - exposes public brand configuration"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/brand", tags=["brand"])


class BrandResponse(BaseModel):
    """Public brand information for frontend consumption"""

    name: str
    short_name: str
    tagline: str
    description: str
    theme_preset: str

    model_config = {"from_attributes": True}


@router.get("", response_model=BrandResponse)
async def get_brand_info() -> BrandResponse:
    """Get public brand configuration"""
    settings = get_settings()
    return BrandResponse(
        name=settings.app_name,
        short_name=settings.app_name,
        tagline=settings.app_tagline,
        description=settings.app_description,
        theme_preset=settings.theme_preset,
    )
