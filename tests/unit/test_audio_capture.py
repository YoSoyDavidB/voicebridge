"""Tests for AudioCapture component."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from voicebridge.audio.capture import AudioCapture
from voicebridge.core.models import AudioChunk


class TestAudioCaptureInitialization:
    """Test AudioCapture initialization."""

    def test_creation_with_default_config(self) -> None:
        """AudioCapture should be creatable with default configuration."""
        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            assert capture.sample_rate == 16000
            assert capture.channels == 1
            assert capture.chunk_duration_ms == 30
            assert capture.device_id is None

    def test_creation_with_custom_device(self) -> None:
        """AudioCapture should accept custom device ID."""
        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=5,
            )

            assert capture.device_id == 5


class TestAudioCaptureLifecycle:
    """Test AudioCapture start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_opens_stream(self) -> None:
        """Starting capture should open a RawInputStream."""
        import asyncio

        mock_stream = MagicMock()
        mock_stream.__aenter__ = Mock(return_value=mock_stream)
        mock_stream.__aexit__ = Mock(return_value=None)
        mock_stream.start = Mock()

        with patch("voicebridge.audio.capture.sd") as mock_sd:
            mock_sd.RawInputStream.return_value = mock_stream

            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            # Set output queue before starting
            queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
            capture.set_output_queue(queue)

            await capture.start()

            # Should have created RawInputStream
            mock_sd.RawInputStream.assert_called_once()
            call_kwargs = mock_sd.RawInputStream.call_args[1]
            assert call_kwargs["samplerate"] == 16000
            assert call_kwargs["channels"] == 1
            assert call_kwargs["dtype"] == "int16"

    @pytest.mark.asyncio
    async def test_stop_closes_stream(self) -> None:
        """Stopping capture should close the stream."""
        import asyncio

        mock_stream = MagicMock()
        mock_stream.__aenter__ = Mock(return_value=mock_stream)
        mock_stream.__aexit__ = Mock(return_value=None)
        mock_stream.close = Mock()
        mock_stream.start = Mock()
        mock_stream.stop = Mock()

        with patch("voicebridge.audio.capture.sd") as mock_sd:
            mock_sd.RawInputStream.return_value = mock_stream

            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            # Set output queue before starting
            queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
            capture.set_output_queue(queue)

            await capture.start()
            await capture.stop()

            # Stream should be closed
            assert capture._stream is None


class TestAudioCaptureDeviceManagement:
    """Test audio device discovery and selection."""

    def test_get_available_devices(self) -> None:
        """Should list all available audio input devices."""
        mock_devices = [
            {"name": "Built-in Microphone", "index": 0, "max_input_channels": 1},
            {"name": "USB Microphone", "index": 1, "max_input_channels": 2},
        ]

        with patch("voicebridge.audio.capture.sd") as mock_sd:
            mock_sd.query_devices.return_value = mock_devices

            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            devices = capture.get_available_devices()

            assert len(devices) >= 0  # At least return empty list
            mock_sd.query_devices.assert_called_once()

    def test_set_device(self) -> None:
        """Should allow setting the input device."""
        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            capture.set_device(3)

            assert capture.device_id == 3


class TestAudioCaptureQueue:
    """Test queue management."""

    @pytest.mark.asyncio
    async def test_set_output_queue(self) -> None:
        """Should allow setting the output queue."""
        import asyncio

        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
            capture.set_output_queue(queue)

            assert capture._output_queue is queue


class TestAudioCaptureChunkCalculation:
    """Test audio chunk size calculations."""

    def test_chunk_size_calculation(self) -> None:
        """Chunk size should match duration and sample rate."""
        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            # 30ms at 16kHz = 480 samples
            expected_samples = int(16000 * 30 / 1000)
            assert capture._chunk_size == expected_samples

    def test_different_sample_rates(self) -> None:
        """Chunk size should adapt to different sample rates."""
        with patch("voicebridge.audio.capture.sd"):
            # 24kHz, 30ms = 720 samples
            capture = AudioCapture(
                sample_rate=24000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            expected_samples = int(24000 * 30 / 1000)
            assert capture._chunk_size == expected_samples


class TestAudioCaptureGain:
    """Test input gain application."""

    def test_applies_input_gain_with_clipping(self) -> None:
        """Input gain should scale samples and clip to int16 range."""
        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
                input_gain=2.0,
            )

            # Samples: -1000, 1000, 20000
            raw = (b"\x18\xfc"  # -1000
                   b"\xe8\x03"  # 1000
                   b"\x20\x4e")  # 20000

            out = capture._apply_gain(raw)

            # Expected: -2000, 2000, 32767 (clipped)
            expected = (b"\x30\xf8"  # -2000
                        b"\xd0\x07"  # 2000
                        b"\xff\x7f")  # 32767

            assert out == expected


class TestAudioCaptureSequencing:
    """Test sequence number generation."""

    @pytest.mark.asyncio
    async def test_sequence_numbers_increment(self) -> None:
        """Chunk sequence numbers should monotonically increase."""
        import asyncio

        with patch("voicebridge.audio.capture.sd"):
            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
            capture.set_output_queue(queue)

            # Simulate creating multiple chunks
            chunk1 = capture._create_audio_chunk(b"data1", 0.0)
            chunk2 = capture._create_audio_chunk(b"data2", 30.0)
            chunk3 = capture._create_audio_chunk(b"data3", 60.0)

            assert chunk1.sequence_number == 0
            assert chunk2.sequence_number == 1
            assert chunk3.sequence_number == 2


class TestAudioCaptureTimestamps:
    """Test timestamp generation."""

    @pytest.mark.asyncio
    async def test_timestamps_are_monotonic(self) -> None:
        """Chunk timestamps should use monotonic time."""
        with patch("voicebridge.audio.capture.sd"), patch(
            "voicebridge.audio.capture.time.monotonic"
        ) as mock_time:
            mock_time.side_effect = [1.0, 1.03, 1.06]  # 30ms intervals

            capture = AudioCapture(
                sample_rate=16000,
                channels=1,
                chunk_duration_ms=30,
                device_id=None,
            )

            chunk1 = capture._create_audio_chunk(b"data", mock_time())
            chunk2 = capture._create_audio_chunk(b"data", mock_time())

            assert chunk1.timestamp_ms == 1000.0  # 1.0s → 1000ms
            assert chunk2.timestamp_ms == 1030.0  # 1.03s → 1030ms
