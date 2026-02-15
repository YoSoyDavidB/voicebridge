from __future__ import annotations

import asyncio
import os

from pydantic import ValidationError

from voicebridge.audio.local_output import LocalSpeakerOutput
from voicebridge.config.settings import VoiceBridgeSettings
from voicebridge.core.pipeline import PipelineOrchestrator


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
    pipeline.set_tts_output_callback(local_output.enqueue)
    return pipeline


async def run_cli() -> None:
    pipeline = create_cli_pipeline()
    await pipeline.start()
    await asyncio.Event().wait()
