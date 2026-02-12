"""System routes — server information for operational use."""

import logging

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from ...core.dependencies import CurrentUserDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["System"])


class OutboundIPResponse(BaseModel):
    """Server outbound IP address response."""
    ip: str | None = None
    source: str = "unknown"
    cached: bool = False


# Module-level cache (refreshed each server restart; lightweight)
_cached_ip: str | None = None
_cached_source: str = "unknown"

# External services that return plain-text IP — tried in order
_IP_SERVICES = [
    ("https://api.ipify.org", "ipify"),
    ("https://ifconfig.me/ip", "ifconfig.me"),
    ("https://icanhazip.com", "icanhazip"),
    ("https://checkip.amazonaws.com", "aws"),
]


async def _detect_outbound_ip() -> tuple[str | None, str]:
    """
    Detect the server's public outbound IP by querying external services.
    Returns (ip, source_name).
    """
    global _cached_ip, _cached_source  # noqa: PLW0603

    if _cached_ip:
        return _cached_ip, _cached_source

    async with httpx.AsyncClient(timeout=5.0) as client:
        for url, source in _IP_SERVICES:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    ip = resp.text.strip()
                    if ip and len(ip) < 46:  # sanity: max IPv6 length
                        _cached_ip = ip
                        _cached_source = source
                        logger.info("Detected outbound IP: %s (via %s)", ip, source)
                        return ip, source
            except Exception:
                continue

    logger.warning("Could not detect outbound IP from any external service")
    return None, "unknown"


@router.get("/outbound-ip", response_model=OutboundIPResponse)
async def get_outbound_ip(user: CurrentUserDep):
    """
    Return the server's public outbound IP address.

    Useful for users who need to configure IP whitelisting on exchanges.
    The result is cached for the lifetime of the server process.
    """
    ip, source = await _detect_outbound_ip()
    return OutboundIPResponse(
        ip=ip,
        source=source,
        cached=_cached_ip is not None,
    )
