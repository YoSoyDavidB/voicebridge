"""Audio output component for writing synthesized audio to output device.

Receives TTSAudioResult from TTS service and writes to virtual audio device
for Microsoft Teams to capture.
"""

from __future__ import annotations

from typing import Optional

import asyncio
import numpy as np
import sounddevice as sd

from voicebridge.core.models import TTSAudioResult


class AudioDevice:
    """Audio device information."""

    def __init__(self, name: str, index: int, max_output_channels: int) -> None:
        """Initialize audio device info.

        Args:
            name: Device name
            index: Device index
            max_output_channels: Maximum output channels
        """
        self.name = name
        self.index = index
        self.max_output_channels = max_output_channels


class AudioOutput:
    """Audio output component.

    Writes synthesized audio from TTS service to virtual audio device
    for Microsoft Teams to capture as microphone input.
    """

    def __init__(
        self,
        sample_rate: int,
        channels: int,
        dtype: str,
        device_id: Optional[int],
        buffer_size_ms: int,
    ) -> None:
        """Initialize AudioOutput.

        Args:
            sample_rate: Output sample rate in Hz
            channels: Number of audio channels (1 = mono, 2 = stereo)
            dtype: Data type (e.g., 'int16', 'float32')
            device_id: Output device ID (None = default device)
            buffer_size_ms: Output buffer size in milliseconds
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.device_id = device_id
        self.buffer_size_ms = buffer_size_ms

        # Calculate buffer size in samples
        self._buffer_size_samples = int((buffer_size_ms / 1000.0) * sample_rate)

        # State
        self._input_queue: Optional[asyncio.Queue[TTSAudioResult]] = None
        self._stream: Optional[sd.OutputStream] = None
        self._is_running = False

    def set_input_queue(self, queue: asyncio.Queue[TTSAudioResult]) -> None:
        """Set the queue to read audio results from.

        Args:
            queue: Input queue with TTSAudioResult objects
        """
        self._input_queue = queue

    def set_output_device(self, device_id: int) -> None:
        """Set the output device ID.

        Args:
            device_id: Device ID to use for output
        """
        self.device_id = device_id

    def get_available_devices(self) -> list[AudioDevice]:
        """Get list of available audio output devices.

        Returns:
            List of AudioDevice objects
        """
        devices = sd.query_devices()
        output_devices = []

        if isinstance(devices, dict):
            # Single device
            devices = [devices]

        for idx, device in enumerate(devices):
            if device["max_output_channels"] > 0:
                output_devices.append(
                    AudioDevice(
                        name=device["name"],
                        index=idx,
                        max_output_channels=device["max_output_channels"],
                    )
                )

        return output_devices

    async def start(self) -> None:
        """Start the audio output processing loop."""
        if self._input_queue is None:
            msg = "Input queue must be set before starting"
            raise RuntimeError(msg)

        self._is_running = True

        # Open output stream
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=self.dtype,
            device=self.device_id,
            blocksize=self._buffer_size_samples,
        )
        self._stream.start()

        # Process audio
        await self._process_loop()

    async def stop(self) -> None:
        """Stop the audio output."""
        self._is_running = False

        # Close stream
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    async def _process_loop(self) -> None:
        """Main processing loop.

        Reads TTSAudioResult from input queue and writes to output device.
        """
        while self._is_running:
            if self._input_queue is None:
                break

            try:
                # Get next audio result
                audio_result = await asyncio.wait_for(
                    self._input_queue.get(),
                    timeout=0.1,
                )

                # Debug: Show we received audio
                print(f"[Output] 🔈 Playing audio chunk ({len(audio_result.audio_data)} bytes)")

                # Write audio to output stream
                await self._write_audio(audio_result)

            except asyncio.TimeoutError:
                # No audio available, continue
                continue
            except Exception as e:
                # Log error but continue
                print(f"Error writing audio: {e}")
                continue

    async def _write_audio(self, audio_result: TTSAudioResult) -> None:
        """Write audio data to output stream.

        Args:
            audio_result: TTS audio result to write
        """
        if self._stream is None:
            return

        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_result.audio_data, dtype=np.int16)

        # Reshape for channels if needed
        if self.channels == 1:
            # Mono - audio_array is already correct shape
            pass
        else:
            # Stereo - reshape
            audio_array = audio_array.reshape(-1, self.channels)

        # Write to stream (blocking, so run in thread)
        await asyncio.to_thread(self._stream.write, audio_array)
