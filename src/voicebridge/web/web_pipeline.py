"""Web Pipeline - Pipeline orchestrator for web interface.

Like PipelineOrchestrator but receives audio from WebSocket instead of microphone.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from voicebridge.audio.vad import VADProcessor
from voicebridge.core.models import AudioChunk, TranscriptResult, TranslationResult, TTSAudioResult, VADResult
from voicebridge.services.stt.deepgram_client import DeepgramSTTClient
from voicebridge.services.translation.openai_client import OpenAITranslationClient
from voicebridge.services.tts.elevenlabs_client import ElevenLabsTTSClient

logger = logging.getLogger(__name__)


class WebPipeline:
    """Web Pipeline - processes audio from WebSocket through VAD→STT→Translation→TTS.

    Unlike PipelineOrchestrator, this doesn't use AudioCapture (microphone).
    Instead, it receives AudioChunks from WebSocket via input_queue.

    Audio flows through the pipeline but TTS output is sent back through WebSocket
    instead of being played locally.
    """

    def __init__(self, api_keys: dict[str, Any]) -> None:
        """Initialize Web Pipeline.

        Args:
            api_keys: Dictionary with API keys:
                - deepgram: Deepgram API key
                - openai: OpenAI API key
                - elevenlabs: ElevenLabs API key
                - voiceId: ElevenLabs voice ID
        """
        self._api_keys = api_keys
        self._is_running = False

        # Callback for sending TTS audio back to browser
        self._audio_output_callback: Optional[callable] = None

        # Components
        self._vad: Optional[VADProcessor] = None
        self._stt: Optional[DeepgramSTTClient] = None
        self._translation: Optional[OpenAITranslationClient] = None
        self._tts: Optional[ElevenLabsTTSClient] = None

        # Queues
        self._queue_input: Optional[asyncio.Queue[AudioChunk]] = None
        self._queue_vad_to_stt: Optional[asyncio.Queue[VADResult]] = None
        self._queue_stt_to_translation: Optional[asyncio.Queue[TranscriptResult]] = None
        self._queue_translation_to_tts: Optional[asyncio.Queue[TranslationResult]] = None
        self._queue_tts_output: Optional[asyncio.Queue[TTSAudioResult]] = None

        # Tasks
        self._tasks: list[asyncio.Task[Any]] = []

    def set_audio_output_callback(self, callback: callable) -> None:
        """Set callback for sending TTS audio to browser.

        Args:
            callback: Async function that takes base64 audio string
        """
        self._audio_output_callback = callback

    async def start(self) -> None:
        """Start the web pipeline."""
        if self._is_running:
            logger.warning("Pipeline already running")
            return

        self._is_running = True
        logger.info("Starting web pipeline")

        # Create queues
        self._queue_input = asyncio.Queue(maxsize=500)
        self._queue_vad_to_stt = asyncio.Queue(maxsize=10)
        self._queue_stt_to_translation = asyncio.Queue(maxsize=10)
        self._queue_translation_to_tts = asyncio.Queue(maxsize=10)
        self._queue_tts_output = asyncio.Queue(maxsize=100)

        # Create components
        self._vad = VADProcessor(
            sample_rate=16000,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=300,
            speech_pad_ms=100,
            max_utterance_duration_ms=15000,
        )

        self._stt = DeepgramSTTClient(
            api_key=self._api_keys['deepgram'],
            language='es',
            model='nova-2',
            sample_rate=16000,
        )

        self._translation = OpenAITranslationClient(
            api_key=self._api_keys['openai'],
            model='gpt-4o-mini',
            temperature=0.3,
        )

        self._tts = ElevenLabsTTSClient(
            api_key=self._api_keys['elevenlabs'],
            voice_id=self._api_keys['voiceId'],
            model='eleven_turbo_v2_5',
            stability=0.5,
            similarity_boost=0.75,
            optimize_streaming_latency=4,
            output_sample_rate=22050,
        )

        # Connect queues
        self._vad.set_input_queue(self._queue_input)
        self._vad.set_output_queue(self._queue_vad_to_stt)

        self._stt.set_input_queue(self._queue_vad_to_stt)
        self._stt.set_output_queue(self._queue_stt_to_translation)

        self._translation.set_input_queue(self._queue_stt_to_translation)
        self._translation.set_output_queue(self._queue_translation_to_tts)

        self._tts.set_input_queue(self._queue_translation_to_tts)
        self._tts.set_output_queue(self._queue_tts_output)

        # Start components
        self._tasks = [
            asyncio.create_task(self._vad.start()),
            asyncio.create_task(self._stt.start()),
            asyncio.create_task(self._translation.start()),
            asyncio.create_task(self._tts.start()),
            asyncio.create_task(self._process_tts_output()),
        ]

        logger.info("Web pipeline started successfully")

    async def process_audio_chunk(self, audio_chunk: AudioChunk) -> None:
        """Process incoming audio chunk from WebSocket.

        Args:
            audio_chunk: Audio chunk from browser
        """
        if not self._is_running or not self._queue_input:
            logger.warning("[WebPipeline] Pipeline not running, dropping audio chunk")
            return

        try:
            logger.debug(f"[WebPipeline] Putting chunk in input queue (qsize={self._queue_input.qsize()})")
            await self._queue_input.put(audio_chunk)
            logger.debug(f"[WebPipeline] Chunk added to queue (qsize={self._queue_input.qsize()})")
        except asyncio.QueueFull:
            logger.warning("[WebPipeline] Input queue full, dropping audio chunk")

    async def _process_tts_output(self) -> None:
        """Process TTS output and send to browser via callback."""
        while self._is_running:
            try:
                # Get TTS result from queue
                tts_result = await self._queue_tts_output.get()

                logger.info(f"TTS output received: {len(tts_result.audio_data)} bytes")

                # Send to browser if callback is set
                if self._audio_output_callback:
                    # Convert audio bytes to base64
                    import base64
                    audio_base64 = base64.b64encode(tts_result.audio_data).decode('utf-8')

                    # Call callback to send to browser
                    await self._audio_output_callback(audio_base64)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing TTS output: {e}", exc_info=True)

    async def stop(self) -> None:
        """Stop the web pipeline."""
        if not self._is_running:
            return

        logger.info("Stopping web pipeline")
        self._is_running = False

        # Stop components
        if self._tts:
            await self._tts.stop()
        if self._translation:
            await self._translation.stop()
        if self._stt:
            await self._stt.stop()
        if self._vad:
            await self._vad.stop()

        # Cancel tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        logger.info("Web pipeline stopped")
