# -*- coding: utf-8 -*-
"""
Tests for gis_service.backends.overpass_backend request handling,
including retry, fallback, and exception coverage.
"""

from unittest.mock import patch

# Ensure src is on path
import requests

from gis_service.backends.overpass_backend import OVERPASS_FALLBACK_URLS, OverpassBackend


class TestOverpassRequestExceptionHandling:
    """Test that OverpassBackend._request handles various RequestException types."""

    def _make_backend(self):
        backend = OverpassBackend(
            url="https://fake-overpass.example/api",
            fallback_urls=OVERPASS_FALLBACK_URLS,
            timeout=5,
            max_retries=2,
        )
        backend.urls = [backend.urls[0]]  # Only use the main URL for retry tests
        return backend

    def _make_backend_with_fallback(self):
        return OverpassBackend(
            url="https://fake-overpass.example/api",
            fallback_urls=["https://fake-fallback.example/api"],
            timeout=5,
            max_retries=1,
        )

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_connection_error_triggers_retry(self, mock_post):
        """ConnectionError should be caught and retried."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        backend = self._make_backend()

        result = backend._request("[out:json]; out;", "test")

        assert result == []
        assert mock_post.call_count == 2  # max_retries=2

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_ssl_error_triggers_retry(self, mock_post):
        """SSLError should be caught and retried."""
        mock_post.side_effect = requests.exceptions.SSLError("SSL handshake failed")
        backend = self._make_backend()

        result = backend._request("[out:json]; out;", "test")

        assert result == []
        assert mock_post.call_count == 2

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_request_exception_triggers_retry(self, mock_post):
        """Generic RequestException should be caught and retried."""
        mock_post.side_effect = requests.exceptions.RequestException("Something went wrong")
        backend = self._make_backend()

        result = backend._request("[out:json]; out;", "test")

        assert result == []
        assert mock_post.call_count == 2

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_request_exception_uses_fallback_url(self, mock_post):
        """After retries exhausted, should try fallback URL."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        backend = self._make_backend_with_fallback()

        result = backend._request("[out:json]; out;", "test")

        assert result == []
        # Main URL: 1 retry (= 1 call), Fallback URL: 1 retry (= 1 call) = 2 total
        assert mock_post.call_count == 2
