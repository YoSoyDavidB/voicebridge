"""Deepgram Speech-to-Text client using WebSocket streaming API.

Provides real-time transcription of Spanish audio to text with low latency.
"""

from __future__ import annotations

from typing import Optional

import asyncio
import json
import time
from typing import Any

import websockets

from voicebridge.core.exceptions import STTConnectionError, STTError
from voicebridge.core.models import TranscriptResult, VADResult


class DeepgramSTTClient:
    """Deepgram STT client with WebSocket streaming.

    Maintains persistent WebSocket connection to Deepgram for low-latency
    streaming transcription. Converts VADResult audio to Spanish text.
    """

    def __init__(
        self,
        api_key: str,
        language: str,
        model: str,
        sample_rate: int,
    ) -> None:
        """Initialize Deepgram STT client.

        Args:
            api_key: Deepgram API key
            language: Source language code (e.g., 'es' for Spanish)
            model: Model name (e.g., 'nova-2')
            sample_rate: Audio sample rate in Hz
        """
        self.api_key = api_key
        self.language = language
        self.model = model
        self.sample_rate = sample_rate

        # State
        self._ws: Any = None
        self._input_queue: Optional[asyncio.Queue[VADResult]] = None
        self._output_queue: Optional[asyncio.Queue[TranscriptResult]] = None
        self._sequence_number = 0
        self._is_running = False

    def set_input_queue(self, queue: asyncio.Queue[VADResult]) -> None:
        """Set the queue to read VAD results from.

        Args:
            queue: Input queue with VADResult objects
        """
        self._input_queue = queue

    def set_output_queue(self, queue: asyncio.Queue[TranscriptResult]) -> None:
        """Set the queue to push transcription results to.

        Args:
            queue: Output queue for TranscriptResult objects
        """
        self._output_queue = queue

    async def connect(self) -> None:
        """Establish WebSocket connection to Deepgram."""
        url = self._build_websocket_url()

        try:
            self._ws = await websockets.connect(
                url,
                additional_headers={"Authorization": f"Token {self.api_key}"},
            )
        except Exception as e:
            raise STTConnectionError(f"Failed to connect to Deepgram: {e}") from e

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def start(self) -> None:
        """Start the STT client processing loop."""
        if self._input_queue is None or self._output_queue is None:
            msg = "Input and output queues must be set before starting"
            raise RuntimeError(msg)

        self._is_running = True
        await self._process_loop()

    async def stop(self) -> None:
        """Stop the STT client."""
        self._is_running = False
        await self.disconnect()

    def _build_websocket_url(self) -> str:
        """Build Deepgram WebSocket URL with parameters.

        Returns:
            Complete WebSocket URL with query parameters
        """
        base_url = "wss://api.deepgram.com/v1/listen"

        params = [
            f"model={self.model}",
            f"language={self.language}",
            "encoding=linear16",
            f"sample_rate={self.sample_rate}",
            "channels=1",
            "punctuate=true",
            "smart_format=true",
            "interim_results=true",
            "endpointing=300",
            "utterance_end_ms=1000",
            "vad_events=true",
        ]

        return f"{base_url}?{'&'.join(params)}"

    async def _process_loop(self) -> None:
        """Main processing loop.

        Reads VADResult from input queue, sends audio to Deepgram,
        and emits TranscriptResult to output queue.
        """
        while self._is_running:
            if self._input_queue is None or self._output_queue is None:
                break

            try:
                # Get next VAD result
                vad_result = await asyncio.wait_for(
                    self._input_queue.get(),
                    timeout=0.1,
                )

                # Debug: Show we received audio
                print(f"[STT] 🎧 Received audio: {vad_result.duration_ms:.0f}ms")

                # Ensure connected
                if self._ws is None:
                    await self.connect()

                # Send audio to Deepgram
                start_time = time.monotonic()
                await self._ws.send(vad_result.audio_data)

                # Receive response
                response_text = await self._ws.recv()
                response = json.loads(response_text)

                # Parse and forward result
                transcript = self._parse_deepgram_response(response, start_time)
                if transcript is not None:
                    print(f"[STT] 📝 Transcript: \"{transcript.text}\" (confidence={transcript.confidence:.2f})")
                    await self._output_queue.put(transcript)

            except asyncio.TimeoutError:
                # No VAD results available, continue
                continue
            except Exception as e:
                raise STTError(f"Error processing audio: {e}") from e

    def _parse_deepgram_response(
        self,
        response: dict[str, Any],
        start_time: float,
    ) -> TranscriptResult | None:
        """Parse Deepgram WebSocket response.

        Args:
            response: JSON response from Deepgram
            start_time: Timestamp when audio was sent

        Returns:
            TranscriptResult if valid transcript, None otherwise
        """
        if response.get("type") != "Results":
            return None

        # Only process final results
        is_final = response.get("is_final", False)
        if not is_final:
            return None

        # Extract transcript
        channel = response.get("channel", {})
        alternatives = channel.get("alternatives", [])

        if not alternatives:
            return None

        best_alternative = alternatives[0]
        text = best_alternative.get("transcript", "").strip()
        confidence = best_alternative.get("confidence", 0.0)

        # Ignore empty transcripts
        if not text:
            return None

        # Calculate latency
        end_time = time.monotonic()
        latency_ms = (end_time - start_time) * 1000.0

        result = TranscriptResult(
            text=text,
            is_final=True,
            confidence=confidence,
            start_timestamp_ms=0.0,  # Will be set by orchestrator
            processing_latency_ms=latency_ms,
            language=self.language,
            words=None,  # Could extract word-level timing if needed
            sequence_number=self._sequence_number,
        )

        self._sequence_number += 1

        return result
