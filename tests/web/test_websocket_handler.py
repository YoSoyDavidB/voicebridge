"""Tests for WebSocket message handler."""

from __future__ import annotations

import json

import pytest

from voicebridge.web.audio_bridge import WebAudioBridge
from voicebridge.web.websocket_handler import WebSocketHandler


class TestWebSocketHandler:
    """Test suite for WebSocket message handler."""

    @pytest.fixture
    def bridge(self) -> WebAudioBridge:
        """Create WebAudioBridge instance."""
        return WebAudioBridge(sample_rate=16000, channels=1)

    @pytest.fixture
    def handler(self, bridge: WebAudioBridge) -> WebSocketHandler:
        """Create WebSocketHandler instance."""
        return WebSocketHandler(bridge)

    @pytest.mark.asyncio
    async def test_handle_config_message(self, handler: WebSocketHandler):
        """Test config message handling and status response."""
        # Arrange
        config_message = json.dumps({
            "type": "config",
            "apiKeys": {
                "deepgram": "test-deepgram-key",
                "openai": "test-openai-key",
                "elevenlabs": "test-elevenlabs-key",
                "voiceId": "test-voice-id"
            }
        })

        # Act
        response = await handler.handle_message(config_message)

        # Assert
        assert response is not None
        response_data = json.loads(response)
        assert response_data["type"] == "status"
        assert response_data["state"] == "ready"
        assert "configured" in response_data["message"].lower()

        # Verify config was stored
        assert handler._config is not None
        assert handler._config["apiKeys"]["deepgram"] == "test-deepgram-key"
        assert handler._config["apiKeys"]["openai"] == "test-openai-key"

    @pytest.mark.asyncio
    async def test_handle_audio_message(self, handler: WebSocketHandler):
        """Test audio message handling (requires config first)."""
        # Arrange - First send config
        config_message = json.dumps({
            "type": "config",
            "apiKeys": {
                "deepgram": "test-deepgram-key",
                "openai": "test-openai-key",
                "elevenlabs": "test-elevenlabs-key",
                "voiceId": "test-voice-id"
            }
        })
        await handler.handle_message(config_message)

        # Create base64-encoded audio data (simple test data)
        import base64
        import struct
        samples = [100 * i for i in range(480)]  # 480 samples = ~30ms @ 16kHz
        pcm_data = b''.join(struct.pack('<h', sample % 32768) for sample in samples)
        base64_audio = base64.b64encode(pcm_data).decode('utf-8')

        audio_message = json.dumps({
            "type": "audio",
            "audio": base64_audio,
            "timestamp": 1234.5
        })

        # Act
        response = await handler.handle_message(audio_message)

        # Assert
        # Audio messages return None (responses come separately from pipeline)
        assert response is None
