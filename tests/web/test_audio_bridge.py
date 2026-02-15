"""Tests for WebAudioBridge format conversion."""

from __future__ import annotations

import base64
import struct

import pytest

from voicebridge.core.models import AudioChunk
from voicebridge.web.audio_bridge import WebAudioBridge


class TestWebAudioBridge:
    """Test suite for WebAudioBridge format conversion."""

    @pytest.fixture
    def bridge(self) -> WebAudioBridge:
        """Create WebAudioBridge instance."""
        return WebAudioBridge(sample_rate=16000, channels=1)

    @pytest.fixture
    def sample_pcm_data(self) -> bytes:
        """Create sample PCM data (480 samples = 960 bytes = ~30ms @ 16kHz).

        Using 16-bit PCM: 2 bytes per sample.
        Duration: (480 samples / 16000 Hz) * 1000 = 30ms
        """
        # Create 480 samples of 16-bit PCM data
        samples = [i % 1000 for i in range(480)]
        pcm_data = b''.join(struct.pack('<h', sample) for sample in samples)
        assert len(pcm_data) == 960  # 480 samples * 2 bytes
        return pcm_data

    def test_decode_web_audio(self, bridge: WebAudioBridge, sample_pcm_data: bytes):
        """Test converting base64 web audio to AudioChunk."""
        # Arrange
        base64_audio = base64.b64encode(sample_pcm_data).decode('utf-8')
        timestamp_ms = 1234.5

        # Act
        chunk = bridge.decode_web_audio(base64_audio, timestamp_ms)

        # Assert
        assert isinstance(chunk, AudioChunk)
        assert chunk.data == sample_pcm_data
        assert chunk.timestamp_ms == timestamp_ms
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1
        assert chunk.duration_ms == pytest.approx(30.0, rel=0.01)  # ~30ms
        assert chunk.sequence_number == 0  # First chunk

    def test_encode_output_audio(self, bridge: WebAudioBridge, sample_pcm_data: bytes):
        """Test converting pipeline audio to base64."""
        # Act
        base64_audio = bridge.encode_output_audio(sample_pcm_data)

        # Assert
        assert isinstance(base64_audio, str)

        # Verify round-trip conversion
        decoded = base64.b64decode(base64_audio)
        assert decoded == sample_pcm_data
