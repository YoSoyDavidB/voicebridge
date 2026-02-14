"""Tests for core data models."""

from __future__ import annotations

import pytest

from voicebridge.core.models import (
    AudioChunk,
    TranscriptResult,
    TranslationResult,
    TTSAudioResult,
    VADResult,
    WordInfo,
)


class TestAudioChunk:
    """Test AudioChunk data model."""

    def test_creation_with_valid_data(self, sample_audio_data: bytes, sample_rate: int) -> None:
        """AudioChunk should be creatable with valid PCM data."""
        chunk = AudioChunk(
            data=sample_audio_data,
            timestamp_ms=0.0,
            sample_rate=sample_rate,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )

        assert chunk.data == sample_audio_data
        assert chunk.timestamp_ms == 0.0
        assert chunk.sample_rate == sample_rate
        assert chunk.channels == 1
        assert chunk.duration_ms == 30.0
        assert chunk.sequence_number == 0

    def test_frozen_immutability(self, sample_audio_data: bytes) -> None:
        """AudioChunk should be immutable (frozen dataclass)."""
        chunk = AudioChunk(
            data=sample_audio_data,
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )

        with pytest.raises(AttributeError):
            chunk.timestamp_ms = 100.0  # type: ignore[misc]

    def test_has_slots(self, sample_audio_data: bytes) -> None:
        """AudioChunk should use __slots__ for memory efficiency."""
        chunk = AudioChunk(
            data=sample_audio_data,
            timestamp_ms=0.0,
            sample_rate=16000,
            channels=1,
            duration_ms=30.0,
            sequence_number=0,
        )

        assert hasattr(chunk, "__slots__")


class TestVADResult:
    """Test VADResult data model."""

    def test_creation_with_speech_audio(self) -> None:
        """VADResult should contain concatenated speech audio."""
        result = VADResult(
            audio_data=b"audio_bytes",
            start_timestamp_ms=0.0,
            end_timestamp_ms=1000.0,
            duration_ms=1000.0,
            confidence=0.95,
            is_partial=False,
            sequence_number=0,
        )

        assert result.audio_data == b"audio_bytes"
        assert result.start_timestamp_ms == 0.0
        assert result.end_timestamp_ms == 1000.0
        assert result.duration_ms == 1000.0
        assert result.confidence == 0.95
        assert result.is_partial is False
        assert result.sequence_number == 0

    def test_partial_flag_for_long_utterances(self) -> None:
        """VADResult should set is_partial=True when force-split."""
        result = VADResult(
            audio_data=b"long_audio",
            start_timestamp_ms=0.0,
            end_timestamp_ms=15000.0,
            duration_ms=15000.0,
            confidence=0.9,
            is_partial=True,
            sequence_number=0,
        )

        assert result.is_partial is True

    def test_frozen_immutability(self) -> None:
        """VADResult should be immutable."""
        result = VADResult(
            audio_data=b"audio",
            start_timestamp_ms=0.0,
            end_timestamp_ms=1000.0,
            duration_ms=1000.0,
            confidence=0.9,
            is_partial=False,
            sequence_number=0,
        )

        with pytest.raises(AttributeError):
            result.confidence = 0.8  # type: ignore[misc]


class TestWordInfo:
    """Test WordInfo data model."""

    def test_creation(self) -> None:
        """WordInfo should store word-level timing and confidence."""
        word = WordInfo(
            word="hello",
            start_ms=0.0,
            end_ms=500.0,
            confidence=0.99,
        )

        assert word.word == "hello"
        assert word.start_ms == 0.0
        assert word.end_ms == 500.0
        assert word.confidence == 0.99

    def test_frozen_immutability(self) -> None:
        """WordInfo should be immutable."""
        word = WordInfo(
            word="test",
            start_ms=0.0,
            end_ms=100.0,
            confidence=0.95,
        )

        with pytest.raises(AttributeError):
            word.confidence = 0.9  # type: ignore[misc]


