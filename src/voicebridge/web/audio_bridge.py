"""Audio bridge between Web Audio API and VoiceBridge pipeline.

Handles conversion between base64-encoded web audio and AudioChunk format.
"""

from __future__ import annotations

import base64

from voicebridge.core.models import AudioChunk


class WebAudioBridge:
    """Bridge for converting between Web Audio API format and AudioChunk format.

    Handles:
    - Decoding base64-encoded PCM audio from browser → AudioChunk
    - Encoding pipeline PCM audio → base64 for browser playback

    Args:
        sample_rate: Audio sample rate in Hz (default: 16000)
        channels: Number of audio channels (default: 1 for mono)
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1) -> None:
        """Initialize WebAudioBridge.

        Args:
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._sequence_counter = 0

    def decode_web_audio(self, base64_audio: str, timestamp_ms: float) -> AudioChunk:
        """Decode base64 web audio to AudioChunk.

        Args:
            base64_audio: Base64-encoded PCM audio data from browser
            timestamp_ms: Timestamp when audio was captured in milliseconds

        Returns:
            AudioChunk object ready for pipeline processing

        Note:
            PCM format: 16-bit samples = 2 bytes per sample
            Duration calculation: (num_samples / sample_rate) * 1000 = duration_ms
        """
        # Decode base64 to raw PCM bytes
        pcm_data = base64.b64decode(base64_audio)

        # Calculate number of samples and duration
        # 16-bit PCM = 2 bytes per sample
        bytes_per_sample = 2
        num_samples = len(pcm_data) // (bytes_per_sample * self.channels)
        duration_ms = (num_samples / self.sample_rate) * 1000

        # Create AudioChunk
        chunk = AudioChunk(
            data=pcm_data,
            timestamp_ms=timestamp_ms,
            sample_rate=self.sample_rate,
            channels=self.channels,
            duration_ms=duration_ms,
            sequence_number=self._sequence_counter,
        )

        # Increment sequence counter
        self._sequence_counter += 1

        return chunk

    def encode_output_audio(self, pcm_data: bytes) -> str:
        """Encode pipeline PCM audio to base64 for browser playback.

        Args:
            pcm_data: Raw PCM audio bytes from pipeline (TTS output)

        Returns:
            Base64-encoded string ready to send to browser

        Note:
            The browser will decode this and play it through Web Audio API
        """
        return base64.b64encode(pcm_data).decode('utf-8')
