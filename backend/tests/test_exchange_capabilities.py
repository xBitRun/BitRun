"""
Tests for Exchange Capabilities.

Covers:
- AssetType: Asset type enumeration
- SettlementCurrency: Settlement currency enumeration
- ExchangeFeature: Exchange feature enumeration
- ExchangeCapabilities: Exchange configuration model
- get_exchange_capabilities: Get capabilities by exchange ID
- get_all_exchanges: Get all exchanges
- get_active_exchanges: Get active exchanges
- get_exchanges_for_asset: Get exchanges by asset type
- get_settlement_currency: Get settlement currency
- supports_asset: Check asset support
- get_ccxt_id: Get CCXT exchange ID
"""

import pytest

from app.traders.exchange_capabilities import (
    AssetType,
    SettlementCurrency,
    ExchangeFeature,
    ExchangeCapabilities,
    EXCHANGE_CAPABILITIES,
    get_exchange_capabilities,
    get_all_exchanges,
    get_active_exchanges,
    get_exchanges_for_asset,
    get_settlement_currency,
    supports_asset,
    get_ccxt_id,
)


# ── Test Enumerations ────────────────────────────────────────────────────


@pytest.mark.unit
class TestAssetType:
    """Tests for AssetType enumeration."""

    def test_crypto_perp(self):
        """Should have CRYPTO_PERP type."""
        assert AssetType.CRYPTO_PERP.value == "crypto_perp"

    def test_crypto_spot(self):
        """Should have CRYPTO_SPOT type."""
        assert AssetType.CRYPTO_SPOT.value == "crypto_spot"

    def test_forex(self):
        """Should have FOREX type."""
        assert AssetType.FOREX.value == "forex"

    def test_metals(self):
        """Should have METALS type."""
        assert AssetType.METALS.value == "metals"

    def test_equities(self):
        """Should have EQUITIES type."""
        assert AssetType.EQUITIES.value == "equities"


@pytest.mark.unit
class TestSettlementCurrency:
    """Tests for SettlementCurrency enumeration."""

    def test_usdt(self):
        """Should have USDT currency."""
        assert SettlementCurrency.USDT.value == "USDT"

    def test_usdc(self):
        """Should have USDC currency."""
        assert SettlementCurrency.USDC.value == "USDC"

    def test_usd(self):
        """Should have USD currency."""
        assert SettlementCurrency.USD.value == "USD"


@pytest.mark.unit
class TestExchangeFeature:
    """Tests for ExchangeFeature enumeration."""

    def test_funding_rates(self):
        """Should have FUNDING_RATES feature."""
        assert ExchangeFeature.FUNDING_RATES.value == "funding_rates"

    def test_leverage_adjustment(self):
        """Should have LEVERAGE_ADJUSTMENT feature."""
        assert ExchangeFeature.LEVERAGE_ADJUSTMENT.value == "leverage_adjustment"

    def test_stop_loss(self):
        """Should have STOP_LOSS feature."""
        assert ExchangeFeature.STOP_LOSS.value == "stop_loss"


# ── Test ExchangeCapabilities Model ───────────────────────────────────────


@pytest.mark.unit
class TestExchangeCapabilitiesModel:
    """Tests for ExchangeCapabilities model."""

    def test_hyperliquid_config(self):
        """Should have correct Hyperliquid configuration."""
        cap = EXCHANGE_CAPABILITIES["hyperliquid"]

        assert cap.id == "hyperliquid"
        assert cap.display_name == "Hyperliquid"
        assert AssetType.CRYPTO_PERP in cap.supported_assets
        assert cap.max_leverage == 50
        assert cap.ccxt_id == "hyperliquid"
        assert cap.settlement_currencies[AssetType.CRYPTO_PERP] == SettlementCurrency.USDC

    def test_binance_config(self):
        """Should have correct Binance configuration."""
        cap = EXCHANGE_CAPABILITIES["binance"]

        assert cap.id == "binance"
        assert cap.display_name == "Binance Futures"
        assert AssetType.CRYPTO_PERP in cap.supported_assets
        assert cap.max_leverage == 125
        assert cap.ccxt_id == "binanceusdm"
        assert cap.requires_passphrase is False

    def test_okx_config(self):
        """Should have correct OKX configuration."""
        cap = EXCHANGE_CAPABILITIES["okx"]

        assert cap.id == "okx"
        assert cap.requires_passphrase is True

    def test_all_exchanges_have_required_fields(self):
        """All exchanges should have required fields."""
        for exchange_id, cap in EXCHANGE_CAPABILITIES.items():
            assert cap.id == exchange_id
            assert cap.display_name
            assert cap.ccxt_id
            assert cap.max_leverage > 0
            assert len(cap.supported_assets) > 0


# ── Test get_exchange_capabilities ────────────────────────────────────────


@pytest.mark.unit
class TestGetExchangeCapabilities:
    """Tests for get_exchange_capabilities function."""

    def test_get_existing_exchange(self):
        """Should return capabilities for existing exchange."""
        cap = get_exchange_capabilities("hyperliquid")

        assert cap is not None
        assert cap.id == "hyperliquid"

    def test_get_exchange_case_insensitive(self):
        """Should handle case-insensitive lookup."""
        cap = get_exchange_capabilities("HYPERLIQUID")

        assert cap is not None
        assert cap.id == "hyperliquid"

    def test_get_nonexistent_exchange(self):
        """Should return None for nonexistent exchange."""
        cap = get_exchange_capabilities("nonexistent")

        assert cap is None


