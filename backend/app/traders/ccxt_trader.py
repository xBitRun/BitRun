"""
Unified CCXT exchange adapter.

A single BaseTrader implementation that drives ALL supported exchanges
(Hyperliquid, OKX, Binance, Bybit, etc.) through the CCXT library.

Exchange-specific differences (auth, margin mode, params) are handled via
configuration rather than separate classes.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, Literal, Optional

import ccxt.async_support as ccxt

from .base import (
    AccountState,
    BaseTrader,
    FundingRate,
    MarketData,
    MarketType,
    OHLCV,
    OrderResult,
    Position,
    TradeError,
    detect_market_type,
)
from .exchange_pool import ExchangePool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exchange-specific configuration
# ---------------------------------------------------------------------------

# Max K-line limits per exchange
_KLINE_MAX: dict[str, int] = {
    "hyperliquid": 5000,
    "okx": 300,
    "binanceusdm": 1500,
    "bybit": 1000,
    "bitget": 1000,
    "kucoinfutures": 200,
    "gateio": 1000,
}

# Default slippage per exchange (only matters for Hyperliquid market orders)
_DEFAULT_SLIPPAGE: dict[str, float] = {
    "hyperliquid": 0.03,
}


def _build_ccxt_config(
    exchange_id: str,
    credentials: dict[str, str],
    testnet: bool,
) -> dict[str, Any]:
    """
    Build the ccxt constructor kwargs for *exchange_id*.

    Args:
        exchange_id: CCXT exchange identifier (e.g. "hyperliquid", "okx")
        credentials: Decrypted credential dict from the database.
        testnet: Whether to use testnet / sandbox mode.

    Returns:
        Dict ready to be unpacked into ``ccxt.<exchange>(…)``.
    """
    cfg: dict[str, Any] = {
        "options": {
            "adjustForTimeDifference": True,
        },
    }

    if exchange_id == "hyperliquid":
        private_key = credentials.get("private_key", "")
        cfg["privateKey"] = private_key

        # walletAddress is mandatory for Hyperliquid (fetchBalance, fetchPositions).
        # If not explicitly provided, derive it from the private key.
        wallet = credentials.get("wallet_address")
        if wallet:
            cfg["walletAddress"] = wallet
        elif private_key:
            from eth_account import Account

            cfg["walletAddress"] = Account.from_key(private_key).address
        # Hyperliquid does not use apiKey / secret

    elif exchange_id == "okx":
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")
        cfg["password"] = credentials.get("passphrase", "")
        cfg["options"]["defaultType"] = "swap"

    elif exchange_id == "binanceusdm":
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")
        cfg["options"]["defaultType"] = "future"

    elif exchange_id == "bybit":
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")
        cfg["options"]["defaultType"] = "linear"

    elif exchange_id == "bitget":
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")
        cfg["password"] = credentials.get("passphrase", "")
        cfg["options"]["defaultType"] = "swap"

    elif exchange_id == "kucoinfutures":
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")
        cfg["password"] = credentials.get("passphrase", "")

    elif exchange_id == "gateio":
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")
        cfg["options"]["defaultType"] = "swap"

    else:
        # Generic fallback – just forward apiKey / secret
        cfg["apiKey"] = credentials.get("api_key", "")
        cfg["secret"] = credentials.get("api_secret", "")

    # Proxy support for geo-restricted exchanges
    from ..core.config import get_ccxt_proxy_config

    cfg.update(get_ccxt_proxy_config())

    return cfg


# Map user-facing exchange name → ccxt exchange class id
EXCHANGE_ID_MAP: dict[str, str] = {
    "hyperliquid": "hyperliquid",
    "okx": "okx",
    "binance": "binanceusdm",
    "bybit": "bybit",
    "bitget": "bitget",
    "kucoin": "kucoinfutures",
    "gate": "gateio",
}


def create_trader_from_account(
    account,
    credentials: dict,
    margin_mode: str = "isolated",
    trade_type: str = "crypto_perp",
) -> "CCXTTrader":
    """
    Create a unified CCXTTrader from a database account and credentials.

    This is the single factory function used by all workers and API routes.

    Args:
        account: Database account model (or any object with .exchange / .is_testnet).
        credentials: Decrypted credentials dict from the repository.
        margin_mode: "isolated" (default, recommended for multi-strategy) or "cross".
        trade_type: Market type – "crypto_perp" (default), "crypto_spot",
                    "forex", or "metals".

    Returns:
        CCXTTrader instance configured for the exchange.

    Raises:
        ValueError: If the exchange is not supported.
    """
    exchange = account.exchange.lower()
    ccxt_id = EXCHANGE_ID_MAP.get(exchange)
    if not ccxt_id:
        raise ValueError(f"Unsupported exchange: {exchange}")

    return CCXTTrader(
        exchange_id=ccxt_id,
        credentials=credentials,
        testnet=account.is_testnet,
        margin_mode=margin_mode,
        trade_type=trade_type,
    )


class CCXTTrader(BaseTrader):
    """
    Unified CCXT trading adapter for all supported exchanges.

    Replaces HyperliquidTrader, OKXTrader, BinanceTrader and BybitTrader
    with a single configurable implementation.

    Usage:
        trader = CCXTTrader("hyperliquid", {"private_key": "0x..."}, testnet=True)
        await trader.initialize()
        account = await trader.get_account_state()
        result = await trader.open_long("ETH", 1000, leverage=5)
    """

    def __init__(
        self,
        exchange_id: str,
        credentials: dict[str, str],
        testnet: bool = True,
        margin_mode: str = "isolated",
        trade_type: str = "crypto_perp",
    ):
        """
        Args:
            exchange_id: CCXT exchange identifier (e.g. "hyperliquid", "okx",
                         "binanceusdm", "bybit").
            credentials: Decrypted credentials dict.
            testnet: Use testnet / sandbox mode if True.
            margin_mode: Margin mode – "isolated" (default, recommended for
                         multi-strategy) or "cross".
            trade_type: Market type – "crypto_perp" (default), "crypto_spot",
                        "forex", or "metals".
        """
        default_slippage = _DEFAULT_SLIPPAGE.get(exchange_id, 0.01)
        super().__init__(testnet=testnet, default_slippage=default_slippage)

        self._exchange_id = exchange_id
        self._credentials = credentials
        self._exchange: Optional[ccxt.Exchange] = None
        self._ccxt_config = _build_ccxt_config(exchange_id, credentials, testnet)
        self._margin_mode = margin_mode
        self._trade_type = trade_type

    # ------------------------------------------------------------------
    # BaseTrader interface – lifecycle
    # ------------------------------------------------------------------

    @property
    def exchange_name(self) -> str:
        return self._exchange_id

    async def initialize(self) -> bool:
        try:
            self._exchange = await ExchangePool.acquire(
                self._exchange_id,
                self._ccxt_config,
                self._credentials,
                self.testnet,
            )

            self._initialized = True
            logger.info(
                f"CCXTTrader initialized: {self._exchange_id} "
                f"(testnet={self.testnet})"
            )
            return True

        except ccxt.AuthenticationError as e:
            raise TradeError(
                f"{self._exchange_id} authentication failed: {e}",
                code="AUTH_ERROR",
            )
        except ccxt.ExchangeError as e:
            raise TradeError(
                f"{self._exchange_id} exchange error: {e}",
                code="EXCHANGE_ERROR",
            )
        except TradeError:
            raise
        except Exception as e:
            raise TradeError(f"Failed to initialize {self._exchange_id}: {e}")

    async def close(self) -> None:
        # Release back to pool instead of closing the underlying connection
        if self._exchange:
            ExchangePool.release(
                self._exchange_id,
                self._credentials,
                self.testnet,
            )
        self._exchange = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Symbol helpers
    # ------------------------------------------------------------------

    def _to_ccxt_symbol(self, symbol: str) -> str:
        """
        Normalise a bare symbol ("BTC") or pair ("EUR/USD") into the CCXT
        unified format used by the current exchange.

        Crypto spot        → "BTC/USDT" (or USDC for Hyperliquid)
        Crypto perpetuals  → "BTC/USDT:USDT" (or USDC:USDC for Hyperliquid)
        Forex / Metals     → "EUR/USD" / "XAU/USD" (already standard)
        """
        symbol = symbol.upper().strip()

        # Detect market type to decide normalisation strategy
        mtype = detect_market_type(symbol)

        # Forex and metals symbols are already in CCXT format (e.g. EUR/USD)
        if mtype in (MarketType.FOREX, MarketType.METALS):
            # If already a pair, return as-is
            if "/" in symbol:
                return symbol
            # Bare metal code → default to /USD
            return f"{symbol}/USD"

        # --- Crypto path ---
        is_spot = self._trade_type == "crypto_spot"

        # Already formatted with settlement - only for perp mode
        if ":" in symbol:
            if is_spot:
                # Strip settlement suffix for spot mode
                return symbol.split(":")[0]
            return symbol

        # Already has quote currency
        if "/" in symbol:
            parts = symbol.split("/")
            base = parts[0]
            quote = parts[1]
            # Spot mode: no settlement suffix
            if is_spot:
                return f"{base}/{quote}"
            # Perp mode: add settlement suffix
            if self._exchange_id == "hyperliquid":
                return f"{base}/{quote}:USDC"
            return f"{base}/{quote}:USDT"

        # Bare symbol - extract base and apply exchange-specific format
        base = (
            symbol.replace("USDT", "")
            .replace("-SWAP", "")
            .replace("_PERP", "")
            .replace("-", "")
            .replace("_", "")
        )

        # Spot mode: no settlement currency suffix
        if is_spot:
            if self._exchange_id == "hyperliquid":
                return f"{base}/USDC"
            return f"{base}/USDT"

        # Perp mode: add settlement currency suffix
        if self._exchange_id == "hyperliquid":
            # Hyperliquid uses USDC for both quote and settlement: BTC/USDC:USDC
            return f"{base}/USDC:USDC"

        # OKX / Binance / Bybit all use USDT settled perps
        return f"{base}/USDT:USDT"

    @staticmethod
    def _base_symbol(ccxt_symbol: str) -> str:
        """Extract the base asset from a CCXT symbol ("BTC/USDT:USDT" → "BTC")."""
        return ccxt_symbol.split("/")[0] if "/" in ccxt_symbol else ccxt_symbol

    # ------------------------------------------------------------------
    # Precision helpers (CCXT market info)
    # ------------------------------------------------------------------

    def _amount_to_precision(self, symbol: str, amount: float) -> float:
        """Round *amount* to the exchange's allowed precision for *symbol*."""
        if self._exchange is None:
            return amount
        try:
            return float(self._exchange.amount_to_precision(symbol, amount))
        except Exception:
            return amount

    def _get_min_amount(self, symbol: str) -> float:
        """Return the exchange minimum order amount for *symbol*, or 0."""
        if self._exchange is None:
            return 0.0
        try:
            market = self._exchange.market(symbol)
            return float(market.get("limits", {}).get("amount", {}).get("min", 0) or 0)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def get_account_state(self) -> AccountState:
        self._ensure_initialized()
        try:
            fetch_params: dict[str, Any] = {}
            if self._exchange_id == "okx":
                fetch_params["type"] = "swap"
            elif self._exchange_id == "bybit":
                fetch_params["type"] = "linear"

            balance, positions_data = await asyncio.gather(
                self._exchange.fetch_balance(fetch_params),
                self._exchange.fetch_positions(),
            )

            positions: list[Position] = []
            total_margin_used = 0.0

            for pos in positions_data:
                size = float(pos.get("contracts", 0) or 0)
                if size == 0:
                    continue

                entry_price = float(pos.get("entryPrice", 0) or 0)
                mark_price = float(pos.get("markPrice", 0) or entry_price)
                notional = float(pos.get("notional", 0) or 0)
                unrealized_pnl = float(pos.get("unrealizedPnl", 0) or 0)
                margin_used = float(pos.get("initialMargin", 0) or 0)
                total_margin_used += margin_used

                raw_symbol = pos.get("symbol", "")
                base_symbol = self._base_symbol(raw_symbol)

                positions.append(
                    Position(
                        symbol=base_symbol,
                        side="long" if pos.get("side") == "long" else "short",
                        size=abs(size),
                        size_usd=abs(notional) if notional else abs(size) * mark_price,
                        entry_price=entry_price,
                        mark_price=mark_price,
                        leverage=int(pos.get("leverage", 1) or 1),
                        unrealized_pnl=unrealized_pnl,
                        unrealized_pnl_percent=(
                            (unrealized_pnl / abs(notional)) * 100 if notional else 0
                        ),
                        liquidation_price=(
                            float(pos.get("liquidationPrice", 0) or 0) or None
                        ),
                        margin_used=margin_used,
                    )
                )

            # Determine quote currency key for balance
            quote = "USDC" if self._exchange_id == "hyperliquid" else "USDT"
            quote_balance = balance.get(quote, {})
            equity = float(quote_balance.get("total", 0) or 0)
            available = float(quote_balance.get("free", 0) or 0)

            return AccountState(
                equity=equity,
                available_balance=available,
                total_margin_used=total_margin_used,
                unrealized_pnl=sum(p.unrealized_pnl for p in positions),
                positions=positions,
            )

        except ccxt.AuthenticationError as e:
            raise TradeError(
                f"{self._exchange_id} authentication failed: {e}",
                code="AUTH_ERROR",
            )
        except Exception as e:
            raise TradeError(f"Failed to get account state: {e}")

    async def get_positions(self) -> list[Position]:
        account = await self.get_account_state()
        return account.positions

    async def get_position(self, symbol: str) -> Optional[Position]:
        base = self._validate_symbol(symbol)
        positions = await self.get_positions()
        for pos in positions:
            if pos.symbol.upper() == base.upper():
                return pos
        return None

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    async def get_market_price(self, symbol: str) -> float:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                ticker = await self._exchange.fetch_ticker(ccxt_symbol)
                return float(ticker.get("last", 0) or ticker.get("close", 0))
            except Exception as e:
                last_err = e
                if attempt < 2:
                    delay = 1 * (attempt + 1)  # 1s, 2s
                    logger.warning(
                        f"get_market_price({symbol}) attempt {attempt + 1} failed: {e}, "
                        f"retrying in {delay}s…"
                    )
                    await asyncio.sleep(delay)
        raise TradeError(f"Failed to get market price for {symbol}: {last_err}")

    async def get_market_data(self, symbol: str) -> MarketData:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        mtype = detect_market_type(symbol)
        try:
            ticker = await self._exchange.fetch_ticker(ccxt_symbol)
            bid = float(ticker.get("bid", 0) or 0)
            ask = float(ticker.get("ask", 0) or 0)
            last = float(ticker.get("last", 0) or ticker.get("close", 0))

            # Funding rate only applies to crypto perpetuals
            funding_rate = None
            if mtype == MarketType.CRYPTO_PERP:
                try:
                    funding = await self._exchange.fetch_funding_rate(ccxt_symbol)
                    funding_rate = float(funding.get("fundingRate", 0) or 0)
                except Exception:
                    logger.debug(f"Could not fetch funding rate for {symbol}")

            base = self._base_symbol(ccxt_symbol)
            return MarketData(
                symbol=base,
                mid_price=last,
                bid_price=bid or last,
                ask_price=ask or last,
                volume_24h=float(ticker.get("quoteVolume", 0) or 0),
                funding_rate=funding_rate,
                open_interest=(
                    float(ticker.get("openInterest", 0) or 0)
                    if ticker.get("openInterest")
                    else None
                ),
            )
        except TradeError:
            raise
        except Exception as e:
            raise TradeError(f"Failed to get market data for {symbol}: {e}")

    async def fetch_tickers(self, symbols: list[str]) -> dict[str, dict]:
        """
        Fetch ticker data for multiple symbols.

        Uses exchange-native batch ``fetch_tickers`` when possible and falls back
        to per-symbol ``fetch_ticker`` for exchanges that don't support batch.
        """
        self._ensure_initialized()
        if not symbols:
            return {}

        symbol_map = {symbol: self._to_ccxt_symbol(symbol) for symbol in symbols}
        ccxt_symbols = list(symbol_map.values())

        # Prefer native batch API (best for rate limits/latency).
        try:
            raw = await self._exchange.fetch_tickers(ccxt_symbols)
            if isinstance(raw, dict) and raw:
                return {
                    src_symbol: raw.get(ccxt_symbol, {})
                    for src_symbol, ccxt_symbol in symbol_map.items()
                    if raw.get(ccxt_symbol)
                }
        except Exception as e:
            logger.debug(
                f"Batch fetch_tickers unavailable for {self._exchange_id}, "
                f"falling back to per-symbol fetch_ticker: {e}"
            )

        # Fallback: fetch each ticker independently.
        results: dict[str, dict] = {}
        for src_symbol, ccxt_symbol in symbol_map.items():
            try:
                results[src_symbol] = await self._exchange.fetch_ticker(ccxt_symbol)
            except Exception as e:
                logger.debug(f"fetch_ticker failed for {src_symbol}: {e}")
        return results

    # ------------------------------------------------------------------
    # K-lines / OHLCV
    # ------------------------------------------------------------------

    async def get_klines(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list[OHLCV]:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        max_limit = _KLINE_MAX.get(self._exchange_id, 1000)
        try:
            data = await self._exchange.fetch_ohlcv(
                ccxt_symbol,
                timeframe=timeframe,
                limit=min(limit, max_limit),
            )
            if not data:
                return []
            return [OHLCV.from_ccxt(c) for c in data]
        except Exception as e:
            logger.warning(f"Failed to get klines for {symbol} ({timeframe}): {e}")
            return []

    async def get_funding_history(
        self,
        symbol: str,
        limit: int = 24,
    ) -> list[FundingRate]:
        self._ensure_initialized()

        # Funding rates are only applicable to crypto perpetuals
        mtype = detect_market_type(symbol)
        if mtype in (MarketType.FOREX, MarketType.METALS):
            return []

        ccxt_symbol = self._to_ccxt_symbol(symbol)
        try:
            data = await self._exchange.fetch_funding_rate_history(
                ccxt_symbol,
                limit=limit,
            )
            if not data:
                return []

            rates: list[FundingRate] = []
            for item in data:
                ts = item.get("timestamp") or item.get("datetime")
                if isinstance(ts, int):
                    timestamp = datetime.utcfromtimestamp(ts / 1000)
                elif isinstance(ts, str):
                    timestamp = datetime.fromisoformat(
                        ts.replace("Z", "+00:00").replace("+00:00", "")
                    )
                else:
                    timestamp = datetime.now(UTC)

                rates.append(
                    FundingRate(
                        timestamp=timestamp,
                        rate=float(item.get("fundingRate", 0) or 0),
                    )
                )

            rates.sort(key=lambda r: r.timestamp, reverse=True)
            return rates

        except Exception as e:
            logger.warning(f"Failed to get funding history for {symbol}: {e}")
            return []

    async def get_open_interest(self, symbol: str) -> Optional[float]:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        try:
            ticker = await self._exchange.fetch_ticker(ccxt_symbol)
            oi = ticker.get("openInterest")
            return float(oi) if oi else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Order operations
    # ------------------------------------------------------------------

    async def place_market_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        leverage: int = 1,
        reduce_only: bool = False,
        slippage: Optional[float] = None,
        price: Optional[float] = None,
    ) -> OrderResult:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)

        # Round to exchange precision
        size = self._amount_to_precision(ccxt_symbol, size)

        # Validate minimum order size
        if not reduce_only:
            min_amount = self._get_min_amount(ccxt_symbol)
            if min_amount > 0 and size < min_amount:
                return OrderResult(
                    success=False,
                    error=(
                        f"Order size {size} below exchange minimum {min_amount} "
                        f"for {ccxt_symbol}"
                    ),
                )
            if size <= 0:
                return OrderResult(
                    success=False,
                    error=f"Order size is zero after precision rounding for {ccxt_symbol}",
                )

        try:
            # Set leverage (skip for reduce-only / close orders)
            if not reduce_only:
                await self._safe_set_leverage(ccxt_symbol, leverage)

            # Build params
            params: dict[str, Any] = {}
            if self._exchange_id == "okx":
                params["tdMode"] = self._margin_mode
            if reduce_only:
                params["reduceOnly"] = True
            # Hyperliquid: pass slippage so CCXT builds the right limit price
            if self._exchange_id == "hyperliquid":
                params["slippage"] = slippage or self.default_slippage

            order = await self._exchange.create_market_order(
                ccxt_symbol,
                side,
                size,
                price=price,
                params=params,
            )

            return OrderResult(
                success=True,
                order_id=str(order.get("id", "")),
                filled_size=float(order.get("filled", 0) or 0),
                filled_price=float(order.get("average", 0) or 0),
                status=order.get("status", ""),
                raw_response=order,
            )

        except ccxt.RateLimitExceeded:
            # Retry once after a short backoff for rate limits
            logger.warning(
                f"Rate limit hit for {ccxt_symbol} {side} {size}, " "retrying in 2s..."
            )
            await asyncio.sleep(2)
            try:
                order = await self._exchange.create_market_order(
                    ccxt_symbol,
                    side,
                    size,
                    price=price,
                    params=params,
                )
                return OrderResult(
                    success=True,
                    order_id=str(order.get("id", "")),
                    filled_size=float(order.get("filled", 0) or 0),
                    filled_price=float(order.get("average", 0) or 0),
                    status=order.get("status", ""),
                    raw_response=order,
                )
            except Exception as retry_err:
                logger.error(f"Rate limit retry failed for {ccxt_symbol}: {retry_err}")
                return OrderResult(success=False, error=f"Rate limit: {retry_err}")
        except ccxt.InsufficientFunds as e:
            logger.error(f"Insufficient funds for {ccxt_symbol} {side} {size}: {e}")
            return OrderResult(success=False, error=f"Insufficient funds: {e}")
        except ccxt.InvalidOrder as e:
            logger.error(f"Invalid order for {ccxt_symbol} {side} {size}: {e}")
            return OrderResult(success=False, error=f"Invalid order: {e}")
        except Exception as e:
            logger.error(f"Market order failed for {ccxt_symbol} {side} {size}: {e}")
            return OrderResult(success=False, error=str(e))

    async def place_limit_order(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        price: float,
        leverage: int = 1,
        reduce_only: bool = False,
        post_only: bool = False,
    ) -> OrderResult:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        size = self._amount_to_precision(ccxt_symbol, size)

        try:
            if not reduce_only:
                await self._safe_set_leverage(ccxt_symbol, leverage)

            params: dict[str, Any] = {}
            if self._exchange_id == "okx":
                params["tdMode"] = self._margin_mode
            if reduce_only:
                params["reduceOnly"] = True
            if post_only:
                params["postOnly"] = True

            order = await self._exchange.create_limit_order(
                ccxt_symbol,
                side,
                size,
                price,
                params=params,
            )

            return OrderResult(
                success=True,
                order_id=str(order.get("id", "")),
                filled_size=float(order.get("filled", 0) or 0),
                filled_price=float(order.get("average", 0) or 0),
                status=order.get("status", ""),
                raw_response=order,
            )
        except Exception as e:
            logger.error(f"Limit order failed for {ccxt_symbol}: {e}")
            return OrderResult(success=False, error=str(e))

    async def place_stop_loss(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        size = self._amount_to_precision(ccxt_symbol, size)

        try:
            params: dict[str, Any] = {
                "triggerPrice": trigger_price,
                "reduceOnly": reduce_only,
            }
            if self._exchange_id == "okx":
                params["tdMode"] = self._margin_mode
                params["triggerType"] = "last"

            order = await self._exchange.create_order(
                ccxt_symbol,
                "market",
                side,
                size,
                None,
                params=params,
            )
            return OrderResult(
                success=True,
                order_id=str(order.get("id", "")),
                status="pending",
                raw_response=order,
            )
        except Exception as e:
            logger.error(f"Stop loss order failed for {symbol}: {e}")
            return OrderResult(success=False, error=str(e))

    async def place_take_profit(
        self,
        symbol: str,
        side: Literal["buy", "sell"],
        size: float,
        trigger_price: float,
        reduce_only: bool = True,
    ) -> OrderResult:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        size = self._amount_to_precision(ccxt_symbol, size)

        try:
            params: dict[str, Any] = {
                "triggerPrice": trigger_price,
                "reduceOnly": reduce_only,
            }
            if self._exchange_id == "okx":
                params["tdMode"] = self._margin_mode
                params["triggerType"] = "last"

            order = await self._exchange.create_order(
                ccxt_symbol,
                "market",
                side,
                size,
                None,
                params=params,
            )
            return OrderResult(
                success=True,
                order_id=str(order.get("id", "")),
                status="pending",
                raw_response=order,
            )
        except Exception as e:
            logger.error(f"Take profit order failed for {symbol}: {e}")
            return OrderResult(success=False, error=str(e))

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        try:
            await self._exchange.cancel_order(order_id, ccxt_symbol)
            return True
        except Exception as e:
            logger.warning(f"Failed to cancel order {order_id}: {e}")
            return False

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        self._ensure_initialized()
        try:
            if symbol:
                ccxt_symbol = self._to_ccxt_symbol(symbol)
                result = await self._exchange.cancel_all_orders(ccxt_symbol)
                return len(result) if isinstance(result, list) else 1
            else:
                open_orders = await self._exchange.fetch_open_orders()
                count = 0
                for order in open_orders:
                    try:
                        await self._exchange.cancel_order(
                            order["id"],
                            order["symbol"],
                        )
                        count += 1
                    except Exception as e:
                        logger.debug(f"Failed to cancel order {order.get('id')}: {e}")
                return count
        except Exception as e:
            logger.error(f"Failed to cancel orders: {e}")
            return 0

    # ------------------------------------------------------------------
    # Position operations
    # ------------------------------------------------------------------

    async def close_position(
        self,
        symbol: str,
        size: Optional[float] = None,
        slippage: Optional[float] = None,
    ) -> OrderResult:
        self._ensure_initialized()
        try:
            position = await self.get_position(symbol)
            if not position:
                return OrderResult(success=True, status="no_position")

            close_size = size or position.size
            close_side: Literal["buy", "sell"] = (
                "sell" if position.side == "long" else "buy"
            )

            # Fetch price so Hyperliquid can calculate slippage without an
            # extra internal fetch_ticker call.
            price = await self.get_market_price(symbol)

            return await self.place_market_order(
                symbol,
                close_side,
                close_size,
                reduce_only=True,
                slippage=slippage,
                price=price,
            )
        except Exception as e:
            return OrderResult(success=False, error=str(e))

    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        self._ensure_initialized()
        ccxt_symbol = self._to_ccxt_symbol(symbol)
        return await self._safe_set_leverage(ccxt_symbol, leverage)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _safe_set_leverage(
        self,
        ccxt_symbol: str,
        leverage: int,
    ) -> bool:
        """Set margin mode + leverage, distinguishing benign from critical errors."""
        try:
            await self._exchange.set_margin_mode(self._margin_mode, ccxt_symbol)
        except Exception as e:
            err_msg = str(e).lower()
            # "already set" / "no change" are benign
            if any(
                kw in err_msg
                for kw in ("already", "no change", "not modified", "margin mode is")
            ):
                logger.debug(f"set_margin_mode note for {ccxt_symbol}: {e}")
            elif "position" in err_msg and ("exist" in err_msg or "open" in err_msg):
                # Cannot switch margin mode while position exists – critical
                logger.error(
                    f"Cannot change margin mode to {self._margin_mode} for "
                    f"{ccxt_symbol}: position already exists. {e}"
                )
                raise TradeError(
                    f"Cannot set margin mode to {self._margin_mode} for {ccxt_symbol}: "
                    "existing position prevents mode change.",
                    code="MARGIN_MODE_CONFLICT",
                )
            else:
                # Unknown error – log but don't block (some exchanges don't support the call)
                logger.debug(f"set_margin_mode note for {ccxt_symbol}: {e}")

        try:
            await self._exchange.set_leverage(leverage, ccxt_symbol)
            return True
        except Exception as e:
            err_msg = str(e).lower()
            # "already set" / "no change" / "leverage not modified" are benign
            if any(
                kw in err_msg
                for kw in ("already", "no change", "not modified", "same leverage")
            ):
                logger.debug(f"set_leverage note for {ccxt_symbol}: {e}")
                return True
            # Critical: leverage could not be set to desired value
            logger.error(
                f"set_leverage FAILED for {ccxt_symbol} (target={leverage}x): {e}"
            )
            raise TradeError(
                f"Failed to set leverage to {leverage}x for {ccxt_symbol}: {e}",
                code="LEVERAGE_ERROR",
            )
