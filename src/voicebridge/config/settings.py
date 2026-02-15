"""Configuration management using Pydantic Settings.

All configuration values are loaded from environment variables and .env file.
Values are type-validated at startup using Pydantic.
"""

from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VoiceBridgeSettings(BaseSettings):
    """Centralized configuration using Pydantic Settings.

    Values are loaded from environment variables and .env file.
    All API keys are required. Other values have sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── API Keys (Required) ─────────────────────────────────────
    deepgram_api_key: str = Field(..., description="Deepgram API key for STT")
    openai_api_key: str = Field(..., description="OpenAI API key for translation")
    elevenlabs_api_key: str = Field(..., description="ElevenLabs API key for TTS")

    # ─── Voice Configuration ─────────────────────────────────────
    elevenlabs_voice_id: str = Field(..., description="Cloned voice ID from ElevenLabs")
    elevenlabs_model: str = Field(default="eleven_turbo_v2_5", description="TTS model to use")
    tts_stability: float = Field(default=0.5, ge=0.0, le=1.0, description="Voice stability (0-1)")
    tts_similarity_boost: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="How close to original voice (0-1)",
    )
    tts_optimize_streaming_latency: int = Field(
        default=3,
        ge=0,
        le=4,
        description="Optimize streaming latency (0-4, higher = lower latency)",
    )

    # ─── Audio Configuration ─────────────────────────────────────
    audio_input_device_id: Optional[int] = Field(
        default=None,
        description="Input device ID (None = system default)",
    )
    audio_input_gain: float = Field(
        default=1.0,
        ge=0.0,
        description="Input gain multiplier for microphone audio",
    )
    audio_output_device_id: Optional[int] = Field(
        default=None,
        description="Output device ID (None = system default)",
    )
    audio_sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    audio_channels: int = Field(default=1, description="Number of audio channels (1=mono, 2=stereo)")
    audio_chunk_duration_ms: int = Field(default=30, description="Chunk duration in milliseconds")
    output_buffer_size_ms: int = Field(default=50, description="Output buffer size in milliseconds")
    tts_output_sample_rate: int = Field(default=24000, description="TTS output sample rate in Hz")

    # ─── STT Configuration ───────────────────────────────────────
    stt_provider: str = Field(default="deepgram", description="STT provider to use")
    deepgram_language: str = Field(default="es", description="Source language code")
    deepgram_model: str = Field(default="nova-2", description="STT model name")

    # ─── Translation Configuration ───────────────────────────────
    translation_provider: str = Field(default="openai", description="Translation provider")
    openai_model: str = Field(default="gpt-4o-mini", description="Translation model")
    openai_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Translation temperature (0-2)",
    )

    # ─── VAD Configuration ───────────────────────────────────────
    vad_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Speech probability threshold",
    )
    vad_min_speech_duration_ms: int = Field(
        default=250,
        description="Minimum speech duration to consider (ms)",
    )
    vad_min_silence_duration_ms: int = Field(
        default=300,
        description="Minimum silence duration to end utterance (ms)",
    )
    vad_speech_pad_ms: int = Field(
        default=100,
        description="Padding around speech segments (ms)",
    )
    vad_max_utterance_duration_ms: int = Field(
        default=15000,
        description="Maximum utterance duration before force-split (ms)",
    )

    # ─── Pipeline Configuration ──────────────────────────────────
    pipeline_passthrough_mode: bool = Field(
        default=False,
        description="Enable passthrough mode (bypass translation)",
    )
    pipeline_log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    pipeline_metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    pipeline_metrics_interval_seconds: int = Field(
        default=30,
        description="Metrics reporting interval (seconds)",
    )

    # ─── Fallback Configuration ──────────────────────────────────
    fallback_tts_provider: str = Field(
        default="openai",
        description="Fallback TTS provider if ElevenLabs fails",
    )
    fallback_tts_voice: str = Field(
        default="onyx",
        description="Fallback TTS voice (OpenAI)",
    )
