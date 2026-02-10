"""
Tests for app.core.errors module.

Covers ErrorCode, AppError, sanitize_error_message,
log_and_raise_http_error, create_http_exception,
and pre-built error helpers.
"""

from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException, status

from app.core.errors import (
    AppError,
    ErrorCode,
    ai_service_error,
    backtest_failed_error,
    create_http_exception,
    exchange_api_error,
    exchange_connection_error,
    internal_error,
    log_and_raise_http_error,
    sanitize_error_message,
)


# ======================== ErrorCode ========================

class TestErrorCode:
    def test_auth_codes(self):
        assert ErrorCode.AUTH_INVALID_TOKEN == "AUTH_INVALID_TOKEN"
        assert ErrorCode.AUTH_TOKEN_EXPIRED == "AUTH_TOKEN_EXPIRED"
        assert ErrorCode.AUTH_TOKEN_REVOKED == "AUTH_TOKEN_REVOKED"
        assert ErrorCode.AUTH_INVALID_CREDENTIALS == "AUTH_INVALID_CREDENTIALS"

    def test_exchange_codes(self):
        assert ErrorCode.EXCHANGE_ERROR == "EXCHANGE_ERROR"
        assert ErrorCode.EXCHANGE_CONNECTION_FAILED == "EXCHANGE_CONNECTION_FAILED"

    def test_all_codes_are_strings(self):
        for code in ErrorCode:
            assert isinstance(code.value, str)

    def test_total_count(self):
        # There should be at least 15 error codes
        assert len(ErrorCode) >= 15


# ======================== AppError ========================

class TestAppError:
    def test_basic_creation(self):
        err = AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Something went wrong",
        )
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.message == "Something went wrong"
        assert err.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert err.details == {}
        assert err.internal_message is None

    def test_with_all_fields(self):
        err = AppError(
            code=ErrorCode.EXCHANGE_ERROR,
            message="Exchange error",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"exchange": "binance"},
            internal_message="Connection refused at 10.0.0.1:443",
        )
        assert err.status_code == 502
        assert err.details == {"exchange": "binance"}
        assert err.internal_message == "Connection refused at 10.0.0.1:443"

    def test_is_exception(self):
        err = AppError(code=ErrorCode.INTERNAL_ERROR, message="test")
        assert isinstance(err, Exception)
        assert str(err) == "test"


# ======================== sanitize_error_message ========================

