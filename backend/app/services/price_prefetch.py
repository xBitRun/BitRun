"""
Price Prefetch Service - Background price preloading.

Provides:
- Background service to prefetch prices for active symbols
- Redis leader election for single-instance execution
- Symbol registration from running agents
- Integration with SharedPriceCache

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    PricePrefetchService                  │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
    │  │   Leader    │  │   Symbol    │  │   Prefetch  │     │
    │  │  Election   │  │  Registry   │  │    Loop     │     │
    │  └─────────────┘  └─────────────┘  └─────────────┘     │
    │         │               │               │               │
    │         └───────────────┴───────────────┘               │
    │                         │                               │
    │                         ▼                               │
    │              ┌─────────────────────┐                    │
    │              │  SharedPriceCache   │                    │
    │              └─────────────────────┘                    │
    └─────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

import ccxt.async_support as ccxt

from ..core.config import get_ccxt_proxy_config
from .shared_price_cache import SharedPriceCache, get_shared_price_cache

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

PREFETCH_INTERVAL = 3.0  # Prefetch every 3 seconds
LEADER_TTL = 30  # Leader lock TTL in seconds
LEADER_RENEW_INTERVAL = 10  # Renew leader lock every 10 seconds
STREAM_TIMEOUT_RATIO = 0.8  # watch_tickers timeout = interval * ratio
MIN_PUBLISH_CHANGE_PCT = 0.0001  # 0.01%


@dataclass
class SymbolSubscription:
    """Tracks subscription for a symbol."""

    symbol: str
    exchange: str
    subscriber_count: int = 1
    last_fetch: Optional[float] = None


class PricePrefetchService:
    """
    Background service that prefetches prices for active symbols.

    Features:
    - Runs as a singleton background task
    - Redis leader election ensures only one instance runs
    - Symbols are registered by running agents
    - Prefetches at configurable intervals
    - Integrates with SharedPriceCache for cross-Agent sharing

    Usage:
        service = PricePrefetchService()
        await service.start()

        # Register symbols from agents
        await service.register_symbol("hyperliquid", "BTC", agent_id="agent-1")
        await service.register_symbol("hyperliquid", "ETH", agent_id="agent-2")

        # Unregister when agent stops
        await service.unregister_symbol("hyperliquid", "BTC", agent_id="agent-1")

        # Stop service
        await service.stop()
    """

    # Redis key for leader election
    LEADER_KEY = "price_prefetch:leader"

    def __init__(
        self,
        prefetch_interval: float = PREFETCH_INTERVAL,
        price_cache: Optional[SharedPriceCache] = None,
    ):
        """
        Initialize the prefetch service.

        Args:
            prefetch_interval: Interval between prefetch cycles in seconds
            price_cache: SharedPriceCache instance (default: singleton)
        """
        self._prefetch_interval = prefetch_interval
        self._price_cache = price_cache

        # Symbol registry: f"{exchange}:{symbol}" -> SymbolSubscription
        self._subscriptions: Dict[str, SymbolSubscription] = {}

        # Agent -> Set of subscribed symbols (for cleanup)
        self._agent_symbols: Dict[str, Set[str]] = {}

        # Running state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._leader_task: Optional[asyncio.Task] = None
        self._is_leader = False

        # Redis connection
        self._redis = None

        # CCXT exchange instances per exchange
        self._exchanges: Dict[str, ccxt.Exchange] = {}

        # Metrics
        self._prefetch_count = 0
        self._prefetch_errors = 0
        self._stream_hits = 0
        self._stream_fallbacks = 0
        self._publish_skips_no_subscribers = 0
        self._publish_skips_small_change = 0

        # Last published price per symbol for suppressing tiny oscillations.
        self._last_published_prices: Dict[str, float] = {}

    async def _get_redis(self):
        """Get Redis connection lazily."""
        if self._redis is None:
            try:
                from .redis_service import get_redis_service

                self._redis = await get_redis_service()
            except Exception as e:
                logger.warning(f"Redis unavailable for leader election: {e}")
        return self._redis

    async def _get_price_cache(self) -> SharedPriceCache:
        """Get or create price cache."""
        if self._price_cache is None:
            self._price_cache = get_shared_price_cache()
        return self._price_cache

    async def _get_exchange(self, exchange_id: str) -> Optional[ccxt.Exchange]:
        """Get or create CCXT exchange instance."""
        if exchange_id not in self._exchanges:
            try:
                exchange_class = getattr(ccxt, exchange_id, None)
                if exchange_class is None:
                    logger.warning(f"Unknown exchange: {exchange_id}")
                    return None

                self._exchanges[exchange_id] = exchange_class(
                    {
                        "enableRateLimit": True,
                        "options": {"defaultType": "swap"},
                        **get_ccxt_proxy_config(),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create exchange {exchange_id}: {e}")
                return None
        return self._exchanges[exchange_id]

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> bool:
        """Start the prefetch service."""
        if self._running:
            return True

        self._running = True

        # Start leader election loop
        self._leader_task = asyncio.create_task(self._leader_election_loop())

        logger.info("PricePrefetchService started")
        return True

    async def stop(self) -> None:
        """Stop the prefetch service."""
        self._running = False

        # Cancel leader task
        if self._leader_task:
            self._leader_task.cancel()
            try:
                await self._leader_task
            except asyncio.CancelledError:
                pass

        # Cancel prefetch task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Close CCXT connections
        for exchange in self._exchanges.values():
            try:
                await exchange.close()
            except Exception:
                pass
        self._exchanges.clear()

        logger.info(
            f"PricePrefetchService stopped "
            f"(prefetches={self._prefetch_count}, errors={self._prefetch_errors})"
        )

    # =========================================================================
    # Leader Election
    # =========================================================================

    async def _leader_election_loop(self) -> None:
        """Background loop for leader election."""
        while self._running:
            try:
                acquired = await self._try_acquire_leadership()

                if acquired and not self._is_leader:
                    self._is_leader = True
                    logger.info("PricePrefetchService acquired leadership")
                    # Start prefetch loop
                    if self._task is None or self._task.done():
                        self._task = asyncio.create_task(self._prefetch_loop())

                elif not acquired and self._is_leader:
                    self._is_leader = False
                    logger.warning("PricePrefetchService lost leadership")
                    # Stop prefetch loop
                    if self._task:
                        self._task.cancel()
                        try:
                            await self._task
                        except asyncio.CancelledError:
                            pass
                        self._task = None

                # Renew or retry
                await asyncio.sleep(LEADER_RENEW_INTERVAL if self._is_leader else 5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Leader election error: {e}")
                await asyncio.sleep(5)

    async def _try_acquire_leadership(self) -> bool:
        """Try to acquire or renew leadership."""
        redis = await self._get_redis()
        if redis is None:
            # No Redis, assume single instance - always leader
            return True

        try:
            instance_id = f"prefetch:{id(self)}"
            # Use SET NX EX for atomic acquire
            result = await redis.set(
                self.LEADER_KEY,
                instance_id,
                nx=True,
                ex=LEADER_TTL,
            )
            if result:
                return True

            # Check if we already hold the lock
            current = await redis.get(self.LEADER_KEY)
            if current and current.decode() == instance_id:
                # Renew the lock
                await redis.expire(self.LEADER_KEY, LEADER_TTL)
                return True

            return False
        except Exception as e:
            logger.debug(f"Leader election failed: {e}")
            return False

    async def _release_leadership(self) -> None:
        """Release leadership."""
        redis = await self._get_redis()
        if redis:
            try:
                await redis.delete(self.LEADER_KEY)
            except Exception:
                pass
        self._is_leader = False

    # =========================================================================
    # Prefetch Loop
    # =========================================================================

    async def _prefetch_loop(self) -> None:
        """Background loop that prefetches prices."""
        while self._running and self._is_leader:
            try:
                await self._prefetch_cycle()
                await asyncio.sleep(self._prefetch_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Prefetch cycle error: {e}")
                self._prefetch_errors += 1
                await asyncio.sleep(self._prefetch_interval)

    async def _prefetch_cycle(self) -> None:
        """Run one prefetch cycle."""
        if not self._subscriptions:
            return

        cache = await self._get_price_cache()
        now = time.monotonic()

        # Group symbols by exchange
        exchange_symbols: Dict[str, Set[str]] = {}
        for key, sub in self._subscriptions.items():
            if sub.exchange not in exchange_symbols:
                exchange_symbols[sub.exchange] = set()
            exchange_symbols[sub.exchange].add(sub.symbol)

        # Prefetch for each exchange
        for exchange_id, symbols in exchange_symbols.items():
            exchange = await self._get_exchange(exchange_id)
            if exchange is None:
                continue

            batch_prices = await self._try_stream_batch(exchange, exchange_id, symbols)
            for symbol in symbols:
                try:
                    # Check if we need to fetch (cache TTL consideration)
                    sub = self._subscriptions.get(f"{exchange_id}:{symbol}")
                    if sub and sub.last_fetch:
                        # Skip if recently fetched (within 1/2 of cache TTL)
                        if (now - sub.last_fetch) < self._prefetch_interval:
                            continue

                    # Convert symbol to CCXT format
                    ccxt_symbol = self._to_ccxt_symbol(exchange_id, symbol)

                    # Prefer stream ticker data when available for this cycle.
                    ticker = batch_prices.get(ccxt_symbol)
                    if ticker is None:
                        ticker = await exchange.fetch_ticker(ccxt_symbol)
                    if ticker and ticker.get("last"):
                        price = float(ticker["last"])
                        bid = float(ticker.get("bid", price))
                        ask = float(ticker.get("ask", price))

                        # Update cache
                        await cache.set_price(exchange_id, symbol, price, bid, ask)

                        # Update subscription
                        if sub:
                            sub.last_fetch = now

                        self._prefetch_count += 1
                        # Publish live price updates to app WebSocket channel.
                        try:
                            from ..api.websocket import (
                                has_price_subscribers,
                                publish_price_update,
                            )

                            if not has_price_subscribers(exchange_id, symbol):
                                self._publish_skips_no_subscribers += 1
                                continue

                            publish_key = f"{exchange_id}:{symbol}"
                            last_published = self._last_published_prices.get(
                                publish_key
                            )
                            if last_published and last_published > 0:
                                delta_pct = abs(price - last_published) / last_published
                                if delta_pct < MIN_PUBLISH_CHANGE_PCT:
                                    self._publish_skips_small_change += 1
                                    continue

                            await publish_price_update(
                                exchange=exchange_id,
                                symbol=symbol,
                                price=price,
                                bid=bid,
                                ask=ask,
                                source="prefetch",
                            )
                            self._last_published_prices[publish_key] = price
                        except Exception as e:
                            logger.debug(
                                f"Failed to publish price update for "
                                f"{exchange_id}:{symbol}: {e}"
                            )
                        logger.debug(f"Prefetched {exchange_id}:{symbol} = {price}")

                except Exception as e:
                    logger.debug(f"Prefetch failed for {exchange_id}:{symbol}: {e}")

    async def _try_stream_batch(
        self,
        exchange,
        exchange_id: str,
        symbols: Set[str],
    ) -> Dict[str, dict]:
        """
        Try to fetch a batch of tickers through exchange streaming API.

        Falls back silently when streaming is unavailable or times out.
        """
        watch_tickers = getattr(exchange, "watch_tickers", None)
        if not callable(watch_tickers):
            self._stream_fallbacks += 1
            return {}

        ccxt_symbols = [self._to_ccxt_symbol(exchange_id, s) for s in symbols]
        timeout = max(0.5, self._prefetch_interval * STREAM_TIMEOUT_RATIO)

        try:
            tickers = await asyncio.wait_for(watch_tickers(ccxt_symbols), timeout)
            if isinstance(tickers, dict) and tickers:
                self._stream_hits += 1
                return tickers
        except Exception as e:
            logger.debug(f"Streaming watch_tickers unavailable for {exchange_id}: {e}")

        self._stream_fallbacks += 1
        return {}

    def _to_ccxt_symbol(self, exchange_id: str, symbol: str) -> str:
        """Convert bare symbol to CCXT format."""
        symbol = symbol.upper().strip()

        # Already formatted
        if ":" in symbol:
            return symbol
        if "/" in symbol:
            base, quote = symbol.split("/")
            if exchange_id == "hyperliquid":
                return f"{base}/{quote}:USDC"
            return f"{base}/{quote}:USDT"

        # Bare symbol
        if exchange_id == "hyperliquid":
            return f"{symbol}/USDC:USDC"
        return f"{symbol}/USDT:USDT"

    # =========================================================================
    # Symbol Registration
    # =========================================================================

    async def register_symbol(
        self,
        exchange: str,
        symbol: str,
        agent_id: str,
    ) -> None:
        """
        Register a symbol for prefetching.

        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            agent_id: Agent ID subscribing to this symbol
        """
        exchange = exchange.lower()
        symbol = symbol.upper()
        key = f"{exchange}:{symbol}"

        # Update subscription
        if key in self._subscriptions:
            self._subscriptions[key].subscriber_count += 1
        else:
            self._subscriptions[key] = SymbolSubscription(
                symbol=symbol,
                exchange=exchange,
            )
            logger.debug(f"Registered symbol for prefetch: {key}")

        # Track agent -> symbols mapping
        if agent_id not in self._agent_symbols:
            self._agent_symbols[agent_id] = set()
        self._agent_symbols[agent_id].add(key)

    async def unregister_symbol(
        self,
        exchange: str,
        symbol: str,
        agent_id: str,
    ) -> None:
        """
        Unregister a symbol from prefetching.

        Args:
            exchange: Exchange identifier
            symbol: Trading symbol
            agent_id: Agent ID unsubscribing
        """
        exchange = exchange.lower()
        symbol = symbol.upper()
        key = f"{exchange}:{symbol}"

        # Remove from agent's symbols
        if agent_id in self._agent_symbols:
            self._agent_symbols[agent_id].discard(key)
            if not self._agent_symbols[agent_id]:
                del self._agent_symbols[agent_id]

        # Update subscription
        if key in self._subscriptions:
            self._subscriptions[key].subscriber_count -= 1
            if self._subscriptions[key].subscriber_count <= 0:
                del self._subscriptions[key]
                logger.debug(f"Unregistered symbol from prefetch: {key}")

    async def unregister_agent(self, agent_id: str) -> None:
        """
        Unregister all symbols for an agent.

        Call this when an agent stops.

        Args:
            agent_id: Agent ID to unregister
        """
        if agent_id not in self._agent_symbols:
            return

        # Copy set to avoid modification during iteration
        symbols = list(self._agent_symbols[agent_id])
        for key in symbols:
            if key in self._subscriptions:
                self._subscriptions[key].subscriber_count -= 1
                if self._subscriptions[key].subscriber_count <= 0:
                    del self._subscriptions[key]

        del self._agent_symbols[agent_id]
        logger.debug(f"Unregistered agent {agent_id} from prefetch")

    # =========================================================================
    # Status & Metrics
    # =========================================================================

    def get_stats(self) -> dict:
        """Get service statistics."""
        return {
            "running": self._running,
            "is_leader": self._is_leader,
            "subscriptions": len(self._subscriptions),
            "agents": len(self._agent_symbols),
            "symbols": [
                {
                    "exchange": s.exchange,
                    "symbol": s.symbol,
                    "subscribers": s.subscriber_count,
                }
                for s in self._subscriptions.values()
            ],
            "prefetch_count": self._prefetch_count,
            "prefetch_errors": self._prefetch_errors,
            "stream_hits": self._stream_hits,
            "stream_fallbacks": self._stream_fallbacks,
            "publish_skips_no_subscribers": self._publish_skips_no_subscribers,
            "publish_skips_small_change": self._publish_skips_small_change,
        }

    def is_active(self) -> bool:
        """Check if service is running and is leader."""
        return self._running and self._is_leader


# =============================================================================
# Singleton Instance
# =============================================================================

_price_prefetch_service: Optional[PricePrefetchService] = None


def get_price_prefetch_service(
    prefetch_interval: float = PREFETCH_INTERVAL,
) -> PricePrefetchService:
    """
    Get or create the price prefetch service singleton.

    Args:
        prefetch_interval: Interval between prefetch cycles

    Returns:
        PricePrefetchService singleton instance
    """
    global _price_prefetch_service
    if _price_prefetch_service is None:
        _price_prefetch_service = PricePrefetchService(
            prefetch_interval=prefetch_interval,
        )
    return _price_prefetch_service


def reset_price_prefetch_service() -> None:
    """Reset the price prefetch service (for testing)."""
    global _price_prefetch_service
    _price_prefetch_service = None
