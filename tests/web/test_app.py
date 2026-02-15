"""Tests for FastAPI application."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from voicebridge.web.app import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestStaticFileServing:
    """Test static file serving functionality."""

    def test_serve_index_html_at_root(self, client: TestClient) -> None:
        """Test that index.html is served at root path '/'."""
        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "VoiceBridge" in response.text
        assert "<!DOCTYPE html>" in response.text

    def test_serve_static_css_file(self, client: TestClient) -> None:
        """Test that static CSS files are served correctly."""
        response = client.get("/static/css/styles.css")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/css")
        assert "body" in response.text


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_healthy(self, client: TestClient) -> None:
        """Test that /health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