class TestSanitizeErrorMessage:
    def _mock_settings(self, env):
        mock = MagicMock()
        mock.environment = env
        return mock

    def test_production_returns_user_message(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("production")):
            result = sanitize_error_message(
                ValueError("secret details"),
                user_message="An error occurred",
            )
            assert result == "An error occurred"
            assert "secret details" not in result

    def test_development_returns_error_string(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            result = sanitize_error_message(
                ValueError("detailed error info"),
            )
            assert result == "detailed error info"

    def test_development_with_type(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            result = sanitize_error_message(
                ValueError("oops"),
                include_type=True,
            )
            assert result == "ValueError: oops"

    def test_staging_includes_details(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("staging")):
            result = sanitize_error_message(
                RuntimeError("debug info"),
            )
            assert result == "debug info"


# ======================== log_and_raise_http_error ========================

class TestLogAndRaiseHttpError:
    def _mock_settings(self, env):
        mock = MagicMock()
        mock.environment = env
        return mock

    def test_raises_http_exception(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_http_error(
                    ValueError("test error"),
                    ErrorCode.INTERNAL_ERROR,
                    "Something failed",
                )
            assert exc_info.value.status_code == 500
            assert "Something failed" in exc_info.value.detail

    def test_production_sanitizes(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("production")):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_http_error(
                    ValueError("sensitive stuff"),
                    ErrorCode.INTERNAL_ERROR,
                    "An error occurred",
                )
            assert exc_info.value.detail == "An error occurred"
            assert "sensitive stuff" not in exc_info.value.detail

    def test_custom_status_code(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            with pytest.raises(HTTPException) as exc_info:
                log_and_raise_http_error(
                    ValueError("bad"),
                    ErrorCode.VALIDATION_ERROR,
                    "Validation failed",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            assert exc_info.value.status_code == 422

    def test_logs_error(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            with patch("app.core.errors.logger") as mock_logger:
                with pytest.raises(HTTPException):
                    log_and_raise_http_error(
                        ValueError("err"),
                        ErrorCode.INTERNAL_ERROR,
                        "fail",
                        log_level="error",
                    )
                mock_logger.error.assert_called_once()


# ======================== create_http_exception ========================

class TestCreateHttpException:
    def _mock_settings(self, env):
        mock = MagicMock()
        mock.environment = env
        return mock

    def test_basic_creation(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            exc = create_http_exception(
                ErrorCode.INTERNAL_ERROR,
                "Something went wrong",
            )
            assert isinstance(exc, HTTPException)
            assert exc.status_code == 500
            assert exc.detail == "Something went wrong"

    def test_with_internal_error_dev(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            exc = create_http_exception(
                ErrorCode.EXCHANGE_ERROR,
                "Exchange failed",
                internal_error=ConnectionError("timeout"),
            )
            assert "timeout" in exc.detail

    def test_with_internal_error_prod(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("production")):
            exc = create_http_exception(
                ErrorCode.EXCHANGE_ERROR,
                "Exchange failed",
                internal_error=ConnectionError("timeout at 10.0.0.1"),
            )
            assert exc.detail == "Exchange failed"
            assert "10.0.0.1" not in exc.detail

    def test_no_log(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            with patch("app.core.errors.logger") as mock_logger:
                create_http_exception(
                    ErrorCode.INTERNAL_ERROR,
                    "test",
                    log_error=False,
                )
                mock_logger.error.assert_not_called()

    def test_log_with_internal_error(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            with patch("app.core.errors.logger") as mock_logger:
                create_http_exception(
                    ErrorCode.INTERNAL_ERROR,
                    "test",
                    internal_error=ValueError("detail"),
                    log_error=True,
                )
                mock_logger.error.assert_called_once()

    def test_log_without_internal_error(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            with patch("app.core.errors.logger") as mock_logger:
                create_http_exception(
                    ErrorCode.INTERNAL_ERROR,
                    "plain error",
                    log_error=True,
                )
                mock_logger.error.assert_called_once()


# ======================== Pre-built Error Helpers ========================

class TestPrebuiltErrors:
    def _mock_settings(self, env="development"):
        mock = MagicMock()
        mock.environment = env
        return mock

    def test_backtest_failed_error(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = backtest_failed_error(RuntimeError("bad data"))
            assert isinstance(exc, HTTPException)
            assert exc.status_code == 500
            assert "Backtest" in exc.detail

    def test_exchange_connection_error_with_exchange(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = exchange_connection_error(ConnectionError("refused"), exchange="binance")
            assert exc.status_code == 502
            assert "binance" in exc.detail

    def test_exchange_connection_error_without_exchange(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = exchange_connection_error(ConnectionError("refused"))
            assert exc.status_code == 502
            assert "connect to exchange" in exc.detail

    def test_exchange_api_error_with_operation(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = exchange_api_error(RuntimeError("rate limited"), operation="get_balance")
            assert exc.status_code == 502
            assert "get_balance" in exc.detail

    def test_exchange_api_error_without_operation(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = exchange_api_error(RuntimeError("err"))
            assert exc.status_code == 502

    def test_exchange_api_error_with_trade_error_auth(self):
        """Test exchange_api_error with TradeError AUTH_ERROR code"""
        from app.traders.base import TradeError
        
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            trade_error = TradeError(
                message="binanceusdm authentication failed: Invalid API key",
                code="AUTH_ERROR"
            )
            exc = exchange_api_error(trade_error, operation="connection test")
            assert exc.status_code == 502
            assert "认证失败" in exc.detail
            assert "connection test" in exc.detail
            assert "API Key" in exc.detail
            # In development, should include detailed error message
            assert "Invalid API key" in exc.detail

    def test_exchange_api_error_with_trade_error_auth_production(self):
        """Test exchange_api_error with TradeError AUTH_ERROR code in production"""
        from app.traders.base import TradeError
        
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("production")):
            trade_error = TradeError(
                message="binanceusdm authentication failed: Invalid API key",
                code="AUTH_ERROR"
            )
            exc = exchange_api_error(trade_error, operation="connection test")
            assert exc.status_code == 502
            assert "认证失败" in exc.detail
            assert "API Key" in exc.detail
            # In production, should not include detailed error message
            assert "Invalid API key" not in exc.detail

    def test_exchange_api_error_with_trade_error_exchange_error(self):
        """Test exchange_api_error with TradeError EXCHANGE_ERROR code"""
        from app.traders.base import TradeError
        
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            trade_error = TradeError(
                message="binanceusdm exchange error: Rate limit exceeded",
                code="EXCHANGE_ERROR"
            )
            exc = exchange_api_error(trade_error, operation="connection test")
            assert exc.status_code == 502
            assert "交易所 API 错误" in exc.detail
            assert "connection test" in exc.detail
            # In development, should include detailed error message
            assert "Rate limit exceeded" in exc.detail

    def test_exchange_api_error_with_trade_error_exchange_error_production(self):
        """Test exchange_api_error with TradeError EXCHANGE_ERROR code in production"""
        from app.traders.base import TradeError
        
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("production")):
            trade_error = TradeError(
                message="binanceusdm exchange error: Rate limit exceeded",
                code="EXCHANGE_ERROR"
            )
            exc = exchange_api_error(trade_error, operation="connection test")
            assert exc.status_code == 502
            assert "交易所 API 错误" in exc.detail
            # In production, should not include detailed error message
            assert "Rate limit exceeded" not in exc.detail
            assert "请稍后重试" in exc.detail

    def test_exchange_api_error_with_trade_error_no_code(self):
        """Test exchange_api_error with TradeError without code"""
        from app.traders.base import TradeError
        
        with patch("app.core.errors.get_settings", return_value=self._mock_settings("development")):
            trade_error = TradeError(
                message="Some trading error occurred"
            )
            exc = exchange_api_error(trade_error, operation="connection test")
            assert exc.status_code == 502
            assert "交易所 API 错误" in exc.detail
            # In development, should include detailed error message
            assert "Some trading error occurred" in exc.detail

    def test_ai_service_error(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = ai_service_error(TimeoutError("timeout"))
            assert exc.status_code == 503
            assert "AI service" in exc.detail

    def test_internal_error_with_context(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = internal_error(RuntimeError("oops"), context="user_creation")
            assert exc.status_code == 500
            assert "user_creation" in exc.detail

    def test_internal_error_without_context(self):
        with patch("app.core.errors.get_settings", return_value=self._mock_settings()):
            exc = internal_error(RuntimeError("oops"))
            assert exc.status_code == 500
            assert "internal error" in exc.detail.lower()
