"""Tests for STT (Speech-to-Text) client."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from voicebridge.core.models import TranscriptResult, VADResult
from voicebridge.services.stt.deepgram_client import DeepgramSTTClient


class TestDeepgramSTTClientInitialization:
    """Test DeepgramSTTClient initialization."""

    def test_creation_with_config(self) -> None:
        """STT client should be creatable with configuration."""
        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        assert client.api_key == "test_key"
        assert client.language == "es"
        assert client.model == "nova-2"
        assert client.sample_rate == 16000


class TestDeepgramSTTClientConnection:
    """Test WebSocket connection management."""

    @pytest.mark.asyncio
    async def test_connect_establishes_websocket(self) -> None:
        """Should establish WebSocket connection to Deepgram."""
        mock_ws = MagicMock()

        with patch("voicebridge.services.stt.deepgram_client.websockets.connect") as mock_connect:
            # Make connect return a coroutine that resolves to mock_ws
            mock_connect.return_value = mock_ws

            async def fake_connect(*args, **kwargs):
                return mock_ws

            mock_connect.side_effect = fake_connect

            client = DeepgramSTTClient(
                api_key="test_key",
                language="es",
                model="nova-2",
                sample_rate=16000,
            )

            await client.connect()

            # Should have called websockets.connect
            mock_connect.assert_called_once()
            assert mock_connect.call_args.kwargs.get("additional_headers") == {
                "Authorization": "Token test_key",
            }
            assert client._ws is not None

    @pytest.mark.asyncio
    async def test_disconnect_closes_websocket(self) -> None:
        """Should close WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.close = AsyncMock()

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )
        client._ws = mock_ws

        await client.disconnect()

        mock_ws.close.assert_called_once()
        assert client._ws is None


class TestDeepgramSTTClientTranscription:
    """Test transcription functionality."""

    @pytest.mark.asyncio
    async def test_parses_final_transcript(self) -> None:
        """Should emit TranscriptResult for final transcripts."""
        mock_ws = AsyncMock()

        # Simulate Deepgram response
        deepgram_response = {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "hola mundo",
                        "confidence": 0.95,
                    }
                ]
            },
        }

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )
        client._ws = mock_ws

        # Parse response
        result = client._parse_deepgram_response(deepgram_response, start_time=0.0)

        assert result is not None
        assert result.text == "hola mundo"
        assert result.is_final is True
        assert result.confidence == 0.95
        assert result.language == "es"

    @pytest.mark.asyncio
    async def test_ignores_interim_results(self) -> None:
        """Should not forward interim (non-final) transcripts."""
        deepgram_response = {
            "type": "Results",
            "is_final": False,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "hola",
                        "confidence": 0.5,
                    }
                ]
            },
        }

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        # Parse response - should return None for interim results
        result = client._parse_deepgram_response(deepgram_response, start_time=0.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_empty_transcript(self) -> None:
        """Should not forward empty/whitespace-only transcripts."""
        deepgram_response = {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "   ",
                        "confidence": 0.9,
                    }
                ]
            },
        }

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        result = client._parse_deepgram_response(deepgram_response, start_time=0.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_emits_transcript_after_interim_results(self) -> None:
        """Should keep reading until a final transcript is received."""
        mock_ws = AsyncMock()

        interim_response = {
            "type": "Results",
            "is_final": False,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "hola",
                        "confidence": 0.4,
                    }
                ]
            },
        }

        final_response = {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "hola mundo",
                        "confidence": 0.95,
                    }
                ]
            },
        }

        mock_ws.recv = AsyncMock(side_effect=[
            json.dumps(interim_response),
            json.dumps(final_response),
        ])

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )
        client._ws = mock_ws

        input_queue: asyncio.Queue[VADResult] = asyncio.Queue()
        output_queue: asyncio.Queue[TranscriptResult] = asyncio.Queue()
        client.set_input_queue(input_queue)
        client.set_output_queue(output_queue)

        vad_result = VADResult(
            audio_data=b"\x00" * 3200,
            start_timestamp_ms=0.0,
            end_timestamp_ms=100.0,
            duration_ms=100.0,
            confidence=0.9,
            is_partial=False,
            sequence_number=0,
        )

        await input_queue.put(vad_result)

        client._is_running = True
        task = asyncio.create_task(client._process_loop())

        result = await asyncio.wait_for(output_queue.get(), timeout=1.0)

        client._is_running = False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        assert result.text == "hola mundo"

    @pytest.mark.asyncio
    async def test_sends_close_stream_after_audio(self) -> None:
        """Should send CloseStream after audio to finalize transcript."""
        mock_ws = AsyncMock()

        final_response = {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "hola mundo",
                        "confidence": 0.95,
                    }
                ]
            },
        }

        mock_ws.recv = AsyncMock(side_effect=[json.dumps(final_response)])

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )
        client._ws = mock_ws

        input_queue: asyncio.Queue[VADResult] = asyncio.Queue()
        output_queue: asyncio.Queue[TranscriptResult] = asyncio.Queue()
        client.set_input_queue(input_queue)
        client.set_output_queue(output_queue)

        vad_result = VADResult(
            audio_data=b"\x00" * 3200,
            start_timestamp_ms=0.0,
            end_timestamp_ms=100.0,
            duration_ms=100.0,
            confidence=0.9,
            is_partial=False,
            sequence_number=0,
        )

        await input_queue.put(vad_result)

        client._is_running = True
        task = asyncio.create_task(client._process_loop())

        result = await asyncio.wait_for(output_queue.get(), timeout=1.0)

        client._is_running = False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        assert result.text == "hola mundo"

        mock_ws.send.assert_any_call(vad_result.audio_data)
        mock_ws.send.assert_any_call(json.dumps({"type": "CloseStream"}))

    @pytest.mark.asyncio
    async def test_final_transcript_timeout(self) -> None:
        """Should return None when no final transcript arrives in time."""
        mock_ws = AsyncMock()

        async def slow_recv() -> str:
            await asyncio.sleep(0.05)
            return json.dumps({"type": "Results", "is_final": False})

        mock_ws.recv = AsyncMock(side_effect=slow_recv)

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
            finalization_timeout_s=0.01,
        )
        client._ws = mock_ws

        result = await client._receive_final_transcript(start_time=0.0)

        assert result is None

    @pytest.mark.asyncio
    async def test_final_transcript_timeout_with_interim_flood(self) -> None:
        """Should timeout even if interim results keep arriving."""
        mock_ws = AsyncMock()

        interim_response = {
            "type": "Results",
            "is_final": False,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "hola",
                        "confidence": 0.4,
                    }
                ]
            },
        }

        async def recv_forever():
            return json.dumps(interim_response)

        mock_ws.recv = AsyncMock(side_effect=recv_forever)

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
            finalization_timeout_s=0.01,
        )
        client._ws = mock_ws

        result = await asyncio.wait_for(
            client._receive_final_transcript(start_time=0.0),
            timeout=0.05,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_receive_error_resets_connection(self) -> None:
        """Should reset connection on receive errors."""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=RuntimeError("boom"))

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
            finalization_timeout_s=0.01,
        )
        client._ws = mock_ws

        result = await client._receive_final_transcript(start_time=0.0)

        assert result is None
        assert client._ws is None