# ── Test get_all_exchanges ────────────────────────────────────────────────


@pytest.mark.unit
class TestGetAllExchanges:
    """Tests for get_all_exchanges function."""

    def test_returns_all_exchanges(self):
        """Should return all configured exchanges."""
        exchanges = get_all_exchanges()

        assert len(exchanges) == len(EXCHANGE_CAPABILITIES)
        assert all(isinstance(e, ExchangeCapabilities) for e in exchanges)


# ── Test get_active_exchanges ──────────────────────────────────────────────


@pytest.mark.unit
class TestGetActiveExchanges:
    """Tests for get_active_exchanges function."""

    def test_returns_active_only(self):
        """Should return only active exchanges."""
        exchanges = get_active_exchanges()

        assert all(e.is_active for e in exchanges)

    def test_all_configured_exchanges_are_active(self):
        """All configured exchanges should be active by default."""
        exchanges = get_active_exchanges()

        assert len(exchanges) == len(EXCHANGE_CAPABILITIES)


# ── Test get_exchanges_for_asset ──────────────────────────────────────────


@pytest.mark.unit
class TestGetExchangesForAsset:
    """Tests for get_exchanges_for_asset function."""

    def test_get_crypto_perp_exchanges(self):
        """Should return exchanges that support crypto perpetual."""
        exchanges = get_exchanges_for_asset(AssetType.CRYPTO_PERP)

        assert len(exchanges) > 0
        # All major exchanges should support perp
        exchange_ids = [e.id for e in exchanges]
        assert "hyperliquid" in exchange_ids
        assert "binance" in exchange_ids

    def test_get_crypto_spot_exchanges(self):
        """Should return exchanges that support crypto spot."""
        exchanges = get_exchanges_for_asset(AssetType.CRYPTO_SPOT)

        assert len(exchanges) > 0
        exchange_ids = [e.id for e in exchanges]
        assert "hyperliquid" in exchange_ids
        assert "binance" in exchange_ids

    def test_get_forex_exchanges(self):
        """Should return empty list for unsupported asset type."""
        exchanges = get_exchanges_for_asset(AssetType.FOREX)

        # No exchanges support forex yet
        assert exchanges == []


# ── Test get_settlement_currency ──────────────────────────────────────────


@pytest.mark.unit
class TestGetSettlementCurrency:
    """Tests for get_settlement_currency function."""

    def test_hyperliquid_perp_settlement(self):
        """Hyperliquid perp should use USDC."""
        currency = get_settlement_currency("hyperliquid", AssetType.CRYPTO_PERP)

        assert currency == SettlementCurrency.USDC

    def test_binance_perp_settlement(self):
        """Binance perp should use USDT."""
        currency = get_settlement_currency("binance", AssetType.CRYPTO_PERP)

        assert currency == SettlementCurrency.USDT

    def test_default_to_usdt_for_unknown_exchange(self):
        """Should default to USDT for unknown exchange."""
        currency = get_settlement_currency("unknown", AssetType.CRYPTO_PERP)

        assert currency == SettlementCurrency.USDT

    def test_default_to_exchange_default_for_unknown_asset(self):
        """Should use exchange default for unknown asset type."""
        currency = get_settlement_currency("hyperliquid", AssetType.FOREX)

        # Should fall back to Hyperliquid's default (USDC)
        assert currency == SettlementCurrency.USDC


# ── Test supports_asset ───────────────────────────────────────────────────


@pytest.mark.unit
class TestSupportsAsset:
    """Tests for supports_asset function."""

    def test_supports_crypto_perp(self):
        """Should return True for exchanges supporting crypto perp."""
        assert supports_asset("hyperliquid", AssetType.CRYPTO_PERP) is True
        assert supports_asset("binance", AssetType.CRYPTO_PERP) is True

    def test_supports_crypto_spot(self):
        """Should return True for exchanges supporting crypto spot."""
        assert supports_asset("hyperliquid", AssetType.CRYPTO_SPOT) is True
        assert supports_asset("binance", AssetType.CRYPTO_SPOT) is True

    def test_does_not_support_forex(self):
        """Should return False for forex on all exchanges."""
        assert supports_asset("hyperliquid", AssetType.FOREX) is False
        assert supports_asset("binance", AssetType.FOREX) is False

    def test_unknown_exchange_supports_nothing(self):
        """Should return False for unknown exchange."""
        assert supports_asset("unknown", AssetType.CRYPTO_PERP) is False


# ── Test get_ccxt_id ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetCcxtId:
    """Tests for get_ccxt_id function."""

    def test_hyperliquid_ccxt_id(self):
        """Should return correct CCXT ID for Hyperliquid."""
        assert get_ccxt_id("hyperliquid") == "hyperliquid"

    def test_binance_ccxt_id(self):
        """Should return correct CCXT ID for Binance."""
        assert get_ccxt_id("binance") == "binanceusdm"

    def test_okx_ccxt_id(self):
        """Should return correct CCXT ID for OKX."""
        assert get_ccxt_id("okx") == "okx"

    def test_kucoin_ccxt_id(self):
        """Should return correct CCXT ID for KuCoin."""
        assert get_ccxt_id("kucoin") == "kucoinfutures"

    def test_gate_ccxt_id(self):
        """Should return correct CCXT ID for Gate.io."""
        assert get_ccxt_id("gate") == "gateio"

    def test_unknown_exchange_fallback(self):
        """Should return exchange_id as fallback for unknown exchange."""
        assert get_ccxt_id("unknown") == "unknown"
