"""Core data models for VoiceBridge pipeline.

All models are immutable (frozen) dataclasses with __slots__ for memory efficiency.
This is critical for low-latency performance when processing many audio chunks.
"""

from __future__ import annotations

from typing import Optional

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioChunk:
    """Raw audio chunk from microphone capture.

    Represents a small chunk of PCM audio data (typically 30ms).
    Chunks flow from AudioCapture → VAD processor.
    """

    data: bytes
    timestamp_ms: float
    sample_rate: int
    channels: int
    duration_ms: float
    sequence_number: int


@dataclass(frozen=True)
class VADResult:
    """Voice activity detection result containing speech audio.

    Represents a detected utterance (speech segment).
    Flows from VAD → STT client.
    """

    audio_data: bytes
    start_timestamp_ms: float
    end_timestamp_ms: float
    duration_ms: float
    confidence: float
    is_partial: bool
    sequence_number: int


@dataclass(frozen=True)
class WordInfo:
    """Word-level timing and confidence information.

    Optional metadata from STT services that support word-level timing.
    """

    word: str
    start_ms: float
    end_ms: float
    confidence: float


@dataclass(frozen=True)
class TranscriptResult:
    """Speech-to-text transcription result.

    Contains transcribed text from STT service (Deepgram).
    Flows from STT → Translation client.
    """

    text: str
    is_final: bool
    confidence: float
    start_timestamp_ms: float
    processing_latency_ms: float
    language: str
    words: Optional[list[WordInfo]]
    sequence_number: int


@dataclass(frozen=True)
class TranslationResult:
    """Translation result from Spanish to English.

    Contains both original and translated text.
    Flows from Translation → TTS client.
    """

    original_text: str
    translated_text: str
    start_timestamp_ms: float
    processing_latency_ms: float
    sequence_number: int


@dataclass(frozen=True)
class TTSAudioResult:
    """Synthesized audio from TTS service.

    Contains generated audio in PCM format (24kHz).
    Flows from TTS → Audio output.
    """

    audio_data: bytes
    sample_rate: int
    channels: int
    is_final: bool
    start_timestamp_ms: float
    processing_latency_ms: float
    sequence_number: int
