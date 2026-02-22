"""
Exchange capabilities configuration.

This module defines the capabilities and configuration for each supported exchange,
including supported asset types, settlement currencies, features, and limits.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Supported asset/market types"""

    CRYPTO_PERP = "crypto_perp"  # Crypto perpetual futures
    CRYPTO_SPOT = "crypto_spot"  # Crypto spot
    FOREX = "forex"  # Foreign exchange (future)
    METALS = "metals"  # Precious metals (future)
    EQUITIES = "equities"  # Stocks/equities (future)


class SettlementCurrency(str, Enum):
    """Supported settlement currencies"""

    USDT = "USDT"
    USDC = "USDC"
    USD = "USD"  # For forex/metals/equities
    BUSD = "BUSD"


class ExchangeFeature(str, Enum):
    """Optional exchange features"""

    FUNDING_RATES = "funding_rates"
    OPEN_INTEREST = "open_interest"
    LEVERAGE_ADJUSTMENT = "leverage_adjustment"
    ISOLATED_MARGIN = "isolated_margin"
    CROSS_MARGIN = "cross_margin"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"


class ExchangeCapabilities(BaseModel):
    """Exchange capabilities and configuration"""

    id: str = Field(
        ..., description="Exchange identifier (e.g., 'hyperliquid', 'binance')"
    )
    display_name: str = Field(
        ..., description="Human-readable name (e.g., 'Binance Futures')"
    )

    # Supported assets
    supported_assets: list[AssetType] = Field(
        default_factory=list, description="List of supported asset types"
    )

    # Settlement currencies per asset type
    settlement_currencies: dict[AssetType, SettlementCurrency] = Field(
        default_factory=dict, description="Settlement currency mapping per asset type"
    )

    # Default settlement currency (for backward compatibility)
    default_settlement: SettlementCurrency = Field(
        default=SettlementCurrency.USDT, description="Default settlement currency"
    )

    # Optional features
    features: list[ExchangeFeature] = Field(
        default_factory=list, description="List of supported features"
    )

    # Limits
    max_leverage: int = Field(default=100, description="Maximum leverage")
    min_order_size_usd: float = Field(
        default=1.0, description="Minimum order size in USD"
    )
    max_kline_limit: int = Field(default=1000, description="Maximum kline data limit")

    # CCXT-specific config
    ccxt_id: str = Field(..., description="CCXT exchange class ID")
    requires_passphrase: bool = Field(
        default=False, description="Whether passphrase is required"
    )
    supports_testnet: bool = Field(
        default=True, description="Whether testnet is supported"
    )

    # Metadata
    is_active: bool = Field(default=True, description="Whether exchange is active")
    logo_url: Optional[str] = Field(default=None, description="Exchange logo URL")
    website_url: Optional[str] = Field(default=None, description="Exchange website URL")


# ==================== Exchange Configurations ====================

