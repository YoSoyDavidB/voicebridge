"""Tests for VAD (Voice Activity Detection) processor."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from voicebridge.audio.vad import VADProcessor
from voicebridge.core.models import AudioChunk, VADResult


class TestVADProcessorInitialization:
    """Test VADProcessor initialization."""

    def test_creation_with_config(self) -> None:
        """VADProcessor should be creatable with configuration."""
        mock_model = MagicMock()

        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.min_silence_duration_ms == 300
        assert vad.max_utterance_duration_ms == 15000


class TestVADProcessorSpeechDetection:
    """Test speech detection functionality."""

    @pytest.mark.asyncio
    async def test_detects_speech(self, speech_audio_data: bytes) -> None:
        """VAD should detect speech in audio with speech content."""
        mock_model = MagicMock()
        mock_model.return_value = 0.9  # High confidence speech

        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        chunk = AudioChunk(
            data=speech_audio_data,
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )

        # Process chunk - should detect as speech
        is_speech = vad._is_speech(chunk)
        assert is_speech is True

    @pytest.mark.asyncio
    async def test_ignores_silence(self, silence_audio_data: bytes) -> None:
        """VAD should not detect speech in silence."""
        mock_model = MagicMock()
        mock_model.return_value = 0.1  # Low confidence (silence)

        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        chunk = AudioChunk(
            data=silence_audio_data,
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )

        # Process chunk - should NOT detect as speech
        is_speech = vad._is_speech(chunk)
        assert is_speech is False


class TestVADProcessorUtteranceGrouping:
    """Test utterance grouping and segmentation."""

    def test_groups_continuous_speech(self) -> None:
        """VAD should group continuous speech chunks into one utterance."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        # Add multiple speech chunks
        chunk1 = AudioChunk(
            data=b"speech1",
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )
        chunk2 = AudioChunk(
            data=b"speech2",
            timestamp_ms=30.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=1,
        )

        vad._add_speech_chunk(chunk1)
        vad._add_speech_chunk(chunk2)

        # Should have accumulated both chunks
        assert len(vad._speech_buffer) == 2

    def test_splits_on_silence(self) -> None:
        """VAD should split utterances on sufficient silence."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        # Need speech in buffer first
        vad._speech_buffer = [MagicMock()]
        # Simulate silence longer than min_silence_duration
        vad._silence_duration_ms = 350.0  # More than 300ms

        should_emit = vad._should_emit_utterance()
        assert should_emit is True

    def test_min_silence_duration(self) -> None:
        """VAD should not split on silence shorter than min_silence_duration."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        # Simulate short silence
        vad._silence_duration_ms = 100.0  # Less than 300ms
        vad._speech_buffer = [MagicMock()]  # Has speech

        should_emit = vad._should_emit_utterance()
        assert should_emit is False

    def test_max_utterance_duration(self) -> None:
        """VAD should force-split utterances exceeding max_utterance_duration."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        # Simulate very long utterance
        start_chunk = AudioChunk(
            data=b"start",
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )
        vad._speech_buffer = [start_chunk]
        vad._speech_start_ms = 0.0

        # Current time is way past max duration
        current_timestamp = 16000.0  # 16 seconds

        should_force_emit = vad._should_force_emit(current_timestamp)
        assert should_force_emit is True


class TestVADProcessorVADResult:
    """Test VADResult creation."""

    def test_partial_flag_on_force_split(self) -> None:
        """Force-split VADResult should have is_partial=True."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        chunk = AudioChunk(
            data=b"audio",
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )
        vad._speech_buffer = [chunk]
        vad._speech_start_ms = 0.0

        # Create result with is_partial=True
        result = vad._create_vad_result(is_partial=True)

        assert result.is_partial is True

    def test_confidence_calculation(self) -> None:
        """Confidence should be calculated from speech probabilities."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        chunk = AudioChunk(
            data=b"audio",
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )
        vad._speech_buffer = [chunk]
        vad._speech_start_ms = 0.0
        vad._speech_probabilities = [0.9, 0.95, 0.85]

        result = vad._create_vad_result(is_partial=False)

        # Average of [0.9, 0.95, 0.85] = 0.9
        assert result.confidence == pytest.approx(0.9, abs=0.01)


class TestVADProcessorQueue:
    """Test queue management."""

    @pytest.mark.asyncio
    async def test_set_input_queue(self) -> None:
        """Should allow setting input queue."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
        vad.set_input_queue(queue)

        assert vad._input_queue is queue

    @pytest.mark.asyncio
    async def test_set_output_queue(self) -> None:
        """Should allow setting output queue."""
        mock_model = MagicMock()
        vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
            model=mock_model,
        )

        queue: asyncio.Queue[VADResult] = asyncio.Queue()
        vad.set_output_queue(queue)

        assert vad._output_queue is queue
