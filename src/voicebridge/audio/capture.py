"""Audio capture from physical microphone using sounddevice.

Captures raw PCM audio in small chunks (typically 30ms) and pushes them
to an asyncio queue for processing by the VAD component.
"""

from __future__ import annotations

from typing import Optional

import asyncio
import queue
import time
from typing import Any

import sounddevice as sd

from voicebridge.core.models import AudioChunk


class AudioCapture:
    """Capture audio from physical microphone.

    Uses sounddevice (PortAudio) for cross-platform audio capture.
    Runs audio callback in a separate thread and safely pushes chunks
    to an asyncio queue using call_soon_threadsafe.
    """

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        chunk_duration_ms: int,
        device_id: Optional[int] = None,
    ) -> None:
        """Initialize audio capture.

        Args:
            sample_rate: Audio sample rate in Hz (e.g., 16000)
            channels: Number of audio channels (1 = mono)
            chunk_duration_ms: Duration of each audio chunk in milliseconds
            device_id: Input device ID (None = system default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration_ms = chunk_duration_ms
        self.device_id = device_id

        # Calculate chunk size in samples
        self._chunk_size = int(sample_rate * chunk_duration_ms / 1000)

        # State
        self._stream: Optional[sd.RawInputStream] = None
        self._output_queue: Optional[asyncio.Queue[AudioChunk]] = None
        self._thread_queue: queue.Queue[AudioChunk] = queue.Queue(maxsize=500)
        self._sequence_number = 0
        self._stop_event: Optional[asyncio.Event] = None

    def set_output_queue(self, queue: asyncio.Queue[AudioChunk]) -> None:
        """Set the queue where captured audio chunks will be pushed.

        Args:
            queue: asyncio.Queue to receive AudioChunk objects
        """
        self._output_queue = queue

    def get_available_devices(self) -> list[dict[str, Any]]:
        """List all available audio input devices.

        Returns:
            List of device info dictionaries with name, index, etc.
        """
        devices = sd.query_devices()
        if isinstance(devices, dict):
            return [devices]
        return list(devices)

    def set_device(self, device_id: int) -> None:
        """Set the input device to use for capture.

        Args:
            device_id: Device index from get_available_devices()
        """
        self.device_id = device_id

    async def start(self) -> None:
        """Start capturing audio from the microphone.

        Opens a RawInputStream and begins pushing AudioChunk objects
        to the output queue.
        """
        if self._output_queue is None:
            msg = "Output queue must be set before starting capture"
            raise RuntimeError(msg)

        # Create stop event
        self._stop_event = asyncio.Event()

        # Reset sequence number
        self._sequence_number = 0

        # Create stream
        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=self._chunk_size,
            device=self.device_id,
            callback=self._audio_callback,
        )

        # Start stream
        self._stream.start()
        print(f"[Capture] 🎙️  Audio capture started (device: {self.device_id or 'default'}, sample_rate: {self.sample_rate}Hz)")

        # Run bridge loop (transfers from thread queue to async queue)
        await self._bridge_queues()

    async def stop(self) -> None:
        """Stop capturing audio and release the device."""
        # Signal stop
        if self._stop_event:
            self._stop_event.set()

        # Stop stream
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    async def _bridge_queues(self) -> None:
        """Bridge between thread-safe queue and async queue.

        Reads from thread queue (populated by audio callback) and
        writes to async queue (consumed by VAD).

        This runs as the main loop for the capture task.
        """
        bridged_count = 0
        while not self._stop_event.is_set():
            try:
                # Try to get from thread queue (non-blocking)
                chunk = self._thread_queue.get_nowait()
                # Put into async queue
                await self._output_queue.put(chunk)
                bridged_count += 1
                # Debug: removed for performance
            except queue.Empty:
                # No chunks available, sleep briefly
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"[Capture] ⚠️  Bridge error: {e}")
                await asyncio.sleep(0.1)

    def _audio_callback(
        self,
        indata: bytes,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        """Audio callback (runs in separate thread).

        Called by PortAudio when new audio data is available.
        Pushes AudioChunk to thread-safe queue.

        Args:
            indata: Raw PCM audio bytes
            frames: Number of frames captured
            time_info: Timing information from PortAudio
            status: Stream status flags
        """
        # Get current monotonic time (in seconds)
        timestamp_s = time.monotonic()

        # Create AudioChunk
        chunk = self._create_audio_chunk(indata, timestamp_s)

        # Push to thread-safe queue (non-blocking)
        try:
            self._thread_queue.put_nowait(chunk)
        except queue.Full:
            # Queue full, drop chunk (expected for real-time audio)
            pass

    def _create_audio_chunk(self, data: bytes, timestamp_s: float) -> AudioChunk:
        """Create an AudioChunk from raw audio data.

        Args:
            data: Raw PCM audio bytes
            timestamp_s: Timestamp in seconds (monotonic)

        Returns:
            AudioChunk with all metadata filled in
        """
        chunk = AudioChunk(
            data=data,
            timestamp_ms=timestamp_s * 1000.0,  # Convert to milliseconds
            sample_rate=self.sample_rate,
            channels=self.channels,
            duration_ms=float(self.chunk_duration_ms),
            sequence_number=self._sequence_number,
        )

        self._sequence_number += 1

        return chunk