EXCHANGE_CAPABILITIES: dict[str, ExchangeCapabilities] = {
    "hyperliquid": ExchangeCapabilities(
        id="hyperliquid",
        display_name="Hyperliquid",
        supported_assets=[AssetType.CRYPTO_PERP, AssetType.CRYPTO_SPOT],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDC,
            AssetType.CRYPTO_SPOT: SettlementCurrency.USDC,
        },
        default_settlement=SettlementCurrency.USDC,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
        ],
        max_leverage=50,
        max_kline_limit=5000,
        ccxt_id="hyperliquid",
        supports_testnet=True,
        website_url="https://hyperliquid.xyz",
    ),
    "binance": ExchangeCapabilities(
        id="binance",
        display_name="Binance Futures",
        supported_assets=[AssetType.CRYPTO_PERP, AssetType.CRYPTO_SPOT],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDT,
            AssetType.CRYPTO_SPOT: SettlementCurrency.USDT,
        },
        default_settlement=SettlementCurrency.USDT,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
            ExchangeFeature.STOP_LOSS,
            ExchangeFeature.TAKE_PROFIT,
            ExchangeFeature.TRAILING_STOP,
        ],
        max_leverage=125,
        max_kline_limit=1500,
        ccxt_id="binanceusdm",
        supports_testnet=True,
        website_url="https://www.binance.com",
    ),
    "okx": ExchangeCapabilities(
        id="okx",
        display_name="OKX",
        supported_assets=[AssetType.CRYPTO_PERP, AssetType.CRYPTO_SPOT],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDT,
            AssetType.CRYPTO_SPOT: SettlementCurrency.USDT,
        },
        default_settlement=SettlementCurrency.USDT,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
            ExchangeFeature.STOP_LOSS,
            ExchangeFeature.TAKE_PROFIT,
        ],
        max_leverage=125,
        max_kline_limit=1000,
        ccxt_id="okx",
        requires_passphrase=True,
        supports_testnet=True,
        website_url="https://www.okx.com",
    ),
    "bybit": ExchangeCapabilities(
        id="bybit",
        display_name="Bybit",
        supported_assets=[AssetType.CRYPTO_PERP, AssetType.CRYPTO_SPOT],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDT,
            AssetType.CRYPTO_SPOT: SettlementCurrency.USDT,
        },
        default_settlement=SettlementCurrency.USDT,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
            ExchangeFeature.STOP_LOSS,
            ExchangeFeature.TAKE_PROFIT,
            ExchangeFeature.TRAILING_STOP,
        ],
        max_leverage=100,
        max_kline_limit=1000,
        ccxt_id="bybit",
        supports_testnet=True,
        website_url="https://www.bybit.com",
    ),
    "bitget": ExchangeCapabilities(
        id="bitget",
        display_name="Bitget",
        supported_assets=[AssetType.CRYPTO_PERP, AssetType.CRYPTO_SPOT],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDT,
            AssetType.CRYPTO_SPOT: SettlementCurrency.USDT,
        },
        default_settlement=SettlementCurrency.USDT,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
            ExchangeFeature.STOP_LOSS,
            ExchangeFeature.TAKE_PROFIT,
        ],
        max_leverage=125,
        max_kline_limit=1000,
        ccxt_id="bitget",
        supports_testnet=False,
        website_url="https://www.bitget.com",
    ),
    "kucoin": ExchangeCapabilities(
        id="kucoin",
        display_name="KuCoin Futures",
        supported_assets=[AssetType.CRYPTO_PERP],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDT,
        },
        default_settlement=SettlementCurrency.USDT,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
        ],
        max_leverage=100,
        max_kline_limit=1000,
        ccxt_id="kucoinfutures",
        requires_passphrase=True,
        supports_testnet=True,
        website_url="https://www.kucoin.com",
    ),
    "gate": ExchangeCapabilities(
        id="gate",
        display_name="Gate.io",
        supported_assets=[AssetType.CRYPTO_PERP, AssetType.CRYPTO_SPOT],
        settlement_currencies={
            AssetType.CRYPTO_PERP: SettlementCurrency.USDT,
            AssetType.CRYPTO_SPOT: SettlementCurrency.USDT,
        },
        default_settlement=SettlementCurrency.USDT,
        features=[
            ExchangeFeature.FUNDING_RATES,
            ExchangeFeature.OPEN_INTEREST,
            ExchangeFeature.LEVERAGE_ADJUSTMENT,
            ExchangeFeature.ISOLATED_MARGIN,
            ExchangeFeature.CROSS_MARGIN,
        ],
        max_leverage=100,
        max_kline_limit=1000,
        ccxt_id="gateio",
        supports_testnet=False,
        website_url="https://www.gate.io",
    ),
}


# ==================== Helper Functions ====================


def get_exchange_capabilities(exchange_id: str) -> Optional[ExchangeCapabilities]:
    """Get capabilities for a specific exchange.

    Args:
        exchange_id: Exchange identifier (e.g., "hyperliquid", "binance")

    Returns:
        ExchangeCapabilities if found, None otherwise
    """
    return EXCHANGE_CAPABILITIES.get(exchange_id.lower())


def get_all_exchanges() -> list[ExchangeCapabilities]:
    """Get all configured exchanges.

    Returns:
        List of all ExchangeCapabilities
    """
    return list(EXCHANGE_CAPABILITIES.values())


def get_active_exchanges() -> list[ExchangeCapabilities]:
    """Get all active exchanges.

    Returns:
        List of active ExchangeCapabilities
    """
    return [cap for cap in EXCHANGE_CAPABILITIES.values() if cap.is_active]


def get_exchanges_for_asset(asset_type: AssetType) -> list[ExchangeCapabilities]:
    """Get all exchanges that support a specific asset type.

    Args:
        asset_type: The asset type to filter by

    Returns:
        List of ExchangeCapabilities that support the given asset type
    """
    return [
        cap
        for cap in EXCHANGE_CAPABILITIES.values()
        if asset_type in cap.supported_assets and cap.is_active
    ]


def get_settlement_currency(
    exchange_id: str, asset_type: AssetType = AssetType.CRYPTO_PERP
) -> SettlementCurrency:
    """Get settlement currency for an exchange and asset type.

    Args:
        exchange_id: Exchange identifier
        asset_type: Asset type to get settlement for

    Returns:
        SettlementCurrency for the exchange/asset combination
    """
    cap = get_exchange_capabilities(exchange_id)
    if cap:
        return cap.settlement_currencies.get(asset_type, cap.default_settlement)
    return SettlementCurrency.USDT


def supports_asset(exchange_id: str, asset_type: AssetType) -> bool:
    """Check if an exchange supports a specific asset type.

    Args:
        exchange_id: Exchange identifier
        asset_type: Asset type to check

    Returns:
        True if exchange supports the asset type
    """
    cap = get_exchange_capabilities(exchange_id)
    if not cap:
        return False
    return asset_type in cap.supported_assets


def get_ccxt_id(exchange_id: str) -> str:
    """Get CCXT exchange ID for a given exchange identifier.

    Args:
        exchange_id: Exchange identifier

    Returns:
        CCXT exchange class ID
    """
    cap = get_exchange_capabilities(exchange_id)
    if cap:
        return cap.ccxt_id
    # Fallback to exchange_id if not found
    return exchange_id
