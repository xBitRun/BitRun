#!/usr/bin/env python3
"""Development server runner"""

import uvicorn

from app.core.config import get_settings


def main():
    settings = get_settings()
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_debug,
        log_level="debug" if settings.is_debug else "info",
    )


if __name__ == "__main__":
    main()
