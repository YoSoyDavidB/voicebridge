"""Voice Activity Detection (VAD) processor using Silero VAD.

Detects speech segments in audio stream and groups continuous speech
into utterances for transcription.
"""

from __future__ import annotations

from typing import Optional

import asyncio
import time
from asyncio import QueueEmpty
from typing import Any

import numpy as np
import torch

from voicebridge.core.models import AudioChunk, VADResult


class VADProcessor:
    """Voice Activity Detection processor.

    Uses Silero VAD model to detect speech in audio chunks and group
    continuous speech into utterances. Critical for low latency by
    detecting end of speech quickly.
    """

    def __init__(
        self,
        sample_rate: int,
        threshold: float,
        min_speech_duration_ms: int,
        min_silence_duration_ms: int,
        speech_pad_ms: int,
        max_utterance_duration_ms: int,
        model: Optional[Any] = None,
    ) -> None:
        """Initialize VAD processor.

        Args:
            sample_rate: Audio sample rate (must be 16000 for Silero)
            threshold: Speech probability threshold (0.0-1.0)
            min_speech_duration_ms: Minimum speech duration to consider
            min_silence_duration_ms: Silence duration to end utterance
            speech_pad_ms: Padding to add around speech segments
            max_utterance_duration_ms: Maximum utterance before force-split
            model: Optional pre-loaded VAD model (for testing)
        """
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.max_utterance_duration_ms = max_utterance_duration_ms

        # State
        self._input_queue: Optional[asyncio.Queue[AudioChunk]] = None
        self._output_queue: Optional[asyncio.Queue[VADResult]] = None
        self._speech_buffer: list[AudioChunk] = []
        self._speech_probabilities: list[float] = []
        self._speech_start_ms: float = 0.0
        self._silence_duration_ms: float = 0.0
        self._sequence_number = 0
        self._is_running = False

        # Load or use provided model
        self._model = model if model is not None else self._load_vad_model()

    def _load_vad_model(self) -> Any:
        """Load Silero VAD model from torch hub.

        Returns:
            Loaded VAD model
        """
        model_and_utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        model = model_and_utils[0]  # type: ignore[index]
        model.eval()
        return model

    def set_input_queue(self, queue: asyncio.Queue[AudioChunk]) -> None:
        """Set the queue to read audio chunks from.

        Args:
            queue: asyncio.Queue with AudioChunk objects
        """
        self._input_queue = queue

    def set_output_queue(self, queue: asyncio.Queue[VADResult]) -> None:
        """Set the queue to push VAD results to.

        Args:
            queue: Output queue for VADResult objects
        """
        self._output_queue = queue

    async def start(self) -> None:
        """Start the VAD processor."""
        if self._input_queue is None or self._output_queue is None:
            msg = "Input and output queues must be set before starting"
            raise RuntimeError(msg)

        self._is_running = True
        await self._process_loop()

    async def stop(self) -> None:
        """Stop the VAD processor."""
        self._is_running = False

    async def _process_loop(self) -> None:
        """Main processing loop.

        Reads audio chunks from input queue, detects speech,
        and emits VADResult objects to output queue.
        """
        print(f"[VAD] 🔄 Processing loop started (threshold: {self.threshold:.2f})")
        chunk_count = 0
        timeout_count = 0

        while self._is_running:
            if self._input_queue is None or self._output_queue is None:
                break

            try:
                # Try to get chunk without blocking
                chunk = self._input_queue.get_nowait()

                chunk_count += 1

                # Detect speech
                is_speech = self._is_speech(chunk)

                # Debug: Show speech detection
                if is_speech and len(self._speech_buffer) == 0:
                    print(f"[VAD] 🎤 Speech started")

                if is_speech:
                    # Add to speech buffer
                    self._add_speech_chunk(chunk)
                    self._silence_duration_ms = 0.0

                    # Check if we need to force-emit (max duration)
                    if self._should_force_emit(chunk.timestamp_ms):
                        result = self._create_vad_result(is_partial=True)
                        await self._output_queue.put(result)
                        self._reset_buffer()
                else:
                    # Accumulate silence
                    self._silence_duration_ms += chunk.duration_ms

                    # Check if we should emit utterance
                    if self._should_emit_utterance():
                        result = self._create_vad_result(is_partial=False)
                        print(f"[VAD] ✅ Utterance complete: {len(self._speech_buffer)} chunks, {result.duration_ms:.0f}ms, confidence={result.confidence:.2f}")
                        await self._output_queue.put(result)
                        self._reset_buffer()

            except QueueEmpty:
                # No chunks available, sleep briefly and continue
                await asyncio.sleep(0.01)  # 10ms
                continue

    def _is_speech(self, chunk: AudioChunk) -> bool:
        """Detect if audio chunk contains speech.

        Args:
            chunk: Audio chunk to analyze

        Returns:
            True if speech detected, False otherwise
        """
        # Convert bytes to numpy array
        audio_array = np.frombuffer(chunk.data, dtype=np.int16)

        # Pad short chunks to satisfy Silero minimum length (~512 samples @ 16kHz)
        min_samples = int(self.sample_rate / 31.25)
        if audio_array.size < min_samples:
            pad_width = min_samples - audio_array.size
            audio_array = np.pad(audio_array, (0, pad_width), mode="constant")

        # Convert to float32 and normalize to [-1, 1]
        audio_float = audio_array.astype(np.float32) / 32768.0

        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio_float)

        # Run VAD model
        with torch.no_grad():
            result = self._model(audio_tensor, self.sample_rate)
            # Handle both tensor and float (for mocking)
            speech_prob = result.item() if hasattr(result, "item") else float(result)

        # Store probability
        self._speech_probabilities.append(speech_prob)

        # Debug: removed for performance

        # Compare against threshold
        return speech_prob >= self.threshold

    def _add_speech_chunk(self, chunk: AudioChunk) -> None:
        """Add speech chunk to buffer.

        Args:
            chunk: Speech audio chunk
        """
        if len(self._speech_buffer) == 0:
            self._speech_start_ms = chunk.timestamp_ms

        self._speech_buffer.append(chunk)

    def _should_emit_utterance(self) -> bool:
        """Check if we should emit accumulated speech as utterance.

        Returns:
            True if should emit, False otherwise
        """
        # Need speech in buffer
        if len(self._speech_buffer) == 0:
            return False

        # Check if silence duration exceeds threshold
        if self._silence_duration_ms < self.min_silence_duration_ms:
            return False

        # Check if speech duration meets minimum
        start_ms = self._speech_buffer[0].timestamp_ms
        end_ms = self._speech_buffer[-1].timestamp_ms + self._speech_buffer[-1].duration_ms
        duration_ms = end_ms - start_ms
        return duration_ms >= self.min_speech_duration_ms

    def _should_force_emit(self, current_timestamp_ms: float) -> bool:
        """Check if we should force-emit due to max duration.

        Args:
            current_timestamp_ms: Current timestamp

        Returns:
            True if should force-emit, False otherwise
        """
        if len(self._speech_buffer) == 0:
            return False

        duration_ms = current_timestamp_ms - self._speech_start_ms
        return duration_ms >= self.max_utterance_duration_ms

    def _create_vad_result(self, is_partial: bool) -> VADResult:
        """Create VADResult from accumulated speech buffer.

        Args:
            is_partial: Whether this is a partial result (force-split)

        Returns:
            VADResult with concatenated audio
        """
        # Concatenate all audio data
        audio_bytes = b"".join(chunk.data for chunk in self._speech_buffer)

        # Append trailing silence for final utterances to help STT finalization
        if not is_partial:
            silence_samples = int(self.sample_rate * (self.min_silence_duration_ms / 1000.0))
            if silence_samples > 0:
                audio_bytes += b"\x00\x00" * silence_samples

        # Calculate timestamps
        start_ms = self._speech_buffer[0].timestamp_ms
        end_ms = self._speech_buffer[-1].timestamp_ms + self._speech_buffer[-1].duration_ms
        if not is_partial:
            end_ms += self.min_silence_duration_ms
        duration_ms = end_ms - start_ms

        # Calculate average confidence
        avg_confidence = (
            sum(self._speech_probabilities) / len(self._speech_probabilities)
            if self._speech_probabilities
            else 0.0
        )

        result = VADResult(
            audio_data=audio_bytes,
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms,
            duration_ms=duration_ms,
            confidence=avg_confidence,
            is_partial=is_partial,
            sequence_number=self._sequence_number,
        )

        self._sequence_number += 1

        return result

    def _reset_buffer(self) -> None:
        """Reset speech buffer and state."""
        self._speech_buffer = []
        self._speech_probabilities = []
        self._silence_duration_ms = 0.0
