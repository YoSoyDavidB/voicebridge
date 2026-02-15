"""Pipeline Orchestrator - coordinates all VoiceBridge components.

Manages the lifecycle of the entire audio processing pipeline and connects
all components through asyncio queues.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import asyncio
import inspect
import time

from voicebridge.audio.capture import AudioCapture
from voicebridge.audio.output import AudioOutput
from voicebridge.audio.vad import VADProcessor
from voicebridge.core.models import (
    AudioChunk,
    ComponentStatus,
    PipelineHealth,
    PipelineMetrics,
    TranscriptResult,
    TranslationResult,
    TTSAudioResult,
    VADResult,
)
from voicebridge.services.stt.deepgram_client import DeepgramSTTClient
from voicebridge.services.translation.openai_client import OpenAITranslationClient
from voicebridge.services.tts.elevenlabs_client import ElevenLabsTTSClient


class PipelineOrchestrator:
    """Pipeline Orchestrator.

    Coordinates all VoiceBridge components, manages their lifecycle,
    and monitors system health.
    """

    def __init__(self, settings: Any) -> None:
        """Initialize Pipeline Orchestrator.

        Args:
            settings: VoiceBridgeSettings object with all configuration
        """
        self.settings = settings
        self._is_running = False
        self._start_time = 0.0
        self._utterances_processed = 0

        # Components (will be initialized in start())
        self._audio_capture: Optional[AudioCapture] = None
        self._vad: Optional[VADProcessor] = None
        self._stt: Optional[DeepgramSTTClient] = None
        self._translation: Optional[OpenAITranslationClient] = None
        self._tts: Optional[ElevenLabsTTSClient] = None
        self._audio_output: Optional[AudioOutput] = None

        # Optional callback for TTS output
        self._tts_output_callback: Optional[Callable[[bytes], Any]] = None

        # Queues
        self._queue_capture_to_vad: Optional[asyncio.Queue[AudioChunk]] = None
        self._queue_vad_to_stt: Optional[asyncio.Queue[VADResult]] = None
        self._queue_stt_to_translation: Optional[asyncio.Queue[TranscriptResult]] = None
        self._queue_translation_to_tts: Optional[asyncio.Queue[TranslationResult]] = None
        self._queue_tts_to_output: Optional[asyncio.Queue[TTSAudioResult]] = None

        # Component tasks
        self._tasks: list[asyncio.Task[Any]] = []

    def set_tts_output_callback(self, callback: Callable[[bytes], Any]) -> None:
        """Set callback for TTS audio output.

        Args:
            callback: Function that accepts raw PCM audio bytes
        """
        self._tts_output_callback = callback

    async def start(self) -> None:
        """Start the pipeline.

        Creates all components, connects them with queues, and starts
        processing.
        """
        if self._is_running:
            return

        self._is_running = True
        self._start_time = time.monotonic()

        # Create queues
        # AudioCapture uses run_coroutine_threadsafe to put items from audio thread
        self._queue_capture_to_vad = asyncio.Queue(maxsize=500)  # ~15 seconds buffer
        self._queue_vad_to_stt = asyncio.Queue(maxsize=10)
        self._queue_stt_to_translation = asyncio.Queue(maxsize=10)
        self._queue_translation_to_tts = asyncio.Queue(maxsize=10)
        self._queue_tts_to_output = asyncio.Queue(maxsize=100)  # More buffer for audio playback

        # Create components
        self._audio_capture = AudioCapture(
            sample_rate=self.settings.audio_sample_rate,
            channels=self.settings.audio_channels,
            chunk_duration_ms=self.settings.audio_chunk_duration_ms,
        )

        self._vad = VADProcessor(
            sample_rate=self.settings.audio_sample_rate,
            threshold=self.settings.vad_threshold,
            min_speech_duration_ms=getattr(self.settings, "vad_min_speech_duration_ms", 250),
            min_silence_duration_ms=getattr(self.settings, "vad_min_silence_duration_ms", 300),
            speech_pad_ms=getattr(self.settings, "vad_speech_pad_ms", 100),
            max_utterance_duration_ms=getattr(self.settings, "vad_max_utterance_duration_ms", 15000),
        )

        self._stt = DeepgramSTTClient(
            api_key=self.settings.deepgram_api_key,
            language=self.settings.deepgram_language,
            model=self.settings.deepgram_model,
            sample_rate=self.settings.audio_sample_rate,
        )

        self._translation = OpenAITranslationClient(
            api_key=self.settings.openai_api_key,
            model=self.settings.openai_model,
            temperature=self.settings.openai_temperature,
        )

        self._tts = ElevenLabsTTSClient(
            api_key=self.settings.elevenlabs_api_key,
            voice_id=self.settings.elevenlabs_voice_id,
            model=self.settings.elevenlabs_model,
            stability=self.settings.tts_stability,
            similarity_boost=self.settings.tts_similarity_boost,
            optimize_streaming_latency=self.settings.tts_optimize_streaming_latency,
            output_sample_rate=self.settings.tts_output_sample_rate,
        )

        if self._tts_output_callback is None:
            self._audio_output = AudioOutput(
                sample_rate=self.settings.tts_output_sample_rate,
                channels=1,
                dtype="int16",
                device_id=getattr(self.settings, "output_device_id", None),
                buffer_size_ms=getattr(self.settings, "output_buffer_size_ms", 50),
            )

        # Connect components with queues
        print(f"[Pipeline] 🔗 Connecting components with queues")
        self._audio_capture.set_output_queue(self._queue_capture_to_vad)

        self._vad.set_input_queue(self._queue_capture_to_vad)
        self._vad.set_output_queue(self._queue_vad_to_stt)

        self._stt.set_input_queue(self._queue_vad_to_stt)
        self._stt.set_output_queue(self._queue_stt_to_translation)

        self._translation.set_input_queue(self._queue_stt_to_translation)
        self._translation.set_output_queue(self._queue_translation_to_tts)

        self._tts.set_input_queue(self._queue_translation_to_tts)
        self._tts.set_output_queue(self._queue_tts_to_output)

        if self._audio_output is not None:
            self._audio_output.set_input_queue(self._queue_tts_to_output)

        # Start all components
        self._tasks = [
            asyncio.create_task(self._audio_capture.start()),
            asyncio.create_task(self._vad.start()),
            asyncio.create_task(self._stt.start()),
            asyncio.create_task(self._translation.start()),
            asyncio.create_task(self._tts.start()),
        ]

        if self._audio_output is not None:
            self._tasks.append(asyncio.create_task(self._audio_output.start()))
        else:
            self._tasks.append(asyncio.create_task(self._process_tts_output_callback()))

        # Wait for all tasks
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _process_tts_output_callback(self) -> None:
        """Process TTS output and send to callback when configured."""
        if self._queue_tts_to_output is None:
            return

        while self._is_running:
            try:
                tts_result = await asyncio.wait_for(
                    self._queue_tts_to_output.get(),
                    timeout=0.1,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if self._tts_output_callback is None:
                continue

            try:
                result = self._tts_output_callback(tts_result.audio_data)
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                print(f"Error sending TTS output: {e}")

    async def stop(self) -> None:
        """Stop the pipeline.

        Stops all components in reverse order and cleans up resources.
        """
        if not self._is_running:
            return

        self._is_running = False

        # Stop all components in reverse order
        if self._audio_output:
            await self._audio_output.stop()
        if self._tts:
            await self._tts.stop()
        if self._translation:
            await self._translation.stop()
        if self._stt:
            await self._stt.stop()
        if self._vad:
            await self._vad.stop()
        if self._audio_capture:
            await self._audio_capture.stop()

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks.clear()

    async def health_check(self) -> PipelineHealth:
        """Check pipeline health.

        Returns:
            PipelineHealth with current system status
        """
        uptime = time.monotonic() - self._start_time if self._start_time > 0 else 0.0

        # Build component statuses
        component_statuses = {
            "audio_capture": ComponentStatus(
                name="audio_capture",
                is_running=self._is_running and self._audio_capture is not None,
                queue_depth=self._queue_capture_to_vad.qsize() if self._queue_capture_to_vad else 0,
                last_error=None,
                avg_processing_time_ms=0.0,
            ),
            "vad": ComponentStatus(
                name="vad",
                is_running=self._is_running and self._vad is not None,
                queue_depth=self._queue_vad_to_stt.qsize() if self._queue_vad_to_stt else 0,
                last_error=None,
                avg_processing_time_ms=0.0,
            ),
            "stt": ComponentStatus(
                name="stt",
                is_running=self._is_running and self._stt is not None,
                queue_depth=self._queue_stt_to_translation.qsize() if self._queue_stt_to_translation else 0,
                last_error=None,
                avg_processing_time_ms=0.0,
            ),
            "translation": ComponentStatus(
                name="translation",
                is_running=self._is_running and self._translation is not None,
                queue_depth=self._queue_translation_to_tts.qsize() if self._queue_translation_to_tts else 0,
                last_error=None,
                avg_processing_time_ms=0.0,
            ),
            "tts": ComponentStatus(
                name="tts",
                is_running=self._is_running and self._tts is not None,
                queue_depth=self._queue_tts_to_output.qsize() if self._queue_tts_to_output else 0,
                last_error=None,
                avg_processing_time_ms=0.0,
            ),
            "audio_output": ComponentStatus(
                name="audio_output",
                is_running=self._is_running and self._audio_output is not None,
                queue_depth=0,
                last_error=None,
                avg_processing_time_ms=0.0,
            ),
        }

        return PipelineHealth(
            is_healthy=self._is_running,
            component_statuses=component_statuses,
            uptime_seconds=uptime,
            total_utterances_processed=self._utterances_processed,
            average_latency_ms=0.0,  # TODO: Calculate from metrics
        )

    def get_metrics(self) -> PipelineMetrics:
        """Get pipeline performance metrics.

        Returns:
            PipelineMetrics with current performance data
        """
        queue_depths = {
            "capture_to_vad": self._queue_capture_to_vad.qsize() if self._queue_capture_to_vad else 0,
            "vad_to_stt": self._queue_vad_to_stt.qsize() if self._queue_vad_to_stt else 0,
            "stt_to_translation": self._queue_stt_to_translation.qsize() if self._queue_stt_to_translation else 0,
            "translation_to_tts": self._queue_translation_to_tts.qsize() if self._queue_translation_to_tts else 0,
            "tts_to_output": self._queue_tts_to_output.qsize() if self._queue_tts_to_output else 0,
        }

        return PipelineMetrics(
            total_latency_ms=0.0,  # TODO: Calculate from component latencies
            capture_latency_ms=0.0,
            vad_latency_ms=0.0,
            stt_latency_ms=0.0,
            translation_latency_ms=0.0,
            tts_latency_ms=0.0,
            output_latency_ms=0.0,
            queue_depths=queue_depths,
            timestamp=time.monotonic(),
        )
