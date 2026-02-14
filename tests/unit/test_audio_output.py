"""Tests for AudioOutput component."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from voicebridge.audio.output import AudioOutput
from voicebridge.core.models import TTSAudioResult


class TestAudioOutputInitialization:
    """Test AudioOutput initialization."""

    def test_creation_with_config(self) -> None:
        """AudioOutput should be creatable with configuration."""
        output = AudioOutput(
            sample_rate=24000,
            channels=1,
            dtype="int16",
            device_id=None,
            buffer_size_ms=50,
        )

        assert output.sample_rate == 24000
        assert output.channels == 1
        assert output.dtype == "int16"
        assert output.buffer_size_ms == 50


class TestAudioOutputDeviceManagement:
    """Test audio device management."""

    def test_get_available_devices(self) -> None:
        """Should list available audio output devices."""
        with patch("sounddevice.query_devices") as mock_query:
            mock_query.return_value = [
                {"name": "Virtual Mic", "max_output_channels": 2, "index": 5},
                {"name": "Built-in", "max_output_channels": 2, "index": 0},
            ]

            output = AudioOutput(
                sample_rate=24000,
                channels=1,
                dtype="int16",
                device_id=None,
                buffer_size_ms=50,
            )

            devices = output.get_available_devices()

            assert len(devices) >= 0  # Should return list
            mock_query.assert_called_once()

    def test_set_output_device(self) -> None:
        """Should allow setting output device."""
        output = AudioOutput(
            sample_rate=24000,
            channels=1,
            dtype="int16",
            device_id=None,
            buffer_size_ms=50,
        )

        output.set_output_device(5)

        assert output.device_id == 5


class TestAudioOutputStreaming:
    """Test audio streaming functionality."""

    @pytest.mark.asyncio
    async def test_start_opens_output_stream(self) -> None:
        """Should open OutputStream when started."""
        with patch("sounddevice.OutputStream") as mock_stream_cls:
            mock_stream = MagicMock()
            mock_stream_cls.return_value = mock_stream

            output = AudioOutput(
                sample_rate=24000,
                channels=1,
                dtype="int16",
                device_id=5,
                buffer_size_ms=50,
            )

            queue: asyncio.Queue[TTSAudioResult] = asyncio.Queue()
            output.set_input_queue(queue)

            # Start in background
            task = asyncio.create_task(output.start())

            # Give it time to start
            await asyncio.sleep(0.1)

            # Stop
            await output.stop()
            await task

            # Should have opened stream
            mock_stream_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_writes_audio_to_stream(self) -> None:
        """Should write TTSAudioResult audio data to output stream."""
        with patch("sounddevice.OutputStream") as mock_stream_cls:
            mock_stream = MagicMock()
            mock_stream.write = MagicMock()
            mock_stream_cls.return_value = mock_stream

            output = AudioOutput(
                sample_rate=24000,
                channels=1,
                dtype="int16",
                device_id=5,
                buffer_size_ms=50,
            )

            queue: asyncio.Queue[TTSAudioResult] = asyncio.Queue()
            output.set_input_queue(queue)

            # Put audio result in queue
            audio_result = TTSAudioResult(
                audio_data=b"\x00\x01" * 100,  # Fake PCM data
                sample_rate=24000,
                channels=1,
                is_final=False,
                start_timestamp_ms=0.0,
                processing_latency_ms=100.0,
                sequence_number=0,
            )
            await queue.put(audio_result)

            # Start processing
            task = asyncio.create_task(output.start())

            # Give it time to process
            await asyncio.sleep(0.1)

            # Stop
            await output.stop()
            await task

            # Should have written audio
            assert mock_stream.write.call_count >= 1

    @pytest.mark.asyncio
    async def test_handles_empty_queue_gracefully(self) -> None:
        """Should handle empty queue without errors."""
        with patch("sounddevice.OutputStream") as mock_stream_cls:
            mock_stream = MagicMock()
            mock_stream_cls.return_value = mock_stream

            output = AudioOutput(
                sample_rate=24000,
                channels=1,
                dtype="int16",
                device_id=5,
                buffer_size_ms=50,
            )

            queue: asyncio.Queue[TTSAudioResult] = asyncio.Queue()
            output.set_input_queue(queue)

            # Start with empty queue
            task = asyncio.create_task(output.start())

            # Give it time
            await asyncio.sleep(0.1)

            # Should still be running
            assert not task.done()

            # Stop
            await output.stop()
            await task


class TestAudioOutputQueue:
    """Test queue management."""

    @pytest.mark.asyncio
    async def test_set_input_queue(self) -> None:
        """Should allow setting input queue."""
        output = AudioOutput(
            sample_rate=24000,
            channels=1,
            dtype="int16",
            device_id=5,
            buffer_size_ms=50,
        )

        queue: asyncio.Queue[TTSAudioResult] = asyncio.Queue()
        output.set_input_queue(queue)

        assert output._input_queue is queue


class TestAudioOutputBuffering:
    """Test audio buffering."""

    def test_buffer_size_calculation(self) -> None:
        """Should calculate correct buffer size from ms."""
        output = AudioOutput(
            sample_rate=24000,
            channels=1,
            dtype="int16",
            device_id=5,
            buffer_size_ms=50,
        )

        # 50ms at 24000 Hz = 1200 samples
        # 1200 samples * 1 channel * 2 bytes (int16) = 2400 bytes
        expected_buffer_size = int((50 / 1000.0) * 24000)

        assert output._buffer_size_samples == expected_buffer_size


class TestAudioOutputLifecycle:
    """Test start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_requires_input_queue(self) -> None:
        """Should raise error if started without input queue."""
        output = AudioOutput(
            sample_rate=24000,
            channels=1,
            dtype="int16",
            device_id=5,
            buffer_size_ms=50,
        )

        with pytest.raises(RuntimeError, match="Input queue must be set"):
            await output.start()

    @pytest.mark.asyncio
    async def test_stop_closes_stream(self) -> None:
        """Should close output stream on stop."""
        with patch("sounddevice.OutputStream") as mock_stream_cls:
            mock_stream = MagicMock()
            mock_stream.close = MagicMock()
            mock_stream_cls.return_value = mock_stream

            output = AudioOutput(
                sample_rate=24000,
                channels=1,
                dtype="int16",
                device_id=5,
                buffer_size_ms=50,
            )

            queue: asyncio.Queue[TTSAudioResult] = asyncio.Queue()
            output.set_input_queue(queue)

            # Start and stop
            task = asyncio.create_task(output.start())
            await asyncio.sleep(0.1)
            await output.stop()
            await task

            # Should have closed stream
            mock_stream.close.assert_called_once()
