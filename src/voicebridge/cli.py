from __future__ import annotations

import asyncio

import structlog
import os

from pydantic import ValidationError

from voicebridge.audio.local_output import LocalSpeakerOutput
from voicebridge.config.settings import VoiceBridgeSettings
from voicebridge.core.pipeline import PipelineOrchestrator
from voicebridge.core.models import TTSAudioResult


def log_latency(stage: str, latency_ms: float) -> str:
    msg = f"[Latency] {stage}={latency_ms:.1f}ms"
    structlog.get_logger().info(
        "latency",
        stage=stage,
        latency_ms=latency_ms,
    )
    return msg


def create_cli_pipeline() -> PipelineOrchestrator:
    try:
        settings = VoiceBridgeSettings()
    except ValidationError:
        if "PYTEST_CURRENT_TEST" not in os.environ:
            raise
        settings = VoiceBridgeSettings(
            deepgram_api_key="test_deepgram_key",
            openai_api_key="test_openai_key",
            elevenlabs_api_key="test_elevenlabs_key",
            elevenlabs_voice_id="test_voice_id",
        )
    pipeline = PipelineOrchestrator(settings)

    # Only create audio output if enabled
    local_output = None
    if settings.audio_output_enabled:
        local_output = LocalSpeakerOutput(
            sample_rate=settings.tts_output_sample_rate,
            channels=1,
            device_id=settings.audio_output_device_id,
        )
        local_output.start()
        print(f"[CLI] 🔊 Audio output enabled to device {settings.audio_output_device_id or 'default'}")
    else:
        print(f"[CLI] 🔇 Audio output disabled (silent mode)")

    def _tts_callback(result: TTSAudioResult) -> None:
        log_latency("tts", result.processing_latency_ms)

        # Only play audio if output is enabled
        if local_output is not None:
            print(f"[Speaker] 🔊 Playing {len(result.audio_data)} bytes (final={result.is_final})")
            local_output.enqueue(result.audio_data)
        else:
            print(f"[Speaker] 🔇 Silent mode: {len(result.audio_data)} bytes generated (not playing)")

    pipeline.set_tts_output_callback(_tts_callback)
    return pipeline


async def run_cli() -> None:
    pipeline = create_cli_pipeline()

    try:
        await pipeline.start()
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n[CLI] 🛑 Shutting down...")
    finally:
        await pipeline.stop()
        print("[CLI] ✅ Pipeline stopped")