class TestDeepgramSTTClientQueue:
    """Test queue management."""

    @pytest.mark.asyncio
    async def test_set_input_queue(self) -> None:
        """Should allow setting input queue."""
        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        queue: asyncio.Queue[VADResult] = asyncio.Queue()
        client.set_input_queue(queue)

        assert client._input_queue is queue

    @pytest.mark.asyncio
    async def test_set_output_queue(self) -> None:
        """Should allow setting output queue."""
        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        queue: asyncio.Queue[TranscriptResult] = asyncio.Queue()
        client.set_output_queue(queue)

        assert client._output_queue is queue


class TestDeepgramSTTClientURL:
    """Test WebSocket URL construction."""

    def test_builds_correct_url(self) -> None:
        """Should build correct WebSocket URL with parameters."""
        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        url = client._build_websocket_url()

        assert "wss://api.deepgram.com/v1/listen" in url
        assert "model=nova-2" in url
        assert "language=es" in url
        assert "encoding=linear16" in url
        assert "sample_rate=16000" in url
        assert "channels=1" in url


class TestDeepgramSTTClientLatency:
    """Test latency tracking."""

    @pytest.mark.asyncio
    async def test_tracks_latency(self) -> None:
        """Should calculate processing_latency_ms correctly."""
        deepgram_response = {
            "type": "Results",
            "is_final": True,
            "speech_final": True,
            "channel": {
                "alternatives": [
                    {
                        "transcript": "test",
                        "confidence": 0.9,
                    }
                ]
            },
        }

        client = DeepgramSTTClient(
            api_key="test_key",
            language="es",
            model="nova-2",
            sample_rate=16000,
        )

        # Simulate 100ms processing time
        import time
        start_time = time.monotonic()
        time.sleep(0.1)

        result = client._parse_deepgram_response(deepgram_response, start_time=start_time)

        assert result is not None
        assert result.processing_latency_ms >= 100.0
