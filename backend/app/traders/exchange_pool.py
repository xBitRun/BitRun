"""
Exchange connection pool.

Caches initialized CCXT exchange instances to avoid repeated load_markets()
calls, which is the single largest bottleneck (~1-3s per call).

Instances are keyed by (exchange_id, credentials_hash, testnet) and are
automatically evicted after MAX_IDLE_SECONDS of inactivity.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional

import ccxt.async_support as ccxt

from .base import TradeError

logger = logging.getLogger(__name__)

# How long an idle exchange instance is kept alive before cleanup (seconds)
MAX_IDLE_SECONDS = 300  # 5 minutes


def _make_pool_key(exchange_id: str, credentials: dict[str, str], testnet: bool) -> str:
    """Build a deterministic cache key from exchange config.

    Credentials are hashed so that the actual secrets are never stored as
    dict keys in plain text.
    """
    cred_str = json.dumps(credentials, sort_keys=True)
    cred_hash = hashlib.sha256(cred_str.encode()).hexdigest()[:16]
    return f"{exchange_id}:{cred_hash}:{'test' if testnet else 'live'}"


class _PoolEntry:
    """Wrapper that tracks when an exchange instance was last used."""

    __slots__ = ("exchange", "last_used", "lock")

    def __init__(self, exchange: ccxt.Exchange) -> None:
        self.exchange = exchange
        self.last_used = time.monotonic()
        self.lock = asyncio.Lock()

    def touch(self) -> None:
        self.last_used = time.monotonic()

    @property
    def idle_seconds(self) -> float:
        return time.monotonic() - self.last_used


class ExchangePool:
    """
    Process-level pool of initialised CCXT exchange instances.

    Usage::

        exchange = await ExchangePool.acquire(exchange_id, cfg, credentials, testnet)
        try:
            balance = await exchange.fetch_balance()
        finally:
            ExchangePool.release(exchange_id, credentials, testnet)

    ``acquire`` returns an exchange that already has markets loaded.
    ``release`` marks the instance as idle (does **not** close it).
    Idle instances are reaped by a background task.
    """

    MAX_POOL_SIZE = 50  # Maximum number of cached exchange instances

    _entries: dict[str, _PoolEntry] = {}
    _global_lock = asyncio.Lock()
    _cleanup_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    async def acquire(
        cls,
        exchange_id: str,
        ccxt_config: dict[str, Any],
        credentials: dict[str, str],
        testnet: bool,
    ) -> ccxt.Exchange:
        """Get or create an initialised exchange instance.

        If an idle instance exists for the same config, it is reused.
        Otherwise a new one is created and ``load_markets()`` is called.
        """
        key = _make_pool_key(exchange_id, credentials, testnet)

        # Fast path – entry already exists
        entry = cls._entries.get(key)
        if entry is not None:
            async with entry.lock:
                entry.touch()
                logger.debug(f"ExchangePool hit for {exchange_id} (key={key[:24]}…)")
                return entry.exchange

        # Slow path – create under global lock to avoid duplicate creation
        async with cls._global_lock:
            # Double-check after acquiring global lock
            entry = cls._entries.get(key)
            if entry is not None:
                entry.touch()
                return entry.exchange

            # Evict oldest idle entry if pool is at capacity
            if len(cls._entries) >= cls.MAX_POOL_SIZE:
                oldest_key = min(
                    cls._entries, key=lambda k: cls._entries[k].last_used
                )
                evicted = cls._entries.pop(oldest_key, None)
                if evicted:
                    try:
                        await evicted.exchange.close()
                    except Exception:
                        pass
                    logger.info(
                        f"ExchangePool evicted LRU entry {oldest_key[:24]}… "
                        f"to make room (max={cls.MAX_POOL_SIZE})"
                    )

            exchange = await cls._create_exchange(exchange_id, ccxt_config, testnet)
            cls._entries[key] = _PoolEntry(exchange)
            logger.info(
                f"ExchangePool new instance for {exchange_id} "
                f"(key={key[:24]}…, pool_size={len(cls._entries)})"
            )

            # Ensure the cleanup task is running
            cls._ensure_cleanup_task()

            return exchange

    @classmethod
    def release(
        cls,
        exchange_id: str,
        credentials: dict[str, str],
        testnet: bool,
    ) -> None:
        """Mark an instance as idle (touch timestamp).

        This is a no-op if the key doesn't exist.
        """
        key = _make_pool_key(exchange_id, credentials, testnet)
        entry = cls._entries.get(key)
        if entry is not None:
            entry.touch()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    async def close_all(cls) -> None:
        """Close every pooled exchange and cancel the cleanup task."""
        if cls._cleanup_task and not cls._cleanup_task.done():
            cls._cleanup_task.cancel()
            cls._cleanup_task = None

        for key, entry in list(cls._entries.items()):
            try:
                await entry.exchange.close()
            except Exception:
                logger.debug(f"Error closing pooled exchange {key[:24]}…")
        cls._entries.clear()
        logger.info("ExchangePool closed all instances")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @classmethod
    async def _create_exchange(
        cls,
        exchange_id: str,
        ccxt_config: dict[str, Any],
        testnet: bool,
    ) -> ccxt.Exchange:
        """Instantiate, configure and load markets for a new exchange."""
        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise TradeError(f"Unsupported CCXT exchange: {exchange_id}")

        exchange = exchange_class(ccxt_config)

        if testnet:
            exchange.set_sandbox_mode(True)

        await exchange.load_markets()
        return exchange

    @classmethod
    def _ensure_cleanup_task(cls) -> None:
        """Start the background cleanup coroutine if not already running."""
        if cls._cleanup_task is None or cls._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                cls._cleanup_task = loop.create_task(cls._cleanup_loop())
            except RuntimeError:
                pass  # No running event loop – skip cleanup

    @classmethod
    async def _cleanup_loop(cls) -> None:
        """Periodically close exchange instances that have been idle too long."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            now = time.monotonic()
            to_remove: list[str] = []

            for key, entry in cls._entries.items():
                if (now - entry.last_used) > MAX_IDLE_SECONDS:
                    to_remove.append(key)

            for key in to_remove:
                entry = cls._entries.pop(key, None)
                if entry:
                    try:
                        await entry.exchange.close()
                        logger.info(
                            f"ExchangePool evicted idle instance {key[:24]}… "
                            f"(idle {entry.idle_seconds:.0f}s)"
                        )
                    except Exception:
                        logger.debug(f"Error closing evicted exchange {key[:24]}…")

            # Keep running even if pool is empty – new entries may arrive.
            # The task is lightweight (sleeps 60s) so no performance concern.
