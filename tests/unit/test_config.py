"""Tests for configuration management using Pydantic Settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from voicebridge.config.settings import VoiceBridgeSettings


class TestVoiceBridgeSettings:
    """Test VoiceBridgeSettings configuration."""

    def test_settings_requires_api_keys(self) -> None:
        """Settings should require all API keys."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceBridgeSettings()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        error_fields = {error["loc"][0] for error in errors}

        assert "deepgram_api_key" in error_fields
        assert "openai_api_key" in error_fields
        assert "elevenlabs_api_key" in error_fields
        assert "elevenlabs_voice_id" in error_fields

    def test_settings_with_all_required_fields(self) -> None:
        """Settings should be creatable with all required fields."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="test_deepgram_key",
            openai_api_key="test_openai_key",
            elevenlabs_api_key="test_elevenlabs_key",
            elevenlabs_voice_id="test_voice_id",
        )

        assert settings.deepgram_api_key == "test_deepgram_key"
        assert settings.openai_api_key == "test_openai_key"
        assert settings.elevenlabs_api_key == "test_elevenlabs_key"
        assert settings.elevenlabs_voice_id == "test_voice_id"

    def test_default_tts_model(self) -> None:
        """TTS model should default to eleven_turbo_v2_5."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.tts_model == "eleven_turbo_v2_5"

    def test_default_tts_stability(self) -> None:
        """TTS stability should default to 0.5."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.tts_stability == 0.5

    def test_tts_stability_validation_min(self) -> None:
        """TTS stability should be >= 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceBridgeSettings(
                deepgram_api_key="key",
                openai_api_key="key",
                elevenlabs_api_key="key",
                elevenlabs_voice_id="voice",
                tts_stability=-0.1,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "tts_stability" for error in errors)

    def test_tts_stability_validation_max(self) -> None:
        """TTS stability should be <= 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            VoiceBridgeSettings(
                deepgram_api_key="key",
                openai_api_key="key",
                elevenlabs_api_key="key",
                elevenlabs_voice_id="voice",
                tts_stability=1.1,
            )

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "tts_stability" for error in errors)

    def test_tts_similarity_boost_validation(self) -> None:
        """TTS similarity boost should be between 0 and 1."""
        with pytest.raises(ValidationError):
            VoiceBridgeSettings(
                deepgram_api_key="key",
                openai_api_key="key",
                elevenlabs_api_key="key",
                elevenlabs_voice_id="voice",
                tts_similarity_boost=1.5,
            )

    def test_default_audio_sample_rate(self) -> None:
        """Audio sample rate should default to 16000."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.audio_sample_rate == 16000

    def test_default_stt_provider(self) -> None:
        """STT provider should default to 'deepgram'."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.stt_provider == "deepgram"

    def test_default_stt_language(self) -> None:
        """STT language should default to 'es' (Spanish)."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.stt_language == "es"

    def test_default_translation_model(self) -> None:
        """Translation model should default to 'gpt-4o-mini'."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.translation_model == "gpt-4o-mini"

    def test_translation_temperature_validation(self) -> None:
        """Translation temperature should be between 0 and 2."""
        with pytest.raises(ValidationError):
            VoiceBridgeSettings(
                deepgram_api_key="key",
                openai_api_key="key",
                elevenlabs_api_key="key",
                elevenlabs_voice_id="voice",
                translation_temperature=2.5,
            )

    def test_default_vad_threshold(self) -> None:
        """VAD threshold should default to 0.5."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.vad_threshold == 0.5

    def test_vad_threshold_validation(self) -> None:
        """VAD threshold should be between 0 and 1."""
        with pytest.raises(ValidationError):
            VoiceBridgeSettings(
                deepgram_api_key="key",
                openai_api_key="key",
                elevenlabs_api_key="key",
                elevenlabs_voice_id="voice",
                vad_threshold=1.5,
            )

    def test_default_vad_min_silence_ms(self) -> None:
        """VAD min silence should default to 300ms."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.vad_min_silence_ms == 300

    def test_default_pipeline_passthrough_mode(self) -> None:
        """Pipeline passthrough mode should default to False."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.pipeline_passthrough_mode is False

    def test_default_pipeline_log_level(self) -> None:
        """Pipeline log level should default to 'INFO'."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.pipeline_log_level == "INFO"

    def test_optional_audio_device_ids(self) -> None:
        """Audio device IDs should be optional (None by default)."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )

        assert settings.audio_input_device_id is None
        assert settings.audio_output_device_id is None

    def test_custom_audio_device_ids(self) -> None:
        """Audio device IDs should be settable."""
        settings = VoiceBridgeSettings(
            deepgram_api_key="key",
            openai_api_key="key",
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
            audio_input_device_id=1,
            audio_output_device_id=2,
        )

        assert settings.audio_input_device_id == 1
        assert settings.audio_output_device_id == 2
