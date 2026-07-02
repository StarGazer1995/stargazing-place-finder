# -*- coding: utf-8 -*-
"""
Tests for gis_service.backends.overpass_backend request handling,
including retry, fallback, and exception coverage.
"""

from unittest.mock import patch

import pytest

# Ensure src is on path
import requests

from gis_service.backends.overpass_backend import OVERPASS_FALLBACK_URLS, OverpassBackend
from models import NetworkError


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
        """ConnectionError should be caught, retried, then raise NetworkError."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        backend = self._make_backend()

        with pytest.raises(NetworkError, match="all URLs exhausted"):
            backend._request("[out:json]; out;", "test")

        assert mock_post.call_count == 2  # max_retries=2

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_ssl_error_triggers_retry(self, mock_post):
        """SSLError should be caught, retried, then raise NetworkError."""
        mock_post.side_effect = requests.exceptions.SSLError("SSL handshake failed")
        backend = self._make_backend()

        with pytest.raises(NetworkError, match="all URLs exhausted"):
            backend._request("[out:json]; out;", "test")

        assert mock_post.call_count == 2

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_request_exception_triggers_retry(self, mock_post):
        """Generic RequestException should be caught, retried, then raise NetworkError."""
        mock_post.side_effect = requests.exceptions.RequestException("Something went wrong")
        backend = self._make_backend()

        with pytest.raises(NetworkError, match="all URLs exhausted"):
            backend._request("[out:json]; out;", "test")

        assert mock_post.call_count == 2

    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_request_exception_uses_fallback_url(self, mock_post):
        """After retries exhausted on primary, tries fallback then raises NetworkError."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        backend = self._make_backend_with_fallback()

        with pytest.raises(NetworkError, match="all URLs exhausted"):
            backend._request("[out:json]; out;", "test")

        # Main URL: 1 call, Fallback URL: 1 call = 2 total
        assert mock_post.call_count == 2


class TestOverpassTotalTimeout:
    """Test OverpassBackend._request total_timeout deadline check."""

    @patch("gis_service.backends.overpass_backend.time.sleep")
    @patch("gis_service.backends.overpass_backend.time.time")
    def test_total_timeout_raises_network_error(self, mock_time, mock_sleep):
        """When elapsed exceeds total_timeout, NetworkError is raised immediately."""
        # Provide many return values — logger.error also calls time.time()
        mock_time.side_effect = [0.0] + [999.0] * 20
        backend = OverpassBackend(
            url="https://fake-overpass.example/api",
            timeout=5,
            max_retries=3,
            total_timeout=1,
        )
        backend.urls = [backend.urls[0]]

        with pytest.raises(NetworkError, match="total timeout"):
            backend._request("[out:json];node;out;", "test")

    @patch("gis_service.backends.overpass_backend.time.sleep")
    @patch("gis_service.backends.overpass_backend.requests.post")
    def test_total_timeout_none_disables_deadline_check(self, mock_post, mock_sleep):
        """total_timeout=None skips the deadline check entirely."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        backend = OverpassBackend(
            url="https://fake-overpass.example/api",
            timeout=5,
            max_retries=2,
            total_timeout=None,
        )
        backend.urls = [backend.urls[0]]

        with pytest.raises(NetworkError, match="all URLs exhausted"):
            backend._request("[out:json];node;out;", "test")
