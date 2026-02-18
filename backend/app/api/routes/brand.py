"""Brand API routes - exposes public brand configuration"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/brand", tags=["brand"])


class BrandResponse(BaseModel):
    """Public brand information for frontend consumption"""

    name: str
    tagline: str
    description: str

    model_config = {"from_attributes": True}


@router.get("", response_model=BrandResponse)
async def get_brand_info() -> BrandResponse:
    """Get public brand configuration (identity only, UI branding handled by frontend)"""
    settings = get_settings()
    return BrandResponse(
        name=settings.brand_name,
        tagline=settings.brand_tagline,
        description=settings.brand_description,
    )
