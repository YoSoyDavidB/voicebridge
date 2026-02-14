"""Tests for custom exception hierarchy."""

from __future__ import annotations

import pytest

from voicebridge.core.exceptions import (
    AudioDeviceError,
    ConfigurationError,
    PipelineError,
    STTConnectionError,
    STTError,
    STTTimeoutError,
    TranslationError,
    TranslationTimeoutError,
    TTSConnectionError,
    TTSError,
    TTSTimeoutError,
    VoiceBridgeError,
)


class TestExceptionHierarchy:
    """Test custom exception hierarchy."""

    def test_base_exception_is_exception(self) -> None:
        """VoiceBridgeError should inherit from Exception."""
        assert issubclass(VoiceBridgeError, Exception)

    def test_base_exception_can_be_raised(self) -> None:
        """VoiceBridgeError should be raiseable with a message."""
        with pytest.raises(VoiceBridgeError, match="test error"):
            raise VoiceBridgeError("test error")

    def test_configuration_error_inherits_from_base(self) -> None:
        """ConfigurationError should inherit from VoiceBridgeError."""
        assert issubclass(ConfigurationError, VoiceBridgeError)

    def test_audio_device_error_inherits_from_base(self) -> None:
        """AudioDeviceError should inherit from VoiceBridgeError."""
        assert issubclass(AudioDeviceError, VoiceBridgeError)

    def test_stt_error_inherits_from_base(self) -> None:
        """STTError should inherit from VoiceBridgeError."""
        assert issubclass(STTError, VoiceBridgeError)

    def test_stt_connection_error_inherits_from_stt_error(self) -> None:
        """STTConnectionError should inherit from STTError."""
        assert issubclass(STTConnectionError, STTError)

    def test_stt_timeout_error_inherits_from_stt_error(self) -> None:
        """STTTimeoutError should inherit from STTError."""
        assert issubclass(STTTimeoutError, STTError)

    def test_translation_error_inherits_from_base(self) -> None:
        """TranslationError should inherit from VoiceBridgeError."""
        assert issubclass(TranslationError, VoiceBridgeError)

    def test_translation_timeout_error_inherits_from_translation_error(self) -> None:
        """TranslationTimeoutError should inherit from TranslationError."""
        assert issubclass(TranslationTimeoutError, TranslationError)

    def test_tts_error_inherits_from_base(self) -> None:
        """TTSError should inherit from VoiceBridgeError."""
        assert issubclass(TTSError, VoiceBridgeError)

    def test_tts_connection_error_inherits_from_tts_error(self) -> None:
        """TTSConnectionError should inherit from TTSError."""
        assert issubclass(TTSConnectionError, TTSError)

    def test_tts_timeout_error_inherits_from_tts_error(self) -> None:
        """TTSTimeoutError should inherit from TTSError."""
        assert issubclass(TTSTimeoutError, TTSError)

    def test_pipeline_error_inherits_from_base(self) -> None:
        """PipelineError should inherit from VoiceBridgeError."""
        assert issubclass(PipelineError, VoiceBridgeError)


class TestExceptionMessages:
    """Test exception messages and string representation."""

    def test_base_exception_message(self) -> None:
        """VoiceBridgeError should store and display message."""
        error = VoiceBridgeError("custom message")
        assert str(error) == "custom message"

    def test_configuration_error_message(self) -> None:
        """ConfigurationError should store message."""
        error = ConfigurationError("invalid config")
        assert str(error) == "invalid config"

    def test_audio_device_error_message(self) -> None:
        """AudioDeviceError should store message."""
        error = AudioDeviceError("device not found")
        assert str(error) == "device not found"

    def test_stt_connection_error_message(self) -> None:
        """STTConnectionError should store message."""
        error = STTConnectionError("websocket failed")
        assert str(error) == "websocket failed"

    def test_translation_timeout_error_message(self) -> None:
        """TranslationTimeoutError should store message."""
        error = TranslationTimeoutError("timeout after 5s")
        assert str(error) == "timeout after 5s"


class TestExceptionCatching:
    """Test exception catching behavior."""

    def test_catch_specific_exception(self) -> None:
        """Specific exceptions should be catchable."""
        with pytest.raises(STTConnectionError):
            raise STTConnectionError("connection failed")

    def test_catch_parent_exception(self) -> None:
        """Child exceptions should be catchable by parent type."""
        with pytest.raises(STTError):
            raise STTConnectionError("connection failed")

    def test_catch_base_exception(self) -> None:
        """All custom exceptions should be catchable by base type."""
        with pytest.raises(VoiceBridgeError):
            raise TTSTimeoutError("timeout")

    def test_different_exception_types_not_caught(self) -> None:
        """Different exception types should not catch each other."""
        with pytest.raises(STTError):
            try:
                raise STTError("stt error")
            except TTSError:
                pytest.fail("Should not catch STTError as TTSError")
