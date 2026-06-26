"""Tests for Sentry tracing utilities."""

import os
from unittest.mock import MagicMock, patch

import pytest

from backend.obs.tracing import (
    capture_exception_with_context,
    init_sentry,
    traced_span,
    traced_span_context,
)


@pytest.fixture(autouse=True)
def reset_sentry_state():
    """Reset Sentry initialization state before each test."""
    from backend.obs import tracing
    tracing._sentry_initialized = False
    yield
    tracing._sentry_initialized = False


def test_init_sentry_with_dsn():
    """Test init_sentry initializes Sentry when DSN is present."""
    with patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"}):
        with patch("backend.obs.tracing.sentry_sdk.init") as mock_init:
            init_sentry()
            mock_init.assert_called_once()
            call_args = mock_init.call_args
            assert call_args[1]["dsn"] == "https://test@sentry.io/123"
            assert call_args[1]["traces_sample_rate"] == 1.0


def test_init_sentry_without_dsn():
    """Test init_sentry is no-op when DSN is missing."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("backend.obs.tracing.sentry_sdk.init") as mock_init:
            init_sentry()
            mock_init.assert_not_called()


def test_init_sentry_with_empty_dsn():
    """Test init_sentry is no-op when DSN is empty string."""
    with patch.dict(os.environ, {"SENTRY_DSN": ""}):
        with patch("backend.obs.tracing.sentry_sdk.init") as mock_init:
            init_sentry()
            mock_init.assert_not_called()


def test_init_sentry_idempotent():
    """Test init_sentry only initializes once."""
    with patch.dict(os.environ, {"SENTRY_DSN": "https://test@sentry.io/123"}):
        with patch("backend.obs.tracing.sentry_sdk.init") as mock_init:
            init_sentry()
            init_sentry()
            init_sentry()
            mock_init.assert_called_once()


def test_traced_span_with_sentry_initialized():
    """Test traced_span decorator calls start_span when Sentry is initialized."""
    from backend.obs import tracing
    tracing._sentry_initialized = True
    
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    
    with patch("backend.obs.tracing.start_span", return_value=mock_span) as mock_start_span:
        @traced_span("test.operation", key="value")
        def test_func(x):
            return x * 2
        
        result = test_func(5)
        assert result == 10
        mock_start_span.assert_called_once_with(op="test.operation")
        mock_span.set_data.assert_called_once_with("key", "value")


def test_traced_span_without_sentry_initialized():
    """Test traced_span decorator is no-op when Sentry is not initialized."""
    from backend.obs import tracing
    tracing._sentry_initialized = False
    
    with patch("backend.obs.tracing.start_span") as mock_start_span:
        @traced_span("test.operation", key="value")
        def test_func(x):
            return x * 2
        
        result = test_func(5)
        assert result == 10
        mock_start_span.assert_not_called()


def test_traced_span_context_with_sentry_initialized():
    """Test traced_span_context calls start_span when Sentry is initialized."""
    from backend.obs import tracing
    tracing._sentry_initialized = True
    
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    
    with patch("backend.obs.tracing.start_span", return_value=mock_span) as mock_start_span:
        with traced_span_context("test.context", url="https://example.com"):
            pass
        
        mock_start_span.assert_called_once_with(op="test.context")
        mock_span.set_data.assert_called_once_with("url", "https://example.com")


def test_traced_span_context_without_sentry_initialized():
    """Test traced_span_context is no-op when Sentry is not initialized."""
    from backend.obs import tracing
    tracing._sentry_initialized = False
    
    with patch("backend.obs.tracing.start_span") as mock_start_span:
        with traced_span_context("test.context", url="https://example.com"):
            pass
        
        mock_start_span.assert_not_called()


def test_capture_exception_with_context_with_sentry_initialized():
    """Test capture_exception_with_context calls Sentry when initialized."""
    from backend.obs import tracing
    tracing._sentry_initialized = True
    
    test_error = ValueError("test error")
    
    with patch("backend.obs.tracing.sentry_sdk.push_scope") as mock_push_scope:
        with patch("backend.obs.tracing.sentry_sdk.capture_exception") as mock_capture:
            mock_push_scope.return_value.__enter__.return_value = MagicMock()
            
            capture_exception_with_context(test_error, function="test_func", key="value")
            
            mock_push_scope.assert_called_once()
            scope_instance = mock_push_scope.return_value.__enter__.return_value
            scope_instance.set_extra.assert_any_call("function", "test_func")
            scope_instance.set_extra.assert_any_call("key", "value")
            mock_capture.assert_called_once_with(test_error)


def test_capture_exception_with_context_without_sentry_initialized():
    """Test capture_exception_with_context is no-op when Sentry is not initialized."""
    from backend.obs import tracing
    tracing._sentry_initialized = False
    
    test_error = ValueError("test error")
    
    with patch("backend.obs.tracing.sentry_sdk.push_scope") as mock_push_scope:
        with patch("backend.obs.tracing.sentry_sdk.capture_exception") as mock_capture:
            capture_exception_with_context(test_error, function="test_func", key="value")
            
            mock_push_scope.assert_not_called()
            mock_capture.assert_not_called()


def test_missing_sentry_dsn_does_not_crash():
    """Test that missing SENTRY_DSN does not cause crashes in usage."""
    with patch.dict(os.environ, {}, clear=True):
        init_sentry()
        
        @traced_span("test.operation")
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
        
        with traced_span_context("test.context"):
            pass
        
        capture_exception_with_context(ValueError("test"))
