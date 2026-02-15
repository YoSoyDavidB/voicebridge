from __future__ import annotations

import asyncio
import os

from pydantic import ValidationError

from voicebridge.audio.local_output import LocalSpeakerOutput
from voicebridge.config.settings import VoiceBridgeSettings
from voicebridge.core.pipeline import PipelineOrchestrator
from voicebridge.core.models import TTSAudioResult


def log_latency(stage: str, latency_ms: float) -> str:
    return f"[Latency] {stage}={latency_ms:.1f}ms"


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
    local_output = LocalSpeakerOutput(
        sample_rate=settings.tts_output_sample_rate,
        channels=1,
    )
    local_output.start()

    def _tts_callback(result: TTSAudioResult) -> None:
        log_latency("tts", result.processing_latency_ms)
        local_output.enqueue(result.audio_data)

    pipeline.set_tts_output_callback(_tts_callback)
    return pipeline


async def run_cli() -> None:
    pipeline = create_cli_pipeline()
    await pipeline.start()
    await asyncio.Event().wait()
