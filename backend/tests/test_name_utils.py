"""
Tests for Name Utilities.

Covers:
- parse_name_with_suffix: Parse name and extract suffix
- add_numeric_suffix: Add numeric suffix to name
- generate_unique_name: Async unique name generation
- generate_unique_name_sync: Sync unique name generation
"""

import pytest

from app.core.name_utils import (
    parse_name_with_suffix,
    add_numeric_suffix,
    generate_unique_name,
    generate_unique_name_sync,
)


# ── Test parse_name_with_suffix ─────────────────────────────────────────


@pytest.mark.unit
class TestParseNameWithSuffix:
    """Tests for parse_name_with_suffix function."""

    def test_no_suffix(self):
        """Should return original name and 0 when no suffix."""
        result = parse_name_with_suffix("BTC策略")
        assert result == ("BTC策略", 0)

    def test_with_suffix_1(self):
        """Should parse name with suffix 1."""
        result = parse_name_with_suffix("BTC策略-1")
        assert result == ("BTC策略", 1)

    def test_with_suffix_10(self):
        """Should parse name with suffix 10."""
        result = parse_name_with_suffix("My Strategy-10")
        assert result == ("My Strategy", 10)

    def test_with_large_suffix(self):
        """Should parse name with large suffix."""
        result = parse_name_with_suffix("Test-999")
        assert result == ("Test", 999)

    def test_english_name_no_suffix(self):
        """Should handle English names without suffix."""
        result = parse_name_with_suffix("MyStrategy")
        assert result == ("MyStrategy", 0)

    def test_empty_name(self):
        """Should handle empty name."""
        result = parse_name_with_suffix("")
        assert result == ("", 0)

    def test_only_dash(self):
        """Should handle name that is only dash."""
        result = parse_name_with_suffix("-")
        assert result == ("-", 0)

    def test_multiple_dashes(self):
        """Should only match last dash-number pattern."""
        result = parse_name_with_suffix("My-Test-5")
        assert result == ("My-Test", 5)


# ── Test add_numeric_suffix ─────────────────────────────────────────────


@pytest.mark.unit
class TestAddNumericSuffix:
    """Tests for add_numeric_suffix function."""

    def test_add_suffix_1(self):
        """Should add suffix 1."""
        result = add_numeric_suffix("BTC策略", 1)
        assert result == "BTC策略-1"

    def test_add_suffix_10(self):
        """Should add suffix 10."""
        result = add_numeric_suffix("Test", 10)
        assert result == "Test-10"

    def test_suffix_0_returns_original(self):
        """Should return original when suffix is 0."""
        result = add_numeric_suffix("BTC策略", 0)
        assert result == "BTC策略"

    def test_negative_suffix_returns_original(self):
        """Should return original when suffix is negative."""
        result = add_numeric_suffix("BTC策略", -1)
        assert result == "BTC策略"


# ── Test generate_unique_name_sync ──────────────────────────────────────


@pytest.mark.unit
class TestGenerateUniqueNameSync:
    """Tests for generate_unique_name_sync function."""

    def test_returns_original_if_available(self):
        """Should return original name if not taken."""
        def check_not_exists(name, user_id):
            return False

        result = generate_unique_name_sync(
            "BTC策略", "user-1", check_not_exists
        )
        assert result == "BTC策略"

    def test_adds_suffix_if_taken(self):
        """Should add suffix if original is taken."""
        existing = {"BTC策略"}

        def check_exists(name, user_id):
            return name in existing

        result = generate_unique_name_sync(
            "BTC策略", "user-1", check_exists
        )
        assert result == "BTC策略-1"

    def test_increments_suffix_until_available(self):
        """Should increment suffix until name is available."""
        existing = {"BTC策略", "BTC策略-1", "BTC策略-2"}

        def check_exists(name, user_id):
            return name in existing

        result = generate_unique_name_sync(
            "BTC策略", "user-1", check_exists
        )
        assert result == "BTC策略-3"

    def test_handles_name_with_existing_suffix(self):
        """Should handle names that already have suffix."""
        existing = {"Test-1"}

        def check_exists(name, user_id):
            return name in existing

        result = generate_unique_name_sync(
            "Test-1", "user-1", check_exists
        )
        # Should parse "Test-1" -> base="Test", then try Test-1 (taken), then Test-2
        assert result == "Test-2"

    def test_uses_timestamp_after_max_attempts(self):
        """Should use timestamp after max attempts."""
        # Create a check that always returns True (name always exists)
        def check_always_exists(name, user_id):
            return True

        result = generate_unique_name_sync(
            "Test", "user-1", check_always_exists, max_attempts=5
        )
        # Should have timestamp suffix
        assert result.startswith("Test-")
        # Timestamp should be a large number
        suffix = int(result.split("-")[-1])
        assert suffix > 1000000000  # Unix timestamp


# ── Test generate_unique_name (async) ────────────────────────────────────


@pytest.mark.unit
class TestGenerateUniqueName:
    """Tests for generate_unique_name async function."""

    @pytest.mark.asyncio
    async def test_returns_original_if_available(self):
        """Should return original name if not taken."""
        async def check_not_exists(name, user_id):
            return False

        result = await generate_unique_name(
            "BTC策略", "user-1", check_not_exists
        )
        assert result == "BTC策略"

    @pytest.mark.asyncio
    async def test_adds_suffix_if_taken(self):
        """Should add suffix if original is taken."""
        existing = {"BTC策略"}

        async def check_exists(name, user_id):
            return name in existing

        result = await generate_unique_name(
            "BTC策略", "user-1", check_exists
        )
        assert result == "BTC策略-1"

    @pytest.mark.asyncio
    async def test_increments_suffix_until_available(self):
        """Should increment suffix until name is available."""
        existing = {"BTC策略", "BTC策略-1", "BTC策略-2", "BTC策略-3"}

        async def check_exists(name, user_id):
            return name in existing

        result = await generate_unique_name(
            "BTC策略", "user-1", check_exists
        )
        assert result == "BTC策略-4"

    @pytest.mark.asyncio
    async def test_uses_timestamp_after_max_attempts(self):
        """Should use timestamp after max attempts."""
        async def check_always_exists(name, user_id):
            return True

        result = await generate_unique_name(
            "Test", "user-1", check_always_exists, max_attempts=5
        )
        # Should have timestamp suffix
        assert result.startswith("Test-")
        suffix = int(result.split("-")[-1])
        assert suffix > 1000000000  # Unix timestamp
