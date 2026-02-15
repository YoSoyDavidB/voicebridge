"""Tests for WebSocket endpoint."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from voicebridge.web.app import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestWebSocketEndpoint:
    """Test WebSocket endpoint functionality."""

    def test_websocket_connection(self, client: TestClient) -> None:
        """Test WebSocket connection and message handling.

        This test:
        1. Connects to /ws endpoint
        2. Sends a config message
        3. Receives and verifies the status response
        """
        with client.websocket_connect("/ws") as websocket:
            # Send config message
            config_message = {
                "type": "config",
                "apiKeys": {
                    "openai": "test-api-key"
                }
            }
            websocket.send_text(json.dumps(config_message))

            # Receive and verify status response
            response = websocket.receive_text()
            response_data = json.loads(response)

            assert response_data["type"] == "status"
            assert response_data["state"] == "ready"
            assert "message" in response_data
