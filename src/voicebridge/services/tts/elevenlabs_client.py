"""ElevenLabs Text-to-Speech client using WebSocket streaming API.

Provides real-time synthesis of English text to speech using ElevenLabs voice cloning.
"""

from __future__ import annotations

from typing import Optional

import asyncio
import base64
import json
import time
from typing import Any

import websockets

from voicebridge.core.exceptions import TTSConnectionError, TTSError
from voicebridge.core.models import TTSAudioResult, TranslationResult


class ElevenLabsTTSClient:
    """ElevenLabs TTS client with WebSocket streaming.

    Maintains persistent WebSocket connection to ElevenLabs for low-latency
    streaming synthesis. Converts English text to cloned voice audio.
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model: str,
        stability: float,
        similarity_boost: float,
        optimize_streaming_latency: int,
        output_sample_rate: int,
    ) -> None:
        """Initialize ElevenLabs TTS client.

        Args:
            api_key: ElevenLabs API key
            voice_id: Voice ID for cloned voice
            model: Model name (e.g., 'eleven_turbo_v2_5')
            stability: Voice stability (0.0-1.0, higher = more stable)
            similarity_boost: Voice similarity boost (0.0-1.0)
            optimize_streaming_latency: Latency optimization level (0-4)
            output_sample_rate: Output audio sample rate in Hz
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.optimize_streaming_latency = optimize_streaming_latency
        self.output_sample_rate = output_sample_rate

        # State
        self._ws: Any = None
        self._input_queue: Optional[asyncio.Queue[TranslationResult]] = None
        self._output_queue: Optional[asyncio.Queue[TTSAudioResult]] = None
        self._sequence_number = 0
        self._is_running = False

    def set_input_queue(self, queue: asyncio.Queue[TranslationResult]) -> None:
        """Set the queue to read translation results from.

        Args:
            queue: Input queue with TranslationResult objects
        """
        self._input_queue = queue

    def set_output_queue(self, queue: asyncio.Queue[TTSAudioResult]) -> None:
        """Set the queue to push TTS audio results to.

        Args:
            queue: Output queue for TTSAudioResult objects
        """
        self._output_queue = queue

    async def connect(self) -> None:
        """Establish WebSocket connection to ElevenLabs."""
        url = self._build_websocket_url()

        try:
            self._ws = await websockets.connect(url)

            # Send initial configuration
            config_message = {
                "text": " ",
                "voice_settings": {
                    "stability": self.stability,
                    "similarity_boost": self.similarity_boost,
                },
                "generation_config": {
                    "chunk_length_schedule": [120, 160, 250, 290],
                },
            }
            await self._ws.send(json.dumps(config_message))

        except Exception as e:
            raise TTSConnectionError(f"Failed to connect to ElevenLabs: {e}") from e

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def start(self) -> None:
        """Start the TTS client processing loop."""
        if self._input_queue is None or self._output_queue is None:
            msg = "Input and output queues must be set before starting"
            raise RuntimeError(msg)

        self._is_running = True
        await self._process_loop()

    async def stop(self) -> None:
        """Stop the TTS client."""
        self._is_running = False
        await self.disconnect()

    def _build_websocket_url(self) -> str:
        """Build ElevenLabs WebSocket URL with parameters.

        Returns:
            Complete WebSocket URL with query parameters
        """
        base_url = f"wss://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream-input"

        params = [
            f"model_id={self.model}",
            f"optimize_streaming_latency={self.optimize_streaming_latency}",
            f"output_format=pcm_{self.output_sample_rate}",
        ]

        return f"{base_url}?{'&'.join(params)}"

    async def _process_loop(self) -> None:
        """Main processing loop.

        Reads TranslationResult from input queue, sends text to ElevenLabs,
        and emits TTSAudioResult to output queue.
        """
        while self._is_running:
            if self._input_queue is None or self._output_queue is None:
                break

            try:
                # Get next translation
                translation = await asyncio.wait_for(
                    self._input_queue.get(),
                    timeout=0.1,
                )

                # Debug: Show we received translation
                print(f"[TTS] 🔊 Generating audio: \"{translation.translated_text}\"")

                # Ensure connected
                if self._ws is None:
                    await self.connect()

                # Send text to ElevenLabs
                start_time = time.monotonic()
                text_message = {
                    "text": translation.translated_text,
                    "try_trigger_generation": True,
                }
                await self._ws.send(json.dumps(text_message))

                # Receive and forward audio chunks
                while True:
                    response_text = await self._ws.recv()
                    response = json.loads(response_text)

                    # Parse and forward audio result
                    audio_result = await self._parse_elevenlabs_response(response, start_time)
                    if audio_result is not None:
                        await self._output_queue.put(audio_result)

                    # Stop receiving if final chunk
                    if response.get("isFinal", False):
                        print(f"[TTS] ✅ Audio generation complete")
                        break

            except asyncio.TimeoutError:
                # No translations available, continue
                continue
            except Exception as e:
                raise TTSError(f"Error synthesizing audio: {e}") from e

    async def _parse_elevenlabs_response(
        self,
        response: dict[str, Any],
        start_time: float,
    ) -> TTSAudioResult | None:
        """Parse ElevenLabs WebSocket response.

        Args:
            response: JSON response from ElevenLabs
            start_time: Timestamp when text was sent

        Returns:
            TTSAudioResult if valid audio, None otherwise
        """
        # Extract audio data (base64 encoded)
        audio_base64 = response.get("audio", "")
        if not audio_base64:
            return None

        # Decode audio
        audio_data = base64.b64decode(audio_base64)
        if not audio_data:
            return None

        # Check if final chunk
        is_final = response.get("isFinal", False)

        # Calculate latency
        end_time = time.monotonic()
        latency_ms = (end_time - start_time) * 1000.0

        result = TTSAudioResult(
            audio_data=audio_data,
            sample_rate=self.output_sample_rate,
            channels=1,  # ElevenLabs outputs mono
            is_final=is_final,
            start_timestamp_ms=0.0,  # Will be set by orchestrator
            processing_latency_ms=latency_ms,
            sequence_number=self._sequence_number,
        )

        self._sequence_number += 1

        return result
