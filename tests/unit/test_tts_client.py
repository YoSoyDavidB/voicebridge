"""Tests for TTS (Text-to-Speech) client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voicebridge.core.models import TTSAudioResult, TranslationResult
from voicebridge.services.tts.elevenlabs_client import ElevenLabsTTSClient


class TestElevenLabsTTSClientInitialization:
    """Test ElevenLabsTTSClient initialization."""

    def test_creation_with_config(self) -> None:
        """TTS client should be creatable with configuration."""
        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        assert client.api_key == "test_key"
        assert client.voice_id == "test_voice_id"
        assert client.model == "eleven_turbo_v2_5"
        assert client.stability == 0.5
        assert client.similarity_boost == 0.8
        assert client.optimize_streaming_latency == 3
        assert client.output_sample_rate == 24000


class TestElevenLabsTTSClientConnection:
    """Test WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_connect_establishes_websocket(self) -> None:
        """Should establish WebSocket connection to ElevenLabs."""
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()

        with patch("voicebridge.services.tts.elevenlabs_client.websockets.connect") as mock_connect:
            # Make connect return a coroutine that resolves to mock_ws
            async def fake_connect(*args, **kwargs):
                return mock_ws

            mock_connect.side_effect = fake_connect

            client = ElevenLabsTTSClient(
                api_key="test_key",
                voice_id="test_voice_id",
                model="eleven_turbo_v2_5",
                stability=0.5,
                similarity_boost=0.8,
                optimize_streaming_latency=3,
                output_sample_rate=24000,
            )

            await client.connect()

            # Should have called websockets.connect
            mock_connect.assert_called_once()
            assert mock_connect.call_args.kwargs.get("additional_headers") == {
                "xi-api-key": "test_key",
            }
            assert client._ws is not None

    @pytest.mark.asyncio
    async def test_disconnect_closes_websocket(self) -> None:
        """Should close WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )
        client._ws = mock_ws

        await client.disconnect()

        mock_ws.close.assert_called_once()
        assert client._ws is None


class TestElevenLabsTTSClientSynthesis:
    """Test speech synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesizes_english_text(self) -> None:
        """Should produce audio from English text input."""
        import base64

        mock_ws = AsyncMock()

        # Simulate ElevenLabs audio response (base64 encoded)
        mock_audio_data = b"fake_audio_chunk"
        mock_audio_base64 = base64.b64encode(mock_audio_data).decode("utf-8")
        mock_response = {
            "audio": mock_audio_base64,
            "isFinal": False,
        }

        async def fake_recv():
            import json
            return json.dumps(mock_response)

        mock_ws.recv = fake_recv

        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )
        client._ws = mock_ws

        # Parse response
        result = await client._parse_elevenlabs_response(mock_response, start_time=0.0)

        assert result is not None
        assert result.audio_data == mock_audio_data
        assert result.sample_rate == 24000
        assert result.channels == 1
        assert result.is_final is False

    @pytest.mark.asyncio
    async def test_handles_final_audio_chunk(self) -> None:
        """Should recognize final audio chunk from ElevenLabs."""
        import base64

        mock_audio_data = b"final_chunk"
        mock_response = {
            "audio": base64.b64encode(mock_audio_data).decode("utf-8"),
            "isFinal": True,
        }

        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        result = await client._parse_elevenlabs_response(mock_response, start_time=0.0)

        assert result is not None
        assert result.is_final is True

    @pytest.mark.asyncio
    async def test_handles_empty_audio(self) -> None:
        """Should not forward empty audio chunks."""
        mock_response = {
            "audio": b"",
            "isFinal": False,
        }

        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        result = await client._parse_elevenlabs_response(mock_response, start_time=0.0)

        assert result is None


class TestElevenLabsTTSClientQueue:
    """Test queue management."""

    @pytest.mark.asyncio
    async def test_set_input_queue(self) -> None:
        """Should allow setting input queue."""
        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        queue: asyncio.Queue[TranslationResult] = asyncio.Queue()
        client.set_input_queue(queue)

        assert client._input_queue is queue

    @pytest.mark.asyncio
    async def test_set_output_queue(self) -> None:
        """Should allow setting output queue."""
        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        queue: asyncio.Queue[TTSAudioResult] = asyncio.Queue()
        client.set_output_queue(queue)

        assert client._output_queue is queue


class TestElevenLabsTTSClientURL:
    """Test WebSocket URL construction."""

    def test_builds_correct_url(self) -> None:
        """Should build correct WebSocket URL with parameters."""
        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        url = client._build_websocket_url()

        assert "wss://api.elevenlabs.io/v1/text-to-speech/test_voice_id/stream-input" in url
        assert "model_id=eleven_turbo_v2_5" in url
        assert "optimize_streaming_latency=3" in url
        assert "output_format=pcm_24000" in url


class TestElevenLabsTTSClientLatency:
    """Test latency tracking."""

    @pytest.mark.asyncio
    async def test_tracks_latency(self) -> None:
        """Should calculate processing_latency_ms correctly."""
        import base64
        import time

        mock_audio_data = b"audio_data"
        mock_response = {
            "audio": base64.b64encode(mock_audio_data).decode("utf-8"),
            "isFinal": False,
        }

        client = ElevenLabsTTSClient(
            api_key="test_key",
            voice_id="test_voice_id",
            model="eleven_turbo_v2_5",
            stability=0.5,
            similarity_boost=0.8,
            optimize_streaming_latency=3,
            output_sample_rate=24000,
        )

        # Simulate 50ms processing time
        start_time = time.monotonic()
        time.sleep(0.05)

        result = await client._parse_elevenlabs_response(mock_response, start_time=start_time)

        assert result is not None
        assert result.processing_latency_ms >= 50.0