class TestTranscriptResult:
    """Test TranscriptResult data model."""

    def test_final_transcript(self) -> None:
        """TranscriptResult with is_final=True should contain complete text."""
        result = TranscriptResult(
            text="Necesitamos revisar el presupuesto",
            is_final=True,
            confidence=0.97,
            start_timestamp_ms=0.0,
            processing_latency_ms=250.0,
            language="es",
            words=None,
            sequence_number=0,
        )

        assert result.text == "Necesitamos revisar el presupuesto"
        assert result.is_final is True
        assert result.confidence == 0.97
        assert result.language == "es"

    def test_latency_tracking(self) -> None:
        """processing_latency_ms should be positive and reasonable."""
        result = TranscriptResult(
            text="test",
            is_final=True,
            confidence=0.9,
            start_timestamp_ms=0.0,
            processing_latency_ms=200.0,
            language="es",
            words=None,
            sequence_number=0,
        )

        assert result.processing_latency_ms > 0
        assert result.processing_latency_ms == 200.0

    def test_with_word_level_info(self) -> None:
        """TranscriptResult can include word-level timing."""
        words = [
            WordInfo(word="hello", start_ms=0.0, end_ms=500.0, confidence=0.99),
            WordInfo(word="world", start_ms=500.0, end_ms=1000.0, confidence=0.98),
        ]

        result = TranscriptResult(
            text="hello world",
            is_final=True,
            confidence=0.98,
            start_timestamp_ms=0.0,
            processing_latency_ms=150.0,
            language="en",
            words=words,
            sequence_number=0,
        )

        assert result.words is not None
        assert len(result.words) == 2
        assert result.words[0].word == "hello"

    def test_frozen_immutability(self) -> None:
        """TranscriptResult should be immutable."""
        result = TranscriptResult(
            text="test",
            is_final=True,
            confidence=0.9,
            start_timestamp_ms=0.0,
            processing_latency_ms=100.0,
            language="es",
            words=None,
            sequence_number=0,
        )

        with pytest.raises(AttributeError):
            result.text = "modified"  # type: ignore[misc]


class TestTranslationResult:
    """Test TranslationResult data model."""

    def test_contains_both_languages(self) -> None:
        """TranslationResult should have both original and translated text."""
        result = TranslationResult(
            original_text="Necesitamos revisar el presupuesto",
            translated_text="We need to review the budget",
            start_timestamp_ms=0.0,
            processing_latency_ms=150.0,
            sequence_number=0,
        )

        assert result.original_text == "Necesitamos revisar el presupuesto"
        assert result.translated_text == "We need to review the budget"
        assert result.processing_latency_ms == 150.0

    def test_frozen_immutability(self) -> None:
        """TranslationResult should be immutable."""
        result = TranslationResult(
            original_text="hola",
            translated_text="hello",
            start_timestamp_ms=0.0,
            processing_latency_ms=100.0,
            sequence_number=0,
        )

        with pytest.raises(AttributeError):
            result.translated_text = "modified"  # type: ignore[misc]


class TestTTSAudioResult:
    """Test TTSAudioResult data model."""

    def test_audio_format(self) -> None:
        """TTSAudioResult should have correct sample_rate and channels."""
        result = TTSAudioResult(
            audio_data=b"audio_bytes",
            sample_rate=24000,
            channels=1,
            is_partial=False,
            start_timestamp_ms=0.0,
            processing_latency_ms=400.0,
            sequence_number=0,
        )

        assert result.sample_rate == 24000
        assert result.channels == 1
        assert result.audio_data == b"audio_bytes"

    def test_partial_streaming_flag(self) -> None:
        """TTSAudioResult should support partial streaming results."""
        result = TTSAudioResult(
            audio_data=b"partial_audio",
            sample_rate=24000,
            channels=1,
            is_partial=True,
            start_timestamp_ms=0.0,
            processing_latency_ms=200.0,
            sequence_number=0,
        )

        assert result.is_partial is True

    def test_frozen_immutability(self) -> None:
        """TTSAudioResult should be immutable."""
        result = TTSAudioResult(
            audio_data=b"audio",
            sample_rate=24000,
            channels=1,
            is_partial=False,
            start_timestamp_ms=0.0,
            processing_latency_ms=300.0,
            sequence_number=0,
        )

        with pytest.raises(AttributeError):
            result.sample_rate = 16000  # type: ignore[misc]
