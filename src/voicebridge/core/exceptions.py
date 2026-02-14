"""Custom exception hierarchy for VoiceBridge.

All VoiceBridge exceptions inherit from VoiceBridgeError, making it easy
to catch any VoiceBridge-specific error with a single except clause.
"""

from __future__ import annotations


class VoiceBridgeError(Exception):
    """Base exception for all VoiceBridge errors."""


class ConfigurationError(VoiceBridgeError):
    """Invalid configuration."""


class AudioDeviceError(VoiceBridgeError):
    """Audio device not found or inaccessible."""


class STTError(VoiceBridgeError):
    """Speech-to-text service error."""


class STTConnectionError(STTError):
    """Cannot connect to STT service."""


class STTTimeoutError(STTError):
    """STT processing timed out."""


class TranslationError(VoiceBridgeError):
    """Translation service error."""


class TranslationTimeoutError(TranslationError):
    """Translation timed out."""


class TTSError(VoiceBridgeError):
    """Text-to-speech service error."""


class TTSConnectionError(TTSError):
    """Cannot connect to TTS service."""


class TTSTimeoutError(TTSError):
    """TTS processing timed out."""


class PipelineError(VoiceBridgeError):
    """Pipeline orchestration error."""
